from backend.zhifei_autoplan import self_evolution


def test_record_runtime_learning_collects_runtime_budget_signals(tmp_path, monkeypatch):
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_PATH", tmp_path / "runtime_budget_profile.json")
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_LOCK", tmp_path / ".runtime_budget_profile.lock")

    results = [
        {
            "project_type": "房建",
            "generation_mode": "quality_200",
            "quality_checks": {
                "issue_list": [
                    {
                        "title": "工程概况",
                        "type": "quantitative_gap",
                        "indicator_group": "缺量化",
                        "strategy_id": "quant_fill_general_v1",
                    }
                ],
                "remediation_strategy_audit": {
                    "by_title": [
                        {
                            "title": "工程概况",
                            "strategy_ids": ["quant_fill_general_v1"],
                        }
                    ]
                },
                "remediation_execution_audit": {
                    "by_title": [
                        {
                            "title": "工程概况",
                            "action_tags": ["add_quant_value", "add_record_acceptance"],
                            "strategy_ids": ["quant_fill_general_v1"],
                        }
                    ]
                },
                "quantitative": {
                    "by_section": [
                        {"title": "工程概况", "ok": False, "missing": ["频次"]},
                    ]
                }
            },
            "quality_gate": {"ok": False, "failed": [{"metric": "quantitative_ok_rate"}]},
            "generation_trace": {
                "provider_chain": [
                    {
                        "slot": "text_main",
                        "provider": "openai",
                        "model": "gpt-5.4",
                        "key_alias": "OPENAI_API_KEY_TEXT_MAIN",
                    }
                ]
            },
            "sections": [
                {
                    "title": "工程概况",
                    "content": "正文内容",
                    "used_key_alias": "OPENAI_API_KEY_TEXT_BACKUP",
                    "requested_timeout_sec": 77,
                    "requested_max_output_tokens": 2600,
                    "requested_section_retry_limit": 1,
                    "runtime_budget_reason": "low_complexity_small_section",
                    "constraint_log": [
                        {"attempt": 1, "status": "compacted"},
                    ],
                    "remediation_execution_trace": [
                        {
                            "title": "工程概况",
                            "indicator_group": "缺量化",
                            "strategy_id": "quant_fill_general_v1",
                            "matched_action_tags": ["add_quant_value", "add_record_acceptance"],
                            "execution_status": "matched",
                        }
                    ],
                }
            ],
        }
    ]

    summary = self_evolution.record_runtime_learning({}, results, params={"self_evolution": {"enabled": True}})
    assert summary["enabled"] is True
    assert summary["updated_entries"] == 1

    profile = self_evolution.load_runtime_budget_profile()
    assert isinstance(profile.get("entries"), dict)
    entry = next(iter(profile["entries"].values()))
    assert entry["runs"] == 1
    assert entry["success_runs"] == 1
    assert entry["fallback_runs"] == 1
    assert entry["compaction_runs"] == 1
    assert entry["quality_issue_runs"] == 1
    assert entry["last_runtime_budget_reason"] == "low_complexity_small_section"
    assert entry["indicator_group_counts"]["缺量化"] == 1
    assert entry["strategy_counts"]["quant_fill_general_v1"] == 1
    assert entry["action_tag_counts"]["add_quant_value"] == 1
    combo_key = self_evolution._combo_key("缺量化", "quant_fill_general_v1", "add_quant_value")
    assert entry["combo_attempt_counts"][combo_key] == 1
    assert combo_key not in entry["combo_indicator_close_counts"]
    assert "缺证据||quant_fill_general_v1||add_quant_value" not in entry["combo_attempt_counts"]
    bundle_key = self_evolution._bundle_key(
        [
            self_evolution._combo_key("缺量化", "quant_fill_general_v1", "add_quant_value"),
            self_evolution._combo_key("缺量化", "quant_fill_general_v1", "add_record_acceptance"),
        ]
    )
    assert bundle_key not in entry["combo_bundle_attempt_counts"]
    assert "add_quant_value" in entry["last_action_tags"]
    assert entry["last_effective_combos"] == []
    assert entry["last_effective_combo_bundle"] == []


def test_build_runtime_budget_hints_promotes_retry_and_timeout_from_history():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 4,
                "success_runs": 2,
                "error_runs": 2,
                "fallback_runs": 2,
                "compaction_runs": 0,
                "quality_issue_runs": 2,
            }
        },
    }
    hints = self_evolution.build_runtime_budget_hints(
        params={"self_evolution": {"enabled": True}},
        title="工程概况",
        project_type="房建",
        generation_mode="quality_200",
        runtime_budget={
            "llm_timeout_sec": 70,
            "max_output_tokens_hint": 2600,
            "section_retry_limit": 1,
        },
        profile=profile,
    )
    assert hints["enabled"] is True
    assert hints["applied"] is True
    assert hints["llm_timeout_sec"] > 70
    assert hints["max_output_tokens_hint"] > 2600
    assert hints["section_retry_limit"] == 2
    assert hints["source_runs"] == 4


def test_build_runtime_budget_hints_trims_tokens_after_repeated_compaction():
    key = self_evolution._profile_key("编制依据与原则", "房建", "quality_200")
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "编制依据与原则",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 5,
                "success_runs": 5,
                "error_runs": 0,
                "fallback_runs": 0,
                "compaction_runs": 4,
                "quality_issue_runs": 0,
            }
        },
    }
    hints = self_evolution.build_runtime_budget_hints(
        params={"self_evolution": {"enabled": True}},
        title="编制依据与原则",
        project_type="房建",
        generation_mode="quality_200",
        runtime_budget={
            "llm_timeout_sec": 55,
            "max_output_tokens_hint": 1800,
            "section_retry_limit": 1,
        },
        profile=profile,
    )
    assert hints["enabled"] is True
    assert hints["applied"] is True
    assert hints["max_output_tokens_hint"] < 1800


def test_build_runtime_budget_hints_promotes_retry_for_quality_issue_rate():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 4,
                "success_runs": 4,
                "error_runs": 0,
                "fallback_runs": 0,
                "compaction_runs": 0,
                "quality_issue_runs": 3,
            }
        },
    }
    hints = self_evolution.build_runtime_budget_hints(
        params={"self_evolution": {"enabled": True, "quality_issue_rate_raise_retry": 0.5}},
        title="工程概况",
        project_type="房建",
        generation_mode="quality_200",
        runtime_budget={
            "llm_timeout_sec": 70,
            "max_output_tokens_hint": 2600,
            "section_retry_limit": 1,
        },
        profile=profile,
    )
    assert hints["enabled"] is True
    assert hints["applied"] is True
    assert hints["section_retry_limit"] == 2
    assert "raise_retry" in str(hints.get("reason") or "")


def test_summarize_runtime_budget_profile_returns_ranked_entries():
    key_a = self_evolution._profile_key("工程概况", "房建", "quality_200")
    key_b = self_evolution._profile_key("主要施工方法", "房建", "quality_200")
    profile = {
        "version": "runtime_budget_profile_v1",
        "updated_at": "2026-03-17T12:00:00",
        "entries": {
            key_a: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 5,
                "success_runs": 5,
                "error_runs": 0,
                "fallback_runs": 1,
                "compaction_runs": 2,
                "quality_issue_runs": 1,
                "timeout_total": 400,
                "max_tokens_total": 15000,
                "retry_total": 7,
                "last_runtime_budget_reason": "historical_quality_issue_rate=0.5_raise_tokens",
                "last_used_key_alias": "OPENAI_API_KEY_TEXT_MAIN",
                "indicator_group_counts": {"缺量化": 2, "缺证据": 1},
                "strategy_counts": {"quant_fill_general_v1": 2},
                "action_tag_counts": {"add_quant_value": 2, "add_record_acceptance": 1},
                "context_signature_counts": {"general|A": 3},
                "combo_attempt_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 3},
                "combo_indicator_close_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 2},
                "combo_gate_pass_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 1},
                "combo_bundle_attempt_counts": {
                    self_evolution._bundle_key(
                        [
                            "缺量化||quant_fill_general_v1||add_quant_value",
                            "缺量化||quant_fill_general_v1||add_record_acceptance",
                        ]
                    ): 3
                },
                "combo_bundle_gate_pass_counts": {
                    self_evolution._bundle_key(
                        [
                            "缺量化||quant_fill_general_v1||add_quant_value",
                            "缺量化||quant_fill_general_v1||add_record_acceptance",
                        ]
                    ): 2
                },
                "combo_context_bundle_attempt_counts": {
                    self_evolution._context_bundle_key(
                        self_evolution._context_signature("general", "A"),
                        [
                            "缺量化||quant_fill_general_v1||add_quant_value",
                            "缺量化||quant_fill_general_v1||add_record_acceptance",
                        ],
                    ): 3
                },
                "combo_context_bundle_gate_pass_counts": {
                    self_evolution._context_bundle_key(
                        self_evolution._context_signature("general", "A"),
                        [
                            "缺量化||quant_fill_general_v1||add_quant_value",
                            "缺量化||quant_fill_general_v1||add_record_acceptance",
                        ],
                    ): 2
                },
                "combo_context_bundle_learning_attempt_counts": {
                    self_evolution._context_bundle_key(
                        self_evolution._context_signature("general", "A"),
                        [
                            "缺量化||quant_fill_general_v1||add_quant_value",
                            "缺量化||quant_fill_general_v1||add_record_acceptance",
                        ],
                    ): 2
                },
                "combo_context_bundle_learning_gate_pass_counts": {
                    self_evolution._context_bundle_key(
                        self_evolution._context_signature("general", "A"),
                        [
                            "缺量化||quant_fill_general_v1||add_quant_value",
                            "缺量化||quant_fill_general_v1||add_record_acceptance",
                        ],
                    ): 2
                },
                "combo_context_metric_attempt_counts": {
                    self_evolution._context_metric_key(
                        self_evolution._context_bundle_key(
                            self_evolution._context_signature("general", "A"),
                            [
                                "缺量化||quant_fill_general_v1||add_quant_value",
                                "缺量化||quant_fill_general_v1||add_record_acceptance",
                            ],
                        ),
                        "quantitative_ok_rate",
                    ): 2
                },
                "combo_context_metric_resolved_counts": {
                    self_evolution._context_metric_key(
                        self_evolution._context_bundle_key(
                            self_evolution._context_signature("general", "A"),
                            [
                                "缺量化||quant_fill_general_v1||add_quant_value",
                                "缺量化||quant_fill_general_v1||add_record_acceptance",
                            ],
                        ),
                        "quantitative_ok_rate",
                    ): 2
                },
                "combo_context_metric_action_attempt_counts": {
                    self_evolution._context_metric_action_key(
                        self_evolution._context_bundle_key(
                            self_evolution._context_signature("general", "A"),
                            [
                                "缺量化||quant_fill_general_v1||add_quant_value",
                                "缺量化||quant_fill_general_v1||add_record_acceptance",
                            ],
                        ),
                        "quantitative_ok_rate",
                        "add_quant_value",
                    ): 2
                },
                "combo_context_metric_action_resolved_counts": {
                    self_evolution._context_metric_action_key(
                        self_evolution._context_bundle_key(
                            self_evolution._context_signature("general", "A"),
                            [
                                "缺量化||quant_fill_general_v1||add_quant_value",
                                "缺量化||quant_fill_general_v1||add_record_acceptance",
                            ],
                        ),
                        "quantitative_ok_rate",
                        "add_quant_value",
                    ): 2
                },
                "last_effective_combos": ["缺量化||quant_fill_general_v1||add_quant_value"],
                "last_effective_combo_bundle": [
                    "缺量化||quant_fill_general_v1||add_quant_value",
                    "缺量化||quant_fill_general_v1||add_record_acceptance",
                ],
                "last_attributed_context_bundles": [
                    "general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺量化/quant_fill_general_v1/add_record_acceptance attributed_pass=100% n=2"
                ],
                "last_metric_effects": [
                    "量化指标达标率 | general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺量化/quant_fill_general_v1/add_record_acceptance metric_resolve=100% n=2"
                ],
                "last_metric_action_effects": [
                    "quantitative_ok_rate/补量化数值"
                ],
                "last_context_signature": "general|A",
                "last_updated_at": "2026-03-17T12:00:00",
            },
            key_b: {
                "title": "主要施工方法",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 3,
                "success_runs": 2,
                "error_runs": 1,
                "fallback_runs": 2,
                "compaction_runs": 0,
                "quality_issue_runs": 2,
                "timeout_total": 315,
                "max_tokens_total": 12000,
                "retry_total": 5,
                "last_runtime_budget_reason": "historical_fallback_rate=0.67_raise_timeout",
                "last_used_key_alias": "OPENAI_API_KEY_TEXT_BACKUP",
                "indicator_group_counts": {"缺闭环": 2},
                "strategy_counts": {"risk_triplet_closure_v1": 2},
                "last_updated_at": "2026-03-17T12:30:00",
            },
        },
    }
    out = self_evolution.summarize_runtime_budget_profile(
        params={"self_evolution": {"enabled": True}},
        profile=profile,
        limit=1,
    )
    assert out["enabled"] is True
    assert out["entry_count"] == 2
    assert out["top_entries"][0]["top_indicator_groups"]
    assert out["top_entries"][0]["top_strategy_ids"]
    assert out["top_entries"][0]["top_action_tags"]
    assert out["top_entries"][0]["top_context_signatures"]
    assert out["top_entries"][0]["top_effective_combos"]
    assert out["top_entries"][0]["top_effective_combo_bundles"]
    assert out["top_entries"][0]["top_effective_context_bundles"]
    assert out["top_entries"][0]["top_attributed_context_bundles"]
    assert out["top_entries"][0]["top_metric_effects"]
    assert out["top_entries"][0]["top_metric_action_effects"]
    assert out["top_entries"][0]["last_metric_effects"]
    assert out["top_entries"][0]["last_metric_action_effects"]
    assert out["updated_at"] == "2026-03-17T12:00:00"
    assert len(out["top_entries"]) == 1
    assert out["top_entries"][0]["title"] == "工程概况"
    assert out["top_entries"][0]["avg_timeout_sec"] == 80.0
    assert out["top_entries"][0]["avg_retry_limit"] == 1.4


def test_prioritize_remediation_rows_with_learning_promotes_effective_combo():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 4,
                "combo_attempt_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 4,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 2,
                },
                "combo_indicator_close_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 3,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 1,
                },
                "combo_gate_pass_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 2,
                },
            }
        },
    }
    rows = [
        {
            "title": "工程概况",
            "indicator_group": "缺闭环",
            "strategy_id": "risk_triplet_closure_v1",
            "strategy_priority": 98,
            "expected_action_tags": ["add_risk_control_verify"],
            "type": "risk_triplet_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "quant_fill_general_v1",
            "strategy_priority": 95,
            "expected_action_tags": ["add_quant_value", "add_record_acceptance"],
            "type": "quantitative_gap",
        },
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={"self_evolution": {"enabled": True, "combo_learning_enabled": True}},
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    assert out["applied"] is True
    ranked = out["rows"]
    assert ranked[0]["strategy_id"] == "quant_fill_general_v1"
    assert ranked[0]["_combo_learning_applied"] is True
    assert ranked[0]["_combo_learning_source_runs"] == 4
    assert "historical_combo_close_rate" in ranked[0]["_combo_learning_reason"]


def test_prioritize_remediation_rows_with_learning_falls_back_to_strategy_action_match():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 3,
                "combo_attempt_counts": {
                    "缺证据||core_conclusion_evidence_fill_v1||add_evidence_locator": 3,
                },
                "combo_indicator_close_counts": {
                    "缺证据||core_conclusion_evidence_fill_v1||add_evidence_locator": 3,
                },
                "combo_gate_pass_counts": {
                    "缺证据||core_conclusion_evidence_fill_v1||add_evidence_locator": 2,
                },
            }
        },
    }
    rows = [
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "core_conclusion_evidence_fill_v1",
            "strategy_priority": 98,
            "expected_action_tags": ["add_evidence_locator"],
            "type": "quantitative_gap",
        }
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={"self_evolution": {"enabled": True, "combo_learning_enabled": True, "combo_learning_min_runs": 1}},
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    ranked = out["rows"]
    assert out["applied"] is True
    assert ranked[0]["_combo_learning_applied"] is True
    assert "match_scope=strategy_action_fallback" in ranked[0]["_combo_learning_reason"]
    assert ranked[0]["_combo_learning_best_combo"] == "缺证据||core_conclusion_evidence_fill_v1||add_evidence_locator"


def test_prioritize_remediation_rows_with_learning_promotes_effective_bundle():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    bundle_key = self_evolution._bundle_key(
        [
            "缺量化||quant_fill_general_v1||add_quant_value",
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
        ]
    )
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 3,
                "combo_attempt_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 3,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 3,
                },
                "combo_indicator_close_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 3,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 3,
                },
                "combo_gate_pass_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 2,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 2,
                },
                "combo_bundle_attempt_counts": {
                    bundle_key: 3,
                },
                "combo_bundle_gate_pass_counts": {
                    bundle_key: 2,
                },
            }
        },
    }
    rows = [
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "quant_fill_general_v1",
            "strategy_priority": 95,
            "expected_action_tags": ["add_quant_value"],
            "type": "quantitative_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "缺闭环",
            "strategy_id": "risk_triplet_closure_v1",
            "strategy_priority": 94,
            "expected_action_tags": ["add_risk_control_verify"],
            "type": "risk_triplet_gap",
        },
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={"self_evolution": {"enabled": True, "combo_bundle_learning_enabled": True, "combo_bundle_min_runs": 1}},
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    assert out["bundle_applied"] is True
    assert out["bundle_applied_count"] == 2
    assert out["bundle_source_runs"] == 3
    ranked = out["rows"]
    assert ranked[0]["_combo_bundle_learning_applied"] is True
    assert "historical_combo_bundle_pass_rate" in ranked[0]["_combo_bundle_learning_reason"]
    assert "缺量化/quant_fill_general_v1/add_quant_value" in ranked[0]["_combo_bundle_learning_best_bundle"]


def test_prioritize_remediation_rows_with_learning_bundle_uses_target_section_title_for_virtual_rows():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    bundle_key = self_evolution._bundle_key(
        [
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
            "缺量化||quant_fill_general_v1||add_quant_value",
        ]
    )
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 3,
                "combo_attempt_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 3,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 3,
                },
                "combo_indicator_close_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 3,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 3,
                },
                "combo_gate_pass_counts": {
                    "缺量化||quant_fill_general_v1||add_quant_value": 2,
                    "缺闭环||risk_triplet_closure_v1||add_risk_control_verify": 2,
                },
                "combo_bundle_attempt_counts": {
                    bundle_key: 3,
                },
                "combo_bundle_gate_pass_counts": {
                    bundle_key: 2,
                },
            }
        },
    }
    rows = [
        {
            "title": "清单重点项",
            "target_section_title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "quant_fill_general_v1",
            "strategy_priority": 95,
            "expected_action_tags": ["add_quant_value"],
            "type": "quantitative_gap",
        },
        {
            "title": "专项主题",
            "target_section_title": "工程概况",
            "indicator_group": "缺闭环",
            "strategy_id": "risk_triplet_closure_v1",
            "strategy_priority": 94,
            "expected_action_tags": ["add_risk_control_verify"],
            "type": "risk_triplet_gap",
        },
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={"self_evolution": {"enabled": True, "combo_bundle_learning_enabled": True, "combo_bundle_min_runs": 1}},
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    assert out["bundle_applied"] is True
    assert out["bundle_titles"] == ["工程概况"]
    ranked = out["rows"]
    assert ranked[0]["_combo_bundle_learning_applied"] is True
    assert ranked[1]["_combo_bundle_learning_applied"] is True


def test_prioritize_remediation_rows_with_learning_prefers_context_bundle_for_matching_context():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    bundle_key = self_evolution._bundle_key(
        [
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
            "缺量化||quant_fill_general_v1||add_quant_value",
        ]
    )
    context_bundle_key = self_evolution._context_bundle_key(
        self_evolution._context_signature("general", "A"),
        [
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
            "缺量化||quant_fill_general_v1||add_quant_value",
        ],
    )
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 3,
                "combo_bundle_attempt_counts": {
                    bundle_key: 3,
                },
                "combo_bundle_gate_pass_counts": {
                    bundle_key: 2,
                },
                "combo_context_bundle_attempt_counts": {
                    context_bundle_key: 3,
                },
                "combo_context_bundle_gate_pass_counts": {
                    context_bundle_key: 3,
                },
            }
        },
    }
    rows = [
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "quant_fill_general_v1",
            "strategy_priority": 95,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_quant_value"],
            "type": "quantitative_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "缺闭环",
            "strategy_id": "risk_triplet_closure_v1",
            "strategy_priority": 94,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_risk_control_verify"],
            "type": "risk_triplet_gap",
        },
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={"self_evolution": {"enabled": True, "combo_context_bundle_learning_enabled": True, "combo_context_bundle_min_runs": 1}},
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    assert out["context_bundle_applied"] is True
    assert out["context_bundle_contexts"] == ["general/A"]
    ranked = out["rows"]
    assert ranked[0]["_combo_context_bundle_learning_applied"] is True
    assert "historical_context_bundle_pass_rate" in ranked[0]["_combo_context_bundle_learning_reason"]
    assert "general/A" in ranked[0]["_combo_context_bundle_learning_best_bundle"]


def test_prioritize_remediation_rows_with_learning_allows_partial_context_bundle_match():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    context_bundle_key = self_evolution._context_bundle_key(
        self_evolution._context_signature("general", "A"),
        [
            "其他问题||special_topic_missing_patch_v1||add_record_acceptance",
            "其他问题||special_topic_missing_patch_v1||rewrite_action_param",
            "缺量化||boq_focus_closure_fill_v1||add_evidence_locator",
            "缺量化||boq_focus_closure_fill_v1||add_quant_value",
        ],
    )
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 2,
                "combo_context_bundle_attempt_counts": {
                    context_bundle_key: 2,
                },
                "combo_context_bundle_gate_pass_counts": {
                    context_bundle_key: 2,
                },
            }
        },
    }
    rows = [
        {
            "title": "清单重点项",
            "target_section_title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "boq_focus_closure_fill_v1",
            "strategy_priority": 92,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_quant_value", "add_evidence_locator"],
            "type": "boq_focus_item_closure_gap",
        }
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={
            "self_evolution": {
                "enabled": True,
                "combo_context_bundle_learning_enabled": True,
                "combo_context_bundle_min_runs": 1,
                "combo_context_bundle_min_pass_rate": 0.0,
                "combo_context_bundle_partial_match_enabled": True,
                "combo_context_bundle_partial_min_match_count": 2,
                "combo_context_bundle_partial_min_match_ratio": 0.5,
                "combo_context_bundle_partial_score_penalty": 0.08,
            }
        },
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    assert out["context_bundle_applied"] is True
    assert out["context_bundle_applied_count"] == 1
    assert out["context_bundle_contexts"] == ["general/A"]
    ranked = out["rows"]
    assert ranked[0]["_combo_context_bundle_learning_applied"] is True
    assert "match_scope=partial" in ranked[0]["_combo_context_bundle_learning_reason"]


def test_prioritize_remediation_rows_with_learning_prefers_context_bundle_with_attribution():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    context_a = self_evolution._context_bundle_key(
        self_evolution._context_signature("general", "A"),
        [
            "缺量化||quant_fill_general_v1||add_quant_value",
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
        ],
    )
    context_b = self_evolution._context_bundle_key(
        self_evolution._context_signature("general", "A"),
        [
            "缺量化||boq_focus_closure_fill_v1||add_quant_value",
            "其他问题||special_topic_missing_patch_v1||rewrite_action_param",
        ],
    )
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 4,
                "combo_context_bundle_attempt_counts": {
                    context_a: 3,
                    context_b: 3,
                },
                "combo_context_bundle_gate_pass_counts": {
                    context_a: 2,
                    context_b: 2,
                },
                "combo_context_bundle_learning_attempt_counts": {
                    context_a: 3,
                    context_b: 3,
                },
                "combo_context_bundle_learning_gate_pass_counts": {
                    context_a: 3,
                    context_b: 0,
                },
            }
        },
    }
    rows = [
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "quant_fill_general_v1",
            "strategy_priority": 95,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_quant_value"],
            "type": "quantitative_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "缺闭环",
            "strategy_id": "risk_triplet_closure_v1",
            "strategy_priority": 94,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_risk_control_verify"],
            "type": "risk_triplet_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "boq_focus_closure_fill_v1",
            "strategy_priority": 93,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_quant_value"],
            "type": "boq_focus_item_closure_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "其他问题",
            "strategy_id": "special_topic_missing_patch_v1",
            "strategy_priority": 92,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["rewrite_action_param"],
            "type": "special_topic_missing",
        },
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={
            "self_evolution": {
                "enabled": True,
                "combo_context_bundle_learning_enabled": True,
                "combo_context_bundle_min_runs": 1,
                "combo_context_bundle_min_pass_rate": 0.0,
                "combo_context_bundle_attribution_enabled": True,
                "combo_context_bundle_attribution_min_runs": 1,
                "combo_context_bundle_attribution_gate_pass_bonus": 0.2,
            }
        },
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    ranked = out["rows"]
    assert out["context_bundle_applied"] is True
    assert ranked[0]["strategy_id"] == "quant_fill_general_v1"
    assert ranked[0]["_combo_context_bundle_learning_attribution_applied"] is True
    assert "attributed_gate_pass_rate=1.00" in ranked[0]["_combo_context_bundle_learning_reason"]
    assert ranked[2]["_combo_context_bundle_learning_applied"] is False


def test_prioritize_remediation_rows_with_learning_uses_context_metric_effect_history():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    context_bundle_id = self_evolution._context_bundle_key(
        self_evolution._context_signature("general", "A"),
        [
            "缺量化||quant_fill_general_v1||add_quant_value",
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
        ],
    )
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 4,
                "combo_context_bundle_attempt_counts": {context_bundle_id: 4},
                "combo_context_bundle_gate_pass_counts": {context_bundle_id: 3},
                "combo_context_metric_attempt_counts": {
                    self_evolution._context_metric_key(context_bundle_id, "quantitative_ok_rate"): 3,
                },
                "combo_context_metric_resolved_counts": {
                    self_evolution._context_metric_key(context_bundle_id, "quantitative_ok_rate"): 3,
                },
            }
        },
    }
    rows = [
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "quant_fill_general_v1",
            "strategy_priority": 95,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_quant_value"],
            "expected_quality_gate_metrics": ["quantitative_ok_rate"],
            "type": "quantitative_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "缺闭环",
            "strategy_id": "risk_triplet_closure_v1",
            "strategy_priority": 95,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_risk_control_verify"],
            "expected_quality_gate_metrics": ["risk_triplet_ok_rate"],
            "type": "risk_triplet_gap",
        },
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={
            "self_evolution": {
                "enabled": True,
                "combo_context_bundle_learning_enabled": True,
                "combo_context_bundle_min_runs": 1,
                "combo_context_bundle_min_pass_rate": 0.0,
                "combo_context_metric_effect_enabled": True,
                "combo_context_metric_effect_min_runs": 1,
                "combo_context_metric_effect_resolve_bonus": 0.2,
            }
        },
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    ranked = out["rows"]
    assert ranked[0]["strategy_id"] == "quant_fill_general_v1"
    assert ranked[0]["_combo_context_metric_effect_applied"] is True
    assert ranked[0]["_combo_context_metric_effect_metrics"] == ["quantitative_ok_rate"]
    assert "quantitative_ok_rate_resolve_rate=1.00" in ranked[0]["_combo_context_metric_effect_reason"]


def test_prioritize_remediation_rows_with_learning_uses_context_metric_action_effect_history():
    key = self_evolution._profile_key("工程概况", "房建", "quality_200")
    context_bundle_id = self_evolution._context_bundle_key(
        self_evolution._context_signature("general", "A"),
        [
            "缺量化||quant_fill_general_v1||add_quant_value",
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
        ],
    )
    action_key = self_evolution._context_metric_action_key(context_bundle_id, "quantitative_ok_rate", "add_quant_value")
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            key: {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 4,
                "combo_context_bundle_attempt_counts": {context_bundle_id: 4},
                "combo_context_bundle_gate_pass_counts": {context_bundle_id: 3},
                "combo_context_metric_action_attempt_counts": {action_key: 3},
                "combo_context_metric_action_resolved_counts": {action_key: 3},
            }
        },
    }
    rows = [
        {
            "title": "工程概况",
            "indicator_group": "缺量化",
            "strategy_id": "quant_fill_general_v1",
            "strategy_priority": 95,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_quant_value"],
            "expected_quality_gate_metrics": ["quantitative_ok_rate"],
            "type": "quantitative_gap",
        },
        {
            "title": "工程概况",
            "indicator_group": "缺闭环",
            "strategy_id": "risk_triplet_closure_v1",
            "strategy_priority": 95,
            "chapter_domain": "general",
            "template_id": "A",
            "expected_action_tags": ["add_risk_control_verify"],
            "expected_quality_gate_metrics": ["risk_triplet_ok_rate"],
            "type": "risk_triplet_gap",
        },
    ]
    out = self_evolution.prioritize_remediation_rows_with_learning(
        params={
            "self_evolution": {
                "enabled": True,
                "combo_context_bundle_learning_enabled": True,
                "combo_context_bundle_min_runs": 1,
                "combo_context_bundle_min_pass_rate": 0.0,
                "combo_context_metric_action_effect_enabled": True,
                "combo_context_metric_action_effect_min_runs": 1,
                "combo_context_metric_action_effect_resolve_bonus": 0.15,
            }
        },
        project_type="房建",
        generation_mode="quality_200",
        rows=rows,
        profile=profile,
    )
    ranked = out["rows"]
    assert ranked[0]["strategy_id"] == "quant_fill_general_v1"
    assert ranked[0]["_combo_context_metric_action_effect_applied"] is True
    assert ranked[0]["_combo_context_metric_action_effect_triplets"] == ["quantitative_ok_rate/补量化数值"]
    assert "quantitative_ok_rate/add_quant_value_resolve_rate=1.00" in ranked[0]["_combo_context_metric_action_effect_reason"]


def test_record_runtime_learning_collects_context_bundle_attribution(tmp_path, monkeypatch):
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_PATH", tmp_path / "runtime_budget_profile.json")
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_LOCK", tmp_path / ".runtime_budget_profile.lock")
    context_bundle_id = self_evolution._context_bundle_key(
        self_evolution._context_signature("general", "A"),
        [
            "缺量化||quant_fill_general_v1||add_quant_value",
            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
        ],
    )
    result = {
        "project_type": "房建",
        "generation_mode": "quality_200",
        "quality_checks": {},
        "quality_gate": {"ok": True, "failed": []},
        "generation_trace": {
            "provider_chain": [
                {"slot": "text_main", "provider": "openai", "model": "gpt-5.4", "key_alias": "OPENAI_API_KEY_TEXT_MAIN"}
            ],
            "self_evolution": {
                "remediation_context_bundle_learning_details": [
                    {
                        "title": "工程概况",
                        "context_signature": "general|A",
                        "context_bundle_id": context_bundle_id,
                        "bundle": "general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify pass=100% n=1",
                        "bundle_combos": [
                            "缺量化||quant_fill_general_v1||add_quant_value",
                            "缺闭环||risk_triplet_closure_v1||add_risk_control_verify",
                        ],
                        "source_runs": 1,
                        "applied_count": 2,
                        "attribution_applied": True,
                        "attributed_gate_pass_rate": 1.0,
                        "attribution_runs": 1,
                        "attribution_reason": "historical_learning_applied_gate_pass_rate=1.00; attribution_runs=1",
                    }
                ],
                "remediation_context_bundle_learning_metric_details": [
                    {
                        "title": "工程概况",
                        "context_bundle_id": context_bundle_id,
                        "metric": "quantitative_ok_rate",
                        "metric_label": "量化指标达标率",
                        "metric_resolved": True,
                        "source_runs": 1,
                        "attribution_runs": 1,
                        "action_tags": ["add_quant_value"],
                        "display": "量化指标达标率 | general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify",
                    }
                ],
            },
        },
        "sections": [
            {
                "title": "工程概况",
                "content": "正文",
                "requested_timeout_sec": 80,
                "requested_max_output_tokens": 2600,
                "requested_section_retry_limit": 1,
                "runtime_budget_reason": "baseline",
                "used_key_alias": "OPENAI_API_KEY_TEXT_MAIN",
                "chapter_domain": "general",
                "logic_template_id": "A",
            }
        ],
    }
    out = self_evolution.record_runtime_learning(
        {"project_type": "房建", "generation_mode": "quality_200"},
        [result],
        params={"self_evolution": {"enabled": True}},
    )
    assert out["enabled"] is True
    profile = self_evolution.load_runtime_budget_profile()
    entry = next(iter(profile["entries"].values()))
    assert entry["combo_context_bundle_learning_attempt_counts"][context_bundle_id] == 1
    assert entry["combo_context_bundle_learning_gate_pass_counts"][context_bundle_id] == 1
    metric_key = self_evolution._context_metric_key(context_bundle_id, "quantitative_ok_rate")
    assert entry["combo_context_metric_attempt_counts"][metric_key] == 1
    assert entry["combo_context_metric_resolved_counts"][metric_key] == 1
    metric_action_key = self_evolution._context_metric_action_key(context_bundle_id, "quantitative_ok_rate", "add_quant_value")
    assert entry["combo_context_metric_action_attempt_counts"][metric_action_key] == 1
    assert entry["combo_context_metric_action_resolved_counts"][metric_action_key] == 1
    assert entry["last_attributed_context_bundles"]
    assert entry["last_metric_effects"]
    assert entry["last_metric_action_effects"]


def test_record_task_parallelism_learning_collects_task_signals(tmp_path, monkeypatch):
    monkeypatch.setattr(self_evolution, "TASK_PARALLELISM_PROFILE_PATH", tmp_path / "task_parallelism_profile.json")
    monkeypatch.setattr(self_evolution, "TASK_PARALLELISM_PROFILE_LOCK", tmp_path / ".task_parallelism_profile.lock")
    payload = {"project_type": "房建", "generation_mode": "quality_200", "outline": ["工程概况", "主要施工方法"]}
    agent_runtime = {
        "requested_agent_parallelism": 6,
        "agent_parallelism": 3,
        "variants_total": 1,
        "planned_total_pages": 20,
        "outline_count": 2,
        "runtime_agent_parallelism_reason": "mid_small_cap=3",
    }
    results = [
        {
            "quality_checks": {"risk_triplet": {"by_section": [{"title": "工程概况", "ok": False}]}},
            "quality_gate": {"ok": False, "failed": [{"metric": "risk_triplet_ok_rate"}]},
            "generation_trace": {
                "provider_chain": [
                    {"slot": "text_main", "provider": "openai", "model": "gpt-5.4", "key_alias": "OPENAI_API_KEY_TEXT_MAIN"}
                ]
            },
            "sections": [{"title": "工程概况", "used_key_alias": "OPENAI_API_KEY_TEXT_BACKUP"}],
        }
    ]
    out = self_evolution.record_task_parallelism_learning(
        payload,
        agent_runtime=agent_runtime,
        results=results,
        hard_failures=[],
        params={"self_evolution": {"enabled": True, "task_parallelism_enabled": True}},
    )
    assert out["enabled"] is True
    assert out["updated_entries"] == 1
    profile = self_evolution.load_task_parallelism_profile()
    assert isinstance(profile.get("entries"), dict)
    entry = next(iter(profile["entries"].values()))
    assert entry["runs"] == 1
    assert entry["success_runs"] == 1
    assert entry["fallback_runs"] == 1
    assert entry["quality_issue_runs"] == 1


def test_build_task_parallelism_hint_reduces_effective_parallelism():
    key = self_evolution._task_parallelism_profile_key("房建", "quality_200", 20, 5, 1)
    profile = {
        "version": "task_parallelism_profile_v1",
        "entries": {
            key: {
                "runs": 4,
                "success_runs": 2,
                "hard_failure_runs": 2,
                "fallback_runs": 2,
                "quality_issue_runs": 2,
            }
        },
    }
    out = self_evolution.build_task_parallelism_hint(
        params={"self_evolution": {"enabled": True, "task_parallelism_enabled": True}},
        payload={
            "project_type": "房建",
            "generation_mode": "quality_200",
            "_mode_policy": {"planned_total_pages": 20},
            "outline": ["工程概况", "主要施工方法", "质量保证", "安全文明施工", "进度计划"],
        },
        requested=6,
        effective=3,
        variants_total=1,
        profile=profile,
    )
    assert out["enabled"] is True
    assert out["applied"] is True
    assert out["effective"] == 2
    assert out["source_runs"] == 4


def test_record_runtime_learning_skips_dry_run_results(tmp_path, monkeypatch):
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_PATH", tmp_path / "runtime_budget_profile.json")
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_LOCK", tmp_path / ".runtime_budget_profile.lock")
    out = self_evolution.record_runtime_learning(
        {"project_type": "房建", "generation_mode": "quality_200", "dry_run": True},
        [
            {
                "project_type": "房建",
                "generation_mode": "quality_200",
                "sections": [
                    {
                        "title": "工程概况",
                        "content": "正文内容",
                        "requested_timeout_sec": 70,
                        "requested_max_output_tokens": 2600,
                        "requested_section_retry_limit": 1,
                    }
                ],
            }
        ],
        params={"self_evolution": {"enabled": True, "ignore_dry_run_learning": True}},
    )
    assert out["enabled"] is True
    assert out["updated_entries"] == 0
    assert out["skipped_dry_run_results"] == 1
    profile = self_evolution.load_runtime_budget_profile()
    assert profile["entries"] == {}


def test_summarize_runtime_budget_profile_includes_maintenance():
    out = self_evolution.summarize_runtime_budget_profile(
        params={"self_evolution": {"enabled": True}},
        profile={
            "version": "runtime_budget_profile_v1",
            "updated_at": "2026-03-19T10:00:00",
            "entries": {},
            "maintenance": {
                "retained_entry_count": 12,
                "pruned_entry_count": 3,
                "stale_pruned": 2,
                "overflow_pruned": 1,
                "soft_limit": 160,
                "stale_days": 21,
                "min_runs_to_keep": 2,
                "last_compacted_at": "2026-03-19T10:00:00",
            },
        },
    )
    assert out["maintenance"]["retained_entry_count"] == 12
    assert out["maintenance"]["pruned_entry_count"] == 3
    assert out["maintenance"]["stale_pruned"] == 2


def test_build_chapter_effect_summary_groups_metrics_and_actions_by_title():
    out = self_evolution.build_chapter_effect_summary(
        {
            "remediation_context_bundle_learning_metric_details": [
                {
                    "title": "工程概况",
                    "metric": "quantitative_ok_rate",
                    "metric_label": "量化指标达标率",
                    "bundle": "general/C | bundle",
                    "reason": "量化指标达标率已拉平",
                    "source_runs": 4,
                    "attribution_runs": 2,
                },
                {
                    "title": "工程概况",
                    "metric": "risk_triplet_ok_rate",
                    "metric_label": "风险三元组达标率",
                    "bundle": "general/C | bundle",
                    "reason": "风险三元组达标率已拉平",
                    "source_runs": 4,
                    "attribution_runs": 2,
                },
            ],
            "remediation_context_bundle_learning_metric_action_details": [
                {
                    "title": "工程概况",
                    "metric": "quantitative_ok_rate",
                    "metric_action_triplet": "量化指标达标率/补量化数值",
                    "bundle": "general/C | bundle",
                    "reason": "量化指标达标率/补量化数值已拉平",
                    "source_runs": 4,
                    "attribution_runs": 2,
                },
                {
                    "title": "工程概况",
                    "metric": "risk_triplet_ok_rate",
                    "metric_action_triplet": "风险三元组达标率/补风险→控制→验证",
                    "bundle": "general/C | bundle",
                    "reason": "风险三元组达标率/补风险→控制→验证已拉平",
                    "source_runs": 4,
                    "attribution_runs": 2,
                },
            ],
        },
        limit=3,
    )
    assert len(out) == 1
    assert out[0]["title"] == "工程概况"
    assert out[0]["resolved_metric_count"] == 2
    assert "量化指标达标率" in out[0]["resolved_metrics"]
    assert "量化指标达标率/补量化数值" in out[0]["resolved_action_triplets"]


def test_maintain_runtime_budget_profile_prunes_stale_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_PATH", tmp_path / "runtime_budget_profile.json")
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_LOCK", tmp_path / ".runtime_budget_profile.lock")
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            "keep": {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 3,
                "last_updated_at": "2026-03-18T12:00:00",
            },
            "drop": {
                "title": "主要施工方法",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 1,
                "last_updated_at": "2020-01-01T00:00:00",
            },
        },
    }
    self_evolution.RUNTIME_BUDGET_PROFILE_PATH.write_text(
        __import__("json").dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    out = self_evolution.maintain_runtime_budget_profile(
        params={"self_evolution": {"enabled": True, "runtime_profile_stale_days": 1, "runtime_profile_min_runs_to_keep": 2}}
    )
    assert out["enabled"] is True
    assert out["changed"] is True
    assert out["maintenance"]["pruned_entry_count"] == 1
    kept = self_evolution.load_runtime_budget_profile()
    assert "keep" in kept["entries"]
    assert "drop" not in kept["entries"]


def test_run_self_evolution_maintenance_returns_both_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_PATH", tmp_path / "runtime_budget_profile.json")
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_LOCK", tmp_path / ".runtime_budget_profile.lock")
    monkeypatch.setattr(self_evolution, "TASK_PARALLELISM_PROFILE_PATH", tmp_path / "task_parallelism_profile.json")
    monkeypatch.setattr(self_evolution, "TASK_PARALLELISM_PROFILE_LOCK", tmp_path / ".task_parallelism_profile.lock")
    out = self_evolution.run_self_evolution_maintenance(params={"self_evolution": {"enabled": True}})
    assert out["enabled"] is True
    assert "runtime_budget_profile" in out
    assert "task_parallelism_profile" in out


def test_maintain_runtime_budget_profile_no_prune_keeps_changed_false(tmp_path, monkeypatch):
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_PATH", tmp_path / "runtime_budget_profile.json")
    monkeypatch.setattr(self_evolution, "RUNTIME_BUDGET_PROFILE_LOCK", tmp_path / ".runtime_budget_profile.lock")
    profile = {
        "version": "runtime_budget_profile_v1",
        "maintenance": {
            "retained_entry_count": 1,
            "pruned_entry_count": 0,
            "stale_pruned": 0,
            "overflow_pruned": 0,
            "soft_limit": 160,
            "stale_days": 21,
            "min_runs_to_keep": 2,
            "last_compacted_at": "2026-03-19T10:00:00",
        },
        "entries": {
            "keep": {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 3,
                "last_updated_at": "2026-03-19T12:00:00",
            }
        },
    }
    self_evolution.RUNTIME_BUDGET_PROFILE_PATH.write_text(
        __import__("json").dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    out = self_evolution.maintain_runtime_budget_profile(
        params={"self_evolution": {"enabled": True, "runtime_profile_stale_days": 21, "runtime_profile_min_runs_to_keep": 2}}
    )
    assert out["enabled"] is True
    assert out["changed"] is False
    kept = self_evolution.load_runtime_budget_profile()
    assert kept["maintenance"]["last_compacted_at"] == "2026-03-19T10:00:00"
