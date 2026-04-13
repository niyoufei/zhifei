from __future__ import annotations

from typing import Any


def build_actions_job_cancel_response(*, job_id: str, status: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "job_id": job_id,
        "status": str(status or "").strip().lower() or None,
    }
