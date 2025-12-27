#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"

def http_get_json(path: str, timeout: int = 10):
    url = BASE + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)

def http_post_json(path: str, payload: dict, timeout: int = 60):
    url = BASE + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"", dict(e.headers or {})

def http_post_raw(path: str, timeout: int = 60):
    url = BASE + path
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"", dict(e.headers or {})

def fail(msg: str):
    print("[FAIL]", msg)
    sys.exit(1)

def ok(msg: str):
    print("[OK]", msg)

def main():
    build = Path("build")
    build.mkdir(exist_ok=True)

    # 0) wait server reachable
    last_err = None
    for _ in range(20):
        try:
            http_get_json("/openapi.json", timeout=3)
            break
        except Exception as e:
            last_err = e
            time.sleep(0.4)
    else:
        fail(f"server not reachable: {last_err!r}")

    # 1) openapi check: /retrieve exists
    openapi = http_get_json("/openapi.json", timeout=10)
    paths = openapi.get("paths") or {}
    ok(f"openapi has /retrieve = {('/retrieve' in paths)}")

    # 2) clean key artifacts
    artifacts = [
        build / "project_profile.json",
        build / "kg_context.json",
        build / "region_upgrade.json",
        build / "precheck_guard.json",
        build / "compose.json",
        build / "retrieve.json",
        build / "compose_exported_with_trace.docx",
    ]
    for p in artifacts:
        if p.exists():
            p.unlink()
    ok("cleaned old build artifacts (if existed)")

    # 3) POST /compose
    payload = {
        "topic": "建筑装饰装修工程施工组织设计（合肥）",
        "outline": [
            "工程概况",
            "施工准备",
            "装饰装修工程施工方案",
            "质量管理体系与措施",
            "安全管理体系与措施",
            "文明施工与环保",
        ],
    }
    st, body, hdr = http_post_json("/compose", payload, timeout=120)
    txt = body.decode("utf-8", errors="replace")
    # hard-fail if placeholder text still exists
    if ("本章节为占位输出" in txt) or ("下一步：接入 /retrieve + LLM" in txt):
        fail("compose still contains placeholder text")

    if st != 200:
        fail(f"/compose http status={st}, body_head={txt[:400]!r}")

    try:
        resp = json.loads(txt)
    except Exception as e:
        fail(f"/compose response not JSON: {e!r}, body_head={txt[:400]!r}")

    if resp.get("status") != "ok":
        fail(f"/compose status != ok: {resp.get('status')}")

    secs = resp.get("sections") or []
    titles = [s.get("title") for s in secs if isinstance(s, dict)]
    ok(f"/compose sections.count={len(secs)}")
    ok(f"/compose first titles={titles[:4]}")

    if not titles or ("可追溯" not in (titles[0] or "")):
        fail("first section is not traceability summary (expected '可追溯' in title[0])")

    if not any("检索证据" in (t or "") for t in titles):
        fail("missing section title containing '检索证据'")

    # 4) artifact existence checks
    must_exist = [
        build / "project_profile.json",
        build / "kg_context.json",
        build / "region_upgrade.json",
        build / "precheck_guard.json",
        build / "compose.json",
        build / "retrieve.json",
    ]
    for p in must_exist:
        if not p.exists():
            fail(f"missing artifact: {p}")
        ok(f"artifact exists: {p.name} size={p.stat().st_size} bytes")

    # 5) GET /audit: replayable true + has retrieve
    audit = http_get_json("/audit", timeout=20)
    replay = (audit.get("replay") or {})
    ok(f"/audit replayable={replay.get('replayable')}, missing_count={len(replay.get('missing') or [])}")
    if replay.get("replayable") is not True:
        fail(f"/audit replayable != True, missing={replay.get('missing')}")
    if "retrieve" not in audit:
        fail("/audit missing 'retrieve' field")

    r = audit.get("retrieve") or {}
    ok(f"/audit retrieve.results_count={r.get('results_count')}, trace_file={r.get('trace_file')}")

    # 6) POST /export: save docx
    st3, body3, hdr3 = http_post_raw("/export", timeout=120)
    ctype = (hdr3.get("Content-Type") or hdr3.get("content-type") or "")
    if st3 != 200 or "application/vnd.openxmlformats-officedocument.wordprocessingml.document" not in ctype.lower():
        # 可能返回 json 错误
        fail(f"/export not docx: status={st3}, content-type={ctype}, body_head={body3[:300]!r}")

    out = build / "compose_exported_with_trace.docx"
    out.write_bytes(body3)
    ok(f"/export saved: {out} size={out.stat().st_size} bytes")

    # HARD GATE: require kg_pack in artifacts
    import json as _json
    from pathlib import Path as _Path
    def _must_have_kg_pack(_fp: str) -> None:
        _p = _Path(_fp)
        if not _p.exists():
            raise SystemExit(f"[FAIL] missing artifact: {_fp}")
        _d = _json.loads(_p.read_text(encoding="utf-8"))
        _kp = _d.get("kg_pack")
        if not isinstance(_kp, dict):
            raise SystemExit(f"[FAIL] {_fp} missing 'kg_pack' (dict required)")
        if not _kp.get("active_pack"):
            raise SystemExit(f"[FAIL] {_fp} kg_pack.active_pack missing")
        if _kp.get("manifest_exists") is not True:
            raise SystemExit(f"[FAIL] {_fp} kg_pack.manifest_exists must be true")
        if not _kp.get("manifest_sha256"):
            raise SystemExit(f"[FAIL] {_fp} kg_pack.manifest_sha256 missing")
    for _fp in ("build/kg_context.json","build/retrieve.json","build/compose.json"):
        _must_have_kg_pack(_fp)
    print("[OK] kg_pack hard gate passed")
    
    print("\n[SUCCESS] smoke_e2e_v2 passed: openapi(/retrieve) + /compose + artifacts + /audit + /export")

if __name__ == "__main__":
    main()
