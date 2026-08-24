from __future__ import annotations

import os
import re
from pathlib import Path


_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _default_env_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env.local"


def load_local_env(path: str | Path | None = None) -> int:
    """Load simple KEY=VALUE pairs without executing shell syntax or overriding env."""
    env_path = Path(path).expanduser() if path is not None else _default_env_path()
    if not env_path.is_file():
        return 0

    loaded = 0
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not _ENV_NAME_RE.fullmatch(name):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not value or name in os.environ:
            continue
        os.environ[name] = value
        loaded += 1
    return loaded
