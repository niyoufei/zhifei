# ZDoc-ZBid 20-user pilot acceptance review and operation baseline archive

## 1. Step 245 to Step 249 stage summary

This document archives the current ZDoc-ZBid 20-user pilot acceptance review and operation baseline. It is docs-only and does not open any formal chain.

Stage summary:

- Step 245 completed a local 20-user口径 deployment and pilot-run controlled execution.
- Step 246 archived the Step 245 stage review and drafted the limited human pilot authorization request.
- Step 247 completed a limited human pilot controlled execution with five role scenarios.
- Step 248 archived pilot readiness and drafted the 20-user expanded pilot authorization request.
- Step 249 completed a 20-user expanded pilot controlled execution with 20 preview-only requests.

The verified flow remains:

- ZDoc preview-only route
- ZDoc outbound adapter with temporary preview-only network-send enablement
- ZBid preview-only receiver endpoint
- Human review of `preview_packet`, `validator_result`, `blocked_reasons`, and five false flags

The verified flow does not include formal generation, DOCX export, review/apply, ZBid writeback, formal evidence, scoring-basis write, real production operation, 50-user formal deployment design, or top local model upgrade implementation.

## 2. 20-user expanded pilot acceptance conclusion

Current acceptance conclusion: accepted as a controlled 20-user preview-only pilot baseline.

Acceptance basis:

- Step 249 executed 20 total requests.
- Step 249 covered 10 role/scenario categories.
- Step 249 included 6 boundary or exception input scenarios.
- ZDoc HTTP result: 20 / 20 returned 200.
- ZBid receiver HTTP result: 20 / 20 returned 200.
- ZDoc outbound adapter sent 20 / 20 preview-only payloads.
- ZBid receiver accepted 20 / 20 preview-only payloads.
- `preview_only=true` held for all requests.
- `no_write=true` held for all requests.
- `no_evidence=true` held for all requests.
- Five no-write / no-formal-chain false flags remained false for all requests.
- No DOCX was generated.
- No `output/job/export` write was observed.
- No `/generate`, `/export_docx`, `/review/apply`, or ZBid writeback was triggered.
- Services were closed and ports were released after the run.

This acceptance is limited to a preview-only 20-user pilot baseline. It is not production acceptance.

## 3. Verified capability list

The following capabilities are verified for the current pilot baseline:

- ZDoc preview-only route can run locally for pilot validation.
- ZBid preview-only receiver endpoint can run locally for pilot validation.
- ZDoc outbound adapter can send preview-only payloads to ZBid when explicitly enabled by temporary environment variables.
- ZBid receiver can accept preview-only payloads.
- `preview_packet` is readable for human review.
- `validator_result` is readable for human review.
- `blocked_reasons` is readable for human review.
- Boundary and exception inputs remain preview-only and no-write.
- The required five false flags are visible and remain false:
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- Controlled batches of 5 concurrent preview-only requests completed without runtime exception in Step 249.
- Role/scenario reporting can be archived in docs.
- Services can be stopped and ports can be released after the run.

## 4. Unverified capability list

The following capabilities remain unverified and must not be treated as complete:

- Real production operation.
- Real business联调.
- Formal generation chain.
- Formal evidence chain.
- Formal scoring-basis write.
- DOCX export.
- Review/apply.
- ZBid writeback.
- Real named-user permission and audit workflow.
- Long-running full-day stability.
- Formal capacity or stress testing.
- 50-user formal deployment design.
- Top local model upgrade implementation.
- Backup, restore, monitoring, alerting, and operations handoff for production.
- Network exposure beyond the controlled local pilot host.

## 5. Conditions for using this as a 20-user pilot baseline

This baseline may be used only if all conditions below remain true:

- The operating mode remains preview-only / no-write / no-evidence.
- Data is limited to desensitized samples, test documents, and non-formal bidding artifacts.
- The host is a controlled local pilot host.
- Services are started only when authorized.
- Ports are accessed only when authorized.
- Endpoints are limited to preview-only endpoints.
- Preview-only network-send is enabled only with temporary environment variables.
- Logs and reports avoid sensitive business data.
- Operators review `preview_packet`, `validator_result`, and `blocked_reasons`.
- Operators confirm all five false flags remain false.
- A stop condition and rollback procedure are available before every run.
- Every run produces a pilot record or issue list.

## 6. Not a formal production server

The current host and baseline must not be described as a formal production server.

It is not:

- A long-term production server.
- A 50-user formal deployment server.
- A formal generation server.
- A formal evidence server.
- A scoring-basis write server.
- A DOCX export server.
- A review/apply server.
- A ZBid writeback server.
- A top local model upgrade host.

It is only a controlled local pilot baseline for preview-only / no-write / no-evidence operation.

## 7. Long-running boundary for preview-only / no-write / no-evidence

Any normal pilot operation must preserve:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

The pilot must keep these five flags false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

These flags are operational guard signals. They are not formal evidence and must not be used as scoring basis.

## 8. Forbidden interface, write, evidence, and scoring requirements

The following remain forbidden:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- DOCX generation
- `output/job/export` write
- Formal evidence creation
- Formal scoring-basis write
- Writing formal business data
- Treating preview-only output as evidence
- Treating preview-only output as scoring basis
- Unknown business endpoints
- Formal-chain fallback

If any forbidden interface or write appears, the run must stop immediately.

## 9. 20-user pilot roles and usage rules

Recommended pilot role groups:

| Role group | Usage rule |
| --- | --- |
| 总控管理员 | Confirms pilot boundary, service start/stop, logs, issue list, and rollback record. |
| 技术标主编 | Reviews preview-only drafting suggestions and blocked reasons. |
| 施工方案编制人员 | Reviews construction-plan preview prompts without generating formal output. |
| 进度计划编制人员 | Reviews schedule preview prompts without creating formal schedule basis. |
| 质量安全复核人员 | Reviews validator_result and confirms no evidence / no scoring-basis write. |
| 商务 / 清单协同人员 | Reviews preview-only commercial notes without writing formal business data. |
| 项目资料整理人员 | Uses blocked reasons to identify missing data without uploading formal evidence. |
| ZBid 评标辅助观察人员 | Observes receiver behavior without scoring, evidence, or writeback authority. |
| 普通试用人员 | Reviews usability and clarity under supervised preview-only constraints. |
| 异常输入 / 边界输入场景 | Confirms boundary prompts remain readable and do not trigger formal fallback. |

Usage rules:

- All users must be told the pilot is preview-only.
- No user may treat output as evidence.
- No user may treat output as scoring basis.
- No user may export DOCX.
- No user may request writeback.
- Every issue must be logged as a pilot observation, not fixed in place unless separately authorized.

## 10. Host operation boundary

Host boundary:

- Use only authorized local services.
- Use only authorized local ports.
- Use only authorized preview-only endpoints.
- Use temporary environment variables only.
- Do not write persistent config.
- Do not expose as a long-term production endpoint.

Recommended known ports from prior runs:

- ZDoc: `127.0.0.1:18766`
- ZBid: `127.0.0.1:18767`

Service lifecycle:

1. Confirm repo status and baseline.
2. Confirm output snapshots.
3. Start authorized services.
4. Record PID and port.
5. Execute authorized preview-only pilot scenarios.
6. Stop services.
7. Confirm ports have no listener.
8. Confirm output snapshots remain clean.
9. Record issue list and rollback result.

Log boundary:

- Record endpoint names, status codes, scenario IDs, role groups, and stop-condition result.
- Do not record sensitive business data.
- Do not record credentials or secrets.
- Do not record formal evidence or scoring basis.

## 11. Concurrency and stability observation conclusion

Step 249 observed:

- 4 controlled batches.
- 5 concurrent requests per batch.
- 20 total preview-only requests.
- All 20 completed with ZDoc HTTP 200.
- All 20 completed with ZBid HTTP 200.
- No runtime exception was observed in the controlled runner.
- ZDoc route latency: min `1.08 ms`, median `2.16 ms`, max `176.51 ms`.
- Outbound-to-ZBid latency: min `1.93 ms`, median `3.41 ms`, max `11.63 ms`.

Conclusion:

- Local response stability was acceptable for a controlled preview-only 20-user pilot baseline.
- This is not a formal capacity benchmark.
- This is not 50-user production readiness.
- Longer duration and real named-user usage remain unverified.

## 12. Risk list and graded handling

### High risk

- Any formal-chain endpoint is called.
- Any DOCX is generated.
- Any `output/job/export` write appears.
- Any ZBid writeback appears.
- Any preview-only result is used as evidence or scoring basis.

Handling: stop immediately, record evidence, close services, and require separate authorization before any fix.

### Medium risk

- Users misunderstand HTTP 200 as formal approval.
- Users overlook `blocked_reasons`.
- Logs contain sensitive business data.
- Boundary input is handled as a normal successful business result.
- Pilot host is mistaken for a production server.

Handling: stop affected scenario if needed, log issue, update training/docs only after authorization.

### Low risk

- Role labels need refinement.
- Report template fields need clearer wording.
- Operator checklist needs formatting improvement.

Handling: record as observation and request a separate docs-only or UI-copy authorization if needed.

## 13. Rollback conditions

Rollback is required if:

- Any required false flag is not false.
- `/generate` is called or required.
- `/export_docx` is called or required.
- `/review/apply` is called or required.
- ZBid writeback is called or required.
- DOCX is generated.
- `output/job/export` is written.
- Preview-only output is used as evidence.
- Preview-only output is used as scoring basis.
- Formal business data is written.
- Unknown endpoint calls appear.
- Services cannot be stopped cleanly.
- Authorized ports remain listening after shutdown.
- Persistent config changes are detected.

Rollback procedure:

1. Stop the current pilot activity.
2. Stop services started for the pilot.
3. Confirm authorized ports have no listener.
4. Capture repo `git status --short`.
5. Capture `output/job/export` snapshots.
6. Record the failed scenario and stop reason.
7. Do not fix in place without separate authorization.

## 14. Normal pilot record template

Use this template for every normal pilot run:

```text
Pilot run ID:
Date/time:
Operator role:
Host:
ZDoc branch / HEAD:
ZBid branch / HEAD:
Authorized services:
Authorized ports:
Authorized endpoints:
Scenario count:
Role coverage:
Boundary input count:

For each scenario:
- Scenario no:
- Role type:
- Payload type:
- Request entry:
- ZDoc HTTP status:
- ZBid HTTP status:
- ZDoc outbound sent:
- ZBid receiver accepted:
- preview_only:
- no_write:
- no_evidence:
- generate_called:
- export_docx_called:
- review_apply_called:
- zbid_writeback_called:
- output_job_export_written:
- preview_packet readable:
- validator_result readable:
- blocked_reasons readable:
- Human review conclusion:
- Issue/risk:
- Rollback required:

Forbidden action review:
- /generate triggered:
- /export_docx triggered:
- /review/apply triggered:
- ZBid writeback triggered:
- DOCX generated:
- output/job/export written:
- Preview used as evidence:
- Preview used as scoring basis:

Shutdown:
- Services stopped:
- Ports released:
- Output snapshot clean:
- Git status clean:

Overall conclusion:
Next authorization needed:
```

## 15. Step 251 normal pilot authorization request draft

Proposed next step:

`Step 251: ZDoc-ZBid 20-user normal pilot operation authorization request`

This draft does not grant authorization. Step 251 may begin only after the user explicitly authorizes it.

Suggested authorization text:

```text
我授权执行 Step 251：ZDoc-ZBid 20-user normal pilot operation authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
[由执行前核验填写]

授权范围：
仅限 docs-only 起草 20-user normal pilot operation 授权请求；
不得修改代码、tests、frontend、backend 或既有 docs；
不得启动服务；
不得运行 Ollama；
不得访问端口；
不得调用 endpoint；
不得触发 /generate、/export_docx、/review/apply；
不得触发 ZBid 写回；
不得生成 DOCX；
不得写 output/job/export；
不得把 preview-only 结果作为 evidence；
不得把 preview-only 结果作为评分依据；
不得进入 50 人正式部署设计；
不得实施顶级模型升级。

授权请求文档需明确：20 人常态试运行仍只允许 preview-only / no-write / no-evidence；允许项、禁止项、服务与端口边界、日志和问题清单模板、回退条件、停止条件，以及后续真正执行常态试运行必须另行授权。
```

## 16. Current Step 250 closure

This Step 250 document is docs-only.

This step did not:

- Modify code
- Modify tests
- Modify frontend
- Modify backend
- Modify existing docs
- Start services
- Run Ollama
- Access ports
- Call endpoints
- Trigger `/generate`
- Trigger `/export_docx`
- Trigger `/review/apply`
- Trigger ZBid writeback
- Generate DOCX
- Write `output/job/export`
- Treat preview-only output as evidence
- Treat preview-only output as scoring basis
- Enter 50-user formal deployment design
- Implement top local model upgrade
- Enter Step 251
