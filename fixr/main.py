import re
import sys
from pathlib import Path

import click
import httpx
import typer
from rich.console import Console
from rich.markup import escape
from rich.syntax import Syntax

from . import cache, config as cfg, llm, runner

app = typer.Typer(
    help="fixr — paste an error or a script file, get a fix. `fxr <error|file>` is shorthand for `fxr fix`.",
    add_completion=False,
    pretty_exceptions_show_locals=False,  # never dump locals (API keys) in a crash
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()

COMMANDS = {"fix", "config", "providers", "models", "clear-cache", "setup"}
SECTIONS = ("ERROR TYPE", "SEVERITY", "EXPLANATION", "ROOT CAUSE", "FIX", "PREVENTION")
HEADER = re.compile(rf"^({'|'.join(SECTIONS)}):[ \t]*", re.M)
INLINE = {"ERROR TYPE": "bold red", "SEVERITY": "bold yellow"}
NETWORK_ERRORS = (ValueError, RuntimeError, httpx.HTTPError)


def fail(msg: str):
    console.print(f"[bold red]✗[/bold red] {escape(msg)}")
    raise typer.Exit(1)


def _describe(e: Exception) -> str:
    return f"{type(e).__name__}: {e}" if isinstance(e, httpx.HTTPError) else str(e)


def _display(text: str, cached: bool = False) -> None:
    parts = HEADER.split(text)  # [preamble, name, body, name, body, ...]
    console.print()
    console.rule("[green]fixr ⚡ cached[/green]" if cached else "[cyan]fixr[/cyan]")
    if len(parts) < 3:  # model ignored the format — show it raw instead of nothing
        console.print(escape(text))
    for name, body in zip(parts[1::2], parts[2::2]):
        body = body.strip()
        if name in INLINE:
            console.print(f"[{INLINE[name]}]{name}:[/] {escape(body)}")
            continue
        console.print(f"\n[bold cyan]● {name}[/bold cyan]")
        code = re.search(r"```(\w*)\n(.*?)```", body, re.S) if name == "FIX" else None
        if code:
            console.print(Syntax(code[2].strip(), code[1] or "text", theme="dracula", line_numbers=True))
        else:
            console.print(escape(body), style="green" if name == "PREVENTION" else "")
    console.rule()
    console.print()


def _target(provider: str, model: str) -> tuple[str, str]:
    conf = cfg.load()
    default = conf.get("provider")
    provider = provider or default
    if not provider:
        fail("Not configured. Run: fxr setup")
    if provider not in cfg.PROVIDERS:
        fail(f"Unknown provider '{provider}'. Run: fxr providers")
    model = model or (conf.get("model") if provider == default else None)
    if not model:
        fail(f"No model set for {provider}. See: fxr models -p {provider}, then pass -m MODEL")
    return provider, model


def _is_file(s: str) -> bool:
    try:
        return "\n" not in s and len(s) < 260 and Path(s).is_file()
    except (OSError, ValueError):
        return False


@app.command(help="Explain an error (text, stdin, or a script file) and suggest a fix.")
def fix(
    error: str = typer.Argument(None, help="Error text or path to a script to run"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model id"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache lookup"),
):
    text = error
    if text is None:
        text = sys.stdin.read() if not sys.stdin.isatty() else typer.prompt("Paste your error")
    text = text.strip()
    if not text:
        fail("Nothing to analyze.")

    if _is_file(text):
        try:
            text = runner.run_file(Path(text))
        except runner.RunnerError as e:
            fail(str(e))
        if text is None:
            console.print("[green]✓ Script ran without errors.[/green]")
            return

    provider, model = _target(provider, model)
    model_id = f"{provider}/{model}"
    if not no_cache and (hit := cache.get(text, model_id)):
        return _display(hit, cached=True)

    try:
        with console.status("[cyan]Analyzing...[/cyan]"):
            solution = llm.ask(text, provider, model)
    except NETWORK_ERRORS as e:
        fail(_describe(e))
    if not solution:
        fail("The model returned an empty response. Try another model: fxr models")
    cache.put(text, model_id, solution)
    _display(solution)


@app.command()
def config(
    provider: str = typer.Option(None, "--provider", "-p", help="Set default provider"),
    model: str = typer.Option(None, "--model", "-m", help="Set default model"),
    api_key: str = typer.Option(None, "--api-key", "-k", help="Set API key (for --provider, or the default)"),
    show: bool = typer.Option(False, "--show", help="Show current config"),
):
    """Configure default provider, model, and API keys."""
    conf = cfg.load()
    if show:
        keys = {p: "…" + k[-4:] for p, k in conf["api_keys"].items() if k}
        console.print(f"Provider: [cyan]{conf.get('provider')}[/cyan]\nModel:    [cyan]{conf.get('model')}[/cyan]\nKeys:     {keys}")
        return
    target = provider or conf.get("provider")
    if target not in cfg.PROVIDERS:
        fail("Give a valid --provider (see: fxr providers)")
    if api_key:
        conf["api_keys"][target] = api_key
    if provider:
        if provider != conf.get("provider") and not model:
            conf.pop("model", None)  # old model belongs to the old provider
        conf["provider"] = provider
    if model:
        conf["model"] = model
    cfg.save(conf)
    console.print(f"[green]✓[/green] Saved. Default: {conf.get('provider')} / {conf.get('model')}")


@app.command()
def providers():
    """List supported providers (✓ = ready to use)."""
    for p, (_, env, free) in cfg.PROVIDERS.items():
        ready = "✓" if cfg.get_key(p) or not env else " "
        console.print(f"  {ready} [cyan]{p:<11}[/cyan] {'free tier' if free else 'paid'}")


@app.command()
def models(provider: str = typer.Option(None, "--provider", "-p", help="Provider (default: current)")):
    """List the models a provider currently serves (live from its API)."""
    provider = provider or cfg.load().get("provider")
    if provider not in cfg.PROVIDERS:
        fail("Give a valid --provider (see: fxr providers)")
    try:
        for m in llm.list_models(provider):
            console.print(m, markup=False, highlight=False)
    except NETWORK_ERRORS as e:
        fail(_describe(e))


@app.command(name="clear-cache")
def clear_cache():
    """Clear the local error cache."""
    console.print(f"[green]✓[/green] Cleared {cache.clear()} cached entries.")


def _pick(label: str, options: list) -> str:
    for i, o in enumerate(options, 1):
        console.print(f"  {i}. {o}", markup=False, highlight=False)
    return options[typer.prompt(label, type=click.IntRange(1, len(options)), default=1) - 1]


@app.command()
def setup():
    """Interactive setup: provider → API key → model (fetched live)."""
    provider = _pick("Provider", list(cfg.PROVIDERS))
    conf = cfg.load()
    if cfg.PROVIDERS[provider][1]:
        key = typer.prompt(f"{provider} API key (blank = keep current / use env var)",
                           hide_input=True, default="", show_default=False).strip()
        if key:
            conf["api_keys"][provider] = key
    conf["provider"] = provider
    conf.pop("model", None)
    cfg.save(conf)  # saved first so the model lookup can use the key

    try:
        available = llm.list_models(provider)
    except NETWORK_ERRORS as e:
        console.print(f"[yellow]Couldn't fetch models: {escape(_describe(e))}[/yellow]")
        available = []
    if len(available) > 25:
        q = typer.prompt("Filter models (text; blank = first 25)", default="", show_default=False).lower()
        available = [m for m in available if q in m.lower()][:25]
    conf["model"] = _pick("Model", available) if available else typer.prompt("Model id")
    cfg.save(conf)
    console.print(f"[green]✓[/green] Ready: {provider} / {conf['model']}. Try: fxr script.py")


def cli():
    # Bare `fxr <error|file>` and `fxr -p groq "..."` → `fxr fix ...`
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS | {"-h", "--help"}:
        sys.argv.insert(1, "fix")
    app()
