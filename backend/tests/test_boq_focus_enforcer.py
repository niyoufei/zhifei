"""Unit tests for backend/zhifei_autoplan/boq_focus_enforcer.py"""

from __future__ import annotations

import hashlib
from copy import deepcopy

from backend.zhifei_autoplan import evidence
from backend.zhifei_autoplan.boq_focus_enforcer import (
    _find_focus_card_span,
    ensure_boq_focus_item_cards,
)
from backend.zhifei_autoplan.project_fact_ledger import build_project_fact_ledger


def _boq_focus():
    return {
        "must_cover_keywords": ["防水卷材"],
        "lines": [
            "清单重点（材料价格高）：",
            "- 防水卷材 / 工程量=100m2 / 单价=50 / 合价=5000",
        ],
    }


def _quality_threshold_item(
    *,
    item_id: str,
    process: str,
    metric: str,
    operator: str,
    value,
    unit: str,
    filename: str,
    sha_char: str,
    page: int,
    offset: int,
    status: str,
) -> dict:
    document_sha256 = sha_char * 64
    end = offset + 16
    return {
        "id": item_id,
        "process": process,
        "metric": metric,
        "operator": operator,
        "value": value,
        "unit": unit,
        "status": status,
        "source": "reviewed_design",
        "locator": f"{filename}#p{page}_{document_sha256}@{offset}",
        "document_sha256": document_sha256,
        "extract_text_sha256": hashlib.sha256(
            f"extract:{item_id}".encode()
        ).hexdigest(),
        "page": page,
        "page_text_sha256": hashlib.sha256(
            f"page:{item_id}".encode()
        ).hexdigest(),
        "offset": offset,
        "end": end,
        "page_start_offset": 0,
        "page_end_offset": max(1000, end + 1),
        "page_match_start": offset,
        "page_match_end": end,
        "match_text_sha256": hashlib.sha256(
            f"match:{item_id}".encode()
        ).hexdigest(),
    }


def test_injects_into_section_where_item_is_mentioned():
    sections = [
        {"title": "质量管理", "content": "本章涉及防水卷材的进场复验与验收。"},
        {"title": "主要施工方案", "content": "施工方案内容。"},
    ]
    changed, injected = ensure_boq_focus_item_cards(sections, _boq_focus(), evidence_src="清单.pdf#p1_abcd@10")
    assert changed is True
    assert "防水卷材" in injected
    assert "【清单重点项控制卡】" in sections[0]["content"]
    assert "防水卷材" in sections[0]["content"]


def test_title_token_match_selects_best_chapter():
    sections = [
        {"title": "防水工程施工方案", "content": "方案正文。"},
        {"title": "质量管理", "content": "质量正文。"},
    ]
    changed, injected = ensure_boq_focus_item_cards(sections, _boq_focus(), evidence_src="清单.pdf#p1_abcd@10")
    assert changed is True
    assert "防水卷材" in injected
    assert "【清单重点项控制卡】" in sections[0]["content"]
    assert "防水卷材" in sections[0]["content"]


def test_idempotent_second_call_no_changes():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    boq_focus = _boq_focus()
    changed1, injected1 = ensure_boq_focus_item_cards(sections, boq_focus, evidence_src="清单.pdf#p1_abcd@10")
    assert changed1 is True
    assert injected1

    changed2, injected2 = ensure_boq_focus_item_cards(sections, boq_focus, evidence_src="清单.pdf#p1_abcd@10")
    assert changed2 is False
    assert injected2 == []


def test_missing_project_facts_never_promote_registry_defaults_into_focus_card():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        _boq_focus(),
        evidence_src="清单.pdf#p1_abcd@10",
        params={
            "quant_defaults": {
                "频次": "2次/日（班前+收工）",
                "阈值": "偏差≤5mm",
                "时长": "4h/作业段",
                "人数": "8人/班",
                "设备型号": "20t挖机1台",
            }
        },
    )

    content = sections[0]["content"]
    assert changed is True
    assert injected == ["防水卷材"]
    for guessed in ("2次/日", "偏差≤5mm", "4h", "8人/班", "20t挖机"):
        assert guessed not in content
    assert "频次=待依据经批准项目制度确认" in content
    assert "阈值=待按图纸及适用规范逐工序确认" in content
    assert "偏差处置时限=待依据经批准项目制度确认" in content
    assert "【证据:清单.pdf#p1_abcd@10】" in content


def test_focus_card_uses_only_accepted_project_facts_with_locators():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    threshold = _quality_threshold_item(
        item_id="waterproof-lap-width",
        process="防水卷材铺贴",
        metric="搭接宽度",
        operator=">=",
        value=100,
        unit="mm",
        filename="防水图.pdf",
        sha_char="a",
        page=2,
        offset=42,
        status="approved",
    )
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved",
                "source_type": "approved_resolution",
                "facts": {
                    "risk_inspection_frequency": "逐班",
                    "quality_threshold": {
                        "mode": "process_bound",
                        "items": [threshold],
                    },
                    "deviation_action_deadline": {"value": 6, "unit": "小时"},
                },
                "evidence": {"locator": "approved_resolution"},
            }
        ]
    )

    changed, _ = ensure_boq_focus_item_cards(
        sections,
        _boq_focus(),
        evidence_src="清单.pdf#p1_abcd@10",
        project_fact_ledger=ledger,
        boq_data={
            "items": [
                {"name": "防水卷材", "process": {"name": "防水卷材铺贴"}}
            ]
        },
    )

    content = sections[0]["content"]
    assert changed is True
    assert "频次=逐班【证据:approved_resolution】" in content
    assert f"阈值=搭接宽度≥100mm【证据:{threshold['locator']}】" in content
    assert "偏差处置时限=6小时【证据:approved_resolution】" in content
    assert "2次/日" not in content
    assert "偏差≤5mm" not in content
    assert "4h" not in content


def test_process_bound_quality_thresholds_never_cross_reuse_between_focus_items():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    boq_focus = {
        "must_cover_keywords": ["防水卷材", "钢梁"],
        "lines": [
            "- 防水卷材 / 工程量=100m2",
            "- 钢梁 / 工程量=59.214t",
        ],
    }
    waterproof_threshold = _quality_threshold_item(
        item_id="waterproof-lap-width",
        process="防水卷材铺贴",
        metric="搭接宽度",
        operator=">=",
        value=100,
        unit="mm",
        filename="防水图.pdf",
        sha_char="b",
        page=2,
        offset=80,
        status="approved",
    )
    steel_threshold = _quality_threshold_item(
        item_id="steel-verticality",
        process="钢梁安装",
        metric="垂直度偏差",
        operator="<=",
        value=3,
        unit="mm",
        filename="钢结构图.pdf",
        sha_char="c",
        page=5,
        offset=160,
        status="verified",
    )
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved-thresholds",
                "source_type": "approved_resolution",
                "facts": {
                    "quality_threshold": {
                        "mode": "process_bound",
                        "items": [waterproof_threshold, steel_threshold],
                    }
                },
                "evidence": {"locator": "approved_resolution"},
            }
        ]
    )

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_abcd@10",
        project_fact_ledger=ledger,
        boq_data={
            "items": [
                {"name": "防水卷材", "process": {"name": "防水卷材铺贴"}},
                {"name": "钢梁", "process": {"name": "钢梁安装"}},
            ]
        },
    )

    assert changed is True
    assert injected == ["防水卷材", "钢梁"]
    content = sections[0]["content"]
    waterproof_span = _find_focus_card_span(content, "防水卷材")
    steel_span = _find_focus_card_span(content, "钢梁")
    assert waterproof_span is not None
    assert steel_span is not None
    waterproof = content[waterproof_span[0] : waterproof_span[1]]
    steel = content[steel_span[0] : steel_span[1]]
    assert "搭接宽度≥100mm" in waterproof
    assert "垂直度偏差≤3mm" not in waterproof
    assert "垂直度偏差≤3mm" in steel
    assert "搭接宽度≥100mm" not in steel


def test_legacy_scalar_quality_threshold_cannot_fill_formal_focus_control():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "legacy",
                "source_type": "approved_resolution",
                "facts": {"quality_threshold": "全局偏差≤5mm"},
                "evidence": {"locator": "approved_resolution"},
            }
        ]
    )

    ensure_boq_focus_item_cards(
        sections,
        _boq_focus(),
        evidence_src="清单.pdf#p1_abcd@10",
        project_fact_ledger=ledger,
        boq_data={
            "items": [
                {"name": "防水卷材", "process": {"name": "防水卷材铺贴"}}
            ]
        },
    )

    content = sections[0]["content"]
    assert "全局偏差≤5mm" not in content
    assert "阈值=待按图纸及适用规范逐工序确认" in content


def test_skip_when_item_already_closed_in_existing_content():
    sections = [
        {
            "title": "主要施工方案",
            "content": (
                "防水卷材已纳入控制。"
                "量化指标：频次=2次/日；阈值=偏差≤5mm；人数=8人/班。"
                "风险→控制→验证：风险：返工；控制：抽检；验证：合格率≥98%。【证据:清单.pdf#p1_abcd@10】"
            ),
        }
    ]
    changed, injected = ensure_boq_focus_item_cards(sections, _boq_focus(), evidence_src="清单.pdf#p1_abcd@10")
    assert changed is False
    assert injected == []


def test_injects_focus_items_beyond_the_legacy_twelve_item_prefix():
    names = [f"重点项{i}" for i in range(1, 14)]
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        {"must_cover_keywords": names, "lines": []},
        evidence_src="清单.pdf#p1_abcd1234@10",
    )

    assert changed is True
    assert injected == names
    assert "清单项：重点项13" in sections[0]["content"]


def test_focus_line_details_join_card_by_canonical_name_key():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    boq_focus = {
        "must_cover_keywords": ["铝 方通吊顶（顶棚四）"],
        "lines": ["- 铝方通吊顶(顶棚四) / 工程量=12m2 / 单价=50 / 合价=600"],
    }

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_abcd1234@10",
    )

    assert changed is True
    assert injected == ["铝 方通吊顶(顶棚四)"]
    assert "清单项：铝方通吊顶(顶棚四)；工程量=12m2；单价=50；合价=600" in sections[0]["content"]


def test_focus_card_lookup_uses_canonical_name_key():
    text = (
        "前文\n"
        "- 清单项: 铝 方通吊顶（顶棚四）；工程量=12m2\n"
        "  量化指标：频次=2次/日。\n"
        "后文\n"
    )

    span = _find_focus_card_span(text, "铝方通吊顶(顶棚四)")

    assert span is not None
    start, end, line_end = span
    assert text[start:line_end].startswith("- 清单项: 铝 方通吊顶")
    assert text[start:end].endswith("后文\n")


def test_hazardous_material_boilerplate_is_centralized_and_idempotent():
    names = ["氧气瓶", "乙炔瓶", "防水涂料"]
    sections = [{"title": "材料与安全管理", "content": "危险品材料分类管理。"}]
    boq_focus = {
        "must_cover_keywords": names,
        "hazardous_materials": names,
        "lines": [f"- {name} / 工程量=1项" for name in names],
    }

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p3_abcd1234@30",
    )

    content = sections[0]["content"]
    assert changed is True
    assert injected == names
    assert content.count("【危险品材料统一管理基线】") == 1
    assert content.count("MSDS随货逐批核验") == 1
    for name in names:
        assert f"{name}挥发/燃爆/泄漏" in content
        assert f"《{name}风险与领用核验记录》" in content

    first = content
    changed_again, injected_again = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p3_abcd1234@30",
    )
    assert changed_again is False
    assert injected_again == []
    assert sections[0]["content"] == first


def test_focus_drawing_binding_repairs_short_locator_and_is_idempotent(monkeypatch):
    sha256 = "a" * 64
    drawing_text = "钢梁安装构件位置与连接做法。"
    locator = f"钢梁图.pdf#p1_{sha256}@0"
    hit = {
        "filename": "钢梁图.pdf",
        "sha256": sha256,
        "page": 1,
        "offset": 0,
        "locator": locator,
        "snippet": drawing_text,
        "matched_token": "钢梁",
        "matched_text": "钢梁",
        "match_start": 0,
        "match_end": 2,
        "match_window": {
            "start_offset": 0,
            "end_offset": len(drawing_text),
            "text": drawing_text,
            "text_sha256": hashlib.sha256(drawing_text.encode()).hexdigest(),
            "summary": drawing_text,
        },
        "page_text_sha256": hashlib.sha256(drawing_text.encode()).hexdigest(),
        "page_summary": drawing_text,
        "page_boundary_status": "reliable_declared_single_page",
    }
    monkeypatch.setattr(
        evidence,
        "list_ingested_filenames_by_tag",
        lambda tag, **_kwargs: ["钢梁图.pdf"] if tag == "drawing" else [],
    )
    drawing_queries: list[str] = []

    def _drawing_hit(query, **_kwargs):
        drawing_queries.append(query)
        return dict(hit)

    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_drawing_hit",
        _drawing_hit,
    )
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_ingested_hit",
        lambda *_args, **_kwargs: None,
    )
    sections = [
        {
            "title": "钢结构施工工艺",
            "content": (
                "- 清单项：钢梁\n"
                "  量化指标：频次=1次/日；阈值=10mm；间距=200mm。\n"
                "  图纸定位：钢梁图.pdf#p1_deadbeef@0；校核点=构件位置。"
                "【证据:钢梁图.pdf#p1_deadbeef@0】\n"
                "  风险→控制→验证：风险：偏差；控制：复核；验证：验收。"
                "【证据:清单.pdf#p1_deadbeef@0】\n"
            ),
        }
    ]
    boq_focus = {"must_cover_keywords": ["钢梁"], "lines": []}
    boq_data = {"items": [{"name": "钢梁", "process": {"name": "钢梁安装"}}]}

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_deadbeef@0",
        project_id="p1",
        boq_data=boq_data,
    )

    assert changed is True
    assert injected == []
    assert drawing_queries == ["钢梁 钢梁安装"]
    assert "钢梁图.pdf#p1_deadbeef@0" not in sections[0]["content"]
    assert sections[0]["content"].count(locator) == 2
    binding = boq_focus["drawing_bindings"][0]
    assert binding["locator"] == locator
    assert binding["binding_basis"] == "focus_item_specific_extract_hit"
    assert binding["source_relation"] == {
        "type": "boq_focus_item_drawing",
        "focus_item": "钢梁",
        "chapter": "钢结构施工工艺",
        "project_id": "p1",
    }

    first_sections = [dict(sections[0])]
    first_bindings = deepcopy(boq_focus["drawing_bindings"])
    changed_again, injected_again = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_deadbeef@0",
        project_id="p1",
        boq_data=boq_data,
    )

    assert changed_again is False
    assert injected_again == []
    assert drawing_queries == ["钢梁 钢梁安装", "钢梁 钢梁安装"]
    assert sections == first_sections
    assert boq_focus["drawing_bindings"] == first_bindings


def test_missing_item_specific_drawing_hit_does_not_duplicate_existing_card(
    monkeypatch,
):
    monkeypatch.setattr(
        evidence,
        "list_ingested_filenames_by_tag",
        lambda tag, **_kwargs: ["其他构件图.pdf"] if tag == "drawing" else [],
    )
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_drawing_hit",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_ingested_hit",
        lambda *_args, **_kwargs: None,
    )
    sections = [{"title": "钢结构施工工艺", "content": "钢梁安装方案。"}]
    boq_focus = {"must_cover_keywords": ["钢梁"], "lines": []}
    boq_data = {"items": [{"name": "钢梁", "process": {"name": "钢梁安装"}}]}

    first_changed, first_injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_deadbeef@0",
        project_id="p1",
        boq_data=boq_data,
    )
    first_content = sections[0]["content"]
    second_changed, second_injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_deadbeef@0",
        project_id="p1",
        boq_data=boq_data,
    )

    assert first_changed is True
    assert first_injected == ["钢梁"]
    assert second_changed is False
    assert second_injected == []
    assert sections[0]["content"] == first_content
    assert sections[0]["content"].count("- 清单项：钢梁") == 1


def test_incomplete_drawing_hit_clears_stale_structured_binding(monkeypatch):
    monkeypatch.setattr(
        evidence,
        "list_ingested_filenames_by_tag",
        lambda tag, **_kwargs: ["钢梁图.pdf"] if tag == "drawing" else [],
    )
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_drawing_hit",
        lambda *_args, **_kwargs: {
            "filename": "钢梁图.pdf",
            "sha256": "deadbeef",
            "page": 1,
            "offset": 0,
            "locator": "钢梁图.pdf#p1_deadbeef@0",
        },
    )
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_ingested_hit",
        lambda *_args, **_kwargs: None,
    )
    sections = [
        {
            "title": "钢结构施工工艺",
            "content": (
                "钢梁：频次=1次/日；阈值=10mm；间距=200mm；"
                "风险→控制→验证。【证据:钢梁图.pdf#p1_deadbeef@0】"
            ),
        }
    ]
    boq_focus = {
        "must_cover_keywords": ["钢梁"],
        "lines": [],
        "drawing_bindings": [{"focus_item": "钢梁", "locator": "stale"}],
    }

    changed, _ = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_deadbeef@0",
        project_id="p1",
        boq_data={"items": [{"name": "钢梁"}]},
    )

    assert changed is True
    assert boq_focus["drawing_bindings"] == []
