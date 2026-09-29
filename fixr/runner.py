import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

INTERPRETED = {
    ".js": ["node"], ".ts": ["ts-node"], ".rb": ["ruby"], ".go": ["go", "run"],
    ".sh": ["bash"], ".java": ["java"], ".php": ["php"], ".lua": ["lua"],
    ".pl": ["perl"], ".r": ["Rscript"],
}
COMPILED = {".c": ["gcc"], ".cpp": ["g++"], ".rs": ["rustc"]}


class RunnerError(Exception):
    """Problem running the file itself (missing tool, timeout) — not a bug in the user's code."""


def _python() -> str:
    # Prefer the user's own python (venv-aware) over the interpreter fixr is installed in.
    return shutil.which("python3") or shutil.which("python") or sys.executable


def _run(cmd: list, timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except FileNotFoundError:
        raise RunnerError(f"'{Path(cmd[0]).name}' not found on PATH — install it to run this file type")
    except subprocess.TimeoutExpired:
        raise RunnerError(f"Timed out after {timeout}s")


def run_file(path: Path, timeout: int = 30) -> str | None:
    """Run a source file. Returns the error output, or None if it succeeded."""
    ext = path.suffix.lower()
    with tempfile.TemporaryDirectory() as tmp:
        if ext in COMPILED:
            exe = str(Path(tmp) / ("prog.exe" if os.name == "nt" else "prog"))
            build = _run(COMPILED[ext] + [str(path), "-o", exe], timeout)
            if build.returncode:
                return build.stderr or build.stdout
            cmd = [exe]
        elif ext == ".py":
            cmd = [_python(), str(path)]
        elif ext in INTERPRETED:
            cmd = INTERPRETED[ext] + [str(path)]
        else:
            raise RunnerError(f"Unsupported file type: {ext or path.name}")
        proc = _run(cmd, timeout)
    if proc.returncode == 0:
        return None
    return proc.stderr.strip() or proc.stdout.strip() or f"Process exited with code {proc.returncode}"
