from __future__ import annotations

from backend.zhifei_autoplan.evidence import best_tender_source_span_hit, search_tender_source_spans


def test_best_tender_source_span_hit_builds_traceable_locator(tmp_path) -> None:
    tender_file = tmp_path / "招标文件.pdf"
    tender_file.write_bytes(b"traceable tender bytes")
    tender = {
        "items": [
            {
                "dimension": "质量目标",
                "keywords": ["质量", "验收"],
                "weight": 1.0,
                "source_spans": [
                    {
                        "file_name": str(tender_file),
                        "page": 0,
                        "start": 2409,
                        "end": 2411,
                        "snippet": "计划工期、质量标准。",
                    }
                ],
            }
        ]
    }

    hit = best_tender_source_span_hit(tender, "质量标准 招标")

    assert hit is not None
    assert hit["filename"] == "招标文件.pdf"
    assert hit["locator"].startswith("招标文件.pdf#p1_")
    assert hit["locator"].endswith("@2409")


def test_search_tender_source_spans_keeps_fallback_hit_without_query_match(tmp_path) -> None:
    tender_file = tmp_path / "招标文件.pdf"
    tender_file.write_bytes(b"fallback tender bytes")
    tender = {
        "items": [
            {
                "dimension": "安全等级",
                "keywords": ["安全", "文明施工"],
                "weight": 1.0,
                "source_spans": [
                    {
                        "file_name": str(tender_file),
                        "page": 0,
                        "start": 88,
                        "end": 92,
                        "snippet": "安全文明施工与环境保护。",
                    }
                ],
            }
        ]
    }

    hits = search_tender_source_spans(tender, "完全无关的章节标题", limit=1)

    assert len(hits) == 1
    assert hits[0]["locator"].startswith("招标文件.pdf#p1_")
