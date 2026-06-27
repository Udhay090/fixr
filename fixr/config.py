import json
from pathlib import Path

FIXR_DIR = Path.home() / ".fixr"
CONFIG_FILE = FIXR_DIR / "config.json"

DEFAULTS = {
    "provider": "groq",
    "model": "groq/llama-3.3-70b-versatile",
    "api_keys": {},
    "auth_tokens": {},
}

def load() -> dict:
    FIXR_DIR.mkdir(exist_ok=True)
    if not CONFIG_FILE.exists():
        save(DEFAULTS.copy())
        return DEFAULTS.copy()
    return json.loads(CONFIG_FILE.read_text())

def save(cfg: dict) -> None:
    FIXR_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def set_key(provider: str, key: str) -> None:
    cfg = load()
    cfg["api_keys"][provider] = key
    save(cfg)

def get_key(provider: str) -> str | None:
    cfg = load()
    return cfg["api_keys"].get(provider)

def set_default(provider: str, model: str) -> None:
    cfg = load()
    cfg["provider"] = provider
    cfg["model"] = model
    save(cfg)
def get_models(provider: str) -> list:
    cfg = load()
    defaults = {
        "groq":       ["groq/llama-3.3-70b-versatile", "groq/llama-3.1-8b-instant", "groq/mixtral-8x7b-32768"],
        "gemini":     ["gemini/gemini-2.0-flash", "gemini/gemini-2.5-pro", "gemini/gemini-1.5-pro"],
        "mistral":    ["mistral/mistral-small-latest", "mistral/mistral-large-latest", "mistral/codestral-latest"],
        "openai":     ["openai/gpt-4o-mini", "openai/gpt-4o", "openai/o4-mini"],
        "anthropic":  ["anthropic/claude-haiku-4-5-20251001", "anthropic/claude-sonnet-4-6", "anthropic/claude-opus-4-6"],
        "openrouter": ["openrouter/meta-llama/llama-3.3-70b-instruct:free", "openrouter/mistralai/mistral-7b-instruct:free", "openrouter/google/gemma-3-27b-it:free"],
        "cerebras":   ["cerebras/llama-3.3-70b", "cerebras/llama-3.1-8b", "cerebras/llama-3.1-70b"],
        "nvidia":     ["nvidia_nim/meta/llama-3.3-70b-instruct", "nvidia_nim/mistralai/mistral-7b-instruct-v0.3", "nvidia_nim/google/gemma-3-27b-it"],
        "ollama":     ["ollama/llama3.3", "ollama/mistral", "ollama/codellama"],
        "cohere":     ["cohere/command-r-plus", "cohere/command-r", "cohere/command-a-03-2025"],
    }
    custom = cfg.get("custom_models", {}).get(provider, [])
    return defaults.get(provider, []) + custom

def add_model(provider: str, model: str) -> None:
    cfg = load()
    cfg.setdefault("custom_models", {}).setdefault(provider, [])
    if model not in cfg["custom_models"][provider]:
        cfg["custom_models"][provider].append(model)
    save(cfg)
