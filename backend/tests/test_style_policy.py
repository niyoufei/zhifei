from __future__ import annotations

from backend.zhifei_autoplan.style_policy import resolve_line_spacing, resolve_style, resolve_style_with_decisions


def test_style_policy_defaults_to_22pt_when_tender_has_no_spacing_requirement():
    resolved, source = resolve_style(user_style={}, tender_style={})

    assert source == "default_or_user"
    assert resolved["line_spacing_pt"] == 22.0
    assert "line_spacing" not in resolved


def test_style_policy_tender_multiple_spacing_replaces_default_fixed_spacing():
    resolved, source = resolve_style(
        user_style={"line_spacing_pt": 22.0},
        tender_style={"line_spacing": 1.5},
    )

    assert source == "tender_override"
    assert resolved["line_spacing"] == 1.5
    assert "line_spacing_pt" not in resolved

    multiple, fixed_pt = resolve_line_spacing(resolved)
    assert multiple == 1.5
    assert fixed_pt is None


def test_style_policy_tender_fixed_spacing_replaces_user_multiple_spacing():
    resolved, source = resolve_style(
        user_style={"line_spacing": 2.0},
        tender_style={"line_spacing_pt": 24.0},
    )

    assert source == "tender_override"
    assert resolved["line_spacing_pt"] == 24.0
    assert "line_spacing" not in resolved


def test_exporter_defaults_to_22pt_only_when_spacing_is_unspecified():
    default_multiple, default_fixed_pt = resolve_line_spacing({})
    explicit_multiple, explicit_fixed_pt = resolve_line_spacing({"line_spacing": 2.0})

    assert default_multiple == 1.5
    assert default_fixed_pt == 22.0
    assert explicit_multiple == 2.0
    assert explicit_fixed_pt is None


def test_behavioral_layout_flags_survive_style_resolution():
    resolved, source = resolve_style(
        user_style={
            "chapter_start_new_page": False,
            "enforce_chapter_pages": True,
        },
        tender_style={},
    )

    assert source == "default_or_user"
    assert resolved["chapter_start_new_page"] is False
    assert resolved["enforce_chapter_pages"] is True


def test_tender_behavioral_layout_flags_override_user_flags():
    resolved, source = resolve_style(
        user_style={"chapter_start_new_page": False},
        tender_style={"chapter_start_new_page": True},
    )

    assert source == "tender_override"
    assert resolved["chapter_start_new_page"] is True


def test_style_decision_matrix_records_default_user_and_tender_precedence():
    resolved, source, matrix = resolve_style_with_decisions(
        user_style={"line_spacing_pt": 22.0},
        tender_style={"line_spacing_pt": 24.0},
    )

    assert source == "tender_override"
    assert resolved["line_spacing_pt"] == 24.0
    decision = matrix["fields"]["line_spacing"]
    assert decision["status"] == "resolved_by_priority"
    assert decision["selected"]["source_type"] == "tender"
