import webbrowser
import httpx
import json
from pathlib import Path
from . import config as cfg

# OAuth configs per provider (add more as providers support it)
OAUTH_CONFIGS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/generative-language",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
    }
}

def set_api_key(provider: str, key: str) -> None:
    cfg.set_key(provider, key)

def get_api_key(provider: str) -> str | None:
    return cfg.get_key(provider)

def oauth_login(provider: str) -> str | None:
    """
    Opens browser for OAuth flow. Returns access token or None.
    Currently supports: google (Gemini)
    """
    import os
    oc = OAUTH_CONFIGS.get(provider)
    if not oc:
        raise ValueError(f"OAuth not supported for provider: {provider}")

    client_id = os.environ.get(oc["client_id_env"])
    if not client_id:
        raise ValueError(f"Set {oc['client_id_env']} env var to use OAuth for {provider}")

    # Build auth URL (device flow simplified)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": oc["scope"],
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "access_type": "offline",
    }
    from urllib.parse import urlencode
    url = f"{oc['auth_url']}?{urlencode(params)}"
    webbrowser.open(url)
    return url  # User pastes code manually in CLI

def save_oauth_token(provider: str, token: str) -> None:
    c = cfg.load()
    c.setdefault("auth_tokens", {})[provider] = token
    cfg.save(c)

def get_oauth_token(provider: str) -> str | None:
    return cfg.load().get("auth_tokens", {}).get(provider)
