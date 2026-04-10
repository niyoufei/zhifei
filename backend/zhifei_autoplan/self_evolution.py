from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable

import fcntl

from backend.zhifei_autoplan.project_types import normalize_project_type
from backend.zhifei_autoplan.remediation_strategy import ACTION_TAG_LABELS


EVOLUTION_DIR = Path("backend/data/autoplan/evolution")
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_BUDGET_PROFILE_PATH = EVOLUTION_DIR / "runtime_budget_profile.json"
RUNTIME_BUDGET_PROFILE_LOCK = EVOLUTION_DIR / ".runtime_budget_profile.lock"
TASK_PARALLELISM_PROFILE_PATH = EVOLUTION_DIR / "task_parallelism_profile.json"
TASK_PARALLELISM_PROFILE_LOCK = EVOLUTION_DIR / ".task_parallelism_profile.lock"


def _default_self_evolution_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "ignore_dry_run_learning": True,
        "runtime_profile_soft_limit": 160,
        "runtime_profile_stale_days": 21,
        "runtime_profile_min_runs_to_keep": 2,
        "min_runs_for_adjustment": 2,
        "max_timeout_delta_sec": 20,
        "max_token_delta": 600,
        "allow_retry_promotion": True,
        "quality_issue_rate_raise_retry": 0.50,
        "error_rate_raise_timeout": 0.35,
        "fallback_rate_raise_timeout": 0.35,
        "quality_issue_rate_raise_tokens": 0.50,
        "compaction_rate_trim_tokens": 0.50,
        "combo_learning_enabled": True,
        "combo_learning_min_runs": 2,
        "combo_learning_min_success_rate": 0.55,
        "combo_learning_gate_pass_bonus": 0.10,
        "combo_learning_max_priority_boost": 8,
        "combo_bundle_learning_enabled": True,
        "combo_bundle_min_runs": 2,
        "combo_bundle_min_pass_rate": 0.55,
        "combo_bundle_gate_pass_bonus": 0.10,
        "combo_bundle_max_priority_boost": 10,
        "combo_context_bundle_learning_enabled": True,
        "combo_context_bundle_min_runs": 2,
        "combo_context_bundle_min_pass_rate": 0.60,
        "combo_context_bundle_gate_pass_bonus": 0.12,
        "combo_context_bundle_max_priority_boost": 12,
        "combo_context_bundle_partial_match_enabled": True,
        "combo_context_bundle_partial_min_match_count": 2,
        "combo_context_bundle_partial_min_match_ratio": 0.50,
        "combo_context_bundle_partial_score_penalty": 0.08,
        "combo_context_bundle_attribution_enabled": True,
        "combo_context_bundle_attribution_min_runs": 2,
        "combo_context_bundle_attribution_gate_pass_bonus": 0.08,
        "combo_context_metric_effect_enabled": True,
        "combo_context_metric_effect_min_runs": 2,
        "combo_context_metric_effect_resolve_bonus": 0.10,
        "combo_context_metric_action_effect_enabled": True,
        "combo_context_metric_action_effect_min_runs": 2,
        "combo_context_metric_action_effect_resolve_bonus": 0.08,
        "task_parallelism_enabled": True,
        "task_parallelism_min_runs": 2,
        "task_parallelism_max_delta": 2,
        "task_parallelism_error_rate_reduce": 0.35,
        "task_parallelism_fallback_rate_reduce": 0.40,
        "task_parallelism_quality_issue_rate_reduce": 0.50,
        "task_parallelism_profile_soft_limit": 96,
        "task_parallelism_profile_stale_days": 30,
        "task_parallelism_profile_min_runs_to_keep": 2,
    }


def _resolve_self_evolution_config(params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(_default_self_evolution_config())
    if isinstance(params, dict):
        custom = params.get("self_evolution")
        if isinstance(custom, dict):
            cfg.update(custom)
    cfg["enabled"] = bool(cfg.get("enabled", True))
    cfg["ignore_dry_run_learning"] = bool(cfg.get("ignore_dry_run_learning", True))
    try:
        cfg["min_runs_for_adjustment"] = max(1, int(cfg.get("min_runs_for_adjustment") or 2))
    except Exception:
        cfg["min_runs_for_adjustment"] = 2
    for key, default, lower, upper in (
        ("runtime_profile_soft_limit", 160, 20, 500),
        ("runtime_profile_stale_days", 21, 1, 365),
        ("runtime_profile_min_runs_to_keep", 2, 1, 10),
        ("task_parallelism_profile_soft_limit", 96, 10, 200),
        ("task_parallelism_profile_stale_days", 30, 1, 365),
        ("task_parallelism_profile_min_runs_to_keep", 2, 1, 10),
    ):
        try:
            cfg[key] = max(lower, min(upper, int(cfg.get(key) or default)))
        except Exception:
            cfg[key] = default
    try:
        cfg["max_timeout_delta_sec"] = max(0, int(cfg.get("max_timeout_delta_sec") or 20))
    except Exception:
        cfg["max_timeout_delta_sec"] = 20
    try:
        cfg["max_token_delta"] = max(0, int(cfg.get("max_token_delta") or 600))
    except Exception:
        cfg["max_token_delta"] = 600
    for key in (
        "quality_issue_rate_raise_retry",
        "error_rate_raise_timeout",
        "fallback_rate_raise_timeout",
        "quality_issue_rate_raise_tokens",
        "compaction_rate_trim_tokens",
        "combo_learning_min_success_rate",
        "combo_learning_gate_pass_bonus",
        "combo_bundle_min_pass_rate",
        "combo_bundle_gate_pass_bonus",
        "combo_context_bundle_min_pass_rate",
        "combo_context_bundle_gate_pass_bonus",
        "combo_context_bundle_partial_min_match_ratio",
        "combo_context_bundle_partial_score_penalty",
        "combo_context_bundle_attribution_gate_pass_bonus",
        "combo_context_metric_effect_resolve_bonus",
        "combo_context_metric_action_effect_resolve_bonus",
        "task_parallelism_error_rate_reduce",
        "task_parallelism_fallback_rate_reduce",
        "task_parallelism_quality_issue_rate_reduce",
    ):
        try:
            cfg[key] = max(0.0, min(1.0, float(cfg.get(key) or 0.0)))
        except Exception:
            cfg[key] = float(_default_self_evolution_config()[key])
    cfg["allow_retry_promotion"] = bool(cfg.get("allow_retry_promotion", True))
    cfg["combo_learning_enabled"] = bool(cfg.get("combo_learning_enabled", True))
    try:
        cfg["combo_learning_min_runs"] = max(1, int(cfg.get("combo_learning_min_runs") or 2))
    except Exception:
        cfg["combo_learning_min_runs"] = 2
    try:
        cfg["combo_learning_max_priority_boost"] = max(1, min(12, int(cfg.get("combo_learning_max_priority_boost") or 8)))
    except Exception:
        cfg["combo_learning_max_priority_boost"] = 8
    cfg["combo_bundle_learning_enabled"] = bool(cfg.get("combo_bundle_learning_enabled", True))
    try:
        cfg["combo_bundle_min_runs"] = max(1, int(cfg.get("combo_bundle_min_runs") or 2))
    except Exception:
        cfg["combo_bundle_min_runs"] = 2
    try:
        cfg["combo_bundle_max_priority_boost"] = max(1, min(12, int(cfg.get("combo_bundle_max_priority_boost") or 10)))
    except Exception:
        cfg["combo_bundle_max_priority_boost"] = 10
    cfg["combo_context_bundle_learning_enabled"] = bool(cfg.get("combo_context_bundle_learning_enabled", True))
    try:
        cfg["combo_context_bundle_min_runs"] = max(1, int(cfg.get("combo_context_bundle_min_runs") or 2))
    except Exception:
        cfg["combo_context_bundle_min_runs"] = 2
    try:
        cfg["combo_context_bundle_max_priority_boost"] = max(1, min(14, int(cfg.get("combo_context_bundle_max_priority_boost") or 12)))
    except Exception:
        cfg["combo_context_bundle_max_priority_boost"] = 12
    cfg["combo_context_bundle_partial_match_enabled"] = bool(cfg.get("combo_context_bundle_partial_match_enabled", True))
    try:
        cfg["combo_context_bundle_partial_min_match_count"] = max(
            1,
            min(4, int(cfg.get("combo_context_bundle_partial_min_match_count") or 2)),
        )
    except Exception:
        cfg["combo_context_bundle_partial_min_match_count"] = 2
    cfg["combo_context_bundle_attribution_enabled"] = bool(cfg.get("combo_context_bundle_attribution_enabled", True))
    try:
        cfg["combo_context_bundle_attribution_min_runs"] = max(
            1,
            int(cfg.get("combo_context_bundle_attribution_min_runs") or 2),
        )
    except Exception:
        cfg["combo_context_bundle_attribution_min_runs"] = 2
    cfg["combo_context_metric_effect_enabled"] = bool(cfg.get("combo_context_metric_effect_enabled", True))
    try:
        cfg["combo_context_metric_effect_min_runs"] = max(
            1,
            int(cfg.get("combo_context_metric_effect_min_runs") or 2),
        )
    except Exception:
        cfg["combo_context_metric_effect_min_runs"] = 2
    cfg["combo_context_metric_action_effect_enabled"] = bool(cfg.get("combo_context_metric_action_effect_enabled", True))
    try:
        cfg["combo_context_metric_action_effect_min_runs"] = max(
            1,
            int(cfg.get("combo_context_metric_action_effect_min_runs") or 2),
        )
    except Exception:
        cfg["combo_context_metric_action_effect_min_runs"] = 2
    cfg["task_parallelism_enabled"] = bool(cfg.get("task_parallelism_enabled", True))
    try:
        cfg["task_parallelism_min_runs"] = max(1, int(cfg.get("task_parallelism_min_runs") or 2))
    except Exception:
        cfg["task_parallelism_min_runs"] = 2
    try:
        cfg["task_parallelism_max_delta"] = max(1, min(2, int(cfg.get("task_parallelism_max_delta") or 2)))
    except Exception:
        cfg["task_parallelism_max_delta"] = 2
    return cfg


def _default_profile() -> Dict[str, Any]:
    return {
        "version": "runtime_budget_profile_v1",
        "updated_at": "",
        "entries": {},
    }


def _bucket_pages(planned_pages: int) -> str:
    pages = max(0, int(planned_pages or 0))
    if pages <= 0:
        return "unknown"
    if pages <= 12:
        return "small"
    if pages <= 24:
        return "mid_small"
    if pages <= 40:
        return "mid"
    if pages <= 80:
        return "large"
    return "xlarge"


def _bucket_outline(outline_count: int) -> str:
    count = max(0, int(outline_count or 0))
    if count <= 0:
        return "unknown"
    if count <= 4:
        return "compact"
    if count <= 8:
        return "standard"
    if count <= 12:
        return "extended"
    return "huge"


def _read_profile_unlocked() -> Dict[str, Any]:
    if not RUNTIME_BUDGET_PROFILE_PATH.exists():
        return _default_profile()
    try:
        data = json.loads(RUNTIME_BUDGET_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_profile()
    if not isinstance(data, dict):
        return _default_profile()
    out = _default_profile()
    out.update(data)
    if not isinstance(out.get("entries"), dict):
        out["entries"] = {}
    return out


def _read_task_parallelism_profile_unlocked() -> Dict[str, Any]:
    if not TASK_PARALLELISM_PROFILE_PATH.exists():
        return _default_profile()
    try:
        data = json.loads(TASK_PARALLELISM_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_profile()
    if not isinstance(data, dict):
        return _default_profile()
    out = _default_profile()
    out.update(data)
    if not isinstance(out.get("entries"), dict):
        out["entries"] = {}
    return out


def _write_profile_unlocked(profile: Dict[str, Any]) -> str:
    payload = _default_profile()
    if isinstance(profile, dict):
        payload.update(profile)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    if not isinstance(payload.get("entries"), dict):
        payload["entries"] = {}
    RUNTIME_BUDGET_PROFILE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(RUNTIME_BUDGET_PROFILE_PATH)


def _write_task_parallelism_profile_unlocked(profile: Dict[str, Any]) -> str:
    payload = _default_profile()
    if isinstance(profile, dict):
        payload.update(profile)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    if not isinstance(payload.get("entries"), dict):
        payload["entries"] = {}
    TASK_PARALLELISM_PROFILE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(TASK_PARALLELISM_PROFILE_PATH)


def load_runtime_budget_profile() -> Dict[str, Any]:
    RUNTIME_BUDGET_PROFILE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with RUNTIME_BUDGET_PROFILE_LOCK.open("a+", encoding="utf-8") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_SH)
        try:
            return _read_profile_unlocked()
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def load_task_parallelism_profile() -> Dict[str, Any]:
    TASK_PARALLELISM_PROFILE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with TASK_PARALLELISM_PROFILE_LOCK.open("a+", encoding="utf-8") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_SH)
        try:
            return _read_task_parallelism_profile_unlocked()
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def _update_profile(mutator):
    RUNTIME_BUDGET_PROFILE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with RUNTIME_BUDGET_PROFILE_LOCK.open("a+", encoding="utf-8") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        try:
            profile = _read_profile_unlocked()
            result = mutator(profile)
            _write_profile_unlocked(profile)
            return result
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def _maintain_profile(
    *,
    profile_path: Path,
    lock_path: Path,
    read_unlocked,
    write_unlocked,
    profile_version: str,
    soft_limit: int,
    stale_days: int,
    min_runs_to_keep: int,
) -> Dict[str, Any]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        try:
            profile = read_unlocked()
            before_version = str(profile.get("version") or "")
            before_maintenance = dict(profile.get("maintenance") or {}) if isinstance(profile.get("maintenance"), dict) else {}
            maintenance = _apply_profile_maintenance(
                profile,
                soft_limit=soft_limit,
                stale_days=stale_days,
                min_runs_to_keep=min_runs_to_keep,
            )
            profile["version"] = profile_version
            changed = (
                before_version != profile_version
                or before_maintenance != maintenance
                or int(maintenance.get("pruned_entry_count") or 0) > 0
            )
            if changed:
                write_unlocked(profile)
            return {
                "enabled": True,
                "profile_path": str(profile_path),
                "profile_version": profile_version,
                "changed": bool(changed),
                "entry_count": len(profile.get("entries") or {}),
                "maintenance": maintenance,
            }
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def maintain_runtime_budget_profile(*, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    if not cfg.get("enabled"):
        return {"enabled": False, "profile_path": str(RUNTIME_BUDGET_PROFILE_PATH), "changed": False, "entry_count": 0}
    return _maintain_profile(
        profile_path=RUNTIME_BUDGET_PROFILE_PATH,
        lock_path=RUNTIME_BUDGET_PROFILE_LOCK,
        read_unlocked=_read_profile_unlocked,
        write_unlocked=_write_profile_unlocked,
        profile_version="runtime_budget_profile_v1",
        soft_limit=int(cfg.get("runtime_profile_soft_limit") or 160),
        stale_days=int(cfg.get("runtime_profile_stale_days") or 21),
        min_runs_to_keep=int(cfg.get("runtime_profile_min_runs_to_keep") or 2),
    )


def maintain_task_parallelism_profile(*, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    if not cfg.get("enabled") or not cfg.get("task_parallelism_enabled"):
        return {"enabled": False, "profile_path": str(TASK_PARALLELISM_PROFILE_PATH), "changed": False, "entry_count": 0}
    return _maintain_profile(
        profile_path=TASK_PARALLELISM_PROFILE_PATH,
        lock_path=TASK_PARALLELISM_PROFILE_LOCK,
        read_unlocked=_read_task_parallelism_profile_unlocked,
        write_unlocked=_write_task_parallelism_profile_unlocked,
        profile_version="task_parallelism_profile_v1",
        soft_limit=int(cfg.get("task_parallelism_profile_soft_limit") or 96),
        stale_days=int(cfg.get("task_parallelism_profile_stale_days") or 30),
        min_runs_to_keep=int(cfg.get("task_parallelism_profile_min_runs_to_keep") or 2),
    )


def run_self_evolution_maintenance(*, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    runtime = maintain_runtime_budget_profile(params=params)
    task_parallelism = maintain_task_parallelism_profile(params=params)
    return {
        "enabled": bool(runtime.get("enabled") or task_parallelism.get("enabled")),
        "runtime_budget_profile": runtime,
        "task_parallelism_profile": task_parallelism,
    }


def _profile_key(title: str, project_type: str, generation_mode: str) -> str:
    ttl = str(title or "").strip()
    ptype = normalize_project_type(str(project_type or "").strip()) or "通用"
    mode = str(generation_mode or "").strip() or "quality_200"
    digest = hashlib.sha1(f"{ptype}|{mode}|{ttl}".encode("utf-8")).hexdigest()[:12]
    return f"{ptype}::{mode}::{digest}"


def _task_parallelism_profile_key(
    project_type: str,
    generation_mode: str,
    planned_pages: int,
    outline_count: int,
    variants_total: int,
) -> str:
    ptype = normalize_project_type(str(project_type or "").strip()) or "通用"
    mode = str(generation_mode or "").strip() or "quality_200"
    page_bucket = _bucket_pages(planned_pages)
    outline_bucket = _bucket_outline(outline_count)
    variant_bucket = "multi" if int(variants_total or 1) >= 2 else "single"
    digest = hashlib.sha1(
        f"{ptype}|{mode}|{page_bucket}|{outline_bucket}|{variant_bucket}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{ptype}::{mode}::{page_bucket}::{outline_bucket}::{variant_bucket}::{digest}"


def _iter_constraint_statuses(section: Dict[str, Any]) -> Iterable[str]:
    logs = section.get("constraint_log") if isinstance(section.get("constraint_log"), list) else []
    for row in logs:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "").strip()
        if status:
            yield status


def _section_has_compaction(section: Dict[str, Any]) -> bool:
    return any(status in {"compacted", "postprocess_compacted"} for status in _iter_constraint_statuses(section))


def _primary_text_key_alias(payload: Dict[str, Any], result: Dict[str, Any]) -> str:
    generation_trace = result.get("generation_trace") if isinstance(result.get("generation_trace"), dict) else {}
    chain = generation_trace.get("provider_chain") if isinstance(generation_trace.get("provider_chain"), list) else []
    for item in chain:
        if not isinstance(item, dict):
            continue
        alias = str(item.get("key_alias") or "").strip()
        if alias:
            return alias
    chain = payload.get("provider_chain") if isinstance(payload.get("provider_chain"), list) else []
    for item in chain:
        if not isinstance(item, dict):
            continue
        alias = str(item.get("key_alias") or "").strip()
        if alias:
            return alias
    return "OPENAI_API_KEY_TEXT_MAIN"


def _collect_quality_issue_titles(quality: Dict[str, Any]) -> set[str]:
    out: set[str] = set()
    category_paths = [
        ("risk_triplet", "by_section"),
        ("quantitative", "by_section"),
        ("vague_terms", "by_section"),
        ("evidence_quality", "by_section"),
        ("evidence_traceability", "by_section"),
        ("agent_contract", "by_section"),
    ]
    for cat, field in category_paths:
        branch = quality.get(cat) if isinstance(quality.get(cat), dict) else {}
        rows = branch.get(field) if isinstance(branch.get(field), list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            if not title:
                continue
            if cat == "agent_contract":
                has_issue = (not bool(row.get("ok", True))) or bool(row.get("errors") or [])
            else:
                has_issue = not bool(row.get("ok", True))
            if has_issue:
                out.add(title)
    return out


def _safe_avg(total: float, runs: int) -> float:
    if runs <= 0:
        return 0.0
    return round(float(total) / float(runs), 2)


def _parse_updated_at(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _entry_signal(entry: Dict[str, Any] | None) -> int:
    if not isinstance(entry, dict):
        return 0
    return (
        int(entry.get("quality_issue_runs") or 0)
        + int(entry.get("fallback_runs") or 0)
        + int(entry.get("error_runs") or 0)
        + int(entry.get("compaction_runs") or 0)
        + int(entry.get("hard_failure_runs") or 0)
    )


def _is_dry_run_sample(payload: Dict[str, Any] | None, result: Dict[str, Any] | None = None) -> bool:
    if isinstance(result, dict) and bool(result.get("dry_run")):
        return True
    if isinstance(payload, dict) and bool(payload.get("dry_run")):
        return True
    return False


def _apply_profile_maintenance(
    profile: Dict[str, Any],
    *,
    soft_limit: int,
    stale_days: int,
    min_runs_to_keep: int,
) -> Dict[str, Any]:
    entries = profile.get("entries") if isinstance(profile.get("entries"), dict) else {}
    if not isinstance(entries, dict):
        profile["entries"] = {}
        entries = profile["entries"]
    previous_maintenance = profile.get("maintenance") if isinstance(profile.get("maintenance"), dict) else {}
    previous_compacted_at = str(previous_maintenance.get("last_compacted_at") or "").strip()
    now = datetime.now()
    stale_before = now - timedelta(days=max(1, int(stale_days or 1)))
    stale_pruned = 0
    overflow_pruned = 0

    for key, entry in list(entries.items()):
        if not isinstance(entry, dict):
            entries.pop(key, None)
            stale_pruned += 1
            continue
        runs = int(entry.get("runs") or 0)
        updated_at = _parse_updated_at(entry.get("last_updated_at"))
        if updated_at is not None and updated_at < stale_before and runs < int(min_runs_to_keep or 1):
            entries.pop(key, None)
            stale_pruned += 1

    overflow = max(0, len(entries) - max(1, int(soft_limit or 1)))
    if overflow > 0:
        ranked = sorted(
            entries.items(),
            key=lambda item: (
                int((item[1] or {}).get("runs") or 0),
                _entry_signal(item[1] if isinstance(item[1], dict) else {}),
                _parse_updated_at((item[1] or {}).get("last_updated_at")) or datetime.min,
                str((item[1] or {}).get("title") or ""),
                str(item[0]),
            ),
        )
        for key, _entry in ranked[:overflow]:
            entries.pop(key, None)
            overflow_pruned += 1

    maintenance = {
        "retained_entry_count": len(entries),
        "pruned_entry_count": int(stale_pruned + overflow_pruned),
        "stale_pruned": int(stale_pruned),
        "overflow_pruned": int(overflow_pruned),
        "soft_limit": max(1, int(soft_limit or 1)),
        "stale_days": max(1, int(stale_days or 1)),
        "min_runs_to_keep": max(1, int(min_runs_to_keep or 1)),
        "last_compacted_at": now.strftime("%Y-%m-%dT%H:%M:%S")
        if int(stale_pruned + overflow_pruned) > 0
        else previous_compacted_at,
    }
    profile["maintenance"] = maintenance
    return maintenance


def build_chapter_effect_summary(source: Dict[str, Any] | None, *, limit: int = 6) -> List[Dict[str, Any]]:
    payload = source if isinstance(source, dict) else {}
    metric_details = (
        payload.get("remediation_context_bundle_learning_metric_details")
        if isinstance(payload.get("remediation_context_bundle_learning_metric_details"), list)
        else payload.get("metric_details")
    )
    action_details = (
        payload.get("remediation_context_bundle_learning_metric_action_details")
        if isinstance(payload.get("remediation_context_bundle_learning_metric_action_details"), list)
        else payload.get("metric_action_details")
    )
    by_title: Dict[str, Dict[str, Any]] = {}
    for detail in metric_details or []:
        if not isinstance(detail, dict):
            continue
        title = str(detail.get("title") or "").strip()
        if not title:
            continue
        bucket = by_title.setdefault(
            title,
            {
                "title": title,
                "resolved_metrics": [],
                "resolved_action_triplets": [],
                "bundles": [],
                "reasons": [],
                "source_runs": 0,
                "attribution_runs": 0,
            },
        )
        metric_label = str(detail.get("metric_label") or detail.get("metric") or "").strip()
        bundle = str(detail.get("bundle") or "").strip()
        reason = str(detail.get("reason") or "").strip()
        if metric_label and metric_label not in bucket["resolved_metrics"]:
            bucket["resolved_metrics"].append(metric_label)
        if bundle and bundle not in bucket["bundles"]:
            bucket["bundles"].append(bundle)
        if reason and reason not in bucket["reasons"]:
            bucket["reasons"].append(reason)
        bucket["source_runs"] = max(bucket["source_runs"], int(detail.get("source_runs") or 0))
        bucket["attribution_runs"] = max(bucket["attribution_runs"], int(detail.get("attribution_runs") or 0))
    for detail in action_details or []:
        if not isinstance(detail, dict):
            continue
        title = str(detail.get("title") or "").strip()
        if not title:
            continue
        bucket = by_title.setdefault(
            title,
            {
                "title": title,
                "resolved_metrics": [],
                "resolved_action_triplets": [],
                "bundles": [],
                "reasons": [],
                "source_runs": 0,
                "attribution_runs": 0,
            },
        )
        triplet = str(detail.get("metric_action_triplet") or "").strip()
        bundle = str(detail.get("bundle") or "").strip()
        reason = str(detail.get("reason") or "").strip()
        if triplet and triplet not in bucket["resolved_action_triplets"]:
            bucket["resolved_action_triplets"].append(triplet)
        if bundle and bundle not in bucket["bundles"]:
            bucket["bundles"].append(bundle)
        if reason and reason not in bucket["reasons"]:
            bucket["reasons"].append(reason)
        bucket["source_runs"] = max(bucket["source_runs"], int(detail.get("source_runs") or 0))
        bucket["attribution_runs"] = max(bucket["attribution_runs"], int(detail.get("attribution_runs") or 0))
    rows: List[Dict[str, Any]] = []
    for title, bucket in by_title.items():
        rows.append(
            {
                "title": title,
                "resolved_metric_count": len(bucket["resolved_metrics"]),
                "resolved_metrics": bucket["resolved_metrics"][:4],
                "resolved_action_count": len(bucket["resolved_action_triplets"]),
                "resolved_action_triplets": bucket["resolved_action_triplets"][:6],
                "bundles": bucket["bundles"][:2],
                "reasons": bucket["reasons"][:3],
                "source_runs": int(bucket["source_runs"] or 0),
                "attribution_runs": int(bucket["attribution_runs"] or 0),
            }
        )
    rows.sort(
        key=lambda item: (
            -int(item.get("resolved_metric_count") or 0),
            -int(item.get("resolved_action_count") or 0),
            -int(item.get("attribution_runs") or 0),
            str(item.get("title") or ""),
        )
    )
    return rows[: max(1, int(limit or 6))]


def _top_counter_items(counter_map: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(counter_map, dict):
        return []
    rows = [
        (str(name).strip(), int(count or 0))
        for name, count in counter_map.items()
        if str(name).strip() and int(count or 0) > 0
    ]
    rows.sort(key=lambda item: (-int(item[1]), str(item[0])))
    return [f"{name}:{count}" for name, count in rows[: max(1, int(limit or 3))]]


def _top_context_signature_items(counter_map: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(counter_map, dict):
        return []
    rows = [
        (_format_context_signature(str(name).strip()), int(count or 0))
        for name, count in counter_map.items()
        if str(name).strip() and int(count or 0) > 0
    ]
    rows = [(name, count) for name, count in rows if name]
    rows.sort(key=lambda item: (-int(item[1]), str(item[0])))
    return [f"{name}:{count}" for name, count in rows[: max(1, int(limit or 3))]]


def _combo_key(indicator_group: str, strategy_id: str, action_tag: str) -> str:
    return "||".join(
        [
            str(indicator_group or "").strip(),
            str(strategy_id or "").strip(),
            str(action_tag or "").strip(),
        ]
    )


def _split_combo_key(raw: str) -> tuple[str, str, str]:
    parts = str(raw or "").split("||", 2)
    while len(parts) < 3:
        parts.append("")
    return tuple(str(x or "").strip() for x in parts[:3])  # type: ignore[return-value]


def _normalize_combo_ids(combo_ids: Iterable[str], *, limit: int = 4) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for raw in combo_ids:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    out.sort()
    return out[: max(1, int(limit or 4))]


def _bundle_key(combo_ids: Iterable[str]) -> str:
    combos = _normalize_combo_ids(combo_ids, limit=4)
    if len(combos) < 2:
        return ""
    return "§§".join(combos)


def _split_bundle_key(raw: str) -> List[str]:
    return _normalize_combo_ids(str(raw or "").split("§§"), limit=8)


def _context_signature(chapter_domain: str | None, template_id: str | None) -> str:
    domain = str(chapter_domain or "").strip().lower() or "general"
    template = str(template_id or "").strip().upper() or "GEN"
    return f"{domain}|{template}"


def _format_context_signature(raw: str) -> str:
    domain, template = _split_context_signature(raw)
    if not domain and not template:
        return ""
    return f"{domain or 'general'}/{template or 'GEN'}"


def _split_context_signature(raw: str) -> tuple[str, str]:
    parts = str(raw or "").split("|", 1)
    while len(parts) < 2:
        parts.append("")
    return str(parts[0] or "").strip().lower(), str(parts[1] or "").strip().upper()


def _context_bundle_key(context_signature: str, combo_ids: Iterable[str]) -> str:
    signature = str(context_signature or "").strip()
    bundle_id = _bundle_key(combo_ids)
    if not signature or not bundle_id:
        return ""
    return f"{signature}@@{bundle_id}"


def _split_context_bundle_key(raw: str) -> tuple[str, List[str]]:
    signature, _, bundle_raw = str(raw or "").partition("@@")
    return str(signature or "").strip(), _split_bundle_key(bundle_raw)


def _context_metric_key(context_bundle_id: str, metric: str) -> str:
    bundle_id = str(context_bundle_id or "").strip()
    metric_name = str(metric or "").strip()
    if not bundle_id or not metric_name:
        return ""
    return f"{bundle_id}##{metric_name}"


def _split_context_metric_key(raw: str) -> tuple[str, str]:
    bundle_id, _, metric_name = str(raw or "").rpartition("##")
    if not bundle_id and metric_name:
        return "", metric_name.strip()
    return str(bundle_id or "").strip(), str(metric_name or "").strip()


def _context_metric_action_key(context_bundle_id: str, metric: str, action_tag: str) -> str:
    bundle_id = str(context_bundle_id or "").strip()
    metric_name = str(metric or "").strip()
    action_name = str(action_tag or "").strip()
    if not bundle_id or not metric_name or not action_name:
        return ""
    return f"{bundle_id}##{metric_name}##{action_name}"


def _split_context_metric_action_key(raw: str) -> tuple[str, str, str]:
    parts = str(raw or "").split("##")
    if len(parts) < 3:
        return "", "", ""
    action_name = str(parts[-1] or "").strip()
    metric_name = str(parts[-2] or "").strip()
    bundle_id = "##".join(parts[:-2]).strip()
    return bundle_id, metric_name, action_name


def _indicator_groups_by_title(report: Dict[str, Any] | None) -> Dict[str, set[str]]:
    out: Dict[str, set[str]] = {}
    issue_list = report.get("issue_list") if isinstance(report, dict) and isinstance(report.get("issue_list"), list) else []
    for row in issue_list:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        indicator_group = str(row.get("indicator_group") or "").strip()
        if not title or not indicator_group:
            continue
        out.setdefault(title, set()).add(indicator_group)
    return out


def _strategy_ids_by_title(report: Dict[str, Any] | None) -> Dict[str, set[str]]:
    out: Dict[str, set[str]] = {}
    audit = report.get("remediation_strategy_audit") if isinstance(report, dict) and isinstance(report.get("remediation_strategy_audit"), dict) else {}
    rows = audit.get("by_title") if isinstance(audit.get("by_title"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        for strategy_id in row.get("strategy_ids") if isinstance(row.get("strategy_ids"), list) else []:
            name = str(strategy_id or "").strip()
            if name:
                out.setdefault(title, set()).add(name)
    return out


def _action_tags_by_title(report: Dict[str, Any] | None) -> Dict[str, set[str]]:
    out: Dict[str, set[str]] = {}
    audit = report.get("remediation_execution_audit") if isinstance(report, dict) and isinstance(report.get("remediation_execution_audit"), dict) else {}
    rows = audit.get("by_title") if isinstance(audit.get("by_title"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        for action_tag in row.get("action_tags") if isinstance(row.get("action_tags"), list) else []:
            name = str(action_tag or "").strip()
            if name:
                out.setdefault(title, set()).add(name)
    return out


def _execution_combos_by_title(sections: list[dict[str, Any]] | None) -> Dict[str, list[dict[str, Any]]]:
    out: Dict[str, list[dict[str, Any]]] = {}
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        traces = section.get("remediation_execution_trace") if isinstance(section.get("remediation_execution_trace"), list) else []
        for row in traces:
            if not isinstance(row, dict):
                continue
            indicator_group = str(row.get("indicator_group") or "").strip()
            strategy_id = str(row.get("strategy_id") or "").strip()
            if not indicator_group or not strategy_id:
                continue
            matched = [
                str(x).strip()
                for x in (row.get("matched_action_tags") or [])
                if str(x).strip()
            ]
            detected = [
                str(x).strip()
                for x in (row.get("detected_action_tags") or [])
                if str(x).strip()
            ]
            expected = [
                str(x).strip()
                for x in (row.get("expected_action_tags") or [])
                if str(x).strip()
            ]
            action_tags = matched or detected or expected
            if not action_tags:
                continue
            out.setdefault(title, []).append(
                {
                    "indicator_group": indicator_group,
                    "strategy_id": strategy_id,
                    "action_tags": action_tags,
                    "execution_status": str(row.get("execution_status") or "").strip(),
                }
            )
    return out


def _top_effective_combos(entry: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(entry, dict):
        return []
    attempts_map = entry.get("combo_attempt_counts") if isinstance(entry.get("combo_attempt_counts"), dict) else {}
    close_map = entry.get("combo_indicator_close_counts") if isinstance(entry.get("combo_indicator_close_counts"), dict) else {}
    gate_map = entry.get("combo_gate_pass_counts") if isinstance(entry.get("combo_gate_pass_counts"), dict) else {}
    rows: list[tuple[float, str]] = []
    for combo_id, attempts_raw in attempts_map.items():
        attempts = int(attempts_raw or 0)
        if attempts <= 0:
            continue
        close_cnt = int(close_map.get(combo_id) or 0)
        gate_cnt = int(gate_map.get(combo_id) or 0)
        close_rate = float(close_cnt) / float(attempts)
        gate_rate = float(gate_cnt) / float(attempts)
        indicator_group, strategy_id, action_tag = _split_combo_key(str(combo_id))
        if not indicator_group or not strategy_id or not action_tag:
            continue
        score = (close_rate * 100.0) + (gate_rate * 10.0) + min(5.0, float(attempts))
        text = (
            f"{indicator_group}/{strategy_id}/{action_tag}"
            f" close={close_rate:.0%} pass={gate_rate:.0%} n={attempts}"
        )
        rows.append((score, text))
    rows.sort(key=lambda item: (-float(item[0]), str(item[1])))
    return [text for _, text in rows[: max(1, int(limit or 3))]]


def _format_bundle_display(bundle_id: str, *, attempts: int, pass_rate: float) -> str:
    combo_labels: List[str] = []
    for combo_id in _split_bundle_key(bundle_id)[:3]:
        indicator_group, strategy_id, action_tag = _split_combo_key(combo_id)
        if indicator_group and strategy_id and action_tag:
            combo_labels.append(f"{indicator_group}/{strategy_id}/{action_tag}")
    joined = " + ".join(combo_labels) if combo_labels else str(bundle_id or "").strip()
    return f"{joined} pass={pass_rate:.0%} n={attempts}"


def _top_effective_combo_bundles(entry: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(entry, dict):
        return []
    attempts_map = entry.get("combo_bundle_attempt_counts") if isinstance(entry.get("combo_bundle_attempt_counts"), dict) else {}
    gate_map = entry.get("combo_bundle_gate_pass_counts") if isinstance(entry.get("combo_bundle_gate_pass_counts"), dict) else {}
    rows: list[tuple[float, str]] = []
    for bundle_id, attempts_raw in attempts_map.items():
        attempts = int(attempts_raw or 0)
        if attempts <= 0:
            continue
        combos = _split_bundle_key(str(bundle_id))
        if len(combos) < 2:
            continue
        gate_cnt = int(gate_map.get(bundle_id) or 0)
        pass_rate = float(gate_cnt) / float(attempts)
        score = (pass_rate * 100.0) + min(8.0, float(attempts))
        rows.append((score, _format_bundle_display(str(bundle_id), attempts=attempts, pass_rate=pass_rate)))
    rows.sort(key=lambda item: (-float(item[0]), str(item[1])))
    return [text for _, text in rows[: max(1, int(limit or 3))]]


def _format_context_bundle_display(
    context_signature: str,
    bundle_id: str,
    *,
    attempts: int,
    pass_rate: float,
) -> str:
    context_label = _format_context_signature(context_signature)
    bundle_label = _format_bundle_display(bundle_id, attempts=attempts, pass_rate=pass_rate)
    if context_label:
        return f"{context_label} | {bundle_label}"
    return bundle_label


def _top_effective_context_bundles(entry: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(entry, dict):
        return []
    attempts_map = entry.get("combo_context_bundle_attempt_counts") if isinstance(entry.get("combo_context_bundle_attempt_counts"), dict) else {}
    gate_map = entry.get("combo_context_bundle_gate_pass_counts") if isinstance(entry.get("combo_context_bundle_gate_pass_counts"), dict) else {}
    rows: list[tuple[float, str]] = []
    for context_bundle_id, attempts_raw in attempts_map.items():
        attempts = int(attempts_raw or 0)
        if attempts <= 0:
            continue
        context_signature, bundle_combos = _split_context_bundle_key(str(context_bundle_id))
        bundle_id = _bundle_key(bundle_combos)
        if not context_signature or not bundle_id:
            continue
        gate_cnt = int(gate_map.get(context_bundle_id) or 0)
        pass_rate = float(gate_cnt) / float(attempts)
        score = (pass_rate * 100.0) + min(10.0, float(attempts)) + (3.0 if context_signature else 0.0)
        rows.append(
            (
                score,
                _format_context_bundle_display(
                    context_signature,
                    bundle_id,
                    attempts=attempts,
                    pass_rate=pass_rate,
                ),
            )
        )
    rows.sort(key=lambda item: (-float(item[0]), str(item[1])))
    return [text for _, text in rows[: max(1, int(limit or 3))]]


def _top_attributed_context_bundles(entry: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(entry, dict):
        return []
    attempts_map = (
        entry.get("combo_context_bundle_learning_attempt_counts")
        if isinstance(entry.get("combo_context_bundle_learning_attempt_counts"), dict)
        else {}
    )
    gate_map = (
        entry.get("combo_context_bundle_learning_gate_pass_counts")
        if isinstance(entry.get("combo_context_bundle_learning_gate_pass_counts"), dict)
        else {}
    )
    rows: list[tuple[float, str]] = []
    for context_bundle_id, attempts_raw in attempts_map.items():
        attempts = int(attempts_raw or 0)
        if attempts <= 0:
            continue
        context_signature, bundle_combos = _split_context_bundle_key(str(context_bundle_id))
        bundle_id = _bundle_key(bundle_combos)
        if not context_signature or not bundle_id:
            continue
        gate_cnt = int(gate_map.get(context_bundle_id) or 0)
        pass_rate = float(gate_cnt) / float(attempts)
        score = (pass_rate * 100.0) + min(12.0, float(attempts))
        rows.append(
            (
                score,
                _format_context_bundle_display(
                    context_signature,
                    bundle_id,
                    attempts=attempts,
                    pass_rate=pass_rate,
                ).replace(" pass=", " attributed_pass="),
            )
        )
    rows.sort(key=lambda item: (-float(item[0]), str(item[1])))
    return [text for _, text in rows[: max(1, int(limit or 3))]]


def _top_context_metric_effects(entry: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(entry, dict):
        return []
    attempts_map = (
        entry.get("combo_context_metric_attempt_counts")
        if isinstance(entry.get("combo_context_metric_attempt_counts"), dict)
        else {}
    )
    resolved_map = (
        entry.get("combo_context_metric_resolved_counts")
        if isinstance(entry.get("combo_context_metric_resolved_counts"), dict)
        else {}
    )
    rows: list[tuple[float, str]] = []
    for effect_key, attempts_raw in attempts_map.items():
        attempts = int(attempts_raw or 0)
        if attempts <= 0:
            continue
        context_bundle_id, metric_name = _split_context_metric_key(str(effect_key))
        if not context_bundle_id or not metric_name:
            continue
        context_signature, bundle_combos = _split_context_bundle_key(context_bundle_id)
        bundle_id = _bundle_key(bundle_combos)
        if not context_signature or not bundle_id:
            continue
        resolved_cnt = int(resolved_map.get(effect_key) or 0)
        resolved_rate = float(resolved_cnt) / float(attempts)
        metric_label = str(metric_name or "").strip()
        bundle_label = _format_context_bundle_display(
            context_signature,
            bundle_id,
            attempts=attempts,
            pass_rate=resolved_rate,
        ).replace(" pass=", " metric_resolve=")
        score = (resolved_rate * 100.0) + min(12.0, float(attempts))
        rows.append((score, f"{metric_label} | {bundle_label}"))
    rows.sort(key=lambda item: (-float(item[0]), str(item[1])))
    return [text for _, text in rows[: max(1, int(limit or 3))]]


def _top_context_metric_action_effects(entry: Dict[str, Any] | None, *, limit: int = 3) -> List[str]:
    if not isinstance(entry, dict):
        return []
    attempts_map = (
        entry.get("combo_context_metric_action_attempt_counts")
        if isinstance(entry.get("combo_context_metric_action_attempt_counts"), dict)
        else {}
    )
    resolved_map = (
        entry.get("combo_context_metric_action_resolved_counts")
        if isinstance(entry.get("combo_context_metric_action_resolved_counts"), dict)
        else {}
    )
    rows: list[tuple[float, str]] = []
    for effect_key, attempts_raw in attempts_map.items():
        attempts = int(attempts_raw or 0)
        if attempts <= 0:
            continue
        context_bundle_id, metric_name, action_tag = _split_context_metric_action_key(str(effect_key))
        if not context_bundle_id or not metric_name or not action_tag:
            continue
        context_signature, bundle_combos = _split_context_bundle_key(context_bundle_id)
        bundle_id = _bundle_key(bundle_combos)
        if not context_signature or not bundle_id:
            continue
        resolved_cnt = int(resolved_map.get(effect_key) or 0)
        resolved_rate = float(resolved_cnt) / float(attempts)
        action_label = str(ACTION_TAG_LABELS.get(action_tag) or action_tag).strip()
        bundle_label = _format_context_bundle_display(
            context_signature,
            bundle_id,
            attempts=attempts,
            pass_rate=resolved_rate,
        ).replace(" pass=", " triplet_resolve=")
        score = (resolved_rate * 100.0) + min(12.0, float(attempts))
        rows.append((score, f"{metric_name}/{action_label} | {bundle_label}"))
    rows.sort(key=lambda item: (-float(item[0]), str(item[1])))
    return [text for _, text in rows[: max(1, int(limit or 3))]]


def record_runtime_learning(
    payload: Dict[str, Any],
    results: list[Dict[str, Any]],
    *,
    params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    if not cfg.get("enabled"):
        return {"enabled": False, "updated_entries": 0, "profile_path": str(RUNTIME_BUDGET_PROFILE_PATH)}

    def _mutate(profile: Dict[str, Any]) -> Dict[str, Any]:
        entries = profile.setdefault("entries", {})
        updated: Dict[str, Dict[str, Any]] = {}
        skipped_dry_run_results = 0
        for result in results or []:
            if not isinstance(result, dict):
                continue
            if bool(cfg.get("ignore_dry_run_learning", True)) and _is_dry_run_sample(payload, result):
                skipped_dry_run_results += 1
                continue
            project_type = str(result.get("project_type") or payload.get("project_type") or "").strip() or "通用"
            generation_mode = str(result.get("generation_mode") or payload.get("generation_mode") or "").strip() or "quality_200"
            quality_draft = result.get("quality_checks_draft") if isinstance(result.get("quality_checks_draft"), dict) else {}
            quality = result.get("quality_checks") if isinstance(result.get("quality_checks"), dict) else {}
            quality_issue_titles = _collect_quality_issue_titles(quality)
            quality_gate = result.get("quality_gate") if isinstance(result.get("quality_gate"), dict) else {}
            primary_alias = _primary_text_key_alias(payload, result)
            draft_indicator_groups_by_title = _indicator_groups_by_title(quality_draft)
            if not draft_indicator_groups_by_title:
                draft_indicator_groups_by_title = _indicator_groups_by_title(quality)
            indicator_groups_by_title = _indicator_groups_by_title(quality)
            strategy_ids_by_title = _strategy_ids_by_title(quality)
            action_tags_by_title = _action_tags_by_title(quality)
            generation_trace = result.get("generation_trace") if isinstance(result.get("generation_trace"), dict) else {}
            self_evolution_trace = generation_trace.get("self_evolution") if isinstance(generation_trace.get("self_evolution"), dict) else {}
            context_learning_details = (
                self_evolution_trace.get("remediation_context_bundle_learning_details")
                if isinstance(self_evolution_trace.get("remediation_context_bundle_learning_details"), list)
                else []
            )
            context_learning_details_by_title: Dict[str, List[Dict[str, Any]]] = {}
            for detail in context_learning_details:
                if not isinstance(detail, dict):
                    continue
                detail_title = str(detail.get("title") or "").strip()
                context_bundle_id = str(detail.get("context_bundle_id") or "").strip()
                if not context_bundle_id:
                    context_bundle_id = _context_bundle_key(
                        str(detail.get("context_signature") or "").strip(),
                        detail.get("bundle_combos") if isinstance(detail.get("bundle_combos"), list) else [],
                    )
                if not detail_title or not context_bundle_id:
                    continue
                detail_row = {
                    "context_bundle_id": context_bundle_id,
                    "bundle_display": str(detail.get("bundle") or "").strip(),
                    "source_runs": int(detail.get("source_runs") or 0),
                    "attributed": bool(detail.get("attribution_applied", False)),
                    "attributed_reason": str(detail.get("attribution_reason") or "").strip(),
                    "attributed_gate_pass_rate": float(detail.get("attributed_gate_pass_rate") or 0.0),
                    "attribution_runs": int(detail.get("attribution_runs") or 0),
                }
                bucket = context_learning_details_by_title.setdefault(detail_title, [])
                if detail_row not in bucket:
                    bucket.append(detail_row)
            context_metric_details = (
                self_evolution_trace.get("remediation_context_bundle_learning_metric_details")
                if isinstance(self_evolution_trace.get("remediation_context_bundle_learning_metric_details"), list)
                else []
            )
            context_metric_details_by_title: Dict[str, List[Dict[str, Any]]] = {}
            for detail in context_metric_details:
                if not isinstance(detail, dict):
                    continue
                detail_title = str(detail.get("title") or "").strip()
                context_bundle_id = str(detail.get("context_bundle_id") or "").strip()
                metric_name = str(detail.get("metric") or "").strip()
                if not detail_title or not context_bundle_id or not metric_name:
                    continue
                display_text = str(detail.get("display") or "").strip()
                detail_row = {
                    "context_bundle_id": context_bundle_id,
                    "metric": metric_name,
                    "metric_label": str(detail.get("metric_label") or metric_name).strip(),
                    "resolved": bool(detail.get("metric_resolved", False)),
                    "source_runs": int(detail.get("attribution_runs") or detail.get("source_runs") or 0),
                    "action_tags": [
                        str(x).strip()
                        for x in (detail.get("action_tags") or [])
                        if str(x).strip()
                    ],
                    "action_labels": [
                        str(x).strip()
                        for x in (detail.get("action_labels") or [])
                        if str(x).strip()
                    ],
                    "display": display_text,
                }
                bucket = context_metric_details_by_title.setdefault(detail_title, [])
                if detail_row not in bucket:
                    bucket.append(detail_row)
            sections = result.get("sections") if isinstance(result.get("sections"), list) else []
            execution_combos_by_title = _execution_combos_by_title(sections)
            for section in sections:
                if not isinstance(section, dict):
                    continue
                title = str(section.get("title") or "").strip()
                if not title:
                    continue
                key = _profile_key(title, project_type, generation_mode)
                entry = entries.setdefault(
                    key,
                    {
                        "title": title,
                        "project_type": project_type,
                        "generation_mode": generation_mode,
                        "runs": 0,
                        "success_runs": 0,
                        "error_runs": 0,
                        "fallback_runs": 0,
                        "compaction_runs": 0,
                        "quality_issue_runs": 0,
                        "timeout_total": 0.0,
                        "max_tokens_total": 0.0,
                        "retry_total": 0.0,
                        "last_runtime_budget_reason": "",
                        "last_used_key_alias": "",
                        "indicator_group_counts": {},
                        "strategy_counts": {},
                        "action_tag_counts": {},
                        "context_signature_counts": {},
                        "combo_attempt_counts": {},
                        "combo_indicator_close_counts": {},
                        "combo_gate_pass_counts": {},
                        "combo_bundle_attempt_counts": {},
                        "combo_bundle_gate_pass_counts": {},
                        "combo_context_bundle_attempt_counts": {},
                        "combo_context_bundle_gate_pass_counts": {},
                        "combo_context_bundle_learning_attempt_counts": {},
                        "combo_context_bundle_learning_gate_pass_counts": {},
                        "combo_context_metric_attempt_counts": {},
                        "combo_context_metric_resolved_counts": {},
                        "combo_context_metric_action_attempt_counts": {},
                        "combo_context_metric_action_resolved_counts": {},
                        "last_indicator_groups": [],
                        "last_strategy_ids": [],
                        "last_action_tags": [],
                        "last_effective_combos": [],
                        "last_effective_combo_bundle": [],
                        "last_attributed_context_bundles": [],
                        "last_metric_effects": [],
                        "last_metric_action_effects": [],
                        "last_context_signature": "",
                        "last_updated_at": "",
                    },
                )
                entry["runs"] = int(entry.get("runs") or 0) + 1
                content = str(section.get("content") or "").strip()
                error_text = str(section.get("error") or "").strip()
                success = bool(content) and not error_text and content != "章节生成失败"
                if success:
                    entry["success_runs"] = int(entry.get("success_runs") or 0) + 1
                else:
                    entry["error_runs"] = int(entry.get("error_runs") or 0) + 1
                used_key_alias = str(section.get("used_key_alias") or "").strip()
                if used_key_alias and primary_alias and used_key_alias != primary_alias:
                    entry["fallback_runs"] = int(entry.get("fallback_runs") or 0) + 1
                if _section_has_compaction(section):
                    entry["compaction_runs"] = int(entry.get("compaction_runs") or 0) + 1
                gate_failed_without_titles = (not bool(quality_gate.get("ok", True))) and (not quality_issue_titles)
                if title in quality_issue_titles or gate_failed_without_titles:
                    entry["quality_issue_runs"] = int(entry.get("quality_issue_runs") or 0) + 1
                try:
                    entry["timeout_total"] = float(entry.get("timeout_total") or 0.0) + float(section.get("requested_timeout_sec") or 0.0)
                except Exception:
                    pass
                try:
                    entry["max_tokens_total"] = float(entry.get("max_tokens_total") or 0.0) + float(section.get("requested_max_output_tokens") or 0.0)
                except Exception:
                    pass
                try:
                    entry["retry_total"] = float(entry.get("retry_total") or 0.0) + float(section.get("requested_section_retry_limit") or 0.0)
                except Exception:
                    pass
                for indicator_group in sorted(indicator_groups_by_title.get(title) or []):
                    counter = entry.setdefault("indicator_group_counts", {})
                    if not isinstance(counter, dict):
                        counter = {}
                        entry["indicator_group_counts"] = counter
                    counter[indicator_group] = int(counter.get(indicator_group) or 0) + 1
                for strategy_id in sorted(strategy_ids_by_title.get(title) or []):
                    counter = entry.setdefault("strategy_counts", {})
                    if not isinstance(counter, dict):
                        counter = {}
                        entry["strategy_counts"] = counter
                    counter[strategy_id] = int(counter.get(strategy_id) or 0) + 1
                for action_tag in sorted(action_tags_by_title.get(title) or []):
                    counter = entry.setdefault("action_tag_counts", {})
                    if not isinstance(counter, dict):
                        counter = {}
                        entry["action_tag_counts"] = counter
                    counter[action_tag] = int(counter.get(action_tag) or 0) + 1
                context_signature = _context_signature(
                    section.get("chapter_domain"),
                    section.get("logic_template_id"),
                )
                context_counter = entry.setdefault("context_signature_counts", {})
                if not isinstance(context_counter, dict):
                    context_counter = {}
                    entry["context_signature_counts"] = context_counter
                context_counter[context_signature] = int(context_counter.get(context_signature) or 0) + 1
                final_indicator_groups = set(indicator_groups_by_title.get(title) or [])
                execution_combo_rows = execution_combos_by_title.get(title) or []
                effective_combos_current: list[str] = []
                combo_attempt_counts = entry.setdefault("combo_attempt_counts", {})
                if not isinstance(combo_attempt_counts, dict):
                    combo_attempt_counts = {}
                    entry["combo_attempt_counts"] = combo_attempt_counts
                combo_close_counts = entry.setdefault("combo_indicator_close_counts", {})
                if not isinstance(combo_close_counts, dict):
                    combo_close_counts = {}
                    entry["combo_indicator_close_counts"] = combo_close_counts
                combo_gate_counts = entry.setdefault("combo_gate_pass_counts", {})
                if not isinstance(combo_gate_counts, dict):
                    combo_gate_counts = {}
                    entry["combo_gate_pass_counts"] = combo_gate_counts
                combo_bundle_attempt_counts = entry.setdefault("combo_bundle_attempt_counts", {})
                if not isinstance(combo_bundle_attempt_counts, dict):
                    combo_bundle_attempt_counts = {}
                    entry["combo_bundle_attempt_counts"] = combo_bundle_attempt_counts
                combo_bundle_gate_counts = entry.setdefault("combo_bundle_gate_pass_counts", {})
                if not isinstance(combo_bundle_gate_counts, dict):
                    combo_bundle_gate_counts = {}
                    entry["combo_bundle_gate_pass_counts"] = combo_bundle_gate_counts
                combo_context_bundle_attempt_counts = entry.setdefault("combo_context_bundle_attempt_counts", {})
                if not isinstance(combo_context_bundle_attempt_counts, dict):
                    combo_context_bundle_attempt_counts = {}
                    entry["combo_context_bundle_attempt_counts"] = combo_context_bundle_attempt_counts
                combo_context_bundle_gate_counts = entry.setdefault("combo_context_bundle_gate_pass_counts", {})
                if not isinstance(combo_context_bundle_gate_counts, dict):
                    combo_context_bundle_gate_counts = {}
                    entry["combo_context_bundle_gate_pass_counts"] = combo_context_bundle_gate_counts
                combo_context_bundle_learning_attempt_counts = entry.setdefault("combo_context_bundle_learning_attempt_counts", {})
                if not isinstance(combo_context_bundle_learning_attempt_counts, dict):
                    combo_context_bundle_learning_attempt_counts = {}
                    entry["combo_context_bundle_learning_attempt_counts"] = combo_context_bundle_learning_attempt_counts
                combo_context_bundle_learning_gate_counts = entry.setdefault("combo_context_bundle_learning_gate_pass_counts", {})
                if not isinstance(combo_context_bundle_learning_gate_counts, dict):
                    combo_context_bundle_learning_gate_counts = {}
                    entry["combo_context_bundle_learning_gate_pass_counts"] = combo_context_bundle_learning_gate_counts
                combo_context_metric_attempt_counts = entry.setdefault("combo_context_metric_attempt_counts", {})
                if not isinstance(combo_context_metric_attempt_counts, dict):
                    combo_context_metric_attempt_counts = {}
                    entry["combo_context_metric_attempt_counts"] = combo_context_metric_attempt_counts
                combo_context_metric_resolved_counts = entry.setdefault("combo_context_metric_resolved_counts", {})
                if not isinstance(combo_context_metric_resolved_counts, dict):
                    combo_context_metric_resolved_counts = {}
                    entry["combo_context_metric_resolved_counts"] = combo_context_metric_resolved_counts
                combo_context_metric_action_attempt_counts = entry.setdefault("combo_context_metric_action_attempt_counts", {})
                if not isinstance(combo_context_metric_action_attempt_counts, dict):
                    combo_context_metric_action_attempt_counts = {}
                    entry["combo_context_metric_action_attempt_counts"] = combo_context_metric_action_attempt_counts
                combo_context_metric_action_resolved_counts = entry.setdefault("combo_context_metric_action_resolved_counts", {})
                if not isinstance(combo_context_metric_action_resolved_counts, dict):
                    combo_context_metric_action_resolved_counts = {}
                    entry["combo_context_metric_action_resolved_counts"] = combo_context_metric_action_resolved_counts
                if execution_combo_rows:
                    for combo_row in execution_combo_rows:
                        indicator_group = str(combo_row.get("indicator_group") or "").strip()
                        strategy_id = str(combo_row.get("strategy_id") or "").strip()
                        if not indicator_group or not strategy_id:
                            continue
                        indicator_closed = indicator_group not in final_indicator_groups
                        for action_tag in combo_row.get("action_tags") or []:
                            tag = str(action_tag or "").strip()
                            if not tag:
                                continue
                            combo_id = _combo_key(indicator_group, strategy_id, tag)
                            combo_attempt_counts[combo_id] = int(combo_attempt_counts.get(combo_id) or 0) + 1
                            if indicator_closed:
                                combo_close_counts[combo_id] = int(combo_close_counts.get(combo_id) or 0) + 1
                                if combo_id not in effective_combos_current:
                                    effective_combos_current.append(combo_id)
                                if bool(quality_gate.get("ok", False)):
                                    combo_gate_counts[combo_id] = int(combo_gate_counts.get(combo_id) or 0) + 1
                normalized_bundle = _normalize_combo_ids(effective_combos_current, limit=4)
                bundle_id = _bundle_key(normalized_bundle)
                if bundle_id:
                    combo_bundle_attempt_counts[bundle_id] = int(combo_bundle_attempt_counts.get(bundle_id) or 0) + 1
                    if bool(quality_gate.get("ok", False)):
                        combo_bundle_gate_counts[bundle_id] = int(combo_bundle_gate_counts.get(bundle_id) or 0) + 1
                    context_bundle_id = _context_bundle_key(context_signature, normalized_bundle)
                    if context_bundle_id:
                        combo_context_bundle_attempt_counts[context_bundle_id] = int(
                            combo_context_bundle_attempt_counts.get(context_bundle_id) or 0
                        ) + 1
                        if bool(quality_gate.get("ok", False)):
                            combo_context_bundle_gate_counts[context_bundle_id] = int(
                                combo_context_bundle_gate_counts.get(context_bundle_id) or 0
                            ) + 1
                attributed_context_bundles_current: list[str] = []
                for learning_detail in context_learning_details_by_title.get(title) or []:
                    context_bundle_id = str(learning_detail.get("context_bundle_id") or "").strip()
                    if not context_bundle_id:
                        continue
                    combo_context_bundle_learning_attempt_counts[context_bundle_id] = int(
                        combo_context_bundle_learning_attempt_counts.get(context_bundle_id) or 0
                    ) + 1
                    if bool(quality_gate.get("ok", False)):
                        combo_context_bundle_learning_gate_counts[context_bundle_id] = int(
                            combo_context_bundle_learning_gate_counts.get(context_bundle_id) or 0
                        ) + 1
                    display_text = str(learning_detail.get("bundle_display") or "").strip()
                    if display_text and display_text not in attributed_context_bundles_current:
                        attributed_context_bundles_current.append(display_text)
                metric_effects_current: list[str] = []
                metric_action_effects_current: list[str] = []
                for effect_detail in context_metric_details_by_title.get(title) or []:
                    context_bundle_id = str(effect_detail.get("context_bundle_id") or "").strip()
                    metric_name = str(effect_detail.get("metric") or "").strip()
                    if not context_bundle_id or not metric_name:
                        continue
                    effect_key = _context_metric_key(context_bundle_id, metric_name)
                    if not effect_key:
                        continue
                    combo_context_metric_attempt_counts[effect_key] = int(
                        combo_context_metric_attempt_counts.get(effect_key) or 0
                    ) + 1
                    if bool(effect_detail.get("resolved", False)):
                        combo_context_metric_resolved_counts[effect_key] = int(
                            combo_context_metric_resolved_counts.get(effect_key) or 0
                        ) + 1
                    display_text = str(effect_detail.get("display") or "").strip()
                    if display_text and display_text not in metric_effects_current:
                        metric_effects_current.append(display_text)
                    action_tags = [
                        str(x).strip()
                        for x in (
                            effect_detail.get("action_tags")
                            if isinstance(effect_detail.get("action_tags"), list)
                            else []
                        )
                        if str(x).strip()
                    ]
                    for action_tag in action_tags:
                        action_key = _context_metric_action_key(context_bundle_id, metric_name, action_tag)
                        if not action_key:
                            continue
                        combo_context_metric_action_attempt_counts[action_key] = int(
                            combo_context_metric_action_attempt_counts.get(action_key) or 0
                        ) + 1
                        if bool(effect_detail.get("resolved", False)):
                            combo_context_metric_action_resolved_counts[action_key] = int(
                                combo_context_metric_action_resolved_counts.get(action_key) or 0
                            ) + 1
                        action_label = str(ACTION_TAG_LABELS.get(action_tag) or action_tag).strip()
                        effect_text = f"{str(effect_detail.get('metric_label') or metric_name).strip()}/{action_label}"
                        if effect_text not in metric_action_effects_current:
                            metric_action_effects_current.append(effect_text)
                entry["last_runtime_budget_reason"] = str(section.get("runtime_budget_reason") or "").strip()
                entry["last_used_key_alias"] = used_key_alias
                entry["last_indicator_groups"] = sorted(indicator_groups_by_title.get(title) or [])
                entry["last_strategy_ids"] = sorted(strategy_ids_by_title.get(title) or [])[:8]
                entry["last_action_tags"] = sorted(action_tags_by_title.get(title) or [])[:12]
                entry["last_effective_combos"] = effective_combos_current[:12]
                entry["last_effective_combo_bundle"] = normalized_bundle[:4]
                entry["last_attributed_context_bundles"] = attributed_context_bundles_current[:4]
                entry["last_metric_effects"] = metric_effects_current[:4]
                entry["last_metric_action_effects"] = metric_action_effects_current[:6]
                entry["last_context_signature"] = context_signature
                entry["last_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
                updated[key] = entry
        maintenance = _apply_profile_maintenance(
            profile,
            soft_limit=int(cfg.get("runtime_profile_soft_limit") or 160),
            stale_days=int(cfg.get("runtime_profile_stale_days") or 21),
            min_runs_to_keep=int(cfg.get("runtime_profile_min_runs_to_keep") or 2),
        )
        sample = []
        for key, item in list(updated.items())[:8]:
            runs = int(item.get("runs") or 0)
            sample.append(
                {
                    "profile_key": key,
                    "title": str(item.get("title") or ""),
                    "project_type": str(item.get("project_type") or ""),
                    "generation_mode": str(item.get("generation_mode") or ""),
                    "runs": runs,
                    "success_runs": int(item.get("success_runs") or 0),
                    "error_runs": int(item.get("error_runs") or 0),
                    "fallback_runs": int(item.get("fallback_runs") or 0),
                    "compaction_runs": int(item.get("compaction_runs") or 0),
                    "quality_issue_runs": int(item.get("quality_issue_runs") or 0),
                    "avg_timeout_sec": _safe_avg(float(item.get("timeout_total") or 0.0), runs),
                    "avg_max_tokens": _safe_avg(float(item.get("max_tokens_total") or 0.0), runs),
                    "avg_retry_limit": _safe_avg(float(item.get("retry_total") or 0.0), runs),
                    "last_runtime_budget_reason": str(item.get("last_runtime_budget_reason") or ""),
                    "last_used_key_alias": str(item.get("last_used_key_alias") or ""),
                    "top_indicator_groups": _top_counter_items(item.get("indicator_group_counts")),
                    "top_strategy_ids": _top_counter_items(item.get("strategy_counts")),
                    "top_action_tags": _top_counter_items(item.get("action_tag_counts")),
                    "top_context_signatures": _top_context_signature_items(item.get("context_signature_counts")),
                    "top_effective_combos": _top_effective_combos(item),
                    "top_effective_combo_bundles": _top_effective_combo_bundles(item),
                    "top_effective_context_bundles": _top_effective_context_bundles(item),
                    "top_attributed_context_bundles": _top_attributed_context_bundles(item),
                    "top_metric_effects": _top_context_metric_effects(item),
                    "top_metric_action_effects": _top_context_metric_action_effects(item),
                    "last_indicator_groups": [str(x) for x in (item.get("last_indicator_groups") or []) if str(x).strip()],
                    "last_strategy_ids": [str(x) for x in (item.get("last_strategy_ids") or []) if str(x).strip()],
                    "last_action_tags": [str(x) for x in (item.get("last_action_tags") or []) if str(x).strip()],
                    "last_effective_combos": [str(x) for x in (item.get("last_effective_combos") or []) if str(x).strip()],
                    "last_effective_combo_bundle": [str(x) for x in (item.get("last_effective_combo_bundle") or []) if str(x).strip()],
                    "last_attributed_context_bundles": [str(x) for x in (item.get("last_attributed_context_bundles") or []) if str(x).strip()],
                    "last_metric_effects": [str(x) for x in (item.get("last_metric_effects") or []) if str(x).strip()],
                    "last_metric_action_effects": [str(x) for x in (item.get("last_metric_action_effects") or []) if str(x).strip()],
                    "last_context_signature": str(item.get("last_context_signature") or "").strip(),
                }
            )
        return {
            "enabled": True,
            "profile_path": str(RUNTIME_BUDGET_PROFILE_PATH),
            "profile_version": str(profile.get("version") or ""),
            "updated_entries": len(updated),
            "skipped_dry_run_results": int(skipped_dry_run_results),
            "maintenance": maintenance,
            "sample": sample,
        }

    return _update_profile(_mutate)


def record_task_parallelism_learning(
    payload: Dict[str, Any],
    *,
    agent_runtime: Dict[str, Any] | None = None,
    results: list[Dict[str, Any]] | None = None,
    hard_failures: list[Dict[str, Any]] | None = None,
    params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    if not cfg.get("enabled") or not cfg.get("task_parallelism_enabled"):
        return {"enabled": False, "updated_entries": 0, "profile_path": str(TASK_PARALLELISM_PROFILE_PATH)}
    if bool(cfg.get("ignore_dry_run_learning", True)) and _is_dry_run_sample(payload):
        return {
            "enabled": True,
            "profile_path": str(TASK_PARALLELISM_PROFILE_PATH),
            "updated_entries": 0,
            "skipped_dry_run_results": 1,
        }

    runtime = agent_runtime if isinstance(agent_runtime, dict) else {}
    requested = max(
        1,
        int(
            runtime.get("requested_agent_parallelism")
            or payload.get("_requested_agent_parallelism")
            or payload.get("agent_parallelism")
            or 1
        ),
    )
    effective = max(
        1,
        int(
            runtime.get("agent_parallelism")
            or payload.get("_runtime_agent_parallelism")
            or payload.get("agent_parallelism")
            or 1
        ),
    )
    planned_pages = int(runtime.get("planned_total_pages") or 0)
    outline_count = int(runtime.get("outline_count") or 0)
    variants_total = int(runtime.get("variants_total") or payload.get("variants") or 1)
    project_type = str(payload.get("project_type") or "").strip() or "通用"
    generation_mode = str(payload.get("generation_mode") or "").strip() or "quality_200"
    key = _task_parallelism_profile_key(project_type, generation_mode, planned_pages, outline_count, variants_total)

    fallback_seen = False
    quality_issue_seen = False
    for result in results or []:
        if not isinstance(result, dict):
            continue
        primary_alias = _primary_text_key_alias(payload, result)
        quality = result.get("quality_checks") if isinstance(result.get("quality_checks"), dict) else {}
        quality_gate = result.get("quality_gate") if isinstance(result.get("quality_gate"), dict) else {}
        issue_titles = _collect_quality_issue_titles(quality)
        if issue_titles or not bool(quality_gate.get("ok", True)):
            quality_issue_seen = True
        for section in (result.get("sections") or []):
            if not isinstance(section, dict):
                continue
            used_key_alias = str(section.get("used_key_alias") or "").strip()
            if used_key_alias and primary_alias and used_key_alias != primary_alias:
                fallback_seen = True
                break
        if fallback_seen and quality_issue_seen:
            break
    hard_failure_seen = bool(hard_failures)

    def _mutate(profile: Dict[str, Any]) -> Dict[str, Any]:
        entries = profile.setdefault("entries", {})
        entry = entries.setdefault(
            key,
            {
                "project_type": project_type,
                "generation_mode": generation_mode,
                "page_bucket": _bucket_pages(planned_pages),
                "outline_bucket": _bucket_outline(outline_count),
                "variant_bucket": "multi" if variants_total >= 2 else "single",
                "runs": 0,
                "success_runs": 0,
                "hard_failure_runs": 0,
                "fallback_runs": 0,
                "quality_issue_runs": 0,
                "requested_parallelism_total": 0.0,
                "effective_parallelism_total": 0.0,
                "last_reason": "",
                "last_updated_at": "",
            },
        )
        entry["runs"] = int(entry.get("runs") or 0) + 1
        if hard_failure_seen:
            entry["hard_failure_runs"] = int(entry.get("hard_failure_runs") or 0) + 1
        else:
            entry["success_runs"] = int(entry.get("success_runs") or 0) + 1
        if fallback_seen:
            entry["fallback_runs"] = int(entry.get("fallback_runs") or 0) + 1
        if quality_issue_seen:
            entry["quality_issue_runs"] = int(entry.get("quality_issue_runs") or 0) + 1
        entry["requested_parallelism_total"] = float(entry.get("requested_parallelism_total") or 0.0) + float(requested)
        entry["effective_parallelism_total"] = float(entry.get("effective_parallelism_total") or 0.0) + float(effective)
        entry["last_reason"] = str(runtime.get("runtime_agent_parallelism_reason") or "").strip()
        entry["last_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        maintenance = _apply_profile_maintenance(
            profile,
            soft_limit=int(cfg.get("task_parallelism_profile_soft_limit") or 96),
            stale_days=int(cfg.get("task_parallelism_profile_stale_days") or 30),
            min_runs_to_keep=int(cfg.get("task_parallelism_profile_min_runs_to_keep") or 2),
        )
        profile["version"] = "task_parallelism_profile_v1"
        runs = int(entry.get("runs") or 0)
        return {
            "enabled": True,
            "profile_path": str(TASK_PARALLELISM_PROFILE_PATH),
            "updated_entries": 1,
            "profile_key": key,
            "maintenance": maintenance,
            "sample": {
                "project_type": project_type,
                "generation_mode": generation_mode,
                "runs": runs,
                "hard_failure_runs": int(entry.get("hard_failure_runs") or 0),
                "fallback_runs": int(entry.get("fallback_runs") or 0),
                "quality_issue_runs": int(entry.get("quality_issue_runs") or 0),
                "avg_requested_parallelism": _safe_avg(float(entry.get("requested_parallelism_total") or 0.0), runs),
                "avg_effective_parallelism": _safe_avg(float(entry.get("effective_parallelism_total") or 0.0), runs),
                "last_reason": str(entry.get("last_reason") or ""),
            },
        }

    TASK_PARALLELISM_PROFILE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with TASK_PARALLELISM_PROFILE_LOCK.open("a+", encoding="utf-8") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        try:
            if not TASK_PARALLELISM_PROFILE_PATH.exists():
                profile = _default_profile()
            else:
                try:
                    profile = json.loads(TASK_PARALLELISM_PROFILE_PATH.read_text(encoding="utf-8"))
                except Exception:
                    profile = _default_profile()
                if not isinstance(profile, dict):
                    profile = _default_profile()
                if not isinstance(profile.get("entries"), dict):
                    profile["entries"] = {}
            result = _mutate(profile)
            TASK_PARALLELISM_PROFILE_PATH.write_text(
                json.dumps(
                    {
                        "version": str(profile.get("version") or "task_parallelism_profile_v1"),
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                        "entries": profile.get("entries") if isinstance(profile.get("entries"), dict) else {},
                        "maintenance": profile.get("maintenance") if isinstance(profile.get("maintenance"), dict) else {},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return result
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def build_runtime_budget_hints(
    *,
    params: Dict[str, Any] | None,
    title: str,
    project_type: str,
    generation_mode: str,
    runtime_budget: Dict[str, Any],
    profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    if not cfg.get("enabled"):
        return {"enabled": False, "applied": False}
    profile_obj = profile if isinstance(profile, dict) else load_runtime_budget_profile()
    entries = profile_obj.get("entries") if isinstance(profile_obj.get("entries"), dict) else {}
    key = _profile_key(title, project_type, generation_mode)
    entry = entries.get(key) if isinstance(entries.get(key), dict) else None
    if not isinstance(entry, dict):
        return {"enabled": True, "applied": False, "profile_key": key, "source_runs": 0}
    runs = max(0, int(entry.get("runs") or 0))
    if runs < int(cfg.get("min_runs_for_adjustment") or 2):
        return {
            "enabled": True,
            "applied": False,
            "profile_key": key,
            "source_runs": runs,
        }

    error_rate = float(entry.get("error_runs") or 0) / float(runs or 1)
    fallback_rate = float(entry.get("fallback_runs") or 0) / float(runs or 1)
    compaction_rate = float(entry.get("compaction_runs") or 0) / float(runs or 1)
    quality_issue_rate = float(entry.get("quality_issue_runs") or 0) / float(runs or 1)
    timeout_base = max(30, int(runtime_budget.get("llm_timeout_sec") or 120))
    token_base = max(900, int(runtime_budget.get("max_output_tokens_hint") or 3200))
    retry_base = max(1, min(3, int(runtime_budget.get("section_retry_limit") or 1)))

    adjusted_timeout = timeout_base
    adjusted_tokens = token_base
    adjusted_retry = retry_base
    reasons: list[str] = []

    timeout_delta = min(int(cfg.get("max_timeout_delta_sec") or 20), 12 if runs < 5 else 18)
    token_delta = min(int(cfg.get("max_token_delta") or 600), 300)
    if error_rate >= float(cfg.get("error_rate_raise_timeout") or 0.35):
        new_timeout = min(240, timeout_base + timeout_delta)
        if new_timeout > adjusted_timeout:
            adjusted_timeout = new_timeout
            reasons.append(f"historical_error_rate={error_rate:.2f}_raise_timeout")
    elif fallback_rate >= float(cfg.get("fallback_rate_raise_timeout") or 0.35):
        new_timeout = min(240, timeout_base + max(8, timeout_delta - 2))
        if new_timeout > adjusted_timeout:
            adjusted_timeout = new_timeout
            reasons.append(f"historical_fallback_rate={fallback_rate:.2f}_raise_timeout")

    if bool(cfg.get("allow_retry_promotion", True)) and adjusted_retry < 2 and (
        fallback_rate >= float(cfg.get("fallback_rate_raise_timeout") or 0.35)
        or error_rate >= float(cfg.get("error_rate_raise_timeout") or 0.35)
    ):
        adjusted_retry = 2
        reasons.append("historical_retries_promoted")
    elif bool(cfg.get("allow_retry_promotion", True)) and adjusted_retry < 2 and (
        quality_issue_rate >= float(cfg.get("quality_issue_rate_raise_retry") or 0.50)
    ):
        adjusted_retry = 2
        reasons.append(f"historical_quality_issue_rate={quality_issue_rate:.2f}_raise_retry")

    if quality_issue_rate >= float(cfg.get("quality_issue_rate_raise_tokens") or 0.50):
        new_tokens = min(6000, token_base + token_delta)
        if new_tokens > adjusted_tokens:
            adjusted_tokens = new_tokens
            reasons.append(f"historical_quality_issue_rate={quality_issue_rate:.2f}_raise_tokens")
    elif compaction_rate >= float(cfg.get("compaction_rate_trim_tokens") or 0.50):
        new_tokens = max(900, token_base - min(int(cfg.get("max_token_delta") or 600), 240))
        if new_tokens < adjusted_tokens:
            adjusted_tokens = new_tokens
            reasons.append(f"historical_compaction_rate={compaction_rate:.2f}_trim_tokens")

    applied = (
        adjusted_timeout != timeout_base
        or adjusted_tokens != token_base
        or adjusted_retry != retry_base
    )
    out = {
        "enabled": True,
        "applied": applied,
        "profile_key": key,
        "source_runs": runs,
        "reason": "; ".join(reasons),
        "metrics": {
            "error_rate": round(error_rate, 4),
            "fallback_rate": round(fallback_rate, 4),
            "compaction_rate": round(compaction_rate, 4),
            "quality_issue_rate": round(quality_issue_rate, 4),
        },
    }
    if applied:
        out.update(
            {
                "llm_timeout_sec": adjusted_timeout,
                "max_output_tokens_hint": adjusted_tokens,
                "section_retry_limit": adjusted_retry,
            }
        )
    return out


def build_task_parallelism_hint(
    *,
    params: Dict[str, Any] | None,
    payload: Dict[str, Any],
    requested: int,
    effective: int,
    variants_total: int,
    profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    if not cfg.get("enabled") or not cfg.get("task_parallelism_enabled"):
        return {"enabled": False, "applied": False}
    if effective <= 1:
        return {"enabled": True, "applied": False, "effective": 1, "source_runs": 0}

    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    planned_pages = int(mode_policy.get("planned_total_pages") or payload.get("total_pages_target") or 0)
    outline = payload.get("outline")
    if isinstance(outline, list):
        outline_count = sum(
            1
            for item in outline
            if (isinstance(item, str) and item.strip())
            or (isinstance(item, dict) and str(item.get("title") or item.get("name") or "").strip())
        )
    else:
        outline_count = 0
    project_type = str(payload.get("project_type") or "").strip() or "通用"
    generation_mode = str(payload.get("generation_mode") or "").strip() or "quality_200"
    profile_obj = profile if isinstance(profile, dict) else load_task_parallelism_profile()
    entries = profile_obj.get("entries") if isinstance(profile_obj.get("entries"), dict) else {}
    key = _task_parallelism_profile_key(project_type, generation_mode, planned_pages, outline_count, variants_total)
    entry = entries.get(key) if isinstance(entries.get(key), dict) else None
    if not isinstance(entry, dict):
        return {"enabled": True, "applied": False, "effective": effective, "source_runs": 0, "profile_key": key}

    runs = max(0, int(entry.get("runs") or 0))
    if runs < int(cfg.get("task_parallelism_min_runs") or 2):
        return {"enabled": True, "applied": False, "effective": effective, "source_runs": runs, "profile_key": key}

    hard_failure_rate = float(entry.get("hard_failure_runs") or 0) / float(runs or 1)
    fallback_rate = float(entry.get("fallback_runs") or 0) / float(runs or 1)
    quality_issue_rate = float(entry.get("quality_issue_runs") or 0) / float(runs or 1)

    delta = 0
    reasons: list[str] = []
    if hard_failure_rate >= float(cfg.get("task_parallelism_error_rate_reduce") or 0.35):
        delta = max(delta, 1)
        reasons.append(f"historical_task_hard_failure_rate={hard_failure_rate:.2f}_reduce_parallelism")
    if fallback_rate >= float(cfg.get("task_parallelism_fallback_rate_reduce") or 0.40):
        delta = max(delta, 1)
        reasons.append(f"historical_task_fallback_rate={fallback_rate:.2f}_reduce_parallelism")
    if quality_issue_rate >= float(cfg.get("task_parallelism_quality_issue_rate_reduce") or 0.50) and effective > 2:
        delta = max(delta, 1)
        reasons.append(f"historical_task_quality_issue_rate={quality_issue_rate:.2f}_reduce_parallelism")
    if runs >= 6 and effective > 2 and (
        hard_failure_rate >= 0.60 or fallback_rate >= 0.75
    ):
        delta = max(delta, min(int(cfg.get("task_parallelism_max_delta") or 2), 2))
        reasons.append("historical_task_high_pressure_extra_reduce")

    adjusted = max(1, effective - delta)
    return {
        "enabled": True,
        "applied": adjusted < effective,
        "effective": adjusted,
        "reason": "; ".join(reasons),
        "source_runs": runs,
        "profile_key": key,
        "metrics": {
            "hard_failure_rate": round(hard_failure_rate, 4),
            "fallback_rate": round(fallback_rate, 4),
            "quality_issue_rate": round(quality_issue_rate, 4),
        },
    }


def prioritize_remediation_rows_with_learning(
    *,
    params: Dict[str, Any] | None,
    project_type: str,
    generation_mode: str,
    rows: List[Dict[str, Any]] | None,
    profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    out_rows = [dict(row) for row in (rows or []) if isinstance(row, dict)]
    if not cfg.get("enabled") or not cfg.get("combo_learning_enabled"):
        return {"enabled": False, "applied": False, "rows": out_rows}

    profile_obj = profile if isinstance(profile, dict) else load_runtime_budget_profile()
    entries = profile_obj.get("entries") if isinstance(profile_obj.get("entries"), dict) else {}
    min_runs = int(cfg.get("combo_learning_min_runs") or 2)
    min_success_rate = float(cfg.get("combo_learning_min_success_rate") or 0.55)
    gate_pass_bonus = float(cfg.get("combo_learning_gate_pass_bonus") or 0.10)
    max_boost = int(cfg.get("combo_learning_max_priority_boost") or 8)
    bundle_enabled = bool(cfg.get("combo_bundle_learning_enabled", True))
    bundle_min_runs = int(cfg.get("combo_bundle_min_runs") or 2)
    bundle_min_pass_rate = float(cfg.get("combo_bundle_min_pass_rate") or 0.55)
    bundle_gate_pass_bonus = float(cfg.get("combo_bundle_gate_pass_bonus") or 0.10)
    bundle_max_boost = int(cfg.get("combo_bundle_max_priority_boost") or 10)
    context_bundle_enabled = bool(cfg.get("combo_context_bundle_learning_enabled", True))
    context_bundle_min_runs = int(cfg.get("combo_context_bundle_min_runs") or 2)
    context_bundle_min_pass_rate = float(cfg.get("combo_context_bundle_min_pass_rate") or 0.60)
    context_bundle_gate_pass_bonus = float(cfg.get("combo_context_bundle_gate_pass_bonus") or 0.12)
    context_bundle_max_boost = int(cfg.get("combo_context_bundle_max_priority_boost") or 12)
    context_bundle_attribution_enabled = bool(cfg.get("combo_context_bundle_attribution_enabled", True))
    context_bundle_attribution_min_runs = int(cfg.get("combo_context_bundle_attribution_min_runs") or 2)
    context_bundle_attribution_gate_pass_bonus = float(cfg.get("combo_context_bundle_attribution_gate_pass_bonus") or 0.08)
    context_metric_effect_enabled = bool(cfg.get("combo_context_metric_effect_enabled", True))
    context_metric_effect_min_runs = int(cfg.get("combo_context_metric_effect_min_runs") or 2)
    context_metric_effect_resolve_bonus = float(cfg.get("combo_context_metric_effect_resolve_bonus") or 0.10)
    context_metric_action_effect_enabled = bool(cfg.get("combo_context_metric_action_effect_enabled", True))
    context_metric_action_effect_min_runs = int(cfg.get("combo_context_metric_action_effect_min_runs") or 2)
    context_metric_action_effect_resolve_bonus = float(cfg.get("combo_context_metric_action_effect_resolve_bonus") or 0.08)
    context_bundle_partial_enabled = bool(cfg.get("combo_context_bundle_partial_match_enabled", True))
    context_bundle_partial_min_match_count = int(cfg.get("combo_context_bundle_partial_min_match_count") or 2)
    context_bundle_partial_min_match_ratio = float(cfg.get("combo_context_bundle_partial_min_match_ratio") or 0.50)
    context_bundle_partial_score_penalty = float(cfg.get("combo_context_bundle_partial_score_penalty") or 0.08)

    applied_rows = 0
    reasons: List[str] = []
    combos: List[str] = []
    titles: set[str] = set()
    max_source_runs = 0
    bundle_applied_rows = 0
    bundle_reasons: List[str] = []
    bundle_texts: List[str] = []
    bundle_titles: set[str] = set()
    bundle_source_runs = 0
    context_bundle_applied_rows = 0
    context_bundle_reasons: List[str] = []
    context_bundle_texts: List[str] = []
    context_bundle_titles: set[str] = set()
    context_bundle_source_runs = 0
    context_bundle_contexts: set[str] = set()
    rows_by_title: Dict[str, List[Dict[str, Any]]] = {}

    def _row_context_signature(row: Dict[str, Any]) -> str:
        return _context_signature(
            row.get("chapter_domain"),
            row.get("template_id"),
        )

    def _select_title_context_signature(title_rows: List[Dict[str, Any]]) -> str:
        counts: Dict[str, int] = {}
        for item in title_rows:
            if not isinstance(item, dict):
                continue
            signature = _row_context_signature(item)
            counts[signature] = int(counts.get(signature) or 0) + 1
        if not counts:
            return ""
        return sorted(counts.items(), key=lambda pair: (-int(pair[1]), str(pair[0])))[0][0]

    for row in out_rows:
        title = str(row.get("title") or "").strip()
        target_section_title = str(row.get("target_section_title") or title).strip() or title
        indicator_group = str(row.get("indicator_group") or "").strip()
        strategy_id = str(row.get("strategy_id") or "").strip()
        expected_action_tags = [
            str(x).strip()
            for x in (row.get("expected_action_tags") or [])
            if str(x).strip()
        ]
        row["_combo_learning_applied"] = False
        row["_combo_learning_priority_boost"] = 0
        row["_combo_learning_score"] = 0.0
        row["_combo_learning_reason"] = ""
        row["_combo_learning_best_combo"] = ""
        row["_combo_learning_source_runs"] = 0
        row["_combo_bundle_learning_applied"] = False
        row["_combo_bundle_learning_priority_boost"] = 0
        row["_combo_bundle_learning_score"] = 0.0
        row["_combo_bundle_learning_reason"] = ""
        row["_combo_bundle_learning_best_bundle"] = ""
        row["_combo_bundle_learning_source_runs"] = 0
        row["_combo_context_bundle_learning_applied"] = False
        row["_combo_context_bundle_learning_priority_boost"] = 0
        row["_combo_context_bundle_learning_score"] = 0.0
        row["_combo_context_bundle_learning_reason"] = ""
        row["_combo_context_bundle_learning_best_bundle"] = ""
        row["_combo_context_bundle_learning_source_runs"] = 0
        row["_combo_context_bundle_learning_key"] = ""
        row["_combo_context_bundle_learning_context_signature"] = ""
        row["_combo_context_bundle_learning_bundle_combos"] = []
        row["_combo_context_bundle_learning_attribution_applied"] = False
        row["_combo_context_bundle_learning_attributed_gate_pass_rate"] = 0.0
        row["_combo_context_bundle_learning_attribution_source_runs"] = 0
        row["_combo_context_bundle_learning_attribution_reason"] = ""
        row["_combo_context_metric_effect_applied"] = False
        row["_combo_context_metric_effect_metrics"] = []
        row["_combo_context_metric_effect_reason"] = ""
        row["_combo_context_metric_effect_source_runs"] = 0
        row["_combo_context_metric_action_effect_applied"] = False
        row["_combo_context_metric_action_effect_triplets"] = []
        row["_combo_context_metric_action_effect_reason"] = ""
        row["_combo_context_metric_action_effect_source_runs"] = 0
        row["_combo_context_metric_action_effect_details"] = []
        if not title or not target_section_title or not indicator_group or not strategy_id or not expected_action_tags:
            continue
        row["_candidate_combo_ids"] = [
            _combo_key(indicator_group, strategy_id, action_tag)
            for action_tag in expected_action_tags
            if str(action_tag).strip()
        ]
        rows_by_title.setdefault(target_section_title, []).append(row)
        entry = entries.get(_profile_key(target_section_title, project_type, generation_mode))
        if not isinstance(entry, dict):
            continue
        attempts_map = entry.get("combo_attempt_counts") if isinstance(entry.get("combo_attempt_counts"), dict) else {}
        close_map = entry.get("combo_indicator_close_counts") if isinstance(entry.get("combo_indicator_close_counts"), dict) else {}
        gate_map = entry.get("combo_gate_pass_counts") if isinstance(entry.get("combo_gate_pass_counts"), dict) else {}
        best_match: Dict[str, Any] | None = None
        fallback_match: Dict[str, Any] | None = None
        for action_tag in expected_action_tags:
            combo_id = _combo_key(indicator_group, strategy_id, action_tag)
            attempts = int(attempts_map.get(combo_id) or 0)
            if attempts < min_runs:
                matching_keys = []
            else:
                matching_keys = [combo_id]
            if not matching_keys:
                matching_keys = [
                    str(existing_combo_id)
                    for existing_combo_id in attempts_map.keys()
                    if (
                        lambda parts: parts[1] == strategy_id and parts[2] == action_tag
                    )(_split_combo_key(str(existing_combo_id)))
                ]
            for existing_combo_id in matching_keys:
                attempts = int(attempts_map.get(existing_combo_id) or 0)
                if attempts < min_runs:
                    continue
                close_count = int(close_map.get(existing_combo_id) or 0)
                gate_count = int(gate_map.get(existing_combo_id) or 0)
                close_rate = float(close_count) / float(attempts or 1)
                gate_rate = float(gate_count) / float(attempts or 1)
                if close_rate < min_success_rate:
                    continue
                exact_match = str(existing_combo_id) == combo_id
                score = close_rate + (gate_rate * gate_pass_bonus) + min(0.05, float(attempts) * 0.01)
                if not exact_match:
                    score -= 0.03
                candidate = {
                    "combo_id": str(existing_combo_id),
                    "attempts": attempts,
                    "close_rate": round(close_rate, 4),
                    "gate_rate": round(gate_rate, 4),
                    "action_tag": action_tag,
                    "score": round(score, 4),
                    "match_scope": "exact" if exact_match else "strategy_action_fallback",
                }
                if exact_match:
                    if best_match is None or float(candidate["score"]) > float(best_match["score"]):
                        best_match = candidate
                elif fallback_match is None or float(candidate["score"]) > float(fallback_match["score"]):
                    fallback_match = candidate
        if best_match is None and fallback_match is not None:
            best_match = fallback_match
        if not best_match:
            continue
        boost = max(
            1,
            int(round((float(best_match["close_rate"]) - min_success_rate) * 10.0)) + 1 + (1 if float(best_match["gate_rate"]) > 0.0 else 0),
        )
        boost = min(max_boost, max(1, boost))
        row["_combo_learning_applied"] = True
        row["_combo_learning_priority_boost"] = boost
        row["_combo_learning_score"] = float(best_match["score"])
        row["_combo_learning_reason"] = (
            f"historical_combo_close_rate={float(best_match['close_rate']):.2f}; "
            f"historical_combo_gate_pass_rate={float(best_match['gate_rate']):.2f}; "
            f"action={str(best_match['action_tag'])}; "
            f"match_scope={str(best_match.get('match_scope') or 'exact')}"
        )
        row["_combo_learning_best_combo"] = str(best_match["combo_id"])
        row["_combo_learning_source_runs"] = int(best_match["attempts"])
        applied_rows += 1
        titles.add(title)
        max_source_runs = max(max_source_runs, int(best_match["attempts"]))
        combo_text = _top_effective_combos(
            {
                "combo_attempt_counts": {str(best_match["combo_id"]): int(best_match["attempts"])},
                "combo_indicator_close_counts": {str(best_match["combo_id"]): int(round(float(best_match["close_rate"]) * int(best_match["attempts"])))},
                "combo_gate_pass_counts": {str(best_match["combo_id"]): int(round(float(best_match["gate_rate"]) * int(best_match["attempts"])))},
            },
            limit=1,
        )
        if combo_text:
            combos.append(combo_text[0])
        reason_text = f"{target_section_title}: {row['_combo_learning_reason']}"
        if reason_text not in reasons:
            reasons.append(reason_text)
        titles.add(target_section_title)

    if bundle_enabled or context_bundle_enabled:
        for target_section_title, title_rows in rows_by_title.items():
            entry = entries.get(_profile_key(target_section_title, project_type, generation_mode))
            if not isinstance(entry, dict):
                continue
            title_context_signature = _select_title_context_signature(title_rows)
            context_bundle_attempts_map = entry.get("combo_context_bundle_attempt_counts") if isinstance(entry.get("combo_context_bundle_attempt_counts"), dict) else {}
            context_bundle_gate_map = entry.get("combo_context_bundle_gate_pass_counts") if isinstance(entry.get("combo_context_bundle_gate_pass_counts"), dict) else {}
            context_bundle_learning_attempts_map = entry.get("combo_context_bundle_learning_attempt_counts") if isinstance(entry.get("combo_context_bundle_learning_attempt_counts"), dict) else {}
            context_bundle_learning_gate_map = entry.get("combo_context_bundle_learning_gate_pass_counts") if isinstance(entry.get("combo_context_bundle_learning_gate_pass_counts"), dict) else {}
            context_metric_attempts_map = entry.get("combo_context_metric_attempt_counts") if isinstance(entry.get("combo_context_metric_attempt_counts"), dict) else {}
            context_metric_resolved_map = entry.get("combo_context_metric_resolved_counts") if isinstance(entry.get("combo_context_metric_resolved_counts"), dict) else {}
            context_metric_action_attempts_map = entry.get("combo_context_metric_action_attempt_counts") if isinstance(entry.get("combo_context_metric_action_attempt_counts"), dict) else {}
            context_metric_action_resolved_map = entry.get("combo_context_metric_action_resolved_counts") if isinstance(entry.get("combo_context_metric_action_resolved_counts"), dict) else {}
            bundle_attempts_map = entry.get("combo_bundle_attempt_counts") if isinstance(entry.get("combo_bundle_attempt_counts"), dict) else {}
            bundle_gate_map = entry.get("combo_bundle_gate_pass_counts") if isinstance(entry.get("combo_bundle_gate_pass_counts"), dict) else {}
            if not bundle_attempts_map and not context_bundle_attempts_map:
                continue
            candidate_combo_pool: set[str] = set()
            row_combo_map: Dict[int, List[str]] = {}
            for pos, row in enumerate(title_rows):
                combo_ids = [str(x).strip() for x in (row.get("_candidate_combo_ids") or []) if str(x).strip()]
                if not combo_ids:
                    continue
                row_combo_map[pos] = combo_ids
                candidate_combo_pool.update(combo_ids)
            if len(candidate_combo_pool) < 2:
                continue
            best_context_bundle: Dict[str, Any] | None = None
            if context_bundle_enabled and title_context_signature:
                for raw_context_bundle_id, attempts_raw in context_bundle_attempts_map.items():
                    attempts = int(attempts_raw or 0)
                    if attempts < context_bundle_min_runs:
                        continue
                    context_signature, bundle_combos = _split_context_bundle_key(str(raw_context_bundle_id))
                    if not context_signature or context_signature != title_context_signature:
                        continue
                    if len(bundle_combos) < 2:
                        continue
                    bundle_set = set(bundle_combos)
                    matched_bundle_combos = sorted(bundle_set.intersection(candidate_combo_pool))
                    match_count = len(matched_bundle_combos)
                    if bundle_set.issubset(candidate_combo_pool):
                        partial_match = False
                    elif context_bundle_partial_enabled:
                        if match_count < min(len(bundle_set), context_bundle_partial_min_match_count):
                            continue
                        match_ratio = float(match_count) / float(len(bundle_set) or 1)
                        if match_ratio < context_bundle_partial_min_match_ratio:
                            continue
                        partial_match = True
                    else:
                        continue
                    gate_count = int(context_bundle_gate_map.get(raw_context_bundle_id) or 0)
                    pass_rate = float(gate_count) / float(attempts or 1)
                    if pass_rate < context_bundle_min_pass_rate:
                        continue
                    attributed_attempts = int(context_bundle_learning_attempts_map.get(raw_context_bundle_id) or 0)
                    attributed_gate_count = int(context_bundle_learning_gate_map.get(raw_context_bundle_id) or 0)
                    attributed_gate_pass_rate = (
                        float(attributed_gate_count) / float(attributed_attempts or 1)
                        if attributed_attempts > 0
                        else 0.0
                    )
                    score = (
                        pass_rate
                        + (pass_rate * context_bundle_gate_pass_bonus)
                        + min(0.05, float(attempts) * 0.01)
                        + min(0.04, float(len(bundle_combos)) * 0.01)
                        + 0.05
                    )
                    if context_bundle_attribution_enabled and attributed_attempts >= context_bundle_attribution_min_runs:
                        score += attributed_gate_pass_rate * context_bundle_attribution_gate_pass_bonus
                    if partial_match:
                        score -= context_bundle_partial_score_penalty
                    candidate = {
                        "context_bundle_id": str(raw_context_bundle_id),
                        "context_signature": context_signature,
                        "bundle_id": _bundle_key(bundle_combos),
                        "bundle_combos": bundle_combos,
                        "matched_bundle_combos": matched_bundle_combos,
                        "attempts": attempts,
                        "pass_rate": round(pass_rate, 4),
                        "attributed_attempts": attributed_attempts,
                        "attributed_gate_pass_rate": round(attributed_gate_pass_rate, 4),
                        "score": round(score, 4),
                        "partial_match": bool(partial_match),
                    }
                    if best_context_bundle is None or float(candidate["score"]) > float(best_context_bundle["score"]):
                        best_context_bundle = candidate
            if best_context_bundle:
                boost = max(
                    1,
                    int(round((float(best_context_bundle["pass_rate"]) - context_bundle_min_pass_rate) * 10.0))
                    + max(1, len(best_context_bundle["bundle_combos"]) - 1)
                    + 1,
                )
                if bool(best_context_bundle.get("partial_match")):
                    boost = max(1, boost - 2)
                boost = min(context_bundle_max_boost, max(1, boost))
                bundle_display = _format_context_bundle_display(
                    str(best_context_bundle["context_signature"]),
                    str(best_context_bundle["bundle_id"]),
                    attempts=int(best_context_bundle["attempts"]),
                    pass_rate=float(best_context_bundle["pass_rate"]),
                )
                for pos, row in enumerate(title_rows):
                    combo_ids = row_combo_map.get(pos) or []
                    if not set(combo_ids).intersection(best_context_bundle["bundle_combos"]):
                        continue
                    row["_combo_context_bundle_learning_applied"] = True
                    row["_combo_context_bundle_learning_priority_boost"] = boost
                    row["_combo_context_bundle_learning_score"] = float(best_context_bundle["score"])
                    row["_combo_context_bundle_learning_reason"] = (
                        f"historical_context_bundle_pass_rate={float(best_context_bundle['pass_rate']):.2f}; "
                        f"context={_format_context_signature(str(best_context_bundle['context_signature']))}; "
                        f"bundle_size={len(best_context_bundle['bundle_combos'])}; "
                        f"bundle_match_count={len(set(combo_ids).intersection(best_context_bundle['bundle_combos']))}; "
                        f"match_scope={'partial' if bool(best_context_bundle.get('partial_match')) else 'exact'}"
                    )
                    if context_bundle_attribution_enabled and int(best_context_bundle.get("attributed_attempts") or 0) >= context_bundle_attribution_min_runs:
                        row["_combo_context_bundle_learning_reason"] += (
                            f"; attributed_gate_pass_rate={float(best_context_bundle['attributed_gate_pass_rate']):.2f}; "
                            f"attribution_runs={int(best_context_bundle['attributed_attempts'])}"
                        )
                    row["_combo_context_bundle_learning_best_bundle"] = bundle_display
                    row["_combo_context_bundle_learning_source_runs"] = int(best_context_bundle["attempts"])
                    row["_combo_context_bundle_learning_key"] = str(best_context_bundle.get("context_bundle_id") or "")
                    row["_combo_context_bundle_learning_context_signature"] = str(best_context_bundle.get("context_signature") or "")
                    row["_combo_context_bundle_learning_bundle_combos"] = [str(x).strip() for x in (best_context_bundle.get("bundle_combos") or []) if str(x).strip()]
                    row["_combo_context_bundle_learning_attribution_applied"] = bool(
                        context_bundle_attribution_enabled
                        and int(best_context_bundle.get("attributed_attempts") or 0) >= context_bundle_attribution_min_runs
                    )
                    row["_combo_context_bundle_learning_attributed_gate_pass_rate"] = float(best_context_bundle.get("attributed_gate_pass_rate") or 0.0)
                    row["_combo_context_bundle_learning_attribution_source_runs"] = int(best_context_bundle.get("attributed_attempts") or 0)
                    row["_combo_context_bundle_learning_attribution_reason"] = (
                        f"historical_learning_applied_gate_pass_rate={float(best_context_bundle['attributed_gate_pass_rate']):.2f}; "
                        f"attribution_runs={int(best_context_bundle.get('attributed_attempts') or 0)}"
                        if row["_combo_context_bundle_learning_attribution_applied"]
                        else ""
                    )
                    if context_metric_effect_enabled:
                        expected_metrics = [
                            str(x).strip()
                            for x in (row.get("expected_quality_gate_metrics") or [])
                            if str(x).strip()
                        ]
                        metric_hits: list[str] = []
                        metric_reasons: list[str] = []
                        metric_source_runs = 0
                        metric_bonus = 0.0
                        for metric_name in expected_metrics:
                            effect_key = _context_metric_key(
                                str(best_context_bundle.get("context_bundle_id") or ""),
                                metric_name,
                            )
                            if not effect_key:
                                continue
                            attempts = int(context_metric_attempts_map.get(effect_key) or 0)
                            if attempts < context_metric_effect_min_runs:
                                continue
                            resolved_cnt = int(context_metric_resolved_map.get(effect_key) or 0)
                            resolved_rate = float(resolved_cnt) / float(attempts or 1)
                            if resolved_rate <= 0.0:
                                continue
                            metric_source_runs = max(metric_source_runs, attempts)
                            metric_hits.append(metric_name)
                            metric_reasons.append(f"{metric_name}_resolve_rate={resolved_rate:.2f}")
                            metric_bonus += resolved_rate * context_metric_effect_resolve_bonus
                        if metric_hits:
                            row["_combo_context_metric_effect_applied"] = True
                            row["_combo_context_metric_effect_metrics"] = metric_hits[:4]
                            row["_combo_context_metric_effect_reason"] = "; ".join(metric_reasons[:4])
                            row["_combo_context_metric_effect_source_runs"] = metric_source_runs
                            row["_combo_context_bundle_learning_score"] = float(row.get("_combo_context_bundle_learning_score") or 0.0) + min(0.20, metric_bonus)
                    if context_metric_action_effect_enabled:
                        expected_metrics = [
                            str(x).strip()
                            for x in (row.get("expected_quality_gate_metrics") or [])
                            if str(x).strip()
                        ]
                        action_hits: list[str] = []
                        action_reasons: list[str] = []
                        action_details: list[Dict[str, Any]] = []
                        action_source_runs = 0
                        action_bonus = 0.0
                        for metric_name in expected_metrics:
                            for combo_id in combo_ids:
                                action_tag = _split_combo_key(combo_id)[2]
                                if not action_tag:
                                    continue
                                effect_key = _context_metric_action_key(
                                    str(best_context_bundle.get("context_bundle_id") or ""),
                                    metric_name,
                                    action_tag,
                                )
                                if not effect_key:
                                    continue
                                attempts = int(context_metric_action_attempts_map.get(effect_key) or 0)
                                if attempts < context_metric_action_effect_min_runs:
                                    continue
                                resolved_cnt = int(context_metric_action_resolved_map.get(effect_key) or 0)
                                resolved_rate = float(resolved_cnt) / float(attempts or 1)
                                if resolved_rate <= 0.0:
                                    continue
                                action_source_runs = max(action_source_runs, attempts)
                                action_label = str(ACTION_TAG_LABELS.get(action_tag) or action_tag).strip()
                                triplet_label = f"{metric_name}/{action_label}"
                                if triplet_label not in action_hits:
                                    action_hits.append(triplet_label)
                                action_reasons.append(f"{metric_name}/{action_tag}_resolve_rate={resolved_rate:.2f}")
                                action_details.append(
                                    {
                                        "metric": metric_name,
                                        "action_tag": action_tag,
                                        "action_label": action_label,
                                        "resolve_rate": round(resolved_rate, 4),
                                        "source_runs": attempts,
                                    }
                                )
                                action_bonus += resolved_rate * context_metric_action_effect_resolve_bonus
                        if action_hits:
                            row["_combo_context_metric_action_effect_applied"] = True
                            row["_combo_context_metric_action_effect_triplets"] = action_hits[:6]
                            row["_combo_context_metric_action_effect_reason"] = "; ".join(action_reasons[:6])
                            row["_combo_context_metric_action_effect_source_runs"] = action_source_runs
                            row["_combo_context_metric_action_effect_details"] = action_details[:8]
                            row["_combo_context_bundle_learning_score"] = float(row.get("_combo_context_bundle_learning_score") or 0.0) + min(0.16, action_bonus)
                    context_bundle_applied_rows += 1
                    context_bundle_titles.add(target_section_title)
                    context_bundle_contexts.add(_format_context_signature(str(best_context_bundle["context_signature"])))
                    context_bundle_source_runs = max(context_bundle_source_runs, int(best_context_bundle["attempts"]))
                    reason_text = f"{target_section_title}: {row['_combo_context_bundle_learning_reason']}"
                    if reason_text not in context_bundle_reasons:
                        context_bundle_reasons.append(reason_text)
                    if bundle_display not in context_bundle_texts:
                        context_bundle_texts.append(bundle_display)
                continue
            if not bundle_enabled:
                continue
            best_bundle: Dict[str, Any] | None = None
            for raw_bundle_id, attempts_raw in bundle_attempts_map.items():
                attempts = int(attempts_raw or 0)
                if attempts < bundle_min_runs:
                    continue
                bundle_combos = _split_bundle_key(str(raw_bundle_id))
                if len(bundle_combos) < 2:
                    continue
                bundle_set = set(bundle_combos)
                if not bundle_set.issubset(candidate_combo_pool):
                    continue
                gate_count = int(bundle_gate_map.get(raw_bundle_id) or 0)
                pass_rate = float(gate_count) / float(attempts or 1)
                if pass_rate < bundle_min_pass_rate:
                    continue
                score = pass_rate + (pass_rate * bundle_gate_pass_bonus) + min(0.05, float(attempts) * 0.01) + min(0.03, float(len(bundle_combos)) * 0.01)
                candidate = {
                    "bundle_id": str(raw_bundle_id),
                    "bundle_combos": bundle_combos,
                    "attempts": attempts,
                    "pass_rate": round(pass_rate, 4),
                    "score": round(score, 4),
                }
                if best_bundle is None or float(candidate["score"]) > float(best_bundle["score"]):
                    best_bundle = candidate
            if not best_bundle:
                continue
            boost = max(
                1,
                int(round((float(best_bundle["pass_rate"]) - bundle_min_pass_rate) * 10.0)) + max(1, len(best_bundle["bundle_combos"]) - 1),
            )
            boost = min(bundle_max_boost, max(1, boost))
            bundle_display = _format_bundle_display(
                str(best_bundle["bundle_id"]),
                attempts=int(best_bundle["attempts"]),
                pass_rate=float(best_bundle["pass_rate"]),
            )
            for pos, row in enumerate(title_rows):
                combo_ids = row_combo_map.get(pos) or []
                if not set(combo_ids).intersection(best_bundle["bundle_combos"]):
                    continue
                row["_combo_bundle_learning_applied"] = True
                row["_combo_bundle_learning_priority_boost"] = boost
                row["_combo_bundle_learning_score"] = float(best_bundle["score"])
                row["_combo_bundle_learning_reason"] = (
                    f"historical_combo_bundle_pass_rate={float(best_bundle['pass_rate']):.2f}; "
                    f"bundle_size={len(best_bundle['bundle_combos'])}; "
                    f"bundle_match_count={len(set(combo_ids).intersection(best_bundle['bundle_combos']))}"
                )
                row["_combo_bundle_learning_best_bundle"] = bundle_display
                row["_combo_bundle_learning_source_runs"] = int(best_bundle["attempts"])
                bundle_applied_rows += 1
                bundle_titles.add(target_section_title)
                bundle_source_runs = max(bundle_source_runs, int(best_bundle["attempts"]))
                reason_text = f"{target_section_title}: {row['_combo_bundle_learning_reason']}"
                if reason_text not in bundle_reasons:
                    bundle_reasons.append(reason_text)
                if bundle_display not in bundle_texts:
                    bundle_texts.append(bundle_display)

    out_rows.sort(
        key=lambda item: (
            -(
                int(item.get("strategy_priority") or 0)
                + int(item.get("_combo_learning_priority_boost") or 0)
                + int(item.get("_combo_context_bundle_learning_priority_boost") or 0)
                + int(item.get("_combo_bundle_learning_priority_boost") or 0)
            ),
            -(
                float(item.get("_combo_context_bundle_learning_score") or 0.0)
                + float(item.get("_combo_bundle_learning_score") or 0.0)
                + float(item.get("_combo_learning_score") or 0.0)
            ),
            str(item.get("indicator_group") or ""),
            str(item.get("title") or ""),
            str(item.get("type") or ""),
        )
    )
    for row in out_rows:
        if isinstance(row, dict):
            row.pop("_candidate_combo_ids", None)
    return {
        "enabled": True,
        "applied": applied_rows > 0,
        "applied_count": applied_rows,
        "source_runs": max_source_runs,
        "titles": sorted(titles),
        "reasons": reasons[:6],
        "combos": combos[:6],
        "bundle_applied": bundle_applied_rows > 0,
        "bundle_applied_count": bundle_applied_rows,
        "bundle_source_runs": bundle_source_runs,
        "bundle_titles": sorted(bundle_titles),
        "bundle_reasons": bundle_reasons[:6],
        "bundles": bundle_texts[:6],
        "context_bundle_applied": context_bundle_applied_rows > 0,
        "context_bundle_applied_count": context_bundle_applied_rows,
        "context_bundle_source_runs": context_bundle_source_runs,
        "context_bundle_titles": sorted(context_bundle_titles),
        "context_bundle_contexts": sorted([x for x in context_bundle_contexts if str(x).strip()]),
        "context_bundle_reasons": context_bundle_reasons[:6],
        "context_bundles": context_bundle_texts[:6],
        "rows": out_rows,
    }


def summarize_runtime_budget_profile(
    *,
    params: Dict[str, Any] | None = None,
    profile: Dict[str, Any] | None = None,
    limit: int = 6,
) -> Dict[str, Any]:
    cfg = _resolve_self_evolution_config(params)
    profile_obj = profile if isinstance(profile, dict) else load_runtime_budget_profile()
    entries = profile_obj.get("entries") if isinstance(profile_obj.get("entries"), dict) else {}
    maintenance = profile_obj.get("maintenance") if isinstance(profile_obj.get("maintenance"), dict) else {}
    try:
        top_n = max(1, min(20, int(limit)))
    except Exception:
        top_n = 6

    rows: list[Dict[str, Any]] = []
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        runs = max(0, int(entry.get("runs") or 0))
        success_runs = max(0, int(entry.get("success_runs") or 0))
        error_runs = max(0, int(entry.get("error_runs") or 0))
        fallback_runs = max(0, int(entry.get("fallback_runs") or 0))
        compaction_runs = max(0, int(entry.get("compaction_runs") or 0))
        quality_issue_runs = max(0, int(entry.get("quality_issue_runs") or 0))
        rows.append(
            {
                "profile_key": str(key),
                "title": str(entry.get("title") or "").strip(),
                "project_type": str(entry.get("project_type") or "").strip(),
                "generation_mode": str(entry.get("generation_mode") or "").strip(),
                "runs": runs,
                "success_runs": success_runs,
                "error_runs": error_runs,
                "fallback_runs": fallback_runs,
                "compaction_runs": compaction_runs,
                "quality_issue_runs": quality_issue_runs,
                "success_rate": round(float(success_runs) / float(runs or 1), 4),
                "avg_timeout_sec": _safe_avg(float(entry.get("timeout_total") or 0.0), runs),
                "avg_max_tokens": _safe_avg(float(entry.get("max_tokens_total") or 0.0), runs),
                "avg_retry_limit": _safe_avg(float(entry.get("retry_total") or 0.0), runs),
                "last_runtime_budget_reason": str(entry.get("last_runtime_budget_reason") or "").strip(),
                "last_used_key_alias": str(entry.get("last_used_key_alias") or "").strip(),
                "top_indicator_groups": _top_counter_items(entry.get("indicator_group_counts")),
                "top_strategy_ids": _top_counter_items(entry.get("strategy_counts")),
                "top_action_tags": _top_counter_items(entry.get("action_tag_counts")),
                "top_context_signatures": _top_context_signature_items(entry.get("context_signature_counts")),
                "top_effective_combos": _top_effective_combos(entry),
                "top_effective_combo_bundles": _top_effective_combo_bundles(entry),
                "top_effective_context_bundles": _top_effective_context_bundles(entry),
                "top_attributed_context_bundles": _top_attributed_context_bundles(entry),
                "top_metric_effects": _top_context_metric_effects(entry),
                "top_metric_action_effects": _top_context_metric_action_effects(entry),
                "last_indicator_groups": [str(x) for x in (entry.get("last_indicator_groups") or []) if str(x).strip()],
                "last_strategy_ids": [str(x) for x in (entry.get("last_strategy_ids") or []) if str(x).strip()],
                "last_action_tags": [str(x) for x in (entry.get("last_action_tags") or []) if str(x).strip()],
                "last_effective_combos": [str(x) for x in (entry.get("last_effective_combos") or []) if str(x).strip()],
                "last_effective_combo_bundle": [str(x) for x in (entry.get("last_effective_combo_bundle") or []) if str(x).strip()],
                "last_attributed_context_bundles": [str(x) for x in (entry.get("last_attributed_context_bundles") or []) if str(x).strip()],
                "last_metric_effects": [str(x) for x in (entry.get("last_metric_effects") or []) if str(x).strip()],
                "last_metric_action_effects": [str(x) for x in (entry.get("last_metric_action_effects") or []) if str(x).strip()],
                "last_context_signature": str(entry.get("last_context_signature") or "").strip(),
                "last_updated_at": str(entry.get("last_updated_at") or "").strip(),
            }
        )
    rows.sort(
        key=lambda item: (
            -int(item.get("runs") or 0),
            -int(item.get("quality_issue_runs") or 0),
            -int(item.get("fallback_runs") or 0),
            str(item.get("title") or ""),
        )
    )

    return {
        "enabled": bool(cfg.get("enabled", True)),
        "profile_path": str(RUNTIME_BUDGET_PROFILE_PATH),
        "profile_version": str(profile_obj.get("version") or ""),
        "updated_at": str(profile_obj.get("updated_at") or ""),
        "entry_count": len(rows),
        "maintenance": maintenance,
        "top_entries": rows[:top_n],
    }
