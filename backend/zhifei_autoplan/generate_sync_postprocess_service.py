from __future__ import annotations

import re
from typing import Any, Callable


def postprocess_generate_sync_results(
    *,
    payload: dict[str, Any],
    results: list[dict[str, Any]],
    load_params_fn: Callable[[], dict[str, Any]],
    rebuild_postprocessed_fn: Callable[..., None],
    workspace_dir_from_payload_fn: Callable[[dict[str, Any] | None], str | None],
    compute_variant_similarity_fn: Callable[..., dict[str, Any]],
    apply_diversity_autofix_fn: Callable[..., bool],
) -> None:
    if len(results) < 2:
        return
    try:
        params = load_params_fn()
        overrides = payload.get("params_override")
        if isinstance(overrides, dict) and overrides:
            for key, value in overrides.items():
                if isinstance(value, dict) and isinstance(params.get(key), dict):
                    merged = dict(params.get(key) or {})
                    merged.update(value)
                    params[key] = merged
                else:
                    params[key] = value

        div_cfg = params.get("variant_diversity") if isinstance(params.get("variant_diversity"), dict) else {}

        def _run_report() -> dict[str, Any]:
            return compute_variant_similarity_fn(
                results,
                chapter_threshold=float(div_cfg.get("chapter_threshold") or 0.90),
                overall_threshold=float(div_cfg.get("overall_threshold") or 0.85),
                min_chars=int(div_cfg.get("min_chars") or 800),
                ignore_title_keywords=(div_cfg.get("ignore_title_keywords") if isinstance(div_cfg.get("ignore_title_keywords"), list) else None),
                relaxed_title_keywords=(div_cfg.get("relaxed_title_keywords") if isinstance(div_cfg.get("relaxed_title_keywords"), list) else None),
                relaxed_chapter_threshold=(float(div_cfg.get("relaxed_chapter_threshold")) if div_cfg.get("relaxed_chapter_threshold") is not None else None),
            )

        report = _run_report()
        max_rounds = int(div_cfg.get("auto_fix_rounds") or 1)
        if max_rounds < 0:
            max_rounds = 0
        rounds = 0
        while rounds < max_rounds and report.get("ok") is False and report.get("flagged"):
            changed_any = False
            for flagged in (report.get("flagged") or [])[:24]:
                title = str(flagged.get("title") or "").strip()
                pair = str(flagged.get("pair") or "").strip()
                match = re.match(r"^v(\d+)_v(\d+)$", pair)
                if not match or not title:
                    continue
                later_index = max(int(match.group(1)), int(match.group(2)))
                if later_index <= 1 or later_index > len(results):
                    continue
                target = results[later_index - 1]
                sections = target.get("sections") if isinstance(target, dict) else None
                if not isinstance(sections, list):
                    continue
                for sec in sections:
                    if not isinstance(sec, dict):
                        continue
                    if str(sec.get("title") or "").strip() != title:
                        continue
                    if apply_diversity_autofix_fn(sec, params=params, evidence_hint=str(pair)):
                        changed_any = True
                    break
            if not changed_any:
                break
            report = _run_report()
            rounds += 1

        rebuild_postprocessed_fn(
            results,
            payload=payload,
            report=report,
            params=params,
            workspace_dir=workspace_dir_from_payload_fn(payload),
        )
    except Exception:
        return None

