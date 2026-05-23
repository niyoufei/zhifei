# ZDoc-ZBid 20-user controlled execution stage review and limited human pilot authorization request

## 1. Step 245 execution review

Step 245 completed a controlled local deployment and pilot-run validation for the ZDoc-ZBid preview-only path under the approximately 20-user team口径.

The execution remained inside the authorized boundary:

- Preview-only
- No-write
- No-evidence
- No formal-chain entry
- No DOCX generation
- No `output/job/export` write
- No 50-user formal deployment design
- No top local model upgrade implementation

Step 245 used representative role payloads rather than real 20-user concurrent load testing. The validated representative roles were:

1. 技术标编制
2. 复核
3. 项目负责人
4. 质控审核
5. 备用综合角色

Step 245 started local ZDoc and ZBid services only for the controlled run:

- ZDoc preview-only service: `127.0.0.1:18766`
- ZBid preview-only receiver service: `127.0.0.1:18767`

Step 245 called only preview-only endpoints:

- ZDoc: `POST /local-trial/preview-only`
- ZBid: `POST /local-llm/zdoc-preview-only/receive`

The Step 245 report confirmed:

- ZDoc local preview-only route returned HTTP 200.
- ZBid receiver endpoint returned HTTP 200.
- ZDoc outbound adapter successfully sent preview-only payloads to the ZBid receiver endpoint.
- Five representative role payloads returned HTTP 200.
- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` was readable.
- `validator_result` was readable.
- `blocked_reasons` was readable.
- All five no-write / no-formal-chain flags stayed false.
- ZDoc and ZBid `output/job/export` snapshots had no new entries.
- Services were stopped after the run and the local ports had no listener.

This review document is docs-only. It does not rerun Step 245, does not start services, does not access ports, and does not call endpoints.

## 2. Verified capability list

The following capabilities have been verified through prior controlled steps, with Step 245 as the latest local 20-user口径 representative run:

- ZDoc preview-only local route can support representative pilot-run entry.
- ZDoc preview-only outbound adapter can send preview-only payloads when explicitly enabled by temporary environment variables.
- ZBid preview-only receiver endpoint can accept ZDoc preview-only payloads.
- ZBid receiver returns preview-only / no-write / no-evidence state.
- `preview_packet`, `validator_result`, and `blocked_reasons` are available for review.
- The five no-write / no-formal-chain flags can be checked in the flow:
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- Representative role-based workflow review can be recorded.
- Error prompts and blocked reasons can be captured in a pilot-run report.
- Local service startup and shutdown can be controlled for preview-only validation.
- The run can complete without writing `output/job/export`.

## 3. Unverified capability list

The following items were not verified and must not be treated as completed:

- Real 20-person concurrent load testing.
- Real human users operating the system in an actual pilot session.
- Long-running stability under a full working day.
- Real production data handling.
- Public or LAN deployment exposure.
- Authentication, authorization, and per-user permission enforcement for a human pilot.
- Formal logging infrastructure beyond controlled run log summaries.
- Production observability, alerting, backup, restore, and operations handoff.
- Formal generation chain.
- Formal evidence chain.
- Formal scoring-basis write.
- DOCX export.
- Review/apply.
- ZBid writeback.
- Any top local model upgrade implementation.
- 50-user formal deployment design.

## 4. 20-user pilot host positioning

The Step 245 run used the local machine as a controlled validation host. It proved that the ZDoc-ZBid preview-only path can run locally for representative approximately 20-person team workflows, but it did not prove production hosting capacity.

For the next limited human pilot, the host should be positioned as:

- A controlled internal local pilot host.
- A preview-only / no-write / no-evidence host.
- A temporary validation environment, not a production deployment.
- A host that may run only authorized preview-only ZDoc and ZBid services.
- A host that must not expose formal-chain endpoints for pilot use.
- A host that must not store formal evidence, DOCX output, scoring basis, or writeback data.

The pilot host must not be described as:

- A 50-user production server.
- A formal generation server.
- A formal evidence or scoring server.
- A ZBid writeback server.
- A top local model upgrade target.

## 5. Preview-only / no-write / no-evidence boundary review

The boundary remains unchanged after Step 245:

- `preview_only=true` means the result is for preview and review only.
- `no_write=true` means the run must not write formal business data.
- `no_evidence=true` means preview-only output must not be treated as evidence.

The required false flags remain mandatory:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

The following remain forbidden:

- Calling `/generate`
- Calling `/export_docx`
- Calling `/review/apply`
- Triggering ZBid writeback
- Generating DOCX
- Writing `output/job/export`
- Treating preview-only output as evidence
- Treating preview-only output as scoring basis
- Writing formal business data
- Entering 50-user formal deployment design
- Implementing top local model upgrade

## 6. Discovered issues and risk points

Step 245 did not find a blocking issue in the preview-only ZDoc-ZBid chain.

Step 245 did observe one process risk during calibration:

- Informal status values can be rejected by the outbound adapter.
- The accepted preview-only status vocabulary must remain visible in operator guidance.
- The valid values used for the successful run were:
  - `zbid_input_status=accepted_preview_only`
  - `zbid_mapping_status=mapped_preview_only`
  - `zbid_scoring_matrix_status=preview_only`

This is recorded as a process and guidance risk, not as an authorized code defect fix.

Other risk points for a limited human pilot:

- Human operators may misunderstand preview-only output as formal evidence.
- Human operators may overlook `blocked_reasons`.
- A pilot host may be mistaken for a formal deployment host.
- Logs may include too much detail unless logging scope is controlled.
- Unknown endpoint calls must be blocked by procedure.
- Any required code, UI, logging, permission, or deployment change must be separately authorized.

## 7. Limited human pilot entry criteria

A limited human pilot may be considered only after the user gives explicit Step 247 authorization.

Minimum entry criteria:

- Pilot remains preview-only / no-write / no-evidence.
- Pilot user scope is explicitly named or role-limited.
- Pilot data is limited to desensitized samples, test documents, and non-formal bidding artifacts.
- Pilot host is identified as a controlled internal local host.
- Allowed services are explicitly listed.
- Allowed ports are explicitly listed.
- Allowed endpoints are explicitly listed.
- Temporary environment variables are allowed only for the pilot run and are not written to persistent config.
- `preview_packet`, `validator_result`, `blocked_reasons`, and the five false flags are visible or recordable.
- Stop conditions are agreed before the pilot starts.
- Log and issue-list templates are prepared.
- Rollback steps are clear.

Recommended limited human pilot scope:

- 2 to 5 internal users or equivalent internal roles.
- Roles may include 技术标编制、复核、项目负责人、质控审核.
- No production bidding result is created.
- No formal document is generated.
- No writeback is allowed.

## 8. Limited human pilot prohibitions

The limited human pilot must prohibit:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- DOCX generation
- `output/job/export` writes
- Formal evidence creation
- Formal scoring-basis write
- Writing formal business data
- Treating `preview_packet` as evidence
- Treating `validator_result` as evidence
- Treating `blocked_reasons` as evidence
- Treating preview-only output as scoring basis
- Calling unknown endpoints
- Running Ollama unless separately authorized
- Performing real business联调
- Entering 50-user formal deployment design
- Implementing top local model upgrade
- Fixing failures during the pilot without separate authorization

## 9. Rollback and stop conditions

The limited human pilot must stop immediately if any of the following occur:

- Any no-write / no-formal-chain flag is not false.
- `/generate` is called or required.
- `/export_docx` is called or required.
- `/review/apply` is called or required.
- Any ZBid writeback endpoint is called or required.
- DOCX is generated.
- `output/job/export` is written.
- Preview-only output is used as evidence.
- Preview-only output is used as scoring basis.
- Formal business data is written.
- Unknown endpoint calls appear.
- Persistent config is changed without authorization.
- Services cannot be stopped cleanly.
- Pilot users cannot distinguish preview-only output from formal output.

Rollback requirements:

- Stop services started for the pilot.
- Confirm authorized ports have no listeners.
- Capture `git status --short` for ZDoc and ZBid if both repositories are in scope.
- Capture `output/job/export` snapshots.
- Record the reason for stopping.
- Do not fix in place without separate authorization.

## 10. Log and issue-list requirements

The limited human pilot should record only the minimum useful operational information:

- Time window
- Pilot role or anonymized operator role
- Authorized service and port
- Authorized endpoint
- Preview-only status
- `preview_packet` readability
- `validator_result` readability
- `blocked_reasons` readability
- Five false flags check result
- Error prompt summary
- Human review notes
- Stop-condition result
- Rollback result

The pilot issue list should classify observations as:

- Blocking issue
- Safety-boundary issue
- Usability issue
- Documentation or training issue
- Logging or traceability issue
- Follow-up authorization required

The logs and issue list must not record:

- Sensitive business data
- Formal evidence
- Formal scoring basis
- DOCX output
- Writeback content
- Credentials or secrets

## 11. Step 247 authorization request draft

The next proposed step is:

`Step 247: ZDoc-ZBid limited human pilot controlled execution authorization request`

This Step 247 draft is only an authorization request. It does not grant permission by itself.

Suggested Step 247 authorization text for user review:

```text
我授权执行 Step 247：ZDoc-ZBid limited human pilot controlled execution。

授权仓库：
/Users/youfeini/Desktop/文档生成系统

授权分支：
main

开始前 HEAD：
[由执行前核验填写]

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
[由执行前核验填写]

授权范围：
仅限 2～5 名内部人员或等效角色的小范围人工试运行；
仅限脱敏样例、测试文档、非正式投标成果；
仅限 preview-only / no-write / no-evidence；
允许启动经授权的本地 ZDoc / ZBid preview-only 服务；
允许访问经授权的本地端口；
允许调用经授权的 preview-only endpoint；
允许临时启用 preview-only network-send；
允许记录日志摘要、问题清单、回退记录和试运行报告。

禁止事项：
不得触发 /generate；
不得触发 /export_docx；
不得触发 /review/apply；
不得触发 ZBid 写回；
不得生成 DOCX；
不得写 output/job/export；
不得把 preview-only 结果作为 evidence；
不得把 preview-only 结果作为评分依据；
不得写入正式业务数据；
不得进入 50 人正式部署设计；
不得实施顶级模型升级；
不得现场修复失败项。

如出现任一正式链 flag 非 false、DOCX 生成、output/job/export 写入、ZBid 写回、unknown endpoint 调用或 preview-only 输出被误用为 evidence / 评分依据，必须立即停止并记录。
```

Step 247 must not begin until the user explicitly authorizes it.

## 12. Current step closure

This Step 246 document is docs-only. It performs stage review and prepares a limited human pilot authorization request draft.

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
