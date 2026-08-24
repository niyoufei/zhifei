from __future__ import annotations

from backend.zhifei_autoplan.local_acceptance_hook import run_acceptance


def test_acceptance_propagates_independent_content_quality_block():
    result = run_acceptance(
        {
            "sections": [{"title": "施工方案", "content": "风险及控制措施，参数、频次、责任、验收和记录。"}],
            "quality_checks": {
                "quality_gate": {
                    "enforced": True,
                    "pass": False,
                    "blocking_issues": [
                        {
                            "code": "QUALITY_SCORE_BELOW_THRESHOLD",
                            "message": "独立内容质量总分不足",
                            "dimension": "tender_alignment",
                        }
                    ],
                }
            },
        }
    )
    codes = {row.get("code") for row in result["issues"]}
    assert "QUALITY_SCORE_BELOW_THRESHOLD" in codes
    assert result["export_allowed"] is False
