from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta


def test_list_users_page_paginates_desc(tmp_path: Path):
    from backend import auth_store

    db_path = tmp_path / "users.db"
    with patch.object(auth_store, "DB_PATH", db_path):
        auth_store.init_db()
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO users(id, email, password_hash, balance, daily_limit) VALUES (?, ?, ?, ?, ?)",
            (1, "u1@example.com", "hash", 10, 50),
        )
        conn.execute(
            "INSERT INTO users(id, email, password_hash, balance, daily_limit) VALUES (?, ?, ?, ?, ?)",
            (2, "u2@example.com", "hash", 20, 60),
        )
        conn.execute(
            "INSERT INTO users(id, email, password_hash, balance, daily_limit) VALUES (?, ?, ?, ?, ?)",
            (3, "u3@example.com", "hash", 30, 70),
        )
        conn.commit()
        conn.close()

        first_page = auth_store.list_users_page(limit=2)
        second_page = auth_store.list_users_page(limit=2, before_id=2)

    assert [item["id"] for item in first_page["items"]] == [3, 2]
    assert first_page["has_more"] is True
    assert first_page["next_before_user_id"] == 2
    assert [item["id"] for item in second_page["items"]] == [1]
    assert second_page["has_more"] is False
    assert second_page["next_before_user_id"] is None


def test_resolve_quota_policy_reads_scope_override_and_env_override(tmp_path: Path):
    from backend.zhifei_autoplan import quota_policy

    policy_path = tmp_path / "backend" / "data" / "autoplan" / "quota_policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        json.dumps(
            {
                "config_version": "test-quota-v1",
                "defaults": {
                    "session": {
                        "running_limit": 1,
                        "queued_limit": 2,
                        "active_limit": 3,
                        "warning_ratio": 0.75,
                        "tokens_last_hour_warning": 120,
                        "scan_limit": 333,
                        "lease_seconds": 777,
                        "text_chain_profile": "default",
                        "degrade_text_chain_profile": "cost_guard",
                    }
                },
                "text_chain_profiles": {
                    "default": {"slot_order": ["text_main", "text_backup"]},
                    "cost_guard": {"slot_order": ["text_backup", "text_main"]},
                },
                "overrides": {
                    "sessions": {
                        "sess-override": {
                            "queued_limit": 5,
                            "active_limit": 7,
                            "tokens_last_hour_warning": 88,
                            "degrade_text_chain_profile": "cost_guard",
                        }
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with patch.object(quota_policy, "QUOTA_POLICY_FILE", policy_path), patch.dict(
        os.environ,
        {"ZF_SESSION_RUNNING_JOB_LIMIT": "4"},
        clear=False,
    ):
        resolved = quota_policy.resolve_quota_policy(
            scope="session",
            tenant_id="sess-override",
            session_id="sess-override",
        )

    assert resolved["config_version"] == "test-quota-v1"
    assert resolved["running_limit"] == 4
    assert resolved["queued_limit"] == 5
    assert resolved["active_limit"] == 7
    assert resolved["tokens_last_hour_warning"] == 88
    assert resolved["text_chain_profile"] == "default"
    assert resolved["degrade_text_chain_profile"] == "cost_guard"
    assert resolved["text_chain_profiles"]["cost_guard"]["slot_order"] == ["text_backup", "text_main"]
    assert resolved["policy_source"] == "config+session_override+env"
    assert resolved["override_scope"] == "session"
    assert resolved["override_key"] == "sess-override"
    assert "ZF_SESSION_RUNNING_JOB_LIMIT" in resolved["env_overrides"]


def test_auth_quota_policy_roundtrip_writes_audit(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    policy_path = tmp_path / "backend" / "data" / "autoplan" / "quota_policy.json"
    audit_path = tmp_path / "backend" / "data" / "audit" / "config.jsonl"
    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        quota_policy, "QUOTA_POLICY_FILE", policy_path
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        out = auth.set_quota_policy(
            payload={
                "config_version": "quota-roundtrip-v1",
                "defaults": {
                    "session": {"running_limit": 2, "text_chain_profile": "default", "degrade_text_chain_profile": "cost_guard"},
                    "user": {"running_limit": 3, "text_chain_profile": "default", "degrade_text_chain_profile": "cost_guard"},
                },
                "text_chain_profiles": {
                    "default": {"slot_order": ["text_main", "text_backup"]},
                    "cost_guard": {"slot_order": ["text_backup", "text_main"]},
                },
            },
            authorization="Bearer admin-secret",
        )
        got = auth.get_quota_policy(authorization="Bearer admin-secret")

    assert out["ok"] is True
    assert got["ok"] is True
    assert got["policy"]["config_version"] == "quota-roundtrip-v1"
    assert got["policy"]["defaults"]["session"]["running_limit"] == 2
    assert got["policy"]["defaults"]["user"]["running_limit"] == 3
    assert got["policy"]["defaults"]["session"]["degrade_text_chain_profile"] == "cost_guard"
    assert got["policy"]["text_chain_profiles"]["cost_guard"]["slot_order"] == ["text_backup", "text_main"]
    assert audit_path.exists()
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "quota_policy_update" in audit_text
    assert "quota-roundtrip-v1" in audit_text


def test_auth_tenant_usage_report_aggregates_ops_and_billing(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy
    from backend.zhifei_autoplan import workspace as ws

    policy_path = tmp_path / "backend" / "data" / "autoplan" / "quota_policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(quota_policy.DEFAULT_QUOTA_POLICY, ensure_ascii=False, indent=2), encoding="utf-8")

    workspace_root = tmp_path / "workspaces"
    workspace_dir = workspace_root / "report-session"
    audit_dir = workspace_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    usage_audit = audit_dir / "resource_usage.jsonl"
    now = datetime.now(timezone.utc).isoformat()
    usage_audit.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": now,
                        "event": "job_queued",
                        "workspace_dir": str(workspace_dir),
                        "session_id": "report-session",
                        "user_id": 7,
                        "degrade_plan": {"applied": True, "text_chain_profile_after": "cost_guard"},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "ts": now,
                        "event": "job_rejected",
                        "workspace_dir": str(workspace_dir),
                        "session_id": "report-session",
                        "user_id": 7,
                        "rejection_code": "user_running_capacity_exceeded",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "ts": now,
                        "event": "llm_section_generation",
                        "workspace_dir": str(workspace_dir),
                        "session_id": "report-session",
                        "user_id": 7,
                        "provider": "openai",
                        "model": "gpt-5.4-mini",
                        "input_tokens": 20,
                        "output_tokens": 10,
                        "total_tokens": 30,
                        "latency_ms": 120,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    user = {"id": 7, "email": "ops@example.com", "balance": 12, "daily_limit": 50}
    charges = [
        {"user_id": 7, "action": "autoplan_generate_async", "cost": 3, "ts": now},
        {"user_id": 7, "action": "autoplan_generate_async", "cost": 3, "ts": now},
        {"user_id": 7, "action": "autoplan_optimize", "cost": 1, "ts": now},
    ]

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(quota_policy, "QUOTA_POLICY_FILE", policy_path), patch.object(
        ws, "WORKSPACE_ROOT", workspace_root
    ), patch(
        "backend.app.routers.auth.get_user_by_id",
        return_value=user,
    ), patch(
        "backend.app.routers.auth.list_charges_by_user",
        return_value=charges,
    ):
        out = auth.tenant_usage_report(
            user_id=7,
            session_id="report-session",
            workspace_dir=str(workspace_dir),
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert out["user"]["email"] == "ops@example.com"
    assert out["user_report"]["billing_summary"]["charge_event_count"] == 3
    assert out["user_report"]["billing_summary"]["charge_cost_total"] == 7
    assert out["user_report"]["billing_summary"]["by_action"]["autoplan_generate_async"]["count"] == 2
    assert out["user_report"]["ops_summary"]["last_hour"]["degraded_jobs"] == 1
    assert out["user_report"]["ops_summary"]["last_hour"]["rejected_jobs"] == 1
    assert out["user_report"]["ops_summary"]["last_hour"]["rejection_codes"]["user_running_capacity_exceeded"] == 1
    assert out["session_report"]["ops_summary"]["last_hour"]["text_chain_profiles"]["cost_guard"] == 1


def test_auth_tenant_usage_reports_returns_paginated_summaries(tmp_path: Path):
    from backend.app.routers import auth

    users_page = {
        "items": [
            {"id": 9, "email": "u9@example.com", "balance": 90, "daily_limit": 50},
            {"id": 8, "email": "u8@example.com", "balance": 80, "daily_limit": 40},
        ],
        "limit": 2,
        "has_more": True,
        "next_before_user_id": 8,
    }
    report_u9 = {
        "admission": {"scope": "user", "allowed": True},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 2,
                "rejected_jobs": 1,
                "degraded_jobs": 1,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "download_count": 1,
                "rejection_codes": {"user_running_capacity_exceeded": 1},
                "text_chain_profiles": {"cost_guard": 1},
            },
            "last_day": {},
        },
        "billing_summary": {
            "charge_event_count": 3,
            "charge_cost_total": 7,
            "by_action": {"autoplan_generate_async": {"count": 2, "cost_total": 6}},
        },
    }
    report_u8 = {
        "admission": {"scope": "user", "allowed": True},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 1,
                "rejected_jobs": 0,
                "degraded_jobs": 0,
                "completed_jobs": 2,
                "failed_jobs": 1,
                "download_count": 0,
                "rejection_codes": {},
                "text_chain_profiles": {"default": 1},
            },
            "last_day": {},
        },
        "billing_summary": {
            "charge_event_count": 1,
            "charge_cost_total": 2,
            "by_action": {"autoplan_optimize": {"count": 1, "cost_total": 2}},
        },
    }

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch(
        "backend.app.routers.auth.list_users_page",
        return_value=users_page,
    ), patch(
        "backend.app.routers.auth._build_user_usage_report",
        side_effect=[report_u9, report_u8],
    ):
        out = auth.tenant_usage_reports(
            limit=2,
            before_user_id=10,
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert len(out["items"]) == 2
    assert out["items"][0]["user"]["id"] == 9
    assert out["items"][0]["report_summary"]["billing_summary"]["charge_cost_total"] == 7
    assert out["items"][1]["report_summary"]["ops_summary"]["last_hour"]["completed_jobs"] == 2
    assert out["page"]["mode"] == "cursor"
    assert out["page"]["has_more"] is True
    assert out["page"]["next_before_user_id"] == 8
    assert out["sort"]["sort_scope"] == "cursor_page"
    assert out["summary"]["tenant_count"] == 2
    assert out["summary"]["charge_event_count"] == 4
    assert out["summary"]["charge_cost_total"] == 9
    assert out["summary"]["last_hour"]["queued_jobs"] == 3
    assert out["summary"]["last_hour"]["rejected_jobs"] == 1
    assert out["summary"]["last_hour"]["degraded_jobs"] == 1


def test_auth_tenant_usage_reports_window_query_filters_and_sorts():
    from backend.app.routers import auth

    users_scan = [
        {"id": 9, "email": "hot@example.com", "balance": 90, "daily_limit": 50},
        {"id": 8, "email": "warm@example.com", "balance": 80, "daily_limit": 40},
        {"id": 7, "email": "quiet@example.com", "balance": 70, "daily_limit": 30},
    ]
    report_hot = {
        "admission": {"scope": "user", "allowed": True, "warning_level": "warning"},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 3,
                "rejected_jobs": 2,
                "degraded_jobs": 1,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "download_count": 1,
                "rejection_codes": {"user_running_capacity_exceeded": 2},
                "text_chain_profiles": {"cost_guard": 1},
            },
            "last_day": {},
        },
        "billing_summary": {"charge_event_count": 5, "charge_cost_total": 11, "by_action": {}},
    }
    report_warm = {
        "admission": {"scope": "user", "allowed": True, "warning_level": "notice"},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 2,
                "rejected_jobs": 1,
                "degraded_jobs": 1,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "download_count": 0,
                "rejection_codes": {"queue_capacity_near_limit": 1},
                "text_chain_profiles": {"default": 1},
            },
            "last_day": {},
        },
        "billing_summary": {"charge_event_count": 3, "charge_cost_total": 6, "by_action": {}},
    }
    report_quiet = {
        "admission": {"scope": "user", "allowed": True, "warning_level": "none"},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 0,
                "rejected_jobs": 0,
                "degraded_jobs": 0,
                "completed_jobs": 2,
                "failed_jobs": 0,
                "download_count": 0,
                "rejection_codes": {},
                "text_chain_profiles": {"default": 1},
            },
            "last_day": {},
        },
        "billing_summary": {"charge_event_count": 1, "charge_cost_total": 1, "by_action": {}},
    }

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch(
        "backend.app.routers.auth.list_users",
        return_value=users_scan,
    ), patch(
        "backend.app.routers.auth._build_user_usage_report",
        side_effect=[report_hot, report_warm, report_quiet],
    ):
        out = auth.tenant_usage_reports(
            limit=1,
            offset=0,
            window_limit=50,
            warning_level="warning",
            sort_by="charge_cost_total",
            sort_order="desc",
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert out["page"]["mode"] == "window_query"
    assert out["page"]["limit"] == 1
    assert out["page"]["offset"] == 0
    assert out["page"]["window_limit"] == 50
    assert out["page"]["total_matched"] == 1
    assert out["page"]["scanned_users"] == 3
    assert out["page"]["has_more"] is False
    assert out["filters"]["warning_level"] == "warning"
    assert out["sort"]["sort_by"] == "charge_cost_total"
    assert out["sort"]["sort_scope"] == "window_query"
    assert len(out["items"]) == 1
    assert out["items"][0]["user"]["id"] == 9
    assert out["summary"]["tenant_count"] == 1
    assert out["summary"]["charge_cost_total"] == 11
    assert out["summary"]["last_hour"]["rejected_jobs"] == 2


def test_auth_tenant_usage_reports_window_query_supports_metric_and_text_chain_filters():
    from backend.app.routers import auth

    users_scan = [
        {"id": 9, "email": "guard@example.com", "balance": 90, "daily_limit": 50},
        {"id": 8, "email": "default@example.com", "balance": 80, "daily_limit": 40},
        {"id": 7, "email": "cheap@example.com", "balance": 70, "daily_limit": 30},
    ]
    report_guard = {
        "admission": {"scope": "user", "allowed": True, "warning_level": "warning"},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 3,
                "rejected_jobs": 2,
                "degraded_jobs": 1,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "download_count": 0,
                "rejection_codes": {"user_running_capacity_exceeded": 2},
                "text_chain_profiles": {"cost_guard": 1},
            },
            "last_day": {},
        },
        "billing_summary": {"charge_event_count": 5, "charge_cost_total": 11, "by_action": {}},
    }
    report_default = {
        "admission": {"scope": "user", "allowed": True, "warning_level": "warning"},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 1,
                "rejected_jobs": 2,
                "degraded_jobs": 0,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "download_count": 0,
                "rejection_codes": {"user_running_capacity_exceeded": 2},
                "text_chain_profiles": {"default": 1},
            },
            "last_day": {},
        },
        "billing_summary": {"charge_event_count": 4, "charge_cost_total": 9, "by_action": {}},
    }
    report_cheap = {
        "admission": {"scope": "user", "allowed": True, "warning_level": "warning"},
        "usage_profile": {"scope": "user"},
        "ops_summary": {
            "last_hour": {
                "queued_jobs": 2,
                "rejected_jobs": 1,
                "degraded_jobs": 1,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "download_count": 0,
                "rejection_codes": {"queue_capacity_near_limit": 1},
                "text_chain_profiles": {"cost_guard": 1},
            },
            "last_day": {},
        },
        "billing_summary": {"charge_event_count": 2, "charge_cost_total": 4, "by_action": {}},
    }

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch(
        "backend.app.routers.auth.list_users",
        return_value=users_scan,
    ), patch(
        "backend.app.routers.auth._build_user_usage_report",
        side_effect=[report_guard, report_default, report_cheap],
    ):
        out = auth.tenant_usage_reports(
            limit=5,
            offset=0,
            window_limit=100,
            warning_level="warning",
            min_charge_cost_total=10,
            min_rejected_jobs=2,
            text_chain_profile="cost_guard",
            sort_by="rejected_jobs",
            sort_order="desc",
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert out["page"]["mode"] == "window_query"
    assert out["page"]["total_matched"] == 1
    assert out["filters"]["min_charge_cost_total"] == 10
    assert out["filters"]["min_rejected_jobs"] == 2
    assert out["filters"]["text_chain_profile"] == "cost_guard"
    assert len(out["items"]) == 1
    assert out["items"][0]["user"]["id"] == 9
    assert out["summary"]["tenant_count"] == 1
    assert out["summary"]["charge_cost_total"] == 11
    assert out["summary"]["last_hour"]["rejected_jobs"] == 2


def test_auth_tenant_usage_reports_export_writes_csv(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    export_dir = tmp_path / "ops_exports"
    audit_path = tmp_path / "audit" / "config.jsonl"
    payload = {
        "ok": True,
        "items": [
            {
                "user": {"id": 9, "email": "hot@example.com", "balance": 90, "daily_limit": 50},
                "report_summary": {
                    "admission": {"allowed": True, "warning_level": "warning", "next_action": "slow_down"},
                    "ops_summary": {
                        "last_hour": {
                            "queued_jobs": 3,
                            "rejected_jobs": 2,
                            "degraded_jobs": 1,
                            "completed_jobs": 0,
                            "failed_jobs": 0,
                            "download_count": 1,
                            "rejection_codes": {"user_running_capacity_exceeded": 2},
                            "text_chain_profiles": {"cost_guard": 1},
                        }
                    },
                    "billing_summary": {"charge_event_count": 5, "charge_cost_total": 11},
                },
            }
        ],
        "page": {"mode": "window_query", "limit": 1},
        "filters": {"warning_level": "warning"},
        "sort": {"sort_by": "charge_cost_total", "sort_order": "desc"},
        "summary": {"tenant_count": 1},
    }

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ), patch(
        "backend.app.routers.auth._tenant_usage_reports_payload",
        return_value=payload,
    ):
        out = auth.tenant_usage_reports_export(
            export_format="csv",
            warning_level="warning",
            authorization="Bearer admin-secret",
        )

    export_path = Path(out["export_path"])
    assert out["ok"] is True
    assert out["export_format"] == "csv"
    assert out["item_count"] == 1
    assert out["audit_path"] == str(audit_path)
    assert export_path.exists()
    csv_text = export_path.read_text(encoding="utf-8")
    assert "user_id,email,balance,daily_limit" in csv_text
    assert "hot@example.com" in csv_text
    assert "cost_guard" in csv_text
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "ops_export_create" in audit_text
    assert str(export_path) in audit_text


def test_auth_tenant_usage_reports_export_writes_json(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    payload = {
        "ok": True,
        "items": [],
        "page": {"mode": "cursor", "limit": 2, "has_more": False},
        "filters": {"email_query": "", "warning_level": ""},
        "sort": {"sort_by": "user_id", "sort_order": "desc"},
        "summary": {"tenant_count": 0, "charge_cost_total": 0},
    }

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch(
        "backend.app.routers.auth._tenant_usage_reports_payload",
        return_value=payload,
    ):
        out = auth.tenant_usage_reports_export(
            export_format="json",
            authorization="Bearer admin-secret",
        )

    export_path = Path(out["export_path"])
    assert out["ok"] is True
    assert out["export_format"] == "json"
    assert out["item_count"] == 0
    assert export_path.exists()
    json_payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert json_payload["page"]["mode"] == "cursor"
    assert json_payload["summary"]["tenant_count"] == 0


def test_auth_tenant_usage_reports_exports_lists_recent_files(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    old_csv = export_dir / "tenant_usage_reports-cursor-20260402-010101.csv"
    new_json = export_dir / "tenant_usage_reports-window_query-20260402-020202.json"
    old_csv.write_text("a", encoding="utf-8")
    new_json.write_text("{}", encoding="utf-8")
    os.utime(old_csv, (1000, 1000))
    os.utime(new_json, (2000, 2000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ):
        out = auth.tenant_usage_reports_exports(
            limit=10,
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert out["count"] == 2
    assert out["items"][0]["filename"] == new_json.name
    assert out["items"][0]["format"] == "json"
    assert out["items"][1]["filename"] == old_csv.name


def test_auth_tenant_usage_reports_exports_summary_reports_inventory_and_preview(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    snapshot_dir = export_dir / "summary_snapshots"
    snapshot_export_dir = export_dir / "summary_snapshot_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    keep_csv = export_dir / "tenant_usage_reports-window_query-20260402-030303.csv"
    prune_json = export_dir / "tenant_usage_reports-cursor-20260401-020202.json"
    old_snapshot = snapshot_dir / "ops_exports_summary-20260401-010101.json"
    new_snapshot = snapshot_dir / "ops_exports_summary-20260402-010101.json"
    old_snapshot_export = snapshot_export_dir / "summary_snapshot_inventory-20260401-010101.csv"
    new_snapshot_export = snapshot_export_dir / "summary_snapshot_inventory-20260402-010101.json"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_export_dir.mkdir(parents=True, exist_ok=True)
    keep_csv.write_text("keep-csv", encoding="utf-8")
    prune_json.write_text('{"ok":true}', encoding="utf-8")
    old_snapshot.write_text('{"ok":true}', encoding="utf-8")
    new_snapshot.write_text('{"ok":true,"new":true}', encoding="utf-8")
    old_snapshot_export.write_text("a,b\n", encoding="utf-8")
    new_snapshot_export.write_text('{"ok":true}', encoding="utf-8")
    os.utime(keep_csv, (2000, 2000))
    os.utime(prune_json, (1000, 1000))
    os.utime(old_snapshot, (900, 900))
    os.utime(new_snapshot, (2100, 2100))
    os.utime(old_snapshot_export, (800, 800))
    os.utime(new_snapshot_export, (2200, 2200))
    confirm_state = export_dir / ".retention_used_tokens.jsonl"
    confirm_state.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "confirm_token": "tok-new",
                        "confirm_generated_at": "2026-04-02T03:00:00+00:00",
                        "confirm_valid_until": "2026-04-02T03:15:00+00:00",
                        "used_at": "2026-04-02T03:01:00+00:00",
                        "export_format": "csv",
                        "keep_latest": 1,
                        "older_than_hours": 0,
                        "prune_candidates_count": 1,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "confirm_token": "tok-old",
                        "confirm_generated_at": "2026-04-01T02:00:00+00:00",
                        "confirm_valid_until": "2026-04-01T02:15:00+00:00",
                        "used_at": "2026-04-01T02:01:00+00:00",
                        "export_format": "json",
                        "keep_latest": 1,
                        "older_than_hours": 0,
                        "prune_candidates_count": 2,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ):
        out = auth.tenant_usage_reports_exports_summary(
            keep_latest=1,
            older_than_hours=0,
            authorization="Bearer admin-secret",
        )

    summary = out["summary"]
    assert out["ok"] is True
    assert summary["total_exports"] == 2
    assert summary["total_size_bytes"] == keep_csv.stat().st_size + prune_json.stat().st_size
    assert summary["by_format"]["csv"] == 1
    assert summary["by_format"]["json"] == 1
    assert summary["by_mode"]["window_query"] == 1
    assert summary["by_mode"]["cursor"] == 1
    assert summary["newest_export"]["filename"] == keep_csv.name
    assert summary["oldest_export"]["filename"] == prune_json.name
    assert summary["retention_preview"]["prune_candidates_count"] == 1
    assert summary["retention_preview"]["prune_candidates_preview"][0]["filename"] == prune_json.name
    assert summary["confirm_token_state"]["path"] == str(confirm_state)
    assert summary["confirm_token_state"]["record_count"] == 2
    assert summary["confirm_token_state"]["retention_preview"]["prune_candidates_count"] == 1
    assert summary["confirm_token_state"]["retention_preview"]["prune_candidates_preview"][0]["confirm_token"] == "tok-old"
    assert summary["summary_snapshot_state"]["path"] == str(snapshot_dir)
    assert summary["summary_snapshot_state"]["count"] == 2
    assert summary["summary_snapshot_state"]["newest_snapshot"]["filename"] == new_snapshot.name
    assert summary["summary_snapshot_state"]["oldest_snapshot"]["filename"] == old_snapshot.name
    assert summary["summary_snapshot_state"]["retention_preview"]["prune_candidates_count"] == 1
    assert summary["summary_snapshot_state"]["retention_preview"]["prune_candidates_preview"][0]["filename"] == old_snapshot.name
    assert summary["summary_snapshot_export_state"]["path"] == str(snapshot_export_dir)
    assert summary["summary_snapshot_export_state"]["count"] == 2
    assert summary["summary_snapshot_export_state"]["by_format"]["csv"] == 1
    assert summary["summary_snapshot_export_state"]["by_format"]["json"] == 1
    assert summary["summary_snapshot_export_state"]["newest_export"]["filename"] == new_snapshot_export.name
    assert summary["summary_snapshot_export_state"]["oldest_export"]["filename"] == old_snapshot_export.name
    assert summary["summary_snapshot_export_state"]["retention_preview"]["prune_candidates_count"] == 1
    assert (
        summary["summary_snapshot_export_state"]["retention_preview"]["prune_candidates_preview"][0]["filename"]
        == old_snapshot_export.name
    )


def test_auth_tenant_usage_reports_exports_summary_export_writes_json_snapshot(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    export_dir = tmp_path / "ops_exports"
    snapshot_dir = export_dir / "summary_snapshots"
    audit_path = tmp_path / "audit" / "config.jsonl"
    export_dir.mkdir(parents=True, exist_ok=True)
    keep_csv = export_dir / "tenant_usage_reports-window_query-20260402-030303.csv"
    keep_csv.write_text("keep-csv", encoding="utf-8")
    os.utime(keep_csv, (2000, 2000))
    confirm_state = export_dir / ".retention_used_tokens.jsonl"
    confirm_state.write_text(
        json.dumps(
            {
                "confirm_token": "tok-new",
                "confirm_generated_at": "2026-04-02T03:00:00+00:00",
                "confirm_valid_until": "2026-04-02T03:15:00+00:00",
                "used_at": "2026-04-02T03:01:00+00:00",
                "export_format": "csv",
                "keep_latest": 1,
                "older_than_hours": 0,
                "prune_candidates_count": 1,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        auth, "AUTH_OPS_SUMMARY_SNAPSHOT_DIR", snapshot_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        out = auth.tenant_usage_reports_exports_summary_export(
            keep_latest=1,
            older_than_hours=0,
            authorization="Bearer admin-secret",
        )

    snapshot_path = Path(out["snapshot_path"])
    assert out["ok"] is True
    assert snapshot_path.exists() is True
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["summary"]["total_exports"] == 1
    assert payload["summary"]["confirm_token_state"]["record_count"] == 1
    assert out["audit_path"] == str(audit_path)
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "ops_export_summary_snapshot_create" in audit_text


def test_auth_tenant_usage_reports_exports_summary_snapshots_lists_recent_files(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    snapshot_dir = export_dir / "summary_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    old_snapshot = snapshot_dir / "ops_exports_summary-20260401-010101.json"
    new_snapshot = snapshot_dir / "ops_exports_summary-20260402-010101.json"
    old_snapshot.write_text('{"old":true}', encoding="utf-8")
    new_snapshot.write_text('{"new":true}', encoding="utf-8")
    os.utime(old_snapshot, (1000, 1000))
    os.utime(new_snapshot, (2000, 2000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ):
        out = auth.tenant_usage_reports_exports_summary_snapshots(
            limit=10,
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert out["path"] == str(snapshot_dir)
    assert out["count"] == 2
    assert out["total_size_bytes"] == old_snapshot.stat().st_size + new_snapshot.stat().st_size
    assert out["items"][0]["filename"] == new_snapshot.name
    assert out["items"][1]["filename"] == old_snapshot.name


def test_auth_tenant_usage_reports_exports_summary_snapshots_export_writes_json(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    export_dir = tmp_path / "ops_exports"
    snapshot_dir = export_dir / "summary_snapshots"
    export_meta_dir = export_dir / "summary_snapshot_exports"
    audit_path = tmp_path / "audit" / "config.jsonl"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snap = snapshot_dir / "ops_exports_summary-20260402-010101.json"
    snap.write_text('{"ok":true}', encoding="utf-8")
    os.utime(snap, (2000, 2000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        auth, "AUTH_OPS_SUMMARY_SNAPSHOT_EXPORT_DIR", export_meta_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        out = auth.tenant_usage_reports_exports_summary_snapshots_export(
            export_format="json",
            limit=10,
            authorization="Bearer admin-secret",
        )

    export_path = Path(out["export_path"])
    assert out["ok"] is True
    assert out["export_format"] == "json"
    assert out["snapshot_count"] == 1
    assert export_path.exists() is True
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["items"][0]["filename"] == snap.name
    assert out["audit_path"] == str(audit_path)
    assert "ops_export_summary_snapshot_inventory_export" in audit_path.read_text(encoding="utf-8")


def test_auth_tenant_usage_reports_exports_summary_snapshots_export_writes_csv(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    snapshot_dir = export_dir / "summary_snapshots"
    export_meta_dir = export_dir / "summary_snapshot_exports"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snap = snapshot_dir / "ops_exports_summary-20260402-010101.json"
    snap.write_text('{"ok":true}', encoding="utf-8")
    os.utime(snap, (2000, 2000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        auth, "AUTH_OPS_SUMMARY_SNAPSHOT_EXPORT_DIR", export_meta_dir
    ):
        out = auth.tenant_usage_reports_exports_summary_snapshots_export(
            export_format="csv",
            limit=10,
            authorization="Bearer admin-secret",
        )

    export_path = Path(out["export_path"])
    assert out["ok"] is True
    assert out["export_format"] == "csv"
    assert export_path.exists() is True
    csv_text = export_path.read_text(encoding="utf-8")
    assert "filename,path,size_bytes,mtime_iso" in csv_text
    assert snap.name in csv_text


def test_auth_tenant_usage_reports_exports_summary_snapshot_exports_lists_recent_files(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    export_meta_dir = export_dir / "summary_snapshot_exports"
    export_meta_dir.mkdir(parents=True, exist_ok=True)
    old_export = export_meta_dir / "summary_snapshot_inventory-20260401-010101.csv"
    new_export = export_meta_dir / "summary_snapshot_inventory-20260402-010101.json"
    old_export.write_text("a,b\n", encoding="utf-8")
    new_export.write_text('{"ok":true}', encoding="utf-8")
    os.utime(old_export, (1000, 1000))
    os.utime(new_export, (2000, 2000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ):
        out = auth.tenant_usage_reports_exports_summary_snapshot_exports(
            limit=10,
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert out["path"] == str(export_meta_dir)
    assert out["count"] == 2
    assert out["by_format"]["csv"] == 1
    assert out["by_format"]["json"] == 1
    assert out["items"][0]["filename"] == new_export.name
    assert out["items"][1]["filename"] == old_export.name


def test_auth_tenant_usage_reports_exports_summary_snapshot_exports_summary_reports_inventory_and_preview(
    tmp_path: Path,
):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    export_meta_dir = export_dir / "summary_snapshot_exports"
    export_meta_dir.mkdir(parents=True, exist_ok=True)
    old_export = export_meta_dir / "summary_snapshot_inventory-20260401-010101.csv"
    new_export = export_meta_dir / "summary_snapshot_inventory-20260402-010101.json"
    old_export.write_text("a,b\n", encoding="utf-8")
    new_export.write_text('{"ok":true}', encoding="utf-8")
    os.utime(old_export, (1000, 1000))
    os.utime(new_export, (2000, 2000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ):
        out = auth.tenant_usage_reports_exports_summary_snapshot_exports_summary(
            limit=10,
            keep_latest=1,
            older_than_hours=0,
            authorization="Bearer admin-secret",
        )

    assert out["ok"] is True
    assert out["path"] == str(export_meta_dir)
    assert out["count"] == 2
    assert out["size_bytes"] == old_export.stat().st_size + new_export.stat().st_size
    assert out["by_format"]["csv"] == 1
    assert out["by_format"]["json"] == 1
    assert out["newest_export"]["filename"] == new_export.name
    assert out["oldest_export"]["filename"] == old_export.name
    assert out["retention_preview"]["prune_candidates_count"] == 1
    assert out["retention_preview"]["prune_candidates_preview"][0]["filename"] == old_export.name


def test_auth_tenant_usage_reports_exports_retention_preview_and_execute(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    export_dir = tmp_path / "ops_exports"
    audit_path = tmp_path / "audit" / "config.jsonl"
    confirm_state_path = export_dir / ".retention_used_tokens.jsonl"
    export_dir.mkdir(parents=True, exist_ok=True)
    keep_file = export_dir / "tenant_usage_reports-window_query-20260402-030303.csv"
    prune_file = export_dir / "tenant_usage_reports-window_query-20260401-030303.csv"
    keep_file.write_text("keep", encoding="utf-8")
    prune_file.write_text("prune", encoding="utf-8")
    os.utime(keep_file, (2000, 2000))
    os.utime(prune_file, (1000, 1000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        preview = auth.tenant_usage_reports_exports_retention(
            req=auth.ExportRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                export_format="csv",
                execute=False,
            ),
            authorization="Bearer admin-secret",
        )

    assert preview["ok"] is True
    assert preview["mode"] == "preview"
    assert preview["prune_candidates_count"] == 1
    assert preview["deleted_count"] == 0
    assert preview["audit_path"] == str(audit_path)
    assert len(preview["confirm_token"]) == 64
    assert preview["confirm_generated_at"].endswith("+00:00")
    assert preview["confirm_valid_until"].endswith("+00:00")
    assert preview["confirm_ttl_seconds"] >= 60
    assert preview["confirm_state_path"] == str(confirm_state_path)
    assert preview["confirm_prune_candidates_count"] == 1
    assert keep_file.exists() is True
    assert prune_file.exists() is True
    assert confirm_state_path.exists() is False
    preview_candidate = preview["prune_candidates"][0]["path"]
    assert preview_candidate.endswith(prune_file.name)

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        execute = auth.tenant_usage_reports_exports_retention(
            req=auth.ExportRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                export_format="csv",
                execute=True,
                confirm_token=preview["confirm_token"],
                confirm_generated_at=preview["confirm_generated_at"],
                confirm_prune_candidates_count=preview["confirm_prune_candidates_count"],
            ),
            authorization="Bearer admin-secret",
        )

    assert execute["ok"] is True
    assert execute["mode"] == "execute"
    assert execute["deleted_count"] == 1
    assert execute["audit_path"] == str(audit_path)
    assert execute["confirm_state_path"] == str(confirm_state_path)
    assert keep_file.exists() is True
    assert prune_file.exists() is False
    assert confirm_state_path.exists() is True
    state_text = confirm_state_path.read_text(encoding="utf-8")
    assert preview["confirm_token"] in state_text
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "ops_export_retention_preview" in audit_text
    assert "ops_export_retention_execute" in audit_text


def test_auth_tenant_usage_reports_exports_retention_execute_requires_confirm(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    keep_file = export_dir / "tenant_usage_reports-window_query-20260402-030303.csv"
    prune_file = export_dir / "tenant_usage_reports-window_query-20260401-030303.csv"
    keep_file.write_text("keep", encoding="utf-8")
    prune_file.write_text("prune", encoding="utf-8")
    os.utime(keep_file, (2000, 2000))
    os.utime(prune_file, (1000, 1000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ):
        try:
            auth.tenant_usage_reports_exports_retention(
                req=auth.ExportRetentionRequest(
                    keep_latest=1,
                    older_than_hours=0,
                    export_format="csv",
                    execute=True,
                ),
                authorization="Bearer admin-secret",
            )
            assert False, "expected HTTPException"
        except Exception as exc:
            from fastapi import HTTPException

            assert isinstance(exc, HTTPException)
            assert exc.status_code == 400
            assert "confirm_generated_at required" in str(exc.detail)

    assert keep_file.exists() is True
    assert prune_file.exists() is True


def test_auth_tenant_usage_reports_exports_retention_execute_rejects_expired_confirm(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    keep_file = export_dir / "tenant_usage_reports-window_query-20260402-030303.csv"
    prune_file = export_dir / "tenant_usage_reports-window_query-20260401-030303.csv"
    keep_file.write_text("keep", encoding="utf-8")
    prune_file.write_text("prune", encoding="utf-8")
    os.utime(keep_file, (2000, 2000))
    os.utime(prune_file, (1000, 1000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        auth, "_ops_export_retention_confirm_ttl_seconds", return_value=60
    ):
        plan = auth._ops_export_retention_plan(
            keep_latest=1,
            older_than_hours=0,
            export_format="csv",
        )
        stale_generated_at = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).replace(microsecond=0).isoformat()
        stale_token = auth._ops_export_retention_confirm_token(
            plan,
            confirm_generated_at=stale_generated_at,
        )
        try:
            auth.tenant_usage_reports_exports_retention(
                req=auth.ExportRetentionRequest(
                    keep_latest=1,
                    older_than_hours=0,
                    export_format="csv",
                    execute=True,
                    confirm_token=stale_token,
                    confirm_generated_at=stale_generated_at,
                    confirm_prune_candidates_count=1,
                ),
                authorization="Bearer admin-secret",
            )
            assert False, "expected HTTPException"
        except Exception as exc:
            from fastapi import HTTPException

            assert isinstance(exc, HTTPException)
            assert exc.status_code == 400
            assert "confirm_token expired" in str(exc.detail)

    assert keep_file.exists() is True
    assert prune_file.exists() is True


def test_auth_tenant_usage_reports_exports_retention_execute_rejects_reused_confirm(tmp_path: Path):
    from backend.app.routers import auth

    export_dir = tmp_path / "ops_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    keep_file = export_dir / "tenant_usage_reports-window_query-20260402-030303.csv"
    prune_file = export_dir / "tenant_usage_reports-window_query-20260401-030303.csv"
    keep_file.write_text("keep", encoding="utf-8")
    prune_file.write_text("prune", encoding="utf-8")
    os.utime(keep_file, (2000, 2000))
    os.utime(prune_file, (1000, 1000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ):
        preview = auth.tenant_usage_reports_exports_retention(
            req=auth.ExportRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                export_format="csv",
                execute=False,
            ),
            authorization="Bearer admin-secret",
        )
        auth._record_ops_export_retention_token_use(
            confirm_token=preview["confirm_token"],
            confirm_generated_at=preview["confirm_generated_at"],
            confirm_valid_until=preview["confirm_valid_until"],
            export_format="csv",
            keep_latest=1,
            older_than_hours=0,
            prune_candidates_count=1,
        )
        try:
            auth.tenant_usage_reports_exports_retention(
                req=auth.ExportRetentionRequest(
                    keep_latest=1,
                    older_than_hours=0,
                    export_format="csv",
                    execute=True,
                    confirm_token=preview["confirm_token"],
                    confirm_generated_at=preview["confirm_generated_at"],
                    confirm_prune_candidates_count=preview["confirm_prune_candidates_count"],
                ),
                authorization="Bearer admin-secret",
            )
            assert False, "expected HTTPException"
        except Exception as exc:
            from fastapi import HTTPException

            assert isinstance(exc, HTTPException)
            assert exc.status_code == 400
            assert "confirm_token already used" in str(exc.detail)

    assert keep_file.exists() is True
    assert prune_file.exists() is True


def test_auth_tenant_usage_reports_exports_confirm_tokens_retention_preview_and_execute(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    export_dir = tmp_path / "ops_exports"
    audit_path = tmp_path / "audit" / "config.jsonl"
    export_dir.mkdir(parents=True, exist_ok=True)
    confirm_state = export_dir / ".retention_used_tokens.jsonl"
    confirm_state.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "confirm_token": "tok-new",
                        "confirm_generated_at": "2026-04-02T03:00:00+00:00",
                        "confirm_valid_until": "2026-04-02T03:15:00+00:00",
                        "used_at": "2026-04-02T03:01:00+00:00",
                        "export_format": "csv",
                        "keep_latest": 1,
                        "older_than_hours": 0,
                        "prune_candidates_count": 1,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "confirm_token": "tok-old",
                        "confirm_generated_at": "2026-04-01T02:00:00+00:00",
                        "confirm_valid_until": "2026-04-01T02:15:00+00:00",
                        "used_at": "2026-04-01T02:01:00+00:00",
                        "export_format": "json",
                        "keep_latest": 1,
                        "older_than_hours": 0,
                        "prune_candidates_count": 2,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        preview = auth.tenant_usage_reports_exports_confirm_tokens_retention(
            req=auth.ConfirmTokenRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                execute=False,
            ),
            authorization="Bearer admin-secret",
        )

    assert preview["ok"] is True
    assert preview["mode"] == "preview"
    assert preview["path"] == str(confirm_state)
    assert preview["prune_candidates_count"] == 1
    assert preview["prune_candidates"][0]["confirm_token"] == "tok-old"
    assert preview["deleted_count"] == 0
    assert confirm_state.exists() is True

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        execute = auth.tenant_usage_reports_exports_confirm_tokens_retention(
            req=auth.ConfirmTokenRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                execute=True,
            ),
            authorization="Bearer admin-secret",
        )

    assert execute["ok"] is True
    assert execute["mode"] == "execute"
    assert execute["deleted_count"] == 1
    remaining = confirm_state.read_text(encoding="utf-8")
    assert "tok-new" in remaining
    assert "tok-old" not in remaining
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "ops_export_confirm_tokens_retention_preview" in audit_text
    assert "ops_export_confirm_tokens_retention_execute" in audit_text


def test_auth_tenant_usage_reports_exports_summary_snapshots_retention_preview_and_execute(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    export_dir = tmp_path / "ops_exports"
    snapshot_dir = export_dir / "summary_snapshots"
    audit_path = tmp_path / "audit" / "config.jsonl"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    keep_snapshot = snapshot_dir / "ops_exports_summary-20260402-010101.json"
    prune_snapshot = snapshot_dir / "ops_exports_summary-20260401-010101.json"
    keep_snapshot.write_text('{"keep":true}', encoding="utf-8")
    prune_snapshot.write_text('{"prune":true}', encoding="utf-8")
    os.utime(keep_snapshot, (2000, 2000))
    os.utime(prune_snapshot, (1000, 1000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        auth, "AUTH_OPS_SUMMARY_SNAPSHOT_DIR", snapshot_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        preview = auth.tenant_usage_reports_exports_summary_snapshots_retention(
            req=auth.SummarySnapshotRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                execute=False,
            ),
            authorization="Bearer admin-secret",
        )

    assert preview["ok"] is True
    assert preview["mode"] == "preview"
    assert preview["path"] == str(snapshot_dir)
    assert preview["prune_candidates_count"] == 1
    assert preview["prune_candidates"][0]["filename"] == prune_snapshot.name
    assert preview["deleted_count"] == 0
    assert keep_snapshot.exists() is True
    assert prune_snapshot.exists() is True

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        auth, "AUTH_OPS_SUMMARY_SNAPSHOT_DIR", snapshot_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        execute = auth.tenant_usage_reports_exports_summary_snapshots_retention(
            req=auth.SummarySnapshotRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                execute=True,
            ),
            authorization="Bearer admin-secret",
        )

    assert execute["ok"] is True
    assert execute["mode"] == "execute"
    assert execute["deleted_count"] == 1
    assert keep_snapshot.exists() is True
    assert prune_snapshot.exists() is False
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "ops_export_summary_snapshots_retention_preview" in audit_text
    assert "ops_export_summary_snapshots_retention_execute" in audit_text


def test_auth_tenant_usage_reports_exports_summary_snapshot_exports_retention_preview_and_execute(tmp_path: Path):
    from backend.app.routers import auth
    from backend.zhifei_autoplan import quota_policy

    export_dir = tmp_path / "ops_exports"
    export_meta_dir = export_dir / "summary_snapshot_exports"
    audit_path = tmp_path / "audit" / "config.jsonl"
    export_meta_dir.mkdir(parents=True, exist_ok=True)
    keep_export = export_meta_dir / "summary_snapshot_inventory-20260402-010101.json"
    prune_export = export_meta_dir / "summary_snapshot_inventory-20260401-010101.csv"
    keep_export.write_text('{"keep":true}', encoding="utf-8")
    prune_export.write_text("a,b\n", encoding="utf-8")
    os.utime(keep_export, (2000, 2000))
    os.utime(prune_export, (1000, 1000))

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        preview = auth.tenant_usage_reports_exports_summary_snapshot_exports_retention(
            req=auth.SummarySnapshotExportRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                execute=False,
            ),
            authorization="Bearer admin-secret",
        )

    assert preview["ok"] is True
    assert preview["mode"] == "preview"
    assert preview["path"] == str(export_meta_dir)
    assert preview["prune_candidates_count"] == 1
    assert preview["prune_candidates"][0]["filename"] == prune_export.name
    assert preview["deleted_count"] == 0
    assert keep_export.exists() is True
    assert prune_export.exists() is True

    with patch.object(auth, "ADMIN_KEY", "admin-secret"), patch.object(
        auth, "AUTH_OPS_EXPORT_DIR", export_dir
    ), patch.object(
        quota_policy, "CONFIG_AUDIT_FILE", audit_path
    ):
        execute = auth.tenant_usage_reports_exports_summary_snapshot_exports_retention(
            req=auth.SummarySnapshotExportRetentionRequest(
                keep_latest=1,
                older_than_hours=0,
                execute=True,
            ),
            authorization="Bearer admin-secret",
        )

    assert execute["ok"] is True
    assert execute["mode"] == "execute"
    assert execute["deleted_count"] == 1
    assert keep_export.exists() is True
    assert prune_export.exists() is False
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "ops_export_summary_snapshot_exports_retention_preview" in audit_text
    assert "ops_export_summary_snapshot_exports_retention_execute" in audit_text
