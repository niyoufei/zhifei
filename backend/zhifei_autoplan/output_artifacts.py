from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.exporter import (
    export_autoplan_compare_docx,
    export_autoplan_docx,
    export_autoplan_focus_xlsx,
)


_RAW_PROMPT_KEYS = {
    "prompt",
    "messages",
    "system_prompt",
    "stable_system_prompt",
    "shared_context_prompt",
    "dynamic_prompt",
}


def _without_raw_prompts(value: Any, *, key: str = "") -> Any:
    if str(key or "").strip().lower() in _RAW_PROMPT_KEYS:
        return "[OMITTED]"
    if isinstance(value, dict):
        return {
            str(child_key): _without_raw_prompts(child_value, key=str(child_key))
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [_without_raw_prompts(item) for item in value]
    if isinstance(value, tuple):
        return [_without_raw_prompts(item) for item in value]
    return value


def sanitize_output_payload(value: Any) -> Any:
    """Return a persistence-safe result tree without raw model prompts."""

    return _without_raw_prompts(value)


def save_outputs(
    base_name: str,
    results: list[dict],
    *,
    preview_only: bool = False,
) -> dict:
    build_dir = Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    out_json = build_dir / f"{base_name}.json"
    out_json.write_text(
        json.dumps(
            {"variants": sanitize_output_payload(results)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if preview_only:
        # A dry-run is a diagnostic preview, not a bidder-facing delivery.
        # Persist the sanitized structured result, but never route it through
        # formal DOCX/XLSX exporters or their professional delivery gates.
        return {
            "json": str(out_json),
            "docx": [],
            "compare_docx": [],
            "focus_xlsx": [],
            "score_overview_xlsx": [],
            "expert_review_docx": [],
        }
    docx_files = []
    compare_files = []
    focus_xlsx_files = []
    score_overview_xlsx_files = []
    expert_review_docx_files = []
    for i, variant in enumerate(results):
        out_docx = build_dir / f"{base_name}_v{i + 1}.docx"
        export_autoplan_docx(variant, str(out_docx))
        docx_files.append(str(out_docx))
        out_compare = build_dir / f"{base_name}_compare_v{i + 1}.docx"
        export_autoplan_compare_docx(variant, str(out_compare))
        compare_files.append(str(out_compare))
        out_focus = build_dir / f"{base_name}_focus_v{i + 1}.xlsx"
        try:
            focus_path = export_autoplan_focus_xlsx(variant, str(out_focus))
        except Exception:
            focus_path = ""
        focus_xlsx_files.append(str(focus_path) if focus_path else None)
        out_overview = build_dir / f"{base_name}_评分点覆盖与证据引用总览_v{i + 1}.xlsx"
        try:
            from backend.zhifei_autoplan.exporter import export_scoring_evidence_overview_xlsx

            overview_path = export_scoring_evidence_overview_xlsx(variant, str(out_overview))
        except Exception:
            overview_path = ""
        score_overview_xlsx_files.append(str(overview_path) if overview_path else None)

        out_review = build_dir / f"{base_name}_专家复核提要版_v{i + 1}.docx"
        try:
            from backend.zhifei_autoplan.exporter import export_expert_review_brief_docx

            review_path = export_expert_review_brief_docx(variant, str(out_review))
        except Exception:
            review_path = ""
        expert_review_docx_files.append(str(review_path) if review_path else None)
    return {
        "json": str(out_json),
        "docx": docx_files,
        "compare_docx": compare_files,
        "focus_xlsx": focus_xlsx_files,
        "score_overview_xlsx": score_overview_xlsx_files,
        "expert_review_docx": expert_review_docx_files,
    }
