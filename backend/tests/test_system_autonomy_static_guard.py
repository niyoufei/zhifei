from backend.zhifei_autoplan.system_autonomy_static_guard import (
    AUTHORIZED_CHANGED_FILES,
    RiskCategory,
    analyze_command_string,
    analyze_path_string,
    validate_changed_files,
)


def test_path_guard_blocks_real_kg_project_data_secrets_and_outputs():
    cases = {
        "知识图谱/ZF-KG-12-Municipal-Bridge.json": RiskCategory.KG,
        "01_真实项目测试/example.docx": RiskCategory.REAL_PROJECT_DATA,
        ".env.local": RiskCategory.SECRETS,
        "output/result.json": RiskCategory.OUTPUT_JOB_EXPORT_LOG,
        "jobs/state.json": RiskCategory.OUTPUT_JOB_EXPORT_LOG,
        "exports/result.docx": RiskCategory.OUTPUT_JOB_EXPORT_LOG,
        "logs/run.log": RiskCategory.OUTPUT_JOB_EXPORT_LOG,
    }

    for path, category in cases.items():
        result = analyze_path_string(path)
        assert result.allowed is False
        assert category in result.risk_categories


def test_command_guard_blocks_runtime_endpoint_ollama_model_prompt():
    cases = {
        "./scripts/run_web_ui.sh --background": RiskCategory.WEB_UI,
        "curl http://127.0.0.1:8000/health": RiskCategory.ENDPOINT,
        "ollama run qwen": RiskCategory.OLLAMA,
        "python model inference prompt": RiskCategory.MODEL,
    }

    for command, category in cases.items():
        result = analyze_command_string(command)
        assert result.allowed is False
        assert category in result.risk_categories


def test_changed_files_allow_only_system_autonomy_014_static_guard_scope():
    assert AUTHORIZED_CHANGED_FILES == frozenset(
        {
            "backend/zhifei_autoplan/system_autonomy_static_guard.py",
            "backend/tests/test_system_autonomy_static_guard.py",
            "docs/zdoc-system-autonomy-014-implementation-static-guard-scope-correction-no-runtime.md",
        }
    )

    result = validate_changed_files(AUTHORIZED_CHANGED_FILES)

    assert result.allowed is True


def test_changed_files_block_prior_013_and_earlier_scopes():
    result = validate_changed_files(
        [
            "docs/zdoc-system-autonomy-013-implementation-static-guard-scope-correction-no-runtime.md",
            "docs/zdoc-system-autonomy-012-implementation-static-guard-scope-correction-no-runtime.md",
            "docs/zdoc-system-autonomy-011-implementation-static-guard-scope-correction-no-runtime.md",
            "docs/zdoc-system-autonomy-010-implementation-static-guard-scope-correction-no-runtime.md",
            "docs/zdoc-system-autonomy-009-implementation-static-guard-scope-correction-no-runtime.md",
            "docs/zdoc-system-autonomy-008-implementation-static-guard-scope-correction-no-runtime.md",
        ]
    )

    assert result.allowed is False
    assert "changed_file_outside_system_autonomy_014_static_guard_scope" in result.blocked_reasons
    assert result.risk_categories == ()


def test_changed_files_block_runtime_web_ui_and_sensitive_paths():
    result = validate_changed_files(
        [
            "scripts/run_web_ui.sh",
            "local-launcher-v1/app.js",
            "backend/zhifei_autoplan/system_autonomy_permissions.py",
            "kg_packs/live.json",
            "data/uploads/project.docx",
            ".env.local",
            "jobs/state.json",
            "exports/result.docx",
            "logs/run.log",
        ]
    )

    assert result.allowed is False
    assert "changed_file_outside_system_autonomy_014_static_guard_scope" in result.blocked_reasons
    assert RiskCategory.RUNTIME in result.risk_categories
    assert RiskCategory.WEB_UI in result.risk_categories
    assert RiskCategory.KG in result.risk_categories
    assert RiskCategory.REAL_PROJECT_DATA in result.risk_categories
    assert RiskCategory.SECRETS in result.risk_categories
    assert RiskCategory.OUTPUT_JOB_EXPORT_LOG in result.risk_categories
