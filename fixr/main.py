import sys
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import cache, llm, auth, config as cfg
from .llm import PROVIDER_MODELS

app = typer.Typer(help="fixr — AI error explainer with smart caching")
console = Console()


def _read_stdin() -> str | None:
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return None

def _run_fix(err: str, provider=None, model=None, no_cache=False):
    if not no_cache:
        cached = cache.get(err)
        if cached:
            _display(cached, cached=True)
            return
    with console.status("[cyan]Analyzing error...[/cyan]"):
        try:
            solution = llm.ask(err, provider=provider, model=model)
        except ValueError as e:
            console.print(f"[bold red]✗ Config error:[/bold red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[bold red]✗ LLM error:[/bold red] {e}")
            raise typer.Exit(1)


def _display(solution: str, cached: bool = False):
    from rich.syntax import Syntax
    from rich.rule import Rule
    import re

    title = "[green]fixr ⚡ cached[/green]" if cached else "[cyan]fixr[/cyan]"
    console.print()
    console.rule(f"[bold]{title}[/bold]")

    # Extract and style each section
    sections = {
        "ERROR TYPE": "bold red",
        "SEVERITY": "bold yellow",
        "EXPLANATION": "white",
        "ROOT CAUSE": "bold white",
        "FIX": None,  # handled separately for code
        "PREVENTION": "green",
    }

    current = solution
    for section, style in sections.items():
        pattern = rf"{section}:\n?(.*?)(?=\n[A-Z ]+:|$)"
        match = re.search(pattern, current, re.DOTALL)
        if not match:
            continue
        content = match.group(1).strip()

        if section == "FIX":
            console.print(f"\n[bold cyan]● FIX[/bold cyan]")
            # extract code block
            code_match = re.search(r"```(?:\w+)?\n?(.*?)```", content, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
                syntax = Syntax(code, "python", theme="dracula", line_numbers=True)
                console.print(syntax)
            else:
                console.print(content)
        elif section in ("ERROR TYPE", "SEVERITY"):
            console.print(f"[{style}]{section}:[/{style}] {content}")
        else:
            console.print(f"\n[bold cyan]● {section}[/bold cyan]")
            console.print(f"[{style}]{content}[/{style}]")

    console.rule()
    console.print()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """fixr — paste an error or a script file, get a fix."""
    if ctx.invoked_subcommand is not None:
        return

    stdin_error = _read_stdin()
    if stdin_error:
        _run_fix(stdin_error)
        return
    console.print("[yellow]Usage: fxr 'error message'  or  fxr script.py[/yellow]")

@app.command(name="fix", help="Explain an error and suggest a fix.")
def fix(
    error: str = typer.Argument(None, help="Error string to analyze"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model string"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache lookup"),
):
    stdin_error = _read_stdin()
    err = stdin_error or error
    if not err:
        err = typer.prompt("Paste your error")
    _run_fix(err, provider=provider, model=model, no_cache=no_cache)


@app.command()
def config(
    provider: str = typer.Option(None, "--provider", "-p", help="Set default provider"),
    model: str = typer.Option(None, "--model", "-m", help="Set default model"),
    api_key: str = typer.Option(None, "--api-key", "-k", help="Set API key for provider"),
    show: bool = typer.Option(False, "--show", help="Show current config"),
):
    """Configure default provider, model, and API keys."""
    if show:
        c = cfg.load()
        keys = {k: v[:8] + "..." for k, v in c.get("api_keys", {}).items() if v}
        console.print(Panel(
            f"Provider: [cyan]{c.get('provider')}[/cyan]\n"
            f"Model:    [cyan]{c.get('model')}[/cyan]\n"
            f"Keys:     {keys}",
            title="fixr config"
        ))
        return
    if api_key and provider:
        auth.set_api_key(provider, api_key)
        console.print(f"[green]✓[/green] API key saved for [cyan]{provider}[/cyan]")
    if provider or model:
        p = provider or cfg.load().get("provider", "groq")
        m = model or PROVIDER_MODELS.get(p, "groq/llama-3.3-70b-versatile")
        cfg.set_default(p, m)
        console.print(f"[green]✓[/green] Default set to [cyan]{p}[/cyan] / [cyan]{m}[/cyan]")


@app.command()
def login(
    provider: str = typer.Argument(..., help="Provider to OAuth login (e.g. google)"),
):
    """Login via OAuth (browser-based). Currently supports: google."""
    try:
        url = auth.oauth_login(provider)
        console.print(f"[cyan]Browser opened.[/cyan] If not, visit:\n{url}")
        code = typer.prompt("Paste the auth code here")
        auth.save_oauth_token(provider, code)
        console.print(f"[green]✓[/green] Token saved for [cyan]{provider}[/cyan]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def providers():
    """List all supported providers and their default models."""
    console.print("\n[bold]Supported Providers[/bold]\n")
    free = {"groq", "gemini", "mistral", "openrouter", "nvidia", "cerebras"}
    for p, m in PROVIDER_MODELS.items():
        tier = "[green]free tier[/green]" if p in free else "[yellow]paid[/yellow]"
        console.print(f"  [cyan]{p:<12}[/cyan] {tier:<20} {m}")
    console.print()


@app.command()
def clear_cache():
    """Clear the local error cache."""
    n = cache.clear()
    console.print(f"[green]✓[/green] Cleared {n} cached entries.")


@app.command()
def setup():
    """Interactive setup wizard."""
    console.print("\n[bold cyan]fxr setup[/bold cyan]\n")

    providers_list = list(PROVIDER_MODELS.keys())
    free = {"groq", "gemini", "mistral", "openrouter", "cerebras", "ollama", "nvidia"}
    for i, p in enumerate(providers_list):
        tier = "[green]free[/green]" if p in free else "[yellow]paid[/yellow]"
        console.print(f"  {i+1}. {p} ({tier})")

    choice = typer.prompt("\nSelect provider number", default="1")
    provider = providers_list[int(choice) - 1]

    models = cfg.get_models(provider)
    console.print(f"\n[bold]Models for {provider}:[/bold]")
    for i, m in enumerate(models):
        console.print(f"  {i+1}. {m}")
    console.print(f"  {len(models)+1}. Enter custom model")

    mchoice = typer.prompt("Select model number", default="1")
    midx = int(mchoice) - 1
    if midx == len(models):
        model = typer.prompt("Enter model string")
        cfg.add_model(provider, model)
    else:
        model = models[midx]

    api_key = typer.prompt(f"\nPaste your {provider} API key", hide_input=True)
    auth.set_api_key(provider, api_key)
    cfg.set_default(provider, model)
    console.print(f"\n[green]✓[/green] Config saved — {provider} / {model}")
    console.print("\n[bold #50fa7b]✓ Setup complete! Run: fxr \"your error\" or fxr script.py[/bold #50fa7b]")


@app.command(name="add-model")
def add_model_cmd(
    provider: str = typer.Argument(..., help="Provider name"),
    model: str = typer.Argument(..., help="Model string"),
):
    """Add a custom model to a provider's list."""
    cfg.add_model(provider, model)
    console.print(f"[green]✓[/green] Added [cyan]{model}[/cyan] to [cyan]{provider}[/cyan]")

def cli():
    known = {"fix", "config", "login", "providers", "clear-cache", "setup", "add-model", "--help", "-h"}
    if len(sys.argv) > 1 and sys.argv[1] not in known and not sys.argv[1].startswith("--"):
        sys.argv.insert(1, "fix")
    app()
