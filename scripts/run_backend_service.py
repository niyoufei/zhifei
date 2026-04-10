#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import uvicorn


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)

    keys_file = Path(os.environ.get("ZF_KEYS_FILE", root / ".runtime" / "local_keys.env"))
    _load_env_file(keys_file)

    os.environ.setdefault("PYTHONPATH", str(root))
    os.environ.setdefault("ZF_ACTIONS_KEY", "zf-webui-key")

    host = os.environ.get("ZF_HOST", "127.0.0.1")
    port = int(os.environ.get("ZF_PORT", "8010"))
    uvicorn.run("backend.app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
