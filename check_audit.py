"""Offline audit verification script.

This script reads a local audit log and verifies one saved file on disk.
It is not mounted into FastAPI and is not part of the current online request chain.
"""

import json, hashlib, pathlib

audit = pathlib.Path("backend/data/audit/ingest.jsonl")
last_line = audit.read_text(encoding="utf-8").strip().splitlines()[-1]
last = json.loads(last_line)

p = pathlib.Path(last["saved_as"])
data = p.read_bytes()

sha = hashlib.sha256(data).hexdigest()

print("[审计校验结果]")
print("文件存在:", p.exists(), "→", p)
print("字节数  :", len(data), "目标:", last["bytes"], "OK" if len(data)==last["bytes"] else "FAIL")
print("SHA256 :", sha)
print("目标   :", last["sha256"], "OK" if sha==last["sha256"] else "FAIL")
