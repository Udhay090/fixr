import json
import os
from pathlib import Path

DIR = Path(os.environ.get("FIXR_HOME") or Path.home() / ".fixr")
FILE = DIR / "config.json"

# provider -> (OpenAI-compatible base URL, API-key env var or None, has free tier)
PROVIDERS = {
    "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY", True),
    "cerebras":   ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", True),
    "gemini":     ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", True),
    "mistral":    ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", True),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", True),
    "nvidia":     ("https://integrate.api.nvidia.com/v1", "NVIDIA_NIM_API_KEY", True),
    "ollama":     ("http://localhost:11434/v1", None, True),
    "openai":     ("https://api.openai.com/v1", "OPENAI_API_KEY", False),
    "anthropic":  ("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", False),
    "cohere":     ("https://api.cohere.ai/compatibility/v1", "COHERE_API_KEY", False),
}


def write_json(path: Path, data) -> None:
    """Atomic write with owner-only permissions (files may hold API keys)."""
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def load() -> dict:
    try:
        conf = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        conf = {}
    if not isinstance(conf, dict):
        conf = {}
    if not isinstance(conf.get("api_keys"), dict):
        conf["api_keys"] = {}
    return conf


def save(conf: dict) -> None:
    write_json(FILE, conf)


def get_key(provider: str) -> str | None:
    """Env var wins over the stored key."""
    env = PROVIDERS[provider][1]
    return (os.environ.get(env) if env else None) or load()["api_keys"].get(provider)
