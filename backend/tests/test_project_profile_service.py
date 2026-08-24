from __future__ import annotations

import hashlib
import json

import pytest

from backend import project_profile_service


@pytest.fixture
def profile_rule_file(tmp_path):
    rules = {
        "profile_rule_version": "V1.1-test",
        "project_type_inference": {
            "rules": [
                {
                    "if_keywords": ["幕墙", "玻璃幕墙"],
                    "then_project_type": "幕墙工程",
                    "base_confidence": 0.95,
                }
            ],
            "fallback": {"project_type": "综合工程", "base_confidence": 0.60},
        },
        "mandatory_dimension_inference": {
            "base_rules": [
                {
                    "if_project_type": "幕墙工程",
                    "mandatory_dimensions": ["结构稳定与安全", "施工安全风险识别与控制"],
                }
            ]
        },
        "confidence_thresholds": {"auto_accept": 0.85, "require_manual_confirm": 0.70},
        "technology_tolerance_inference": {"default": "medium"},
        "logic_chain_policy": {"default_min_logic_chains": 3},
    }
    path = tmp_path / "project-profile-rules.json"
    path.write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def bind_profile_rules(monkeypatch, profile_rule_file):
    monkeypatch.setattr(project_profile_service.kg_loader, "load_kg_config", lambda: {})
    monkeypatch.setattr(
        project_profile_service.kg_loader,
        "get_project_profile_rule_path",
        lambda _cfg=None: profile_rule_file,
    )


def test_explicit_project_type_is_accepted(profile_rule_file):
    profile = project_profile_service.generate_project_profile({"project_type": "幕墙工程"})

    assert profile["project_type"] == {
        "value": "幕墙工程",
        "confidence": 1.0,
        "source": "explicit:project_type",
        "evidence": ["payload.project_type"],
    }
    assert profile["decision"] == "auto_accept"
    assert profile["mandatory_dimensions"] == ["结构稳定与安全", "施工安全风险识别与控制"]
    assert profile["rule_sha256"] == hashlib.sha256(profile_rule_file.read_bytes()).hexdigest()


def test_configured_keyword_rule_requires_confirmation():
    profile = project_profile_service.generate_project_profile(
        {"project_name": "玻璃幕墙施工与幕墙安全专项工程"}
    )

    assert profile["project_type"]["value"] == "幕墙工程"
    assert profile["project_type"]["source"] == "rule_keyword"
    assert profile["project_type"]["evidence"] == ["幕墙", "玻璃幕墙"]
    assert profile["project_type"]["confidence"] == 0.83
    assert profile["decision"] == "require_manual_confirm"


def test_built_in_rule_supplements_unconfigured_project_types():
    profile = project_profile_service.generate_project_profile(
        {"description": "市政道路沥青路面改造工程"}
    )

    assert profile["project_type"]["value"] == "市政道路"
    assert profile["project_type"]["source"] == "keyword"
    assert profile["decision"] == "require_manual_confirm"


def test_rule_fallback_stays_fail_closed():
    profile = project_profile_service.generate_project_profile(
        {"description": "未包含已知分类词的专业工程"}
    )

    assert profile["project_type"] == {
        "value": "综合工程",
        "confidence": 0.6,
        "source": "rule_fallback",
        "evidence": [],
    }
    assert profile["decision"] == "block_and_review"


def test_empty_input_stays_unclassified_and_blocked():
    profile = project_profile_service.generate_project_profile({})

    assert profile["project_type"] == {
        "value": None,
        "confidence": 0.0,
        "source": "none",
        "evidence": [],
    }
    assert profile["decision"] == "block_and_review"
