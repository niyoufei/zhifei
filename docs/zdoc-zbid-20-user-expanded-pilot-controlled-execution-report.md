# ZDoc-ZBid 20-user expanded pilot controlled execution report

## 1. Step 249 execution summary

Step 249 completed a controlled expanded pilot execution for the ZDoc-ZBid preview-only path under the approximately 20-user team口径.

The execution remained inside the authorized boundary:

- Preview-only
- No-write
- No-evidence
- No formal-chain entry
- No DOCX generation
- No `output/job/export` write
- No 50-user formal deployment design
- No top local model upgrade implementation

The run used desensitized / simulated / preview-only payloads. It did not use real bidding evidence and did not produce scoring basis.

## 2. Runtime environment and port record

### ZDoc

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `992889d35f0d9eaf8f69b542a6ac10c244aaa409`
- Execution-end HEAD before this report commit: `992889d35f0d9eaf8f69b542a6ac10c244aaa409`
- Final HEAD after committing this report: recorded in the completion response.
- Pre-run `git status --short`: empty
- Post-run `git status --short` before this report file was added: empty

ZDoc service:

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- PID: `54727`
- Port: `127.0.0.1:18766`

### ZBid

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Start HEAD: `378355755372e03ac4f4064af59b287054984c25`
- End HEAD: `378355755372e03ac4f4064af59b287054984c25`
- Pre-run `git status --short`: empty
- Post-run `git status --short`: empty
- ZBid commit/tag/push: not performed

ZBid service:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- PID: `54730`
- Port: `127.0.0.1:18767`

The already-validated ports `18766` and `18767` were free before startup. No adjacent ports were needed.

## 3. Temporary environment

The following environment variables were used only for the local process scope:

- `PYTHONDONTWRITEBYTECODE=1`
- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1`
- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`

No `.env`, config file, service definition, code file, test file, frontend file, backend file, or existing doc was modified.

## 4. Endpoint list

Only the following preview-only endpoints were called:

- ZDoc: `POST /local-trial/preview-only`
- ZBid: `POST /local-llm/zdoc-preview-only/receive`

The following were not called:

- `/generate`
- `/export_docx`
- `/review/apply`
- Any ZBid writeback endpoint
- Any unknown business endpoint

## 5. Expanded pilot scenario list

The run executed 20 total requests across 10 role/scenario categories. Six requests were boundary or exception input scenarios.

Role/scenario categories:

1. 总控管理员
2. 技术标主编
3. 施工方案编制人员
4. 进度计划编制人员
5. 质量安全复核人员
6. 商务 / 清单协同人员
7. 项目资料整理人员
8. ZBid 评标辅助观察人员
9. 普通试用人员
10. 异常输入 / 边界输入场景

## 6. Per-scenario verification results

| No. | Role type | Payload type | Boundary | ZDoc HTTP | ZBid HTTP | ZDoc outbound sent | ZBid receiver accepted | preview_only | no_write | no_evidence | blocked_reasons readable | validator_result readable | Five flags false | Manual review conclusion | Issues and risks | Rollback |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 总控管理员 | `admin_control_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可用于总控确认试运行边界，不作为正式审批。 | 总控容易误判 HTTP 200 为正式放行。 | No |
| S02 | 总控管理员 | `admin_audit_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 适合总控审计记录，不作为正式 evidence。 | 需避免日志摘要包含敏感数据。 | No |
| S03 | 技术标主编 | `chief_technical_editor_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可用于主编判断需人工补充的内容。 | 主编不得直接采纳为正式文本。 | No |
| S04 | 技术标主编 | `chief_editor_cross_section_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可读，需人工确认一致性。 | 跨章节预览不是正式审定。 | No |
| S05 | 施工方案编制人员 | `construction_plan_writer_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 适合识别施工方案待补充点。 | 不得生成正式施工方案。 | No |
| S06 | 施工方案编制人员 | `construction_boundary_missing_refs_payload` | Yes | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可识别为边界输入，需人工补齐材料。 | 边界输入不得 fallback 到正式链。 | No |
| S07 | 进度计划编制人员 | `schedule_planner_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可用于检查进度相关 blocked_reasons。 | 不得生成正式进度计划成果。 | No |
| S08 | 进度计划编制人员 | `schedule_milestone_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可读，需人工复核节点合理性。 | 节点预览不是正式计划依据。 | No |
| S09 | 质量安全复核人员 | `quality_safety_reviewer_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可用于复核流程演练。 | 复核记录不得作为正式评分依据。 | No |
| S10 | 质量安全复核人员 | `quality_safety_boundary_payload` | Yes | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可识别缺项，需人工上报。 | 缺项不得触发正式写入。 | No |
| S11 | 商务 / 清单协同人员 | `commercial_boq_collab_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可用于协同沟通，不形成正式清单成果。 | 不得写入正式商务数据。 | No |
| S12 | 商务 / 清单协同人员 | `commercial_clause_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可读，需人工判断风险。 | 不得作为正式商务结论。 | No |
| S13 | 项目资料整理人员 | `document_controller_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 适合形成问题清单候选项。 | 问题清单不得包含敏感材料原文。 | No |
| S14 | 项目资料整理人员 | `document_boundary_missing_scoring_payload` | Yes | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可识别缺失资料，需人工补齐。 | 缺失资料不得被系统自动补全到正式链。 | No |
| S15 | ZBid 评标辅助观察人员 | `zbid_observer_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可用于观察 receiver 行为。 | 观察结果不得成为评分依据。 | No |
| S16 | ZBid 评标辅助观察人员 | `zbid_observer_no_evidence_boundary_payload` | Yes | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可读，适合训练 no-evidence 边界。 | 不得把 preview-only 当 evidence。 | No |
| S17 | 普通试用人员 | `general_trial_user_preview_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可用于观察提示是否易懂。 | 普通用户可能误解 flags。 | No |
| S18 | 普通试用人员 | `general_preview_reader_payload` | No | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 可读性可接受，需配合说明文档。 | 需防止复制预览内容为正式成果。 | No |
| S19 | 异常输入 / 边界输入场景 | `missing_refs_boundary_payload` | Yes | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 应进入人工补齐，不需要回退。 | 不得自动补证据或写入。 | No |
| S20 | 异常输入 / 边界输入场景 | `high_risk_boundary_payload` | Yes | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | Yes | 应记录风险并停止正式链联想。 | 高风险不得触发正式接口。 | No |

## 7. HTTP result summary

- Total request count: 20
- Role/scenario category count: 10
- Boundary or exception input count: 6
- ZDoc HTTP 200 count: 20 / 20
- ZBid HTTP 200 count: 20 / 20
- Exceptions during controlled batches: 0

Controlled concurrency observation:

- The run used 4 controlled batches with 5 concurrent requests per batch.
- All 20 requests completed with HTTP 200.
- This is a local response-stability observation, not a formal load test or capacity benchmark.

Observed response timings:

- ZDoc route latency: min `1.08 ms`, median `2.16 ms`, max `176.51 ms`
- Outbound-to-ZBid latency: min `1.93 ms`, median `3.41 ms`, max `11.63 ms`

## 8. Preview-only / no-write / no-evidence review

All 20 requests confirmed:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

This confirms the expanded pilot preview-only flow under local controlled conditions only. It does not authorize formal generation, formal evidence, scoring-basis write, DOCX export, review/apply, ZBid writeback, real business integration, 50-user formal deployment design, or top local model upgrade implementation.

## 9. Forbidden endpoint and forbidden write review

The run did not:

- Trigger `/generate`
- Trigger `/export_docx`
- Trigger `/review/apply`
- Trigger ZBid writeback
- Generate DOCX
- Write `output/job/export`
- Use preview-only output as evidence
- Use preview-only output as scoring basis
- Write formal business data
- Call unknown business endpoints

## 10. ZDoc to ZBid send and receive result

All 20 requests confirmed:

- ZDoc preview-only route returned HTTP 200.
- ZDoc outbound adapter sent the preview-only payload.
- ZDoc outbound status was `sent_preview_only`.
- ZBid receiver endpoint returned HTTP 200.
- ZBid receiver status was `accepted_preview_only`.
- ZBid receiver accepted the preview-only payload.

## 11. Role coverage

The run covered all required role classes:

- 总控管理员
- 技术标主编
- 施工方案编制人员
- 进度计划编制人员
- 质量安全复核人员
- 商务 / 清单协同人员
- 项目资料整理人员
- ZBid 评标辅助观察人员
- 普通试用人员
- 异常输入 / 边界输入场景

This satisfies the requirement to cover at least 10 role/scenario categories.

## 12. Boundary and exception input behavior

Six scenarios were boundary or exception input scenarios:

- S06: construction boundary input
- S10: quality/safety boundary input
- S14: document boundary input
- S16: no-evidence boundary input
- S19: missing references boundary input
- S20: high-risk boundary input

Observed readable boundary reasons included:

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`
- `missing_evidence_anchor`
- `high_input_risk_not_validated`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

All boundary scenarios remained preview-only / no-write / no-evidence and did not fall back to formal interfaces.

## 13. Human review flow usability

The human review flow remains usable for expanded pilot operation:

1. Confirm the scenario is preview-only / no-write / no-evidence.
2. Confirm the HTTP status is 200.
3. Confirm ZDoc outbound sent the preview-only payload.
4. Confirm ZBid receiver accepted the payload.
5. Review `preview_packet`.
6. Review `validator_result`.
7. Review `blocked_reasons`.
8. Confirm all five false flags are false.
9. Record issue/risk and whether rollback is required.

The flow must remain advisory and review-only. It must not become formal approval, formal evidence, scoring basis, or writeback permission.

## 14. Error prompt and blocked_reasons readability

The observed `blocked_reasons` were readable and useful for human review.

Standard preview-only reasons were consistently visible:

- `missing_evidence_anchor`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

Boundary-specific reasons were also readable:

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`
- `high_input_risk_not_validated`

No blocking issue was observed in `blocked_reasons` readability.

## 15. Concurrency and response stability observation

The execution used 4 batches of 5 concurrent preview-only requests.

Observation:

- All requests completed successfully.
- All ZDoc responses were HTTP 200.
- All ZBid receiver responses were HTTP 200.
- No exception was raised by the controlled runner.
- No forbidden flag changed from false.
- No output/write path appeared.

Limit:

- This is not a formal concurrent load test.
- This is not a 50-user production readiness benchmark.
- Longer-duration operation and real-user permission behavior remain unverified.

## 16. Discovered issues

No blocking issue was discovered in the preview-only send/receive path.

Observed risks and follow-up items:

- Users may misinterpret HTTP 200 as formal approval.
- Users may treat preview-only output as evidence or scoring basis unless training is explicit.
- Boundary-input scenarios require clear human escalation instructions.
- Logs and issue lists must avoid sensitive content.
- A successful local expanded pilot must not be treated as 50-user formal deployment readiness.

## 17. Risk level

Current risk level: Medium.

Reason:

- The preview-only technical path completed 20 / 20 successful requests.
- Ten role/scenario categories were covered.
- Six boundary inputs were handled without formal fallback.
- Human-process risks remain material.
- Production deployment, formal-chain opening, and 50-user readiness remain unverified.

## 18. Rollback record

Rollback was not required.

Rollback readiness was verified:

- No code was modified.
- No tests were modified.
- No frontend/backend files were modified.
- No existing docs were modified.
- No persistent config was modified.
- Only temporary process-level environment variables were used.
- Services were stopped after the run.
- Ports were released after shutdown.
- ZDoc and ZBid `git status --short` remained clean before adding this report.
- No `output/job/export` write was observed.

## 19. Service shutdown and port release

Services were closed:

- ZDoc PID `54727` stopped.
- ZBid PID `54730` stopped.

Port release result:

- `127.0.0.1:18766` had no listener after shutdown.
- `127.0.0.1:18767` had no listener after shutdown.

## 20. output/job/export snapshot

### ZDoc

- Pre-run snapshot: no `output`, `job`, or `export` file entries.
- Post-run snapshot before this report file was added: no `output`, `job`, or `export` file entries.
- Result: no `output/job/export` write observed.

### ZBid

- Pre-run snapshot: no `output`, `job`, or `export` file entries.
- Post-run snapshot: no `output`, `job`, or `export` file entries.
- Result: no `output/job/export` write observed.

## 21. Recommendation on Step 250

Recommendation: enter Step 250 only as a docs-only expanded pilot stage review and next-authorization checkpoint.

Step 250 should not automatically start a larger pilot, real business integration, formal-chain opening, DOCX generation, ZBid writeback, 50-user formal deployment design, or top local model upgrade implementation.

## 22. Step 250 authorization request draft

Proposed next step:

`Step 250: ZDoc-ZBid 20-user expanded pilot controlled execution stage review`

Suggested authorization text:

```text
我授权执行 Step 250：ZDoc-ZBid 20-user expanded pilot controlled execution stage review。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
[由执行前核验填写]

授权范围：
仅限 docs-only 阶段复盘；
仅允许新增 20-user expanded pilot stage review 文档；
不得修改代码、tests、frontend、backend 或既有 docs；
不得启动服务；
不得运行 Ollama；
不得访问端口；
不得调用任何 endpoint；
不得触发 /generate、/export_docx、/review/apply；
不得触发 ZBid 写回；
不得生成 DOCX；
不得写 output/job/export；
不得把 preview-only 结果作为 evidence；
不得把 preview-only 结果作为评分依据；
不得进入 50 人正式部署设计；
不得实施顶级模型升级。

文档需归档 Step 249 的 20 条请求、10 类角色/场景覆盖、6 条异常或边界输入、HTTP 结果、preview-only/no-write/no-evidence 结果、五个 false flags、ZDoc->ZBid send/receive 结果、人工复核结论、并发与响应稳定性观察、风险等级、回退记录、服务关闭与端口释放结果，并提出后续授权建议。
```

Step 250 must not begin until the user explicitly authorizes it.
