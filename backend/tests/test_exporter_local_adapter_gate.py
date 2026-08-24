from __future__ import annotations

import json

import pytest

from backend.zhifei_autoplan import exporter
from backend.zhifei_autoplan.exporter import (
    _require_local_adapter_export_allowed,
    export_autoplan_docx,
)


def _complete_export_payload():
    return {
        "sections": [
            {
                "title": "第十六章 风险与措施",
                "content": (
                    "信息化管理、绿色工地、劳保用品和劳保用品配置矩阵均纳入实施方案。"
                    "关键工序控制点表记录参数、频次、责任、验收和记录要求，形成风险控制措施。"
                ),
                "evidence_refs": ["quality:final-review"],
            }
        ]
    }


def test_complete_content_passes_export_gate():
    assert _require_local_adapter_export_allowed(_complete_export_payload(), "docx") is None


def test_tender_aligned_twelve_chapter_risk_section_passes_export_gate():
    data = _complete_export_payload()
    data["sections"][0]["title"] = "第十二章 风险识别与控制措施"

    assert _require_local_adapter_export_allowed(data, "docx") is None


def test_risk_control_and_verification_wording_passes_without_literal_measures():
    data = _complete_export_payload()
    data["sections"][0]["title"] = "第十二章 风险控制与验证"
    data["sections"][0]["content"] = (
        "信息化管理、绿色工地、劳保用品和劳保用品配置矩阵均纳入实施方案。"
        "关键工序控制点表记录参数、频次、责任、验收和记录要求。"
        "对施工风险执行事前预防、过程控制、异常处置和复验销项。"
    )

    assert _require_local_adapter_export_allowed(data, "docx_build_report") is None


def test_risk_without_any_treatment_wording_remains_blocked():
    data = _complete_export_payload()
    data["sections"][0]["title"] = "风险识别"
    data["sections"][0]["content"] = (
        "信息化管理、绿色工地、劳保用品和劳保用品配置矩阵均纳入实施方案。"
        "关键工序控制点表记录参数、频次、责任、验收和记录要求。"
        "本章仅列出风险清单。"
    )

    with pytest.raises(RuntimeError) as exc_info:
        _require_local_adapter_export_allowed(data, "docx_build_report")

    payload = json.loads(str(exc_info.value))
    assert "RISK_MEASURES_MISSING" in {issue["code"] for issue in payload["issues"]}


def test_incomplete_content_is_blocked_with_machine_readable_issues():
    with pytest.raises(RuntimeError) as exc_info:
        _require_local_adapter_export_allowed(
            {"sections": [{"title": "工程概况", "content": "仅有项目简介。"}]},
            "docx",
        )

    payload = json.loads(str(exc_info.value))
    assert payload["status"] == "blocked"
    assert payload["export_allowed"] is False
    assert payload["export_kind"] == "docx"
    assert {issue["code"] for issue in payload["issues"]} >= {
        "MANDATORY_CONTENT_MISSING",
        "RISK_MEASURES_MISSING",
        "PARAMETER_TRACE_MISSING",
    }


def test_explicit_adapter_rejection_cannot_be_bypassed_by_complete_content():
    data = _complete_export_payload()
    data["local_adapter"] = {
        "export_allowed": False,
        "issues": [{"code": "REVIEW_REJECTED", "message": "independent review rejected export"}],
    }

    with pytest.raises(RuntimeError) as exc_info:
        _require_local_adapter_export_allowed(data, "docx")

    payload = json.loads(str(exc_info.value))
    assert payload["issues"] == [
        {"code": "REVIEW_REJECTED", "message": "independent review rejected export"}
    ]


def test_build_report_gate_blocks_before_docx_is_saved(monkeypatch, tmp_path):
    output_path = tmp_path / "blocked.docx"
    calls = []

    def _gate(_data, export_kind):
        calls.append(export_kind)
        if export_kind == "docx_build_report":
            raise RuntimeError("submission content blocked")

    monkeypatch.setattr(exporter, "_require_local_adapter_export_allowed", _gate)

    with pytest.raises(RuntimeError, match="submission content blocked"):
        export_autoplan_docx(_complete_export_payload(), str(output_path))

    assert calls == ["docx", "docx_build_report"]
    assert not output_path.exists()
    assert not output_path.with_suffix(".build_report.json").exists()
    assert not output_path.with_suffix(".build_report.log").exists()
