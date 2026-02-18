from __future__ import annotations

from backend.zhifei_autoplan.focus_card_parser import extract_focus_cards


def test_extract_focus_cards_parses_fields():
    sections = [
        {
            "title": "主要施工方法",
            "content": (
                "本章略。\n\n"
                "【清单重点项控制卡】\n"
                "- 清单项：钢筋；工程量=120t；单价=5200元/t；合价=624000元\n"
                "  量化指标：频次=1次/日；阈值=偏差≤5mm；间距=200mm；厚度=50mm；时长=4h/段；人数=8人/班；设备型号=20t挖机1台。\n"
                "  图纸定位：dwg.pdf#p1_12345678@90；校核点=构件位置/尺寸/标高/做法。【证据:dwg.pdf#p1_12345678@90】\n"
                "  标准引用：std.pdf#p2_abcdef12@34；条款对照入台账。【证据:std.pdf#p2_abcdef12@34】\n"
                "  风险→控制→验证：风险：误差累积导致返工；控制：放样复核=2次/日；验证：偏差≤5mm，记录=《复核记录》。【证据:boq.xlsx#p1_11111111@10】\n"
            ),
        }
    ]
    cards = extract_focus_cards(sections)
    assert len(cards) == 1
    c = cards[0]
    assert c["chapter"] == "主要施工方法"
    assert c["name"] == "钢筋"
    assert c["quant"]["频次"].startswith("1次/日")
    assert "5mm" in c["quant"]["阈值"]
    assert c["drawing_locator"].startswith("dwg.pdf#p1_")
    assert c["standard_locator"].startswith("std.pdf#p2_")
    assert "误差累积" in c["risk"]
    assert "放样复核" in c["control"]
    assert "偏差" in c["verify"]
    assert "dwg.pdf#p1_12345678@90" in c["evidence_sources"]
    assert "std.pdf#p2_abcdef12@34" in c["evidence_sources"]
    assert "boq.xlsx#p1_11111111@10" in c["evidence_sources"]

