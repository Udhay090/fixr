import hashlib
import json
import re

from . import config as cfg

FILE = cfg.DIR / "cache.json"
MAX_ENTRIES = 500


def _key(error: str, model_id: str) -> str:
    s = re.sub(r"(line |:)\d+", r"\1N", error, flags=re.I)  # line numbers
    s = re.sub(r"0x[0-9a-f]+", "0xADDR", s, flags=re.I)      # memory addresses
    s = " ".join(s.lower().split())
    return hashlib.sha256(f"{model_id}\n{s}".encode()).hexdigest()[:16]


def _load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get(error: str, model_id: str) -> str | None:
    return _load().get(_key(error, model_id))


def put(error: str, model_id: str, solution: str) -> None:
    cache, k = _load(), _key(error, model_id)
    cache.pop(k, None)  # re-insert as newest
    cache[k] = solution
    cfg.write_json(FILE, dict(list(cache.items())[-MAX_ENTRIES:]))


def clear() -> int:
    n = len(_load())
    cfg.write_json(FILE, {})
    return n
