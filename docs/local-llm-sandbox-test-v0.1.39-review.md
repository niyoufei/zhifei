# Local LLM Sandbox Test v0.1.39 Review

## 1. Scope

本文件记录 `v0.1.39-local-llm-sandbox-test` 阶段的沙箱验证结果。

本阶段只验证 sandbox/mock-only/draft-only/no-write 边界，不修改现有文件，不启动正式服务，不连接或运行正式 Ollama 生成，不触发 generation/export/job/build/output/result bundle 链路。

## 2. Baseline

- 工作目录: `/Users/youfeini/Desktop/文档生成系统`
- 当前分支: `main`
- 当前 HEAD: `2a04af3 docs: add ZBid snapshot mapper mock API bridge design`
- 最近提交:
  - `2a04af3 docs: add ZBid snapshot mapper mock API bridge design`
  - `593fe33 docs: add ZBid snapshot mapper API bridge design`
  - `8f3ffb6 docs: add ZBid snapshot mapper stage review`
- 新标签预检查: `v0.1.39-local-llm-sandbox-test` 本地不存在，远端不存在。

## 3. Commands

```bash
git status --short
git log --oneline -3
git tag --list
rg -n "sandbox|mock-only|mock_only|draft-only|draft_only|no-write|no_write|local llm|local-llm|Ollama|ZBid|snapshot" .
rg -n "文档生成系统|zdoc|Ollama|mock-only|draft-only|v0\\.1\\.39|sandbox" /Users/youfeini/.codex/memories/MEMORY.md
sed -n '1,260p' backend/zhifei_autoplan/zbid_snapshot_mapper.py
sed -n '1,280p' backend/tests/test_zbid_snapshot_mapper.py
sed -n '1,220p' scripts/guards/README.md
sed -n '1,430p' scripts/guards/zdoc_guard.py
find . -maxdepth 3 -type f \( -name '*sandbox*' -o -name '*mock*' -o -name '*ollama*' -o -name '*zbid*' -o -name '*llm*' \) | sort
sed -n '1,380p' backend/tests/test_llm_client.py
sed -n '1,340p' backend/tests/test_actions_ollama_preview.py
sed -n '1,360p' backend/tests/test_actions_ollama_section_draft_api.py
sed -n '1,180p' backend/tests/test_ollama_provider_adapter.py
git branch --show-current && git rev-parse --short HEAD && git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true
PYTHONDONTWRITEBYTECODE=1 python3 scripts/guards/zdoc_guard.py preflight
PYTHONDONTWRITEBYTECODE=1 python3 scripts/guards/zdoc_guard.py tag-check --tag v0.1.39-local-llm-sandbox-test
find backend/data/autoplan/jobs build output -type f 2>/dev/null | wc -l
PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -p python3 - <<'PY'
# sandbox hash/diff comparison script
PY
PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -p python3 -m pytest -p no:cacheprovider backend/tests/test_zbid_snapshot_mapper.py backend/tests/test_ollama_provider_adapter.py::test_complete_success_uses_mock_transport_and_api_chat backend/tests/test_llm_client.py::TestComplete::test_complete_ollama_enabled_uses_mock_provider backend/tests/test_actions_ollama_section_draft_api.py::test_actions_ollama_section_draft_build_enabled_returns_draft_diff_audit_without_writes
PYTHONDONTWRITEBYTECODE=1 python3 scripts/guards/zdoc_guard.py preflight
git status --short
find backend/data/autoplan/jobs build output -type f 2>/dev/null | wc -l
```

## 4. Sandbox Deployment Status

- 新模型部署状态: `loaded_mock_only`
- 旧模型标识: `qwen3:0.6b`
- 新模型标识: `local-llm-sandbox-latest`
- sandbox base URL: `sandbox://mock-only/no-ollama`
- 执行 Ollama 命令: 否
- 启动正式服务: 否
- 执行正式生成: 否

说明: 本阶段没有真实拉取、启动或调用本地 Ollama 模型。模型部署只在 sandbox/mock-only 配置中装载，用于验证 ZBid snapshot 到 ZDoc draft-only 输入在模型标识变化时保持一致。

## 5. Mock-only Verification

- `backend/tests/test_zbid_snapshot_mapper.py`: 通过。
- `backend/tests/test_ollama_provider_adapter.py::test_complete_success_uses_mock_transport_and_api_chat`: 通过，使用 fake transport。
- `backend/tests/test_llm_client.py::TestComplete::test_complete_ollama_enabled_uses_mock_provider`: 通过，使用 mock provider。
- `backend/tests/test_actions_ollama_section_draft_api.py::test_actions_ollama_section_draft_build_enabled_returns_draft_diff_audit_without_writes`: 通过，确认 draft-only helper 不触发写入链。

pytest 结果:

- 39 passed
- pytest reported duration: 1.93s
- command wall time: 2.87s

## 6. Output Consistency

- old SHA256: `67fd113846b0adc5fca5e89b1ee555d5db8b7efec207dcd8fa2bfc43d2b03556`
- new SHA256: `67fd113846b0adc5fca5e89b1ee555d5db8b7efec207dcd8fa2bfc43d2b03556`
- hash equal: yes
- unified diff line count: 0
- unified diff text: empty

一致性结论: 同一 ZBid snapshot 输入在旧模型标识和新 sandbox 模型标识下生成的 ZDoc draft-only 输入完全一致。

## 7. Performance

- old mapper: 0.081 ms
- new mapper: 0.065 ms
- hash/diff comparison command wall time: 0.11s
- hash/diff comparison user time: 0.08s
- hash/diff comparison sys time: 0.01s
- pytest command wall time: 2.87s
- pytest user time: 2.09s
- pytest sys time: 0.39s

## 8. No-write Boundary

Guard preflight counts before and after verification remained unchanged:

- `backend/data/autoplan/jobs`: 87 -> 87
- `build`: 1395 -> 1395
- `output`: 0 -> 0
- combined `find backend/data/autoplan/jobs build output -type f`: 1476 -> 1476

Draft-only output boundary:

- `mode`: `draft_only`
- `source_system`: `zbid`
- `section_count`: 1
- `draft_only`: true
- `allow_formal_apply`: false
- `allow_export`: false
- `allow_job_write`: false
- `allow_result_bundle_write`: false
- `allow_ollama`: false
- `no_write`: true
- `requires_human_review`: true

## 9. Boundary Confirmation

- 未修改现有文件。
- 未触发生成链。
- 未触发 export。
- 未创建或更新 job。
- 未写 build/output/result bundle。
- 未启动正式服务。
- 未运行正式 Ollama 生成。
- 所有验证均为 sandbox/mock-only/draft-only/no-write。

## 10. Tag

目标标签: `v0.1.39-local-llm-sandbox-test`

标签创建策略: 指向包含本复盘文档的 docs-only commit，不指向未包含本复盘文档的旧 HEAD。
