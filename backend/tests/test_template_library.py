from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.template_library import (
    build_template_chapter_profiles,
    build_template_chapter_learning_context,
    delete_template_library_item,
    infer_template_scene_tags,
    list_template_library_items,
    match_template_chapter_theme,
    search_template_library_docs,
    summarize_template_learning_digest,
    summarize_template_library,
    template_library_record_id,
)


def _write_audit(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(rec, ensure_ascii=False) for rec in records), encoding="utf-8")


def test_template_library_summary_and_items(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    extract_a = tmp_path / "a.txt"
    extract_b = tmp_path / "b.txt"
    extract_a.write_text(
        """第一章 工程概况
房建项目概况。
第二章 质量管理
质量控制、验收标准、抽检频次齐全。
""",
        encoding="utf-8",
    )
    extract_b.write_text(
        """第一章 工程概况
市政道路项目概况。
第二章 施工部署
路基、路面、交通导改安排完整。
第三章 安全文明施工
文明施工措施齐全。
""",
        encoding="utf-8",
    )
    profiles_a = build_template_chapter_profiles(extract_a.read_text(encoding="utf-8"))
    profiles_b = build_template_chapter_profiles(extract_b.read_text(encoding="utf-8"))
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T10:00:00Z",
                "filename": "房建案例A.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "library_note": "结构清晰",
                "extract_saved_as": str(extract_a),
                "template_chapter_profiles": profiles_a,
                "template_chapter_profile_count": len(profiles_a),
                "preview_saved_as": None,
                "sha256": "a" * 64,
                "pages": 18,
                "bytes": 1234,
                "template_scene_tags": ["医院", "局部改造"],
                "template_feedback_score": 95,
                "template_feedback_origin": "generated_accepted",
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T11:00:00Z",
                "filename": "道路案例B.docx",
                "project_type": "市政道路",
                "library_scope": "template_library",
                "template_page_bucket": "gt_200_pages",
                "library_note": "路基路面完整",
                "extract_saved_as": str(extract_b),
                "template_chapter_profiles": profiles_b,
                "template_chapter_profile_count": len(profiles_b),
                "preview_saved_as": None,
                "sha256": "b" * 64,
                "pages": 22,
                "bytes": 2234,
                "template_scene_tags": ["道路翻修"],
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T12:00:00Z",
                "filename": "普通招标文件.pdf",
                "project_type": "房建",
                "extract_saved_as": str(extract_a),
                "sha256": "c" * 64,
                "tags": ["tender", "qa"],
            },
        ],
    )

    summary = summarize_template_library(project_types=["房建", "市政道路", "装修"], audit_path=audit_path)
    assert summary["total_count"] == 2
    assert summary["by_project_type"]["房建"] == 1
    assert summary["by_project_type"]["市政道路"] == 1
    assert summary["by_project_type"]["装修"] == 0
    assert summary["by_template_page_bucket"]["50_pages"] == 1
    assert summary["by_template_page_bucket"]["gt_200_pages"] == 1
    assert summary["by_project_type_bucket"]["房建"]["50_pages"] == 1
    assert summary["total_profile_count"] == len(profiles_a) + len(profiles_b)
    assert summary["high_priority_count"] == 1
    assert summary["accepted_feedback_count"] == 1
    assert summary["system_feedback_count"] == 1
    assert summary["by_project_type_profile_count"]["房建"] == len(profiles_a)
    assert summary["by_project_type_bucket_profile_count"]["房建"]["50_pages"] == len(profiles_a)
    assert summary["latest_item"]["filename"] == "道路案例B.docx"
    assert summary["latest_item"]["template_chapter_profile_count"] == len(profiles_b)

    items = list_template_library_items(project_type="房建", template_page_bucket="50_pages", limit=5, audit_path=audit_path)
    assert len(items) == 1
    assert items[0]["filename"] == "房建案例A.docx"
    assert items[0]["library_note"] == "结构清晰"
    assert items[0]["template_page_bucket"] == "50_pages"
    assert items[0]["template_chapter_profile_count"] == len(profiles_a)
    assert items[0]["learning_priority_label"] == "高优先"
    assert items[0]["record_id"]
    assert items[0]["template_scene_tags"] == ["医院", "局部改造"]

    filtered_items = list_template_library_items(
        project_type="房建",
        template_page_bucket="50_pages",
        scene_tags=["医院"],
        limit=5,
        audit_path=audit_path,
    )
    assert len(filtered_items) == 1
    assert filtered_items[0]["filename"] == "房建案例A.docx"
    assert (
        list_template_library_items(
            project_type="房建",
            template_page_bucket="50_pages",
            scene_tags=["学校"],
            limit=5,
            audit_path=audit_path,
        )
        == []
    )


def test_search_template_library_docs_filters_by_project_type(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    extract_a = tmp_path / "a.txt"
    extract_b = tmp_path / "b.txt"
    extract_a.write_text("文明施工 风险 控制 验证 闭环 房建优秀案例", encoding="utf-8")
    extract_b.write_text("文明施工 路基压实 交通导改 市政道路优秀案例", encoding="utf-8")
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T10:00:00Z",
                "filename": "房建案例A.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "extract_saved_as": str(extract_a),
                "sha256": "d" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T10:30:00Z",
                "filename": "道路案例B.docx",
                "project_type": "市政道路",
                "library_scope": "template_library",
                "template_page_bucket": "gt_200_pages",
                "extract_saved_as": str(extract_b),
                "sha256": "e" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
        ],
    )

    hits = search_template_library_docs(
        "文明施工 闭环",
        project_type="房建",
        template_page_bucket="50_pages",
        limit=3,
        audit_path=audit_path,
    )
    assert len(hits) == 1
    assert hits[0]["filename"] == "房建案例A.docx"


def test_template_library_items_can_sort_by_learning_priority(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    high_profiles = build_template_chapter_profiles(
        """第一章 施工部署
组织机构、资源配置、施工顺序、质量验收、应急措施齐全。
第二章 安全文明施工
责任分工、检查频次、应急处置完整。
"""
    )
    low_profiles = build_template_chapter_profiles(
        """第一章 施工部署
施工顺序如下。
"""
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T10:00:00Z",
                "filename": "高优先样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_chapter_profiles": high_profiles,
                "template_chapter_profile_count": len(high_profiles),
                "template_feedback_score": 95,
                "template_feedback_origin": "generated_accepted",
                "sha256": "hp" * 32,
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T12:00:00Z",
                "filename": "最新普通样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_chapter_profiles": low_profiles,
                "template_chapter_profile_count": len(low_profiles),
                "sha256": "lp" * 32,
                "tags": ["template_library", "benchmark_case"],
            },
        ],
    )

    recent_items = list_template_library_items(
        project_type="房建",
        template_page_bucket="50_pages",
        sort_by="recent",
        limit=5,
        audit_path=audit_path,
    )
    assert recent_items[0]["filename"] == "最新普通样板.docx"

    priority_items = list_template_library_items(
        project_type="房建",
        template_page_bucket="50_pages",
        sort_by="priority",
        limit=5,
        audit_path=audit_path,
    )
    assert priority_items[0]["filename"] == "高优先样板.docx"
    assert priority_items[0]["learning_priority_label"] == "高优先"


def test_template_chapter_learning_context_prefers_same_chapter_theme(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    extract_a = tmp_path / "部署样板.txt"
    extract_b = tmp_path / "安全样板.txt"
    extract_a.write_text(
        """第一章 编制说明
编制依据如下。
第二章 施工部署
（一）组织机构设置
项目经理部岗位职责明确，责任分工清晰。
（二）资源配置计划
劳动力、机械设备、材料计划按阶段配置。
（三）施工顺序与工序衔接
按照先地下后地上、先主体后装修组织流水施工。
第三章 质量管理
质量验收与检验标准如下。
""",
        encoding="utf-8",
    )
    extract_b.write_text(
        """第一章 安全文明施工
安全生产责任制、文明施工措施、应急预案。
第二章 环境保护
扬尘噪声控制措施如下。
""",
        encoding="utf-8",
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T10:00:00Z",
                "filename": "房建部署样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "extract_saved_as": str(extract_a),
                "sha256": "j" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T10:30:00Z",
                "filename": "房建安全样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "extract_saved_as": str(extract_b),
                "sha256": "k" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
        ],
    )

    assert match_template_chapter_theme("施工部署") == "施工部署"
    ctx = build_template_chapter_learning_context(
        "房建 施工部署 施工组织设计 样板 案例",
        chapter_title="施工部署",
        project_type="房建",
        template_page_bucket="50_pages",
        limit=3,
        audit_path=audit_path,
    )
    assert ctx["theme"] == "施工部署"
    assert ctx["hits"]
    assert ctx["hits"][0]["filename"] == "房建部署样板.docx"
    assert ctx["hits"][0]["section_title"] == "施工部署"
    assert any("样板学习画像" in str(x) for x in ctx["requirement_lines"])
    assert any("样板高频锚点" in str(x) for x in ctx["requirement_lines"])
    assert any("组织分工与岗位责任" in str(x) for x in ctx["requirement_lines"])


def test_build_template_chapter_profiles_returns_storable_profiles() -> None:
    text = """第一章 编制说明
编制依据与适用范围如下。
第二章 施工部署
组织机构、资源配置、施工顺序与流水安排如下。
第三章 质量管理
质量目标、验收标准与抽检频次如下。
"""
    profiles = build_template_chapter_profiles(text)
    assert len(profiles) >= 3
    assert profiles[1]["section_title"] == "施工部署"
    assert profiles[1]["theme"] == "施工部署"
    assert any("组织分工与岗位责任" in str(x) for x in profiles[1]["anchor_headings"])


def test_template_learning_context_can_use_stored_profiles_without_extract(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    profiles = build_template_chapter_profiles(
        """第一章 施工部署
组织机构、劳动力、机械设备、施工顺序与流水安排如下。
第二章 安全文明施工
安全责任制与文明施工措施如下。
"""
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T10:00:00Z",
                "filename": "房建部署样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_chapter_profiles": profiles,
                "template_chapter_profile_count": len(profiles),
                "sha256": "m" * 64,
                "tags": ["template_library", "benchmark_case"],
            }
        ],
    )

    ctx = build_template_chapter_learning_context(
        "房建 施工部署 施工组织设计 样板 案例",
        chapter_title="施工部署",
        project_type="房建",
        template_page_bucket="50_pages",
        limit=2,
        audit_path=audit_path,
    )
    assert ctx["hits"]
    assert ctx["hits"][0]["section_title"] == "施工部署"
    assert any("样板学习画像" in str(x) for x in ctx["requirement_lines"])
    assert any("样板主题覆盖" in str(x) for x in ctx["requirement_lines"])


def test_search_template_library_docs_returns_section_level_hits(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    extract_a = tmp_path / "质量样板.txt"
    extract_a.write_text(
        """第一章 工程概况
项目概况内容。
第二章 质量管理
质量目标、验收标准、抽检频次、记录表单齐全。
第三章 安全文明施工
安全措施内容。
""",
        encoding="utf-8",
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T10:00:00Z",
                "filename": "房建质量样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "extract_saved_as": str(extract_a),
                "sha256": "l" * 64,
                "tags": ["template_library", "benchmark_case"],
            }
        ],
    )

    hits = search_template_library_docs(
        "房建 质量管理 施工组织设计 样板 案例",
        project_type="房建",
        template_page_bucket="50_pages",
        chapter_title="质量管理",
        limit=2,
        audit_path=audit_path,
    )
    assert hits
    assert hits[0]["filename"] == "房建质量样板.docx"
    assert hits[0]["section_title"] == "质量管理"
    assert hits[0]["match_mode"] == "chapter_theme"


def test_template_learning_digest_returns_theme_and_anchor_coverage(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    profiles_a = build_template_chapter_profiles(
        """第一章 施工部署
组织机构、资源配置、施工顺序与工序衔接明确。
第二章 质量管理
验收标准、检测频次与记录表单齐全。
"""
    )
    profiles_b = build_template_chapter_profiles(
        """第一章 施工部署
项目经理部职责、劳动力配置、机械设备计划完整。
第二章 安全文明施工
安全责任制与文明施工措施齐全。
"""
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T16:00:00Z",
                "filename": "房建样板A.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_chapter_profiles": profiles_a,
                "template_chapter_profile_count": len(profiles_a),
                "sha256": "p" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T16:10:00Z",
                "filename": "房建样板B.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_chapter_profiles": profiles_b,
                "template_chapter_profile_count": len(profiles_b),
                "sha256": "q" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
        ],
    )

    digest = summarize_template_learning_digest(
        project_type="房建",
        template_page_bucket="50_pages",
        audit_path=audit_path,
    )
    assert digest["matched_template_count"] == 2
    assert digest["matched_profile_count"] == len(profiles_a) + len(profiles_b)
    assert digest["theme_coverage"][0]["theme"] == "施工部署"
    assert digest["theme_coverage"][0]["count"] == 2
    assert any(str(item.get("anchor") or "").strip() == "组织分工与岗位责任" for item in digest["anchor_coverage"])
    assert any(str(item.get("scene_tag") or "").strip() == "医院" for item in digest["scene_coverage"]) is False
    assert "施工部署" in str(digest["coverage_hint"])


def test_infer_template_scene_tags_and_scene_matching(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    assert "医院" in infer_template_scene_tags("合肥骨科医院局部改造工程", project_type="维修改造")
    nursing_home_tags = infer_template_scene_tags(
        "肥西县公办养老机构改造提升项目—肥西县失能特困人员集中照护区项目，新增无障碍电梯及护理呼叫系统",
        project_type="维修改造",
    )
    assert "养老机构" in nursing_home_tags
    assert "失能照护" in nursing_home_tags
    assert "电梯增设" in nursing_home_tags or "适老化" in nursing_home_tags
    hospital_profiles = build_template_chapter_profiles(
        """第一章 施工部署
医院改造期间，门诊不停诊，需分区施工、降噪封闭与夜间倒排。
"""
    )
    school_profiles = build_template_chapter_profiles(
        """第一章 施工部署
校园改造期间，需避开上课时段并控制学生通行安全。
"""
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T16:20:00Z",
                "filename": "医院改造样板.docx",
                "project_type": "维修改造",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_scene_tags": ["医院", "局部改造"],
                "template_chapter_profiles": hospital_profiles,
                "template_chapter_profile_count": len(hospital_profiles),
                "sha256": "r" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T16:21:00Z",
                "filename": "学校改造样板.docx",
                "project_type": "维修改造",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_scene_tags": ["学校", "局部改造"],
                "template_chapter_profiles": school_profiles,
                "template_chapter_profile_count": len(school_profiles),
                "sha256": "s" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
        ],
    )

    hits = search_template_library_docs(
        "维修改造 合肥骨科医院局部改造工程 施工部署 样板",
        project_type="维修改造",
        template_page_bucket="50_pages",
        chapter_title="施工部署",
        scene_tags=["医院", "局部改造"],
        limit=2,
        audit_path=audit_path,
    )
    assert hits
    assert hits[0]["filename"] == "医院改造样板.docx"
    assert "医院" in (hits[0].get("template_scene_tags") or [])
    assert float(hits[0].get("scene_match_score") or 0) > 0


def test_template_search_prefers_same_project_manual_benchmark(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    senior_profiles = build_template_chapter_profiles(
        """第一章 工程概况
肥西县公办养老机构改造提升项目—肥西县失能特困人员集中照护区项目，包含适老化改造、外挂无障碍电梯、护理呼叫与智能化系统。
第二章 主要施工方法
围绕既有建筑加固、高延性混凝土、植筋、电梯井道和护理区装修组织施工。
"""
    )
    generic_profiles = build_template_chapter_profiles(
        """第一章 工程概况
某养老机构维修改造项目，主要包含室内翻新、设备更新和一般装修施工。
第二章 主要施工方法
按常规拆改、安装和装修顺序推进。
"""
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-15T09:00:00Z",
                "filename": "肥西县公办养老机构改造提升项目.pdf",
                "project_type": "维修改造",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "library_note": "人工高优先参照版本，目录完整，项目针对性强，适老化、照护、电梯和护理呼叫表述成熟。",
                "template_scene_tags": ["养老机构", "失能照护", "适老化", "电梯增设", "护理呼叫"],
                "template_chapter_profiles": senior_profiles,
                "template_chapter_profile_count": len(senior_profiles),
                "template_feedback_score": 98,
                "template_feedback_origin": "manual_benchmark",
                "sha256": "1" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-15T09:10:00Z",
                "filename": "普通养老院维修改造样板.pdf",
                "project_type": "维修改造",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "library_note": "一般参考。",
                "template_scene_tags": ["养老机构", "局部改造"],
                "template_chapter_profiles": generic_profiles,
                "template_chapter_profile_count": len(generic_profiles),
                "sha256": "2" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
        ],
    )

    hits = search_template_library_docs(
        "维修改造 肥西县公办养老机构改造提升项目 2026AEEGZ50006 失能特困人员集中照护区项目 工程概况 施工组织设计 样板 案例",
        project_type="维修改造",
        template_page_bucket="50_pages",
        chapter_title="工程概况",
        scene_tags=["养老机构", "失能照护", "适老化"],
        limit=2,
        audit_path=audit_path,
    )
    assert hits
    assert hits[0]["filename"] == "肥西县公办养老机构改造提升项目.pdf"
    assert float(hits[0].get("project_reference_score") or 0) > 0


def test_template_profile_builder_skips_toc_and_recognizes_numeric_level1() -> None:
    profiles = build_template_chapter_profiles(
        """施工组织设计
目录
1 工程概况 ............................................... 3
2 主要施工方法 ........................................... 8

1 工程概况
项目名称：肥西县公办养老机构改造提升项目。

2 主要施工方法
按既有建筑加固、适老化装修、电梯增设和护理呼叫系统穿插施工。
"""
    )
    titles = [str(item.get("section_title") or "").strip() for item in profiles]
    assert "工程概况" in titles
    assert "主要施工方法" in titles
    assert all("..." not in title for title in titles)


def test_template_learning_priority_prefers_higher_quality_template(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    high_profiles = build_template_chapter_profiles(
        """第一章 施工部署
组织机构、资源配置、施工顺序、进度节点、验收标准与应急措施完整。
第二章 质量管理
质量控制与抽检频次明确。
"""
    )
    low_profiles = build_template_chapter_profiles(
        """第一章 施工部署
施工顺序如下，包含基础组织安排、资源投入和流水段划分。
"""
    )
    _write_audit(
        audit_path,
        [
            {
                "ts": "2026-03-12T15:00:00Z",
                "filename": "普通施工部署样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_chapter_profiles": low_profiles,
                "template_chapter_profile_count": len(low_profiles),
                "library_note": "一般参考",
                "sha256": "n" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
            {
                "ts": "2026-03-12T15:10:00Z",
                "filename": "高分施工部署样板.docx",
                "project_type": "房建",
                "library_scope": "template_library",
                "template_page_bucket": "50_pages",
                "template_chapter_profiles": high_profiles,
                "template_chapter_profile_count": len(high_profiles),
                "library_note": "评分高，目录完整，表达干净，可复用。",
                "template_feedback_score": 95,
                "template_feedback_origin": "generated_accepted",
                "sha256": "o" * 64,
                "tags": ["template_library", "benchmark_case"],
            },
        ],
    )

    hits = search_template_library_docs(
        "房建 施工部署 施工组织设计 样板 案例",
        project_type="房建",
        template_page_bucket="50_pages",
        chapter_title="施工部署",
        limit=2,
        audit_path=audit_path,
    )
    assert hits
    assert hits[0]["filename"] == "高分施工部署样板.docx"
    assert hits[0]["learning_priority_label"] == "高优先"
    assert float(hits[0]["learning_priority_score"] or 0) > float(hits[1]["learning_priority_score"] or 0)


def test_delete_template_library_item_removes_record_and_unreferenced_files(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    saved_path = tmp_path / "房建案例A.docx"
    extract_path = tmp_path / "房建案例A.txt"
    preview_path = tmp_path / "房建案例A.png"
    shared_preview_path = tmp_path / "shared.png"
    saved_path.write_text("binary-placeholder", encoding="utf-8")
    extract_path.write_text("房建优秀施组样板正文", encoding="utf-8")
    preview_path.write_text("preview", encoding="utf-8")
    shared_preview_path.write_text("shared-preview", encoding="utf-8")
    target = {
        "ts": "2026-03-12T13:00:00Z",
        "filename": "房建案例A.docx",
        "project_type": "房建",
        "library_scope": "template_library",
        "template_page_bucket": "50_pages",
        "library_note": "可删除样板",
        "saved_as": str(saved_path),
        "extract_saved_as": str(extract_path),
        "preview_saved_as": str(preview_path),
        "sha256": "f" * 64,
        "tags": ["template_library", "benchmark_case"],
    }
    other = {
        "ts": "2026-03-12T13:10:00Z",
        "filename": "普通招标文件.pdf",
        "preview_saved_as": str(shared_preview_path),
        "sha256": "g" * 64,
        "tags": ["tender", "qa"],
    }
    _write_audit(audit_path, [target, other])

    deleted = delete_template_library_item(template_library_record_id(target), audit_path=audit_path)
    assert deleted["filename"] == "房建案例A.docx"
    assert deleted["template_page_bucket"] == "50_pages"
    assert str(saved_path) in deleted["removed_paths"]
    assert str(extract_path) in deleted["removed_paths"]
    assert str(preview_path) in deleted["removed_paths"]
    assert not saved_path.exists()
    assert not extract_path.exists()
    assert not preview_path.exists()
    assert shared_preview_path.exists()
    assert list_template_library_items(project_type="房建", template_page_bucket="50_pages", audit_path=audit_path) == []
    assert "房建案例A.docx" not in audit_path.read_text(encoding="utf-8")
    assert "普通招标文件.pdf" in audit_path.read_text(encoding="utf-8")


def test_delete_template_library_item_keeps_shared_files(tmp_path: Path) -> None:
    audit_path = tmp_path / "ingest.jsonl"
    shared_extract = tmp_path / "shared.txt"
    shared_extract.write_text("共享提取文本", encoding="utf-8")
    target = {
        "ts": "2026-03-12T14:00:00Z",
        "filename": "房建案例A.docx",
        "project_type": "房建",
        "library_scope": "template_library",
        "template_page_bucket": "50_pages",
        "extract_saved_as": str(shared_extract),
        "sha256": "h" * 64,
        "tags": ["template_library", "benchmark_case"],
    }
    sibling = {
        "ts": "2026-03-12T14:10:00Z",
        "filename": "另一个记录.docx",
        "project_type": "房建",
        "library_scope": "template_library",
        "template_page_bucket": "50_pages",
        "extract_saved_as": str(shared_extract),
        "sha256": "i" * 64,
        "tags": ["template_library", "benchmark_case"],
    }
    _write_audit(audit_path, [target, sibling])

    deleted = delete_template_library_item(template_library_record_id(target), audit_path=audit_path)
    assert deleted["filename"] == "房建案例A.docx"
    assert str(shared_extract) in deleted["kept_paths"]
    assert shared_extract.exists()
    items = list_template_library_items(project_type="房建", template_page_bucket="50_pages", audit_path=audit_path)
    assert len(items) == 1
    assert items[0]["filename"] == "另一个记录.docx"
