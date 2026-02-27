from __future__ import annotations

from backend.zhifei_autoplan.logic_templates import normalize_template_id, pick_logic_template


def test_pick_logic_template_by_variant_id_cycles_abcde():
    assert pick_logic_template(variant_id=1, explicit_template_id=None).template_id == "A"
    assert pick_logic_template(variant_id=2, explicit_template_id=None).template_id == "B"
    assert pick_logic_template(variant_id=3, explicit_template_id=None).template_id == "C"
    assert pick_logic_template(variant_id=4, explicit_template_id=None).template_id == "D"
    assert pick_logic_template(variant_id=5, explicit_template_id=None).template_id == "E"
    assert pick_logic_template(variant_id=6, explicit_template_id=None).template_id == "A"


def test_pick_logic_template_explicit_overrides_variant_id():
    t = pick_logic_template(variant_id=1, explicit_template_id="E")
    assert t.template_id == "E"
    assert t.prompt_rules


def test_normalize_template_id_supports_s_alias():
    assert normalize_template_id("S") == "C"
