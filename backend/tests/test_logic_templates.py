from __future__ import annotations

from backend.zhifei_autoplan.logic_templates import pick_logic_template


def test_pick_logic_template_by_variant_id_cycles_abc():
    assert pick_logic_template(variant_id=1, explicit_template_id=None).template_id == "A"
    assert pick_logic_template(variant_id=2, explicit_template_id=None).template_id == "B"
    assert pick_logic_template(variant_id=3, explicit_template_id=None).template_id == "C"
    assert pick_logic_template(variant_id=4, explicit_template_id=None).template_id == "A"


def test_pick_logic_template_explicit_overrides_variant_id():
    t = pick_logic_template(variant_id=1, explicit_template_id="C")
    assert t.template_id == "C"
    assert t.prompt_rules

