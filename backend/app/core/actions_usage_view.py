from __future__ import annotations

from typing import Any


def build_actions_usage_status_response(admission_detail: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "admission": dict(admission_detail)}


def build_actions_usage_report_response(
    *,
    session_id: str,
    workspace_dir: str,
    decision: dict[str, Any],
) -> dict[str, Any]:
    usage = decision.get("usage") if isinstance(decision.get("usage"), dict) else {}
    return {
        "ok": True,
        "scope": "session",
        "session_id": session_id,
        "workspace_dir": workspace_dir,
        "usage_profile": usage.get("usage_profile") if isinstance(usage.get("usage_profile"), dict) else {},
        "limits": dict(decision.get("limits") or {}),
        "warning_level": str(decision.get("warning_level") or "none"),
        "warnings": list(decision.get("warnings") or []),
    }
