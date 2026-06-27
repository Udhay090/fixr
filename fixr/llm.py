import os
from . import config as cfg

PROVIDER_MODELS = {
    "groq":       "groq/llama-3.3-70b-versatile",
    "gemini":     "gemini/gemini-2.0-flash",
    "mistral":    "mistral/mistral-small-latest",
    "openai":     "openai/gpt-4o-mini",
    "anthropic":  "anthropic/claude-haiku-4-5-20251001",
    "ollama":     "ollama/llama3",
    "openrouter": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "nvidia":     "nvidia_nim/meta/llama-3.3-70b-instruct",
    "cerebras":   "cerebras/llama3.3-70b",
    "cohere":     "cohere/command-r-plus",
}

PROVIDER_ENV_KEYS = {
    "groq":       "GROQ_API_KEY",
    "gemini":     "GEMINI_API_KEY",
    "mistral":    "MISTRAL_API_KEY",
    "openai":     "OPENAI_API_KEY",
    "anthropic":  "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "nvidia":     "NVIDIA_NIM_API_KEY",
    "cerebras":   "CEREBRAS_API_KEY",
    "cohere":     "COHERE_API_KEY",
}

PROMPT = """\
You are a senior software engineer. Analyze the error below. Be precise, technical, and concise.

Respond in EXACTLY this format — no extra text, no deviation:

ERROR TYPE: <NameError | TypeError | SyntaxError | ImportError | RuntimeError | LogicError | Other>
SEVERITY: <Critical | High | Medium | Low>

EXPLANATION:
<2 sentences max. Name the exact variable, line, or function. Say WHY it failed, not just what failed.>

ROOT CAUSE:
<1 sentence. The single deepest technical reason.>

FIX:
```python
<minimal working code that fixes the issue>
```

PREVENTION:
<1 sentence. Actionable rule. Start with "Always" or "Never".>

ERROR:
{error}
"""

def resolve_key(provider: str) -> str | None:
    """Check config store first, then env var."""
    key = cfg.get_key(provider)
    if key:
        return key
    env = PROVIDER_ENV_KEYS.get(provider)
    return os.environ.get(env) if env else None

def _set_env_key(provider: str, key: str) -> None:
    env = PROVIDER_ENV_KEYS.get(provider)
    if env and key:
        os.environ[env] = key

def ask(error: str, provider: str | None = None, model: str | None = None) -> str:
    from litellm import completion

    conf = cfg.load()
    provider = provider or conf.get("provider", "groq")
    model = model or conf.get("model") or PROVIDER_MODELS.get(provider, "groq/llama-3.3-70b-versatile")

    key = resolve_key(provider)
    if not key:
        raise ValueError(
            f"No API key found for '{provider}'.\n"
            f"Run: fxr config --provider {provider} --api-key YOUR_KEY\n"
            f"Or:  fxr setup"
        )
    _set_env_key(provider, key)



    resp = completion(
        model=model,
        messages=[{"role": "user", "content": PROMPT.format(error=error.strip())}],
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()
