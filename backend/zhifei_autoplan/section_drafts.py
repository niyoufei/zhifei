from __future__ import annotations

import copy
import difflib
import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


STATUS_DRAFT = "draft"
STATUS_APPLIED = "applied"
STATUS_REJECTED = "rejected"
STATUS_ROLLED_BACK = "rolled_back"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_text(value: Any) -> str:
    return "" if value is None else str(value)


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def hash_section_content(content: str) -> str:
    return hashlib.sha256(_clean_text(content).encode("utf-8")).hexdigest()


def compute_section_draft_diff(
    original_content: str,
    draft_content: str,
    *,
    fromfile: str = "original",
    tofile: str = "draft",
) -> str:
    original_lines = _clean_text(original_content).splitlines()
    draft_lines = _clean_text(draft_content).splitlines()
    return "\n".join(
        difflib.unified_diff(
            original_lines,
            draft_lines,
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )


def build_draft_audit_record(
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    prompt_hash: str | None = None,
    section_title: str,
    original_hash: str,
    draft_hash: str,
    confirmed_by: str | None = None,
    confirmed_at: str | None = None,
    action_type: str,
) -> dict[str, Any]:
    return {
        "provider": _clean_optional(provider),
        "model": _clean_optional(model),
        "base_url": _clean_optional(base_url),
        "prompt_hash": _clean_optional(prompt_hash),
        "section_title": _clean_text(section_title),
        "original_hash": _clean_text(original_hash),
        "draft_hash": _clean_text(draft_hash),
        "confirmed_by": _clean_optional(confirmed_by),
        "confirmed_at": _clean_optional(confirmed_at),
        "action_type": _clean_text(action_type),
    }


def build_section_draft(
    *,
    section_title: str,
    original_content: str,
    draft_content: str,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    prompt_hash: str | None = None,
    prompt: str | None = None,
    created_at: str | None = None,
    draft_id: str | None = None,
) -> dict[str, Any]:
    original_text = _clean_text(original_content)
    draft_text = _clean_text(draft_content)
    original_hash = hash_section_content(original_text)
    draft_hash = hash_section_content(draft_text)
    resolved_prompt_hash = _clean_optional(prompt_hash)
    if resolved_prompt_hash is None and prompt is not None:
        resolved_prompt_hash = hash_section_content(prompt)
    timestamp = _clean_optional(created_at) or _utc_now_iso()

    audit_record = build_draft_audit_record(
        provider=provider,
        model=model,
        base_url=base_url,
        prompt_hash=resolved_prompt_hash,
        section_title=section_title,
        original_hash=original_hash,
        draft_hash=draft_hash,
        action_type="created",
    )

    return {
        "draft_id": _clean_optional(draft_id) or str(uuid4()),
        "section_title": _clean_text(section_title),
        "original_content": original_text,
        "draft_content": draft_text,
        "original_hash": original_hash,
        "draft_hash": draft_hash,
        "status": STATUS_DRAFT,
        "provider": _clean_optional(provider),
        "model": _clean_optional(model),
        "base_url": _clean_optional(base_url),
        "prompt_hash": resolved_prompt_hash,
        "created_at": timestamp,
        "audit": [audit_record],
    }


def _copy_draft_with_audit(
    draft: dict[str, Any],
    *,
    status: str,
    action_type: str,
    confirmed_by: str | None = None,
    confirmed_at: str | None = None,
) -> dict[str, Any]:
    result = copy.deepcopy(draft)
    result["status"] = status
    timestamp = _clean_optional(confirmed_at) or _utc_now_iso()
    original_hash = _clean_text(result.get("original_hash") or hash_section_content(result.get("original_content", "")))
    draft_hash = _clean_text(result.get("draft_hash") or hash_section_content(result.get("draft_content", "")))
    record = build_draft_audit_record(
        provider=result.get("provider"),
        model=result.get("model"),
        base_url=result.get("base_url"),
        prompt_hash=result.get("prompt_hash"),
        section_title=result.get("section_title", ""),
        original_hash=original_hash,
        draft_hash=draft_hash,
        confirmed_by=confirmed_by,
        confirmed_at=timestamp,
        action_type=action_type,
    )
    audit = result.get("audit")
    if not isinstance(audit, list):
        audit = [] if audit is None else [audit]
    result["audit"] = audit + [record]
    return result


def apply_section_draft(
    draft: dict[str, Any],
    *,
    confirmed_by: str | None = None,
    confirmed_at: str | None = None,
) -> dict[str, Any]:
    result = _copy_draft_with_audit(
        draft,
        status=STATUS_APPLIED,
        action_type="applied",
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
    )
    result["applied_content"] = _clean_text(result.get("draft_content"))
    result["applied_hash"] = hash_section_content(result["applied_content"])
    return result


def reject_section_draft(
    draft: dict[str, Any],
    *,
    confirmed_by: str | None = None,
    confirmed_at: str | None = None,
) -> dict[str, Any]:
    return _copy_draft_with_audit(
        draft,
        status=STATUS_REJECTED,
        action_type="rejected",
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
    )


def rollback_section_draft(
    draft: dict[str, Any],
    *,
    confirmed_by: str | None = None,
    confirmed_at: str | None = None,
) -> dict[str, Any]:
    result = _copy_draft_with_audit(
        draft,
        status=STATUS_ROLLED_BACK,
        action_type="rolled_back",
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
    )
    original_content = _clean_text(result.get("original_content"))
    result["draft_content"] = original_content
    result["draft_hash"] = hash_section_content(original_content)
    result["rolled_back_content"] = original_content
    return result
