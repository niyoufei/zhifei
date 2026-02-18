import os, json, hashlib, socket, platform, datetime as dt, pathlib
from typing import Dict, Any, Optional

LOG_ROOT = pathlib.Path(os.environ.get("AUDIT_LOG_DIR", "audit_logs")) / "m7"
LOG_ROOT.mkdir(parents=True, exist_ok=True)

def _sha256_text(s: str) -> str:
    h = hashlib.sha256()
    h.update(s.encode("utf-8"))
    return h.hexdigest()

def _event_hash(payload: dict) -> str:
    canon = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",",":"))
    return _sha256_text(canon)

def log_export_decision(
    *,
    doc_type: str,
    ruleset_version: str,
    export_template: str,
    postprocessors: list,
    file_fingerprint: str = "",
    recommend_source: str = "recommend.export_path",
    status: str = "ok",
    verified: bool = True,
    quality_score: float = None,
    time_cost_s: float = None,
    extra: Optional[Dict[str, Any]] = None,
) -> dict:
    ts = dt.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
    env = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "service": "traceable-docs",
        "stage": "M7",
    }
    record = {
        "timestamp": ts,
        "route": "/compose/export",
        "verified": bool(verified),
        "status": status,
        "metrics": {
            "quality_score": quality_score,
            "time_cost_s": time_cost_s,
        },
        "context": {
            "doc": {
                "type": doc_type,
                "fingerprint": file_fingerprint,
            },
            "ruleset_version": ruleset_version,
            "env": env,
        },
        "export": {
            "template": export_template,
            "postprocessors": postprocessors or [],
        },
        "source": recommend_source,
        "model": {"name": os.environ.get("MODEL_NAME", "CodexAgent"), "version": os.environ.get("MODEL_VERSION", "")},
    }
    record["hash"] = _event_hash(record)

    date_name = dt.datetime.utcnow().strftime("%Y-%m-%d") + ".jsonl"
    path = LOG_ROOT / date_name
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False)+"\n")

    return {"path": str(path), "event_hash": record["hash"]}
