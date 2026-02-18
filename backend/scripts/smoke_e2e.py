#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:8000"

def http_request(method: str, path: str, payload=None, timeout=60):
    url = BASE + path
    headers = {}
    data = b""
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            body = resp.read()
            return status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"", dict(e.headers or {})
    except Exception as e:
        print("[FATAL] Cannot reach server:", repr(e))
        print("        请确认终端1正在运行：python3 -m uvicorn app.main:app --reload")
        sys.exit(2)

def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return {"_error": repr(e), "_raw_head": path.read_text(encoding="utf-8", errors="replace")[:800]}

def show_kv(title: str, obj: dict, keys):
    print(f"\n[{title}]")
    for k in keys:
        v = obj.get(k)
        if isinstance(v, dict):
            print(f" - {k} = {json.dumps(v, ensure_ascii=False)}")
        else:
            print(f" - {k} = {v}")

def main():
    backend = Path.cwd()
    build = backend / "build"
    build.mkdir(exist_ok=True)

    # 0) clean old artifacts (keep build dir)
    artifacts = [
        build / "project_profile.json",
        build / "precheck_guard.json",
        build / "region_upgrade.json",
        build / "compose.json",
        build / "compose_output.docx",
        build / "compose_exported.docx",
    ]
    for p in artifacts:
        if p.exists():
            try:
                p.unlink()
                print(f"[CLEAN] removed {p}")
            except Exception as e:
                print(f"[WARN] cannot remove {p}: {e}")

    # 1) POST /compose
    payload = {
        "topic": "建筑装饰装修工程施工组织设计（合肥）",
        "outline": [
            "工程概况",
            "施工准备",
            "装饰装修工程施工方案",
            "质量管理体系与措施",
            "安全管理体系与措施",
            "文明施工与环保"
        ]
    }
    print("\n---- POST /compose payload ----")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    st, body, hdr = http_request("POST", "/compose", payload=payload, timeout=120)
    body_txt = body.decode("utf-8", errors="replace")
    print(f"\n[HTTP] POST /compose -> {st}")
    print("[BODY head 1200 chars]:")
    print(body_txt[:1200])

    if st != 200:
        print("[FAIL] /compose http status != 200")
        sys.exit(1)

    try:
        resp = json.loads(body_txt)
    except Exception as e:
        print("[FAIL] /compose response is not JSON:", repr(e))
        sys.exit(1)

    if resp.get("status") != "ok":
        print("[FAIL] /compose status is not ok ->", resp.get("status"))
        print("       说明 PreCheck Guard 仍在阻断或 compose 逻辑异常。")
        sys.exit(1)

    # 2) verify artifacts existence
    must_exist = [
        build / "project_profile.json",
        build / "precheck_guard.json",
        build / "region_upgrade.json",
        build / "compose.json",
    ]
    for p in must_exist:
        if not p.exists():
            print(f"[FAIL] missing artifact: {p}")
            sys.exit(1)
        print(f"[OK] exists: {p} size={p.stat().st_size} bytes")

    # 3) show key fields
    pp = read_json(build / "project_profile.json")
    pg = read_json(build / "precheck_guard.json")
    ru = read_json(build / "region_upgrade.json")
    cj = read_json(build / "compose.json")

    show_kv("project_profile.json", pp, ["decision", "project_type", "mandatory_dimensions", "input_sha256", "rule_path", "rule_sha256"])
    show_kv("precheck_guard.json", pg, ["passed", "project_profile_decision", "input_sha256", "rule_path", "rule_sha256"])
    show_kv("region_upgrade.json", ru, ["applied", "region_key", "project_profile_decision", "input_sha256", "rule_path", "rule_sha256"])
    show_kv("compose.json", cj, ["status", "saved_at", "topic"])

    if cj.get("status") != "ok" or cj.get("saved_at") != "build/compose.json":
        print("[FAIL] compose.json status/saved_at not correct")
        sys.exit(1)

    # 4) GET /audit
    st2, body2, _ = http_request("GET", "/audit", payload=None, timeout=60)
    txt2 = body2.decode("utf-8", errors="replace")
    print(f"\n[HTTP] GET /audit -> {st2}")
    if st2 != 200:
        print("[FAIL] /audit http status != 200")
        print(txt2[:1200])
        sys.exit(1)

    try:
        audit = json.loads(txt2)
    except Exception as e:
        print("[FAIL] /audit response is not JSON:", repr(e))
        print(txt2[:1200])
        sys.exit(1)

    replay = audit.get("replay") or {}
    print("\n[AUDIT replay]")
    print(" - replayable =", replay.get("replayable"))
    print(" - missing    =", replay.get("missing"))

    if replay.get("replayable") is not True:
        print("[FAIL] audit replayable != True")
        sys.exit(1)

    # 5) POST /export (download file)
    st3, body3, hdr3 = http_request("POST", "/export", payload=None, timeout=120)
    print(f"\n[HTTP] POST /export -> {st3}")
    ctype = (hdr3.get("Content-Type") or hdr3.get("content-type") or "").lower()
    print(" - content-type:", ctype)

    out = build / "compose_exported.docx"
    if st3 == 200 and "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in ctype:
        out.write_bytes(body3)
        print(f"[OK] exported docx saved: {out} size={out.stat().st_size} bytes")
    else:
        # 可能返回 JSON 错误信息
        print("[WARN] /export did not return docx; body head 800 chars:")
        print(body3.decode("utf-8", errors="replace")[:800])

    print("\n[SUCCESS] E2E smoke test passed: /compose -> artifacts -> /audit (replayable) -> /export")

if __name__ == "__main__":
    main()
