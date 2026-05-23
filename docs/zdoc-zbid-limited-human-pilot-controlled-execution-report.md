# ZDoc-ZBid limited human pilot controlled execution report

## 1. Step 247 execution summary

Step 247 completed a limited human pilot controlled execution for the ZDoc-ZBid preview-only path.

The pilot remained inside the authorized boundary:

- Preview-only
- No-write
- No-evidence
- No formal-chain entry
- No DOCX generation
- No `output/job/export` write
- No 50-user formal deployment design
- No top local model upgrade implementation

This was a controlled local limited human pilot simulation with five role scenarios. It did not use real sensitive business data and did not perform real production business integration.

## 2. Repository and environment record

### ZDoc

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `b905c1541cd350eb5ed2e43a497ccbdd3fe95c06`
- Execution-end HEAD before this report commit: `b905c1541cd350eb5ed2e43a497ccbdd3fe95c06`
- Final HEAD after committing this report: recorded in the completion response.
- Pre-run `git status --short`: empty
- Post-run `git status --short` before this report file was added: empty

### ZBid

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Start HEAD: `378355755372e03ac4f4064af59b287054984c25`
- End HEAD: `378355755372e03ac4f4064af59b287054984c25`
- Pre-run `git status --short`: empty
- Post-run `git status --short`: empty
- ZBid commit/tag/push: not performed

## 3. Runtime services and ports

### ZDoc service

- Start command:

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- PID: `45172`
- Port: `127.0.0.1:18766`
- Purpose: local ZDoc preview-only entry for limited human pilot scenarios.

### ZBid service

- Start command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- PID: `45187`
- Port: `127.0.0.1:18767`
- Purpose: local ZBid preview-only receiver endpoint for limited human pilot scenarios.

### Port selection

The Step 245 ports were reused:

- ZDoc: `127.0.0.1:18766`
- ZBid: `127.0.0.1:18767`

Both ports were free before startup, so no adjacent port was needed.

## 4. Temporary environment variables

The following environment variables were used only for this controlled execution and were not written to `.env`, config files, or persistent files:

- `PYTHONDONTWRITEBYTECODE=1`
- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1`
- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`

## 5. Authorized endpoint list

The run called only the following preview-only endpoints:

- ZDoc: `POST /local-trial/preview-only`
- ZBid: `POST /local-llm/zdoc-preview-only/receive`

The following endpoints were not called:

- `/generate`
- `/export_docx`
- `/review/apply`
- Any ZBid writeback endpoint
- Any unknown business endpoint

## 6. Limited human pilot scenario list

Five scenarios were executed:

1. 管理员 / 总控角色预览
2. 技术标编制人员角色预览
3. 复核人员角色预览
4. 评标辅助观察角色预览
5. 异常输入 / 边界输入场景预览

All payloads used desensitized samples, test document identifiers, and non-formal bidding artifacts. No real sensitive business data, DOCX artifact, formal evidence, formal scoring result, or writeback data was included.

## 7. Scenario verification table

| Scenario | Request entry | Payload type | ZDoc HTTP | ZBid HTTP | Outbound sent | ZBid received | preview_only | no_write | no_evidence | blocked_reasons readable | validator_result readable | Forbidden flags | Manual review conclusion | Issues and risks | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 管理员 / 总控角色预览 | `POST /local-trial/preview-only` -> outbound `POST /local-llm/zdoc-preview-only/receive` | `desensitized_admin_control_preview_payload` | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | All false | 可用于总控确认 preview-only/no-write/no-evidence 边界，但不能作为正式审批。 | 需避免将总控预览误认为正式放行。 | No |
| 技术标编制人员角色预览 | `POST /local-trial/preview-only` -> outbound `POST /local-llm/zdoc-preview-only/receive` | `desensitized_technical_writer_preview_payload` | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | All false | 可读，适合编制人员识别需要人工补充的材料。 | 需提示编制人员不得把预览建议粘贴为正式 evidence。 | No |
| 复核人员角色预览 | `POST /local-trial/preview-only` -> outbound `POST /local-llm/zdoc-preview-only/receive` | `desensitized_reviewer_preview_payload` | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | All false | 可用于人工复核流程演练，未产生正式复核结论。 | 需防止复核记录被误用为正式评分依据。 | No |
| 评标辅助观察角色预览 | `POST /local-trial/preview-only` -> outbound `POST /local-llm/zdoc-preview-only/receive` | `desensitized_evaluation_observer_preview_payload` | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | All false | 可用于观察 blocked_reasons 可读性，不构成评分依据。 | 必须明确 preview-only 结果不是 evidence 或评分依据。 | No |
| 异常输入 / 边界输入场景预览 | `POST /local-trial/preview-only` -> outbound `POST /local-llm/zdoc-preview-only/receive` | `desensitized_boundary_input_preview_payload` | 200 | 200 | Yes | Yes | True | True | True | Yes | Yes | All false | 可识别为需人工补齐材料的预览，不需要回退。 | 边界输入应停留在 blocked_reasons 和人工上报，不得 fallback 到正式链。 | No |

## 8. Preview-only / no-write / no-evidence review

All five scenarios passed:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

The result confirms only the limited human pilot preview-only path. It does not authorize formal generation, formal evidence, scoring-basis write, DOCX export, review/apply, ZBid writeback, real business integration, 50-user formal deployment design, or top local model upgrade implementation.

## 9. Required false flags review

Every scenario confirmed the five required false flags:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

No forbidden flag was triggered.

## 10. ZDoc to ZBid send and receive result

For all five scenarios:

- ZDoc preview-only route returned HTTP 200.
- ZDoc outbound adapter attempted network send.
- ZDoc outbound adapter reported `sent_preview_only`.
- ZBid receiver endpoint returned HTTP 200.
- ZBid receiver reported `accepted_preview_only`.
- ZBid receiver accepted the preview-only payload.

This confirms the local preview-only send/receive path for the limited human pilot scenario set.

## 11. Human review flow usability

The limited human pilot flow is usable for controlled preview review:

1. Confirm the scenario is preview-only / no-write / no-evidence.
2. Review `preview_packet`.
3. Review `validator_result`.
4. Review `blocked_reasons`.
5. Confirm all five false flags are false.
6. Record whether the scenario needs human follow-up.
7. Stop if any forbidden flag or unknown endpoint appears.

The flow remains advisory and review-only. It must not be treated as formal approval, formal evidence, or scoring basis.

## 12. Error prompts and blocked_reasons readability

The standard preview-only blocked reasons were readable in the first four role scenarios:

- `missing_evidence_anchor`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

The boundary-input scenario additionally exposed readable missing-input reasons:

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`

The observed error and blocked reason behavior is suitable for limited human pilot review, with one process warning: operators must understand that blocked reasons are prompts for human review and must not be used as evidence or scoring basis.

## 13. Discovered issues

No blocking issue was found in the preview-only ZDoc-ZBid path during this Step 247 run.

Recorded non-blocking observations:

- Human operators need explicit reminder that preview-only output is not formal evidence.
- Human operators need explicit reminder that preview-only output is not scoring basis.
- Boundary-input scenarios should be routed to human review and issue logging, not to formal-chain fallback.
- The pilot remains local and controlled; it does not prove long-running multi-user production capacity.

## 14. Risk level

Current risk level: Medium.

Reason:

- Technical preview-only send/receive passed for five scenarios.
- Safety flags remained false.
- No write path was observed.
- Human misuse remains the main risk: preview-only output may be misunderstood as formal evidence, scoring basis, or approval if training and UI wording are weak.

## 15. Rollback record

No rollback was required for the five scenarios.

Rollback readiness was verified:

- Services were started with temporary process-level environment variables.
- No persistent config was changed.
- No code was modified.
- No tests were modified.
- No frontend/backend files were modified.
- No existing docs were modified.
- Services were stopped after the run.
- Ports were released after shutdown.
- ZDoc and ZBid `git status --short` remained clean before adding this report.

## 16. Service shutdown and port release

Service shutdown results:

- ZDoc PID `45172` was stopped.
- ZBid PID `45187` was stopped.
- ZDoc log showed shutdown completion.
- ZBid log showed shutdown completion.

Port release results:

- `127.0.0.1:18766` had no listener after shutdown.
- `127.0.0.1:18767` had no listener after shutdown.

## 17. output/job/export snapshot

### ZDoc

- Pre-run snapshot: no `output`, `job`, or `export` file entries.
- Post-run snapshot before this report file was added: no `output`, `job`, or `export` file entries.
- Result: no `output/job/export` write observed.

### ZBid

- Pre-run snapshot: no `output`, `job`, or `export` file entries.
- Post-run snapshot: no `output`, `job`, or `export` file entries.
- Result: no `output/job/export` write observed.

## 18. Forbidden action review

The run did not:

- Run Ollama
- Trigger `/generate`
- Trigger `/export_docx`
- Trigger `/review/apply`
- Trigger ZBid writeback
- Generate DOCX
- Write `output/job/export`
- Use preview-only output as evidence
- Use preview-only output as scoring basis
- Write formal business data
- Enter 50-user formal deployment design
- Implement top local model upgrade

## 19. Recommendation on Step 248

Recommendation: enter Step 248 only as a docs-only stage review and authorization-boundary checkpoint.

Step 248 should not automatically start a broader pilot, real business integration, formal-chain opening, DOCX generation, ZBid writeback, 50-user formal deployment design, or model upgrade implementation.

## 20. Step 248 authorization request draft

Proposed next step:

`Step 248: ZDoc-ZBid limited human pilot controlled execution stage review`

Suggested authorization text:

```text
我授权执行 Step 248：ZDoc-ZBid limited human pilot controlled execution stage review。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
[由执行前核验填写]

授权范围：
仅限 docs-only 阶段复盘；
仅允许新增 limited human pilot stage review 文档；
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

文档需归档 Step 247 的五个小范围人工试运行场景、HTTP 结果、preview-only/no-write/no-evidence 结果、五个 false flags、blocked_reasons 可读性、人工复核结论、风险等级、回退记录、服务关闭与端口释放结果，并提出后续授权建议。
```

Step 248 must not begin until the user explicitly authorizes it.
