from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional


JOB_DIR = Path("backend/data/autoplan/jobs")
JOB_DIR.mkdir(parents=True, exist_ok=True)


def create_job(payload: Dict[str, Any], user_id: int | None = None) -> str:
    job_id = uuid.uuid4().hex
    rec = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "queued",
        "created_at": time.time(),
        "updated_at": time.time(),
        "payload": payload,
        "result": {},
        "error": None,
    }
    _write_job(rec)
    return job_id


def update_job(job_id: str, **kwargs: Any) -> Dict[str, Any]:
    rec = get_job(job_id) or {"job_id": job_id}
    rec.update(kwargs)
    rec["updated_at"] = time.time()
    _write_job(rec)
    return rec


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    path = JOB_DIR / f"{job_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_jobs(limit: int = 50, user_id: int | None = None) -> list[dict]:
    jobs = []
    for p in sorted(JOB_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if user_id is not None and rec.get("user_id") != user_id:
                continue
            jobs.append(rec)
        except Exception:
            continue
        if len(jobs) >= limit:
            break
    return jobs


def cleanup_jobs(older_than_seconds: int = 7 * 24 * 3600) -> int:
    removed = 0
    now = time.time()
    for p in JOB_DIR.glob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            ts = rec.get("updated_at") or rec.get("created_at") or 0
            if now - float(ts) > older_than_seconds:
                # 删除关联产物
                result = rec.get("result") or {}
                for k in ("json", "docx", "compare_docx"):
                    f = result.get(k)
                    if isinstance(f, list):
                        for pi in f:
                            try:
                                Path(pi).unlink(missing_ok=True)
                            except Exception:
                                pass
                    elif f:
                        try:
                            Path(f).unlink(missing_ok=True)
                        except Exception:
                            pass
                p.unlink(missing_ok=True)
                removed += 1
        except Exception:
            continue
    return removed


def _write_job(rec: Dict[str, Any]) -> None:
    job_id = rec.get("job_id")
    if not job_id:
        return
    path = JOB_DIR / f"{job_id}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
