from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List


_SAFE_CONSISTENCY_RE = re.compile(
    r"(DECISION\s*:\s*PASS|未发现(?:实质性|明显|前后)?冲突|"
    r"无(?:实质性|明显)?冲突|no\s+(?:material\s+)?conflict)",
    re.IGNORECASE,
)
_CONFLICT_RE = re.compile(
    r"(DECISION\s*:\s*BLOCK|存在(?:实质性|明显|前后)?冲突|"
    r"发现(?:实质性|明显|前后)?冲突|不一致|相互矛盾|"
    r"conflict(?:s|ing)?\s+(?:found|detected)|inconsisten)",
    re.IGNORECASE,
)
_MACHINE_DECISION_RE = re.compile(
    r"^\s*DECISION\s*:\s*(PASS|BLOCK)\b",
    re.IGNORECASE,
)


def _canonical_digest(value: Dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _issue(code: str, message: str, *, source: str, details: Any = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "code": code,
        "severity": "error",
        "source": source,
        "message": message,
    }
    if details not in (None, "", [], {}):
        row["details"] = details
    return row


def build_delivery_quality_gate(
    *,
    strict: bool,
    content_review: Dict[str, Any] | None,
    plan_consistency: Dict[str, Any] | None,
    model_review_audit: Dict[str, Any] | None,
    requirement_matrix: Dict[str, Any] | None,
    standard_audit: Dict[str, Any] | None,
    cross_index: Dict[str, Any] | None,
    model_review_required: bool,
) -> Dict[str, Any]:
    """Combine independent specialist results into one fail-closed delivery decision."""

    blockers: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    checks: List[Dict[str, Any]] = []

    content = dict(content_review or {})
    content_gate = content.get("quality_gate") if isinstance(content.get("quality_gate"), dict) else {}
    content_ok = bool(content_gate.get("pass"))
    checks.append({"name": "independent_content_quality", "pass": content_ok})
    if not content_ok:
        blockers.append(
            _issue(
                "DELIVERY_CONTENT_QUALITY_BLOCKED",
                "独立内容质量审核未通过。",
                source="independent_content_review",
                details=content_gate.get("blocking_issues") or content.get("issues") or [],
            )
        )

    plan = dict(plan_consistency or {})
    plan_ok = bool(plan) and bool(plan.get("ok", False))
    checks.append({"name": "plan_consistency", "pass": plan_ok})
    if not plan_ok:
        blockers.append(
            _issue(
                "DELIVERY_PLAN_CONSISTENCY_BLOCKED",
                "工期、资源峰值或关键线路的一致性校验未通过。",
                source="plan_consistency",
                details=plan,
            )
        )

    standards = dict(standard_audit or {})
    standards_ok = bool(standards.get("ok", False))
    checks.append({"name": "verified_standards", "pass": standards_ok})
    if not standards_ok:
        blockers.append(
            _issue(
                "DELIVERY_STANDARD_EVIDENCE_BLOCKED",
                "存在未核验、过期或冲突的规范引用。",
                source="standard_citation_audit",
                details=(standards.get("violations") or [])[:20],
            )
        )

    req = dict(requirement_matrix or {})
    req_summary = req.get("summary") if isinstance(req.get("summary"), dict) else {}
    req_present = bool(req)
    req_ok = (not req_present) or bool(req_summary.get("strict_delivery_allowed", False))
    checks.append({"name": "requirement_evidence_matrix", "pass": req_ok})
    if not req_ok:
        blockers.append(
            _issue(
                "DELIVERY_REQUIREMENT_EVIDENCE_BLOCKED",
                "招标要求尚未全部形成可反查证据闭环。",
                source="requirement_evidence_matrix",
                details=req_summary.get("blocking_requirement_ids") or [],
            )
        )

    cross = dict(cross_index or {})
    cross_contract_fields = {
        "ok",
        "focus_count",
        "mentioned_count",
        "closed_ok_count",
        "missing_drawing_locator_count",
        "missing_standard_locator_count",
        "focus_items",
    }
    focus_count = int(cross.get("focus_count") or 0)
    mentioned_count = int(cross.get("mentioned_count") or 0)
    closed_count = int(cross.get("closed_ok_count") or 0)
    missing_drawing = int(cross.get("missing_drawing_locator_count") or 0)
    missing_standard = int(cross.get("missing_standard_locator_count") or 0)
    focus_rows = cross.get("focus_items")
    cross_available = (
        bool(cross)
        and not bool(cross.get("build_failed"))
        and cross_contract_fields.issubset(cross)
        and isinstance(focus_rows, list)
        and len(focus_rows) == focus_count
        and (focus_count == 0 or cross.get("ok") is True)
        and 0 <= closed_count <= mentioned_count <= focus_count
        and 0 <= missing_drawing <= mentioned_count
        and 0 <= missing_standard <= mentioned_count
    )
    cross_ok = cross_available and (focus_count == 0 or (
        mentioned_count >= focus_count
        and closed_count >= focus_count
        and missing_drawing == 0
        and missing_standard == 0
    ))
    checks.append(
        {
            "name": "boq_cross_index_closure",
            "pass": cross_ok,
            "available": cross_available,
            "focus_count": focus_count,
            "mentioned_count": mentioned_count,
            "closed_ok_count": closed_count,
            "missing_drawing_locator_count": missing_drawing,
            "missing_standard_locator_count": missing_standard,
        }
    )
    if not cross_ok:
        blocker_code = (
            "DELIVERY_CROSS_INDEX_UNAVAILABLE"
            if not cross_available
            else "DELIVERY_CROSS_INDEX_BLOCKED"
        )
        blocker_message = (
            "重点清单项交叉索引构建失败，严格交付已按失败关闭。"
            if not cross_available
            else "重点清单项未全部绑定章节、图纸/规范定位并形成量化闭环。"
        )
        blockers.append(
            _issue(
                blocker_code,
                blocker_message,
                source="cross_index",
                details=checks[-1],
            )
        )

    model_audit = dict(model_review_audit or {})
    consistency = (
        model_audit.get("consistency_review")
        if isinstance(model_audit.get("consistency_review"), dict)
        else {}
    )
    failed_chapters = [row for row in (model_audit.get("failed_chapters") or []) if isinstance(row, dict)]
    summary = str(consistency.get("summary") or "").strip()
    machine_decision = _MACHINE_DECISION_RE.match(summary)
    if machine_decision:
        consistency_safe = machine_decision.group(1).upper() == "PASS"
    else:
        consistency_safe = bool(_SAFE_CONSISTENCY_RE.search(summary)) and not bool(
            _CONFLICT_RE.search(_SAFE_CONSISTENCY_RE.sub("", summary))
        )
    model_ok = True
    if model_review_required:
        model_ok = bool(consistency.get("ok")) and consistency_safe and not failed_chapters
    checks.append(
        {
            "name": "independent_model_review",
            "pass": model_ok,
            "required": bool(model_review_required),
            "failed_chapter_count": len(failed_chapters),
            "explicit_no_conflict": consistency_safe,
            "machine_decision": (
                machine_decision.group(1).upper() if machine_decision else None
            ),
        }
    )
    if not model_ok:
        blockers.append(
            _issue(
                "DELIVERY_MODEL_REVIEW_BLOCKED",
                "关键章节精修或全文一致性终审未给出明确无冲突结论。",
                source="model_review_audit",
                details={
                    "failed_chapters": failed_chapters,
                    "consistency_ok": bool(consistency.get("ok")),
                    "summary": summary[:1200],
                },
            )
        )
    elif not model_review_required:
        warnings.append(
            {
                "code": "DELIVERY_MODEL_REVIEW_NOT_REQUIRED",
                "severity": "info",
                "source": "model_review_audit",
                "message": "当前执行模式未要求外部模型终审；其余确定性质量门仍已执行。",
            }
        )

    decision = {
        "schema_version": "delivery-quality-gate-v1",
        "strict": bool(strict),
        "delivery_allowed": not blockers,
        "checks": checks,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
    }
    decision["decision_digest"] = _canonical_digest(decision)
    return decision
