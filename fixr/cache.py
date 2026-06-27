import json
import hashlib
from pathlib import Path
from .config import FIXR_DIR

CACHE_FILE = FIXR_DIR / "cache.json"

def _normalize(error: str) -> str:
    """Strip line numbers and memory addresses for stable cache keys."""
    import re
    s = re.sub(r'line \d+', 'line N', error)
    s = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s

def _key(error: str) -> str:
    return hashlib.sha256(_normalize(error).encode()).hexdigest()[:16]

def _load() -> dict:
    FIXR_DIR.mkdir(exist_ok=True)
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}

def _save(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2))

def get(error: str) -> str | None:
    return _load().get(_key(error))

def set(error: str, solution: str) -> None:
    cache = _load()
    cache[_key(error)] = solution
    _save(cache)

def clear() -> int:
    count = len(_load())
    _save({})
    return count
