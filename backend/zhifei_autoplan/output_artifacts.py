from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.exporter import (
    export_autoplan_compare_docx,
    export_autoplan_docx,
    export_autoplan_focus_xlsx,
)
from backend.zhifei_autoplan.workspace import workspace_paths


def save_outputs(base_name: str, results: list[dict], *, workspace_dir: str | None = None) -> dict:
    build_dir = workspace_paths(workspace_dir)["build"] if workspace_dir else Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    out_json = build_dir / f"{base_name}.json"
    out_json.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    docx_files = []
    compare_files = []
    focus_xlsx_files = []
    score_overview_xlsx_files = []
    expert_review_docx_files = []
    for i, variant in enumerate(results):
        if isinstance(variant, dict) and workspace_dir and not str(variant.get("workspace_dir") or "").strip():
            variant["workspace_dir"] = workspace_dir
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
