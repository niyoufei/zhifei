# ZDoc-ZBid 20-user pilot readiness review and expanded pilot authorization request

## 1. Step 247 limited human pilot review

Step 247 completed a limited human pilot controlled execution for the ZDoc-ZBid preview-only path.

The Step 247 execution covered five scenarios:

1. 管理员 / 总控角色预览
2. 技术标编制人员角色预览
3. 复核人员角色预览
4. 评标辅助观察角色预览
5. 异常输入 / 边界输入场景预览

Step 247 verified:

- ZDoc preview-only route returned HTTP 200 for all five scenarios.
- ZDoc outbound adapter sent preview-only payloads for all five scenarios.
- ZBid receiver endpoint returned HTTP 200 for all five scenarios.
- ZBid receiver accepted all five preview-only payloads.
- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` was readable.
- `validator_result` was readable.
- `blocked_reasons` was readable.
- The five required no-write / no-formal-chain flags remained false:
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- No DOCX was generated.
- No `output/job/export` write was observed.
- No `/generate`, `/export_docx`, `/review/apply`, or ZBid writeback was triggered.
- Services were stopped after the run and ports were released.

Step 247 did not verify real production usage, real business联调, formal-chain opening, long-running stability, real 20-user concurrency, 50-user formal deployment design, or top local model upgrade implementation.

## 2. 20-user expanded pilot entry conclusion

Current conclusion: ZDoc-ZBid is conditionally ready to request authorization for a controlled 20-user expanded pilot.

The condition is strict:

- The expanded pilot must remain preview-only / no-write / no-evidence.
- It must use desensitized samples, test documents, and non-formal bidding artifacts.
- It must not be treated as production rollout.
- It must not open formal generation, DOCX export, review/apply, ZBid writeback, formal evidence, scoring-basis write, or `output/job/export` write.
- It must not enter 50-user formal deployment design.
- It must not implement top local model upgrade.

The Step 247 evidence supports a next authorization request for a wider controlled pilot. It does not authorize the expanded pilot by itself.

## 3. Prerequisites for entering a 20-user pilot

Before a 20-user pilot starts, the following must be explicitly confirmed:

- Pilot user scope: internal users only, approximately 20-person team or controlled role group.
- Role list: names or role groups must be defined before execution.
- Data scope: desensitized samples, test documents, and non-formal bidding artifacts only.
- Host scope: one controlled local pilot host, not a long-term production server.
- Service scope: only authorized ZDoc preview-only service and ZBid preview-only receiver service.
- Port scope: only explicitly authorized local ports.
- Endpoint scope: only explicitly authorized preview-only endpoints.
- Temporary environment variables: allowed only for the pilot session and not written to persistent config.
- Logging scope: log summaries and issue lists only, without sensitive business data.
- Rollback plan: service stop, port release, status check, output snapshot check, and issue recording.
- Stop conditions: agreed before the pilot begins.
- Human review guide: preview-only / no-write / no-evidence reminders must be available.

## 4. Items not currently allowed

The following remain not allowed:

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
- Real business联调
- Production deployment
- 50-user formal deployment design
- Top local model upgrade implementation
- In-place code fixes during a pilot without separate authorization

## 5. Suggested 20-user pilot role split

For a controlled 20-user pilot, the recommended role grouping is:

| Role group | Suggested count | Purpose |
| --- | ---: | --- |
| 管理员 / 总控 | 1-2 | Coordinate pilot scope, confirm stop conditions, verify logs and rollback record. |
| 技术标编制 | 6-8 | Review preview-only packet usability and blocked_reasons in drafting scenarios. |
| 复核人员 | 4-5 | Check validator_result, false flags, and manual review flow. |
| 项目负责人 | 2-3 | Review project-level readability and decision boundaries. |
| 质控审核 | 2-3 | Verify no evidence, no scoring-basis write, and no formal-chain misuse. |
| 评标辅助观察 | 1-2 | Observe preview-only receiver behavior without scoring or writeback authority. |

The role split may be adjusted by the user before Step 249, but every participant must remain inside preview-only / no-write / no-evidence boundaries.

## 6. 20-user pilot operation boundary

Allowed operation boundary for a future Step 249 expanded pilot should be limited to:

- Starting authorized local ZDoc preview-only service.
- Starting authorized local ZBid preview-only receiver service.
- Accessing authorized local ports.
- Calling authorized preview-only endpoints.
- Temporarily enabling preview-only network-send.
- Recording log summaries, issue lists, rollback records, and pilot report.
- Reviewing `preview_packet`, `validator_result`, `blocked_reasons`, and the five false flags.

The pilot must not:

- Call unknown business endpoints.
- Fall back to formal endpoints.
- Write persistent config.
- Modify code.
- Modify tests.
- Modify frontend/backend files.
- Modify existing docs.
- Generate formal documents.
- Write formal business data.

## 7. Preview-only / no-write / no-evidence review requirements

Each pilot scenario must verify:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` readable
- `validator_result` readable
- `blocked_reasons` readable

Each pilot scenario must also record the human review conclusion:

- Whether the output was understandable.
- Whether `blocked_reasons` were actionable as review prompts.
- Whether any operator could confuse preview-only output with formal evidence.
- Whether any scenario needs follow-up documentation or separate optimization authorization.

## 8. Forbidden endpoint and write review requirements

Each pilot run must confirm:

- `/generate` was not called.
- `/export_docx` was not called.
- `/review/apply` was not called.
- ZBid writeback was not called.
- DOCX was not generated.
- `output/job/export` was not written.
- Preview-only result was not treated as evidence.
- Preview-only result was not treated as scoring basis.
- Formal business data was not written.

The five required flags must remain false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

Any non-false value is a stop condition.

## 9. Log, issue list, and rollback record requirements

The expanded pilot must record:

- Pilot date and time window.
- Host identifier or local host note.
- Authorized services and ports.
- Authorized endpoints.
- Role group for each scenario.
- Payload type.
- HTTP status.
- `preview_only / no_write / no_evidence` result.
- Five false flags result.
- `preview_packet / validator_result / blocked_reasons` readability.
- Human review conclusion.
- Issue list entry, if any.
- Stop-condition check.
- Rollback record.

Logs and reports must not include:

- Sensitive business data.
- Credentials or secrets.
- Formal evidence.
- Formal scoring basis.
- DOCX output.
- Writeback payloads.

Issue list categories:

- Blocking issue
- Safety-boundary issue
- Usability issue
- Documentation/training issue
- Logging/traceability issue
- Separate authorization required

## 10. Concurrency, ports, service startup, and shutdown notes

The next expanded pilot should not be treated as formal load testing unless separately authorized.

Operational notes:

- Use known validated local ports if available.
- If a port is occupied, choose an adjacent free local port and record the reason.
- Start services with `PYTHONDONTWRITEBYTECODE=1` where practical.
- Use temporary environment variables only.
- Do not write `.env`, config files, or persistent service definitions.
- Do not expose the pilot service as a long-term production endpoint.
- Keep a service PID record.
- Stop all services after the pilot.
- Confirm all authorized ports have no listener after shutdown.
- Capture `git status --short` and output snapshots before and after the pilot.

Concurrency note:

- The recommended Step 249 expanded pilot may involve approximately 20 internal users or role representatives.
- It should verify practical workflow readiness and operator behavior.
- It should not be represented as a formal stress test, capacity benchmark, or 50-user production readiness test.

## 11. Host positioning

The pilot host is only a 20-user pilot host.

It is not:

- A long-term production server.
- A 50-user formal deployment server.
- A formal generation server.
- A formal evidence server.
- A scoring-basis write server.
- A DOCX export server.
- A ZBid writeback server.
- A top local model upgrade host.

The host may be used only to validate preview-only / no-write / no-evidence flows under explicit authorization.

## 12. 20-user pilot risk list

Current risk list:

- Human users may treat preview-only results as formal evidence.
- Human users may treat preview-only results as scoring basis.
- Operators may ignore or misunderstand `blocked_reasons`.
- Operators may assume HTTP 200 means formal approval.
- Local host stability under real multi-user behavior is still unverified.
- Permission boundaries for real named users are not yet validated.
- Logs may accidentally capture sensitive data if logging scope is not controlled.
- Port conflicts may occur and must be recorded.
- Any failed scenario must not be fixed in place without separate authorization.
- A successful 20-user pilot must not be reinterpreted as 50-user production readiness.

Risk level: Medium.

Rationale:

- Preview-only technical path has passed controlled checks.
- Human-process and operational risks remain material.
- Formal-chain boundaries remain closed.

## 13. Rollback conditions

The expanded pilot must stop immediately if any of the following occur:

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
- Persistent config is changed.
- Services cannot be stopped cleanly.
- Authorized ports remain listening after shutdown.
- Users cannot distinguish preview-only output from formal output.

Rollback actions:

- Stop services started for the pilot.
- Confirm authorized ports have no listener.
- Record the failing scenario and reason.
- Capture ZDoc and ZBid status if both repositories are in scope.
- Capture output snapshots.
- Preserve the report and issue list.
- Do not fix in place without separate authorization.

## 14. Step 249 authorization request draft

Proposed next step:

`Step 249: ZDoc-ZBid 20-user expanded pilot controlled execution`

This draft does not grant authorization. Step 249 may begin only after the user explicitly authorizes it.

Suggested authorization text:

```text
我授权执行 Step 249：ZDoc-ZBid 20-user expanded pilot controlled execution。

ZDoc 仓库：
/Users/youfeini/Desktop/文档生成系统

ZDoc 分支：
main

ZDoc 开始前 HEAD：
[由执行前核验填写]

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
[由执行前核验填写]

授权范围：
允许在约 20 人内部受控角色范围内执行 expanded pilot；
允许启动必要的 ZDoc 本地 preview-only 服务；
允许启动必要的 ZBid 本地 preview-only receiver 服务；
允许访问明确授权的本地端口；
允许调用明确授权的 preview-only endpoint；
允许临时启用 preview-only network-send；
允许记录日志摘要、问题清单、回退记录和 expanded pilot report。

严格边界：
仅限 preview-only / no-write / no-evidence；
不得修改代码、tests、frontend、backend 或既有 docs；
不得运行 Ollama；
不得触发 /generate、/export_docx、/review/apply；
不得触发 ZBid 写回；
不得生成 DOCX；
不得写 output/job/export；
不得把 preview-only 结果作为 evidence；
不得把 preview-only 结果作为评分依据；
不得写入正式业务数据；
不得进入 50 人正式部署设计；
不得实施顶级模型升级；
不得现场修复失败项。

停止条件：
任一 false flag 非 false、出现 DOCX、出现 output/job/export 写入、出现 ZBid 写回、出现 unknown endpoint、preview-only 输出被误用为 evidence 或评分依据时，必须立即停止并记录。
```

## 15. Current Step 248 closure

This Step 248 document is docs-only.

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
- Enter Step 249
