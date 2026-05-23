# ZDoc preview-only route top-level no_evidence schema alignment plan and minimal-change authorization request

## 1. Step 270 / Step 271 观察项复盘

Step 270 已完成 ZDoc-ZBid preview-only endpoint smoke controlled execution：

- ZDoc `POST /local-trial/preview-only` 返回 HTTP 200。
- ZDoc route 顶层返回 `preview_only=true`。
- ZDoc route 顶层返回 `no_write=true`。
- ZDoc route 顶层返回 `preview_packet`、`validator_result`、`blocked_reasons`。
- ZDoc route 顶层未返回 `no_evidence` 字段。
- ZDoc outbound adapter 使用 ZDoc 返回字段向 ZBid receiver 发送 1 条 preview-only payload。
- ZBid `POST /local-llm/zdoc-preview-only/receive` 返回 HTTP 200。
- ZBid receiver 返回 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- ZBid receiver 返回五个禁止 flags 均为 `false`。

Step 271 已将该差异归档为 response schema 观察项，并明确：

- 该观察项未突破 preview-only / no-write / no-evidence 安全边界。
- 该观察项属于 response schema 可读性 / 显示一致性问题。
- 该观察项不属于写入、证据化或评分化问题。
- 后续如需调整，应单独授权最小代码变更与最小测试。

## 2. 当前问题描述

当前 ZDoc route：

```text
POST /local-trial/preview-only
```

顶层响应包含：

- `preview_only=true`
- `no_write=true`
- `metadata_only=true`
- `preview_packet`
- `validator_result`
- `blocked_reasons`
- 多个正式链阻断 / 不调用 / 不写入相关 false 字段

但顶层响应未包含：

- `no_evidence=true`

因此，人工复核时需要从 `blocked_reasons` 或 ZBid receiver 返回结果确认 no-evidence 边界，ZDoc route 顶层字段未与 ZBid receiver 的 `preview_only / no_write / no_evidence` 三项显示保持完全一致。

## 3. 当前安全结论

当前安全结论保持不变：

- Step 270 中 ZBid receiver 侧 `no_evidence=true` 成立。
- Step 270 中 ZBid receiver 侧 `preview_only=true` 成立。
- Step 270 中 ZBid receiver 侧 `no_write=true` 成立。
- 五个禁止 flags 均为 `false`：
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未创建 evidence。
- 未写入评分依据。

因此，当前观察项不表示安全边界失效。

## 4. 问题性质判断

该问题性质为：

- response schema 可读性问题。
- preview-only 三项状态显示一致性问题。
- 人工复核体验问题。

该问题不属于：

- 写入问题。
- evidence 生成问题。
- 评分依据写入问题。
- ZBid 写回问题。
- DOCX 生成问题。
- `output/job/export` 写入问题。
- 正式生成链、证据链、评分链、导出链或写回链问题。

## 5. 只读定位涉及的文件清单

本步骤只读查看以下文件：

| 文件 | 只读定位目的 |
| --- | --- |
| `backend/app/routers/local_trial_preview_only.py` | 确认 `/local-trial/preview-only` route 顶层响应字段 |
| `backend/tests/test_local_trial_preview_only_route.py` | 确认当前 route 单元测试断言范围 |
| `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py` | 确认 outbound adapter 对 ZBid receiver `no_evidence` 的校验逻辑 |
| `backend/tests/test_zdoc_zbid_preview_outbound.py` | 确认 outbound / receiver response 测试中已有 `no_evidence` 与五个 false flags 断言 |
| `docs/zdoc-zbid-preview-only-endpoint-smoke-controlled-execution-report.md` | 引用 Step 270 endpoint smoke 结果 |
| `docs/zdoc-zbid-preview-only-endpoint-smoke-review-and-response-schema-observation-decision-request.md` | 引用 Step 271 response schema 观察项结论 |

未访问、扫描、读取、复制、移动、分析或识别：

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

## 6. 可能的最小变更范围

如后续进入 Step 273，并获得用户明确授权，建议最小变更范围限定为：

1. `backend/app/routers/local_trial_preview_only.py`
   - 在 `/local-trial/preview-only` route 顶层响应中补充：

```python
"no_evidence": True,
```

2. `backend/tests/test_local_trial_preview_only_route.py`
   - 在 `_assert_no_write_route_flags` 或直接相关测试中补充：

```python
assert result["no_evidence"] is True
```

该变更应保持：

- 不改变 `preview_packet` 构造。
- 不改变 `validator_result` 构造。
- 不改变 `blocked_reasons` 合并逻辑。
- 不改变 outbound adapter 行为。
- 不改变 ZBid receiver 行为。
- 不新增写入行为。
- 不调用任何正式链。

## 7. 不建议变更的范围

不建议在本观察项修复中触碰：

- frontend 文件。
- ZBid 仓库文件。
- `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`。
- `backend/zhifei_autoplan/zdoc_zbid_preview_packet.py`。
- `backend/zhifei_autoplan/zbid_preview_input_validator.py`。
- 正式生成链。
- 正式 evidence 链。
- 正式评分链。
- DOCX 导出链。
- review/apply 链。
- ZBid 写回链。
- storage / output / job / export 写入链。
- 50 人正式部署设计。
- 顶级本地模型升级。

如未来发现 `no_evidence` 需要进入 deeper packet schema 或前端展示，应单独起草授权请求，不应混入 Step 273 最小变更。

## 8. 预期变更目标

预期最小代码变更目标：

- ZDoc `/local-trial/preview-only` route 顶层补充 `no_evidence=true`。
- ZDoc 顶层响应与 ZBid receiver 响应在三项状态字段上保持显示一致：
  - `preview_only=true`
  - `no_write=true`
  - `no_evidence=true`
- 保持既有 preview-only / no-write / no-evidence 语义一致。
- 保持 `blocked_reasons` 中的 no-evidence 边界提示。
- 保持不写入、不证据化、不评分化。

该目标不是开放正式链，也不是让 preview-only 结果成为 evidence。

## 9. 需要同步复核的返回字段

后续如进入 Step 273，应同步复核以下字段：

### ZDoc route 顶层字段

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `blocked_reasons` 可读
- `validator_result` 可读
- `preview_packet` 可读

### ZDoc route 既有正式链阻断字段

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `affects_zbid_writeback=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`
- `calls_ollama=false`
- `calls_external_model_api=false`

### 五个禁止 flags

若执行后续 endpoint smoke 或 outbound/receiver 复核，应继续确认：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

说明：当前最小 route 变更目标不是新增五个禁止 flags 到 ZDoc route 顶层，而是不得影响已有 outbound / receiver 对这五个 flags 的 false 约束。

## 10. 建议测试方式

### 单元测试

建议优先执行最小单元测试：

```bash
python -m pytest backend/tests/test_local_trial_preview_only_route.py -vv
```

验证目标：

- `/local-trial/preview-only` route 返回 HTTP 200。
- 顶层 `preview_only=true`。
- 顶层 `no_write=true`。
- 顶层 `no_evidence=true`。
- `preview_packet`、`validator_result`、`blocked_reasons` 可读。
- 正式链阻断字段保持 false。
- 不写 `output/job/export`。

### response schema smoke

如用户另行授权 runtime smoke，可复核：

- ZDoc `POST /local-trial/preview-only` 顶层返回 `no_evidence=true`。
- ZDoc outbound adapter 仍可向 ZBid receiver 发送 preview-only payload。
- ZBid receiver 仍返回 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- 五个禁止 flags 均为 `false`。

### endpoint preview-only 校验

如进入 endpoint 校验，仍需保持：

- 只调用 preview-only endpoint。
- 不调用 `/generate`。
- 不调用 `/export_docx`。
- 不调用 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。

## 11. 风险与回退

风险：

- 即使只是增加顶层字段，也可能影响前端或报告对 response schema 的展示判断。
- 如果把变更扩大到 packet、adapter 或前端，可能超出最小修复范围。
- 如果在未授权情况下运行服务或 endpoint smoke，会突破本 docs-only 步骤边界。

回退建议：

- 若 Step 273 修改后单元测试失败，优先回退新增字段断言或新增字段本身，再单独分析原因。
- 不得现场扩大改动范围修复无关问题。
- 不得因该字段对齐而接入正式链。
- 不得将 preview-only 结果作为 evidence 或评分依据。

## 12. 是否建议进入 Step 273

建议进入 Step 273，但仅在用户明确授权后进入。

建议的 Step 273 类型：

- ZDoc code-only minimal change。
- 仅补齐 `/local-trial/preview-only` route 顶层 `no_evidence=true`。
- 仅修改直接相关单元测试。
- 不启动服务。
- 不访问端口。
- 不调用 endpoint。
- 不发送 preview payload。
- 不运行 Ollama。
- 不进入 50 人正式部署设计。

## 13. Step 273 最小代码变更授权请求草案

```text
执行 Step 273：ZDoc preview-only route top-level no_evidence schema alignment minimal code change

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<待填入 Step 272 结束后 HEAD>

特别说明：
用户已暂停 /Users/youfeini/Desktop/AI知识图谱大全 文件夹识别任务。本步骤不得访问、扫描、读取、复制、移动、分析或识别该文件夹。

授权范围：
1. 仅允许最小修改 backend/app/routers/local_trial_preview_only.py；
2. 仅允许最小修改 backend/tests/test_local_trial_preview_only_route.py；
3. 目标仅为在 /local-trial/preview-only route 顶层响应中补充 no_evidence=true，并补充对应单元测试断言；
4. 保持 preview_only=true；
5. 保持 no_write=true；
6. 保持 preview_packet、validator_result、blocked_reasons 既有语义；
7. 保持 preview-only / no-write / no-evidence 边界；
8. 可运行最小单元测试：python -m pytest backend/tests/test_local_trial_preview_only_route.py -vv；
9. 可运行 git diff --check。

严格禁止：
1. 不修改 frontend；
2. 不修改 ZBid 仓库；
3. 不修改 outbound adapter；
4. 不修改 preview packet builder；
5. 不修改 validator；
6. 不修改正式生成链；
7. 不修改 evidence 链；
8. 不修改评分链；
9. 不修改 DOCX 导出链；
10. 不修改 review/apply 链；
11. 不修改 ZBid 写回链；
12. 不运行 ZDoc / ZBid 服务；
13. 不运行 Ollama；
14. 不访问端口；
15. 不调用任何 endpoint；
16. 不发送 preview payload；
17. 不触发 /generate、/export_docx、/review/apply；
18. 不触发 ZBid 写回；
19. 不生成 DOCX；
20. 不写 output/job/export；
21. 不把 preview-only 结果作为 evidence；
22. 不把 preview-only 结果作为评分依据；
23. 不进入 50 人正式部署设计；
24. 不实施顶级模型升级；
25. 不自动进入后续步骤。

完成后停止，等待审核。
```
