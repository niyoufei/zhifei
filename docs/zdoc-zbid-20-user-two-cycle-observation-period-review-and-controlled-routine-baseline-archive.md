# ZDoc-ZBid 20-user two-cycle observation-period review and controlled routine baseline archive

## 1. Step 257 and Step 259 observation-period recap

This document archives the two-cycle controlled routine observation-period baseline for the ZDoc-ZBid 20-user pilot path.

Covered cycles:

- Step 257: first controlled routine observation-period execution.
- Step 259: second controlled routine observation-period execution.

Both cycles were executed within the same boundary:

- preview-only
- no-write
- no-evidence
- no formal generation chain
- no formal evidence chain
- no formal scoring chain
- no DOCX export chain
- no review/apply chain
- no ZBid writeback chain
- no `output/job/export` write

This archive does not authorize Step 261. It does not authorize formal deployment design, formal production operation, evidence use, scoring use, DOCX generation, writeback, or top local model upgrade work.

## 2. Two-cycle result summary

Two-cycle effective observation-period total:

- Effective requests: 110.
- Batches: 11.
- Simulated users: 20.
- Role / scenario categories: 11.
- Abnormal / boundary effective requests: 30.

Cycle breakdown:

| Cycle | Effective requests | Batches | Simulated users | Role / scenario categories | Abnormal / boundary effective requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| Step 257 | 50 | 5 | 20 | 11 | 12 |
| Step 259 | 60 | 6 | 20 | 11 | 18 |
| Total | 110 | 11 | 20 | 11 | 30 |

The two-cycle result supports continued controlled routine pilot observation under preview-only / no-write / no-evidence boundaries. It does not prove production readiness and does not open formal chains.

## 3. Preflight payload calibration total

Preflight payload calibration was tracked separately from effective observation-period calls.

Calibration total:

- Step 257 preflight payload calibration: 50.
- Step 259 preflight payload calibration: 8.
- Two-cycle preflight payload calibration total: 58.

Calibration handling:

- Calibration requests were used to check boundary behavior before or around effective observation-period execution.
- Calibration requests are not counted as effective ZBid observation-period calls.
- Calibration requests are not counted in the 110 effective request total.
- Calibration requests do not represent successful ZBid receiver business usage.
- Calibration requests do not authorize writeback, evidence, scoring basis, DOCX, or formal business data writes.

## 4. Preview-only boundary blocking archive

Preflight payload calibration and illegal ZBid status enum checks were blocked by the preview-only boundary before they could become effective ZBid receiver observation calls.

Archived blocking conclusion:

- Invalid ZBid status enum payloads were blocked by the ZDoc outbound adapter.
- Blocked payloads were not sent to the ZBid receiver as effective observation-period calls.
- Blocked payloads did not fallback to formal endpoints.
- Blocked payloads did not trigger `/generate`.
- Blocked payloads did not trigger `/export_docx`.
- Blocked payloads did not trigger `/review/apply`.
- Blocked payloads did not trigger ZBid writeback.
- Blocked payloads did not generate DOCX.
- Blocked payloads did not write `output/job/export`.
- Blocked payloads did not create evidence.
- Blocked payloads did not create scoring basis.

Representative blocked reasons from the second-cycle calibration included:

- `invalid_zbid_input_status`
- `invalid_zbid_mapping_status`
- `invalid_zbid_scoring_matrix_status`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

## 5. Calibration exclusion from effective ZBid calls

The 58 preflight calibration requests must remain separate from effective observation-period records.

Effective-call rule:

- Only preview-only payloads actually sent by ZDoc outbound and accepted by ZBid receiver count as effective ZBid observation-period calls.
- Preflight calibration requests blocked before network-send do not count as effective ZBid calls.
- Invalid enum payloads blocked by the adapter do not count as effective ZBid calls.
- Blocked calibration results must be archived as boundary proof only, not as ZBid observation throughput.

Therefore:

- Effective observation-period total: 110.
- Preflight calibration total: 58.
- Effective ZBid calls from calibration: 0.

## 6. HTTP 200 result summary

Effective observation-period HTTP result:

| Cycle | ZDoc preview-only entry | ZBid preview-only receiver | Non-200 effective responses |
| --- | --- | --- | ---: |
| Step 257 | 50/50 HTTP 200 | 50/50 HTTP 200 | 0 |
| Step 259 | 60/60 HTTP 200 | 60/60 HTTP 200 | 0 |
| Total | 110/110 HTTP 200 | 110/110 HTTP 200 | 0 |

Calibration result:

- Step 257 calibration requests: 50, separately recorded.
- Step 259 calibration requests: 8, separately recorded.
- Calibration requests are excluded from the 110 effective observation-period count.

## 7. Preview-only / no-write / no-evidence conclusion

Across Step 257 and Step 259:

- `preview_only=true`: confirmed for all 110 effective observation-period requests.
- `no_write=true`: confirmed for all 110 effective observation-period requests.
- `no_evidence=true`: confirmed for all 110 effective observation-period requests.

Boundary meaning:

- Results are advisory preview-only results.
- Results are not evidence.
- Results are not scoring basis.
- Results are not formal business data.
- Results are not writeback authorization.

## 8. Five prohibited flags conclusion

Across Step 257 and Step 259, the five no-write / no-formal-chain flags remained false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

If any of these flags becomes non-false in a future run, the pilot must stop immediately and the result must be recorded as a boundary violation candidate. No live repair may be performed without separate authorization.

## 9. Consistency with Step 256 and Step 258 baselines

The two observation-period cycles are consistent with the prior controlled routine baselines:

- Step 256 three-cycle stable pilot baseline required long-term preview-only / no-write / no-evidence operation and prohibited formal chains.
- Step 258 controlled routine baseline update required calibration separation, invalid enum blocking, and continued no-write boundary proof.
- Step 257 and Step 259 both preserved effective request isolation from calibration records.
- Step 257 and Step 259 both kept all effective requests in the preview-only / no-write / no-evidence lane.
- Step 257 and Step 259 both avoided formal generation, evidence, scoring, export, review/apply, writeback, DOCX, and `output/job/export`.

Consistency conclusion:

- The two-cycle observation-period result remains aligned with Step 256 and Step 258.
- No evidence shows baseline drift.

## 10. Regression conclusion

No regression was observed between Step 257 and Step 259.

Comparison summary:

- Effective request count increased from 50 to 60.
- Batch count increased from 5 to 6.
- Simulated user coverage stayed at 20.
- Role / scenario coverage stayed at 11 categories.
- Abnormal / boundary effective request coverage increased from 12 to 18.
- HTTP 200 result remained stable.
- `preview_only=true`, `no_write=true`, and `no_evidence=true` remained stable.
- Five prohibited flags remained false.
- No DOCX generation, writeback, evidence, scoring basis, or `output/job/export` write appeared.

Regression conclusion: none observed.

## 11. Verified capability list

The two-cycle observation period verified the following capabilities within controlled local pilot conditions:

- ZDoc preview-only entry can serve controlled pilot preview requests.
- ZDoc outbound adapter can send preview-only payloads to ZBid receiver.
- ZBid receiver can accept preview-only payloads.
- `preview_packet` remains readable.
- `validator_result` remains readable.
- `blocked_reasons` remains readable.
- 20 simulated users can be represented in controlled observation-period records.
- 11 role / scenario categories can be covered.
- Abnormal / boundary inputs can remain inside preview-only / no-write / no-evidence handling.
- Illegal ZBid status enum calibration can be blocked before effective ZBid receiver calls.
- No formal-chain fallback was observed.
- Service shutdown and port release were verified in execution reports.

## 12. Unverified capability list

The following capabilities remain unverified and must not be inferred from the two-cycle observation-period result:

- Formal production readiness.
- Long-term production server operation.
- 50-user formal deployment readiness.
- Real concurrent production load capacity.
- Formal `/generate` chain.
- Formal `/export_docx` chain.
- Formal `/review/apply` chain.
- ZBid writeback.
- Formal evidence creation.
- Formal scoring-basis write.
- DOCX generation.
- `output/job/export` write.
- Real sensitive business data handling.
- Top local model upgrade implementation.

## 13. Findings and observation items

Blocking findings:

- None observed in the two-cycle effective observation-period result.

High-risk findings:

- None observed.

Medium-risk findings:

- None observed.

Low-risk findings:

- None observed.

Observation items:

- Continue separating preflight calibration from effective observation-period records.
- Continue checking illegal ZBid status enum blocking.
- Continue checking blocked reason readability.
- Continue documenting whether abnormal / boundary inputs remain preview-only.
- Continue verifying service shutdown and port release after controlled runs.
- Continue stating that preview-only results must not become evidence or scoring basis.

## 14. Issue severity classification

| Severity | Current status | Required handling |
| --- | --- | --- |
| Blocking | None observed | Continue controlled observation only. |
| High risk | None observed | Keep formal-chain prohibition active. |
| Medium risk | None observed | Continue baseline checks and records. |
| Low risk | None observed | Continue routine observation and documentation. |
| Observation item | Present | Track in logs and reports; do not treat as authorized code/UI/logging change. |

Any future issue that touches writeback, evidence, scoring basis, DOCX, `output/job/export`, unknown endpoint calls, or formal-chain fallback must be escalated as a stop condition.

## 15. 20-user controlled routine observation-period conclusion

The 20-user controlled routine observation-period stage has completed two effective observation cycles:

- Step 257 first observation period.
- Step 259 second observation period.

Stage conclusion:

- The preview-only / no-write / no-evidence path remained stable across 110 effective requests.
- No formal-chain trigger was observed.
- No regression was observed from first cycle to second cycle.
- The host may continue to be treated only as a controlled 20-user pilot host.
- The host must not be treated as a long-term formal production server.
- The result does not authorize 50-user formal deployment design.

## 16. Conditions for continuing controlled routine pilot

Controlled routine pilot may continue only if all conditions remain true:

- Explicit user authorization exists for the next execution step.
- The next step defines repository, branch, start HEAD, allowed files, allowed endpoints, and stop conditions.
- Preview-only / no-write / no-evidence boundary remains active.
- Five prohibited flags remain false.
- Calibration remains separated from effective observation-period calls.
- Invalid enum and boundary-risk payloads remain blocked or marked without formal fallback.
- `output/job/export` remains unwritten unless separately authorized.
- DOCX generation remains disabled.
- ZBid writeback remains disabled.
- Logs and issue lists avoid sensitive business data, evidence, and scoring-basis content.

## 17. Mandatory pilot pause triggers

The pilot must pause immediately if any condition below occurs:

- `generate_called` becomes non-false.
- `export_docx_called` becomes non-false.
- `review_apply_called` becomes non-false.
- `zbid_writeback_called` becomes non-false.
- `output_job_export_written` becomes non-false.
- `/generate` is called.
- `/export_docx` is called.
- `/review/apply` is called.
- Any ZBid writeback endpoint is called.
- DOCX is generated.
- `output/job/export` is written.
- Preview-only result is treated as evidence.
- Preview-only result is treated as scoring basis.
- Formal business data is written.
- Unknown endpoint calls appear.
- Fallback to formal chain appears.

No live repair is authorized by this archive. Any repair or optimization must be separately authorized.

## 18. Rollback conditions

Rollback or run termination must be recorded when:

- A formal-chain endpoint is triggered.
- A writeback path is triggered.
- A DOCX file is generated.
- `output/job/export` receives a new write.
- Evidence or scoring-basis write occurs.
- Preview-only boundary indicators are missing.
- Service cannot be safely stopped.
- A port remains listening after shutdown.
- A next run cannot prove branch, HEAD, and clean working tree.

Rollback record requirements:

- Time of detection.
- Scenario or batch identifier.
- User or simulated user identifier.
- Endpoint involved.
- Flags observed.
- Output path snapshot.
- Service shutdown result.
- Decision: stop, rollback, or require separate authorization.

## 19. Long-term preview-only / no-write / no-evidence boundary

The long-term controlled routine pilot boundary remains:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

This boundary must remain visible in every pilot report, stage review, authorization request, and baseline archive.

## 20. Prohibited interface, write, evidence, and scoring requirements

The following remain prohibited unless separately authorized in a future step:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- DOCX generation
- `output/job/export` write
- Formal evidence creation
- Formal scoring-basis write
- Preview-only result as evidence
- Preview-only result as scoring basis
- Formal business data write
- Unknown endpoint calls
- Unapproved service startup
- Unapproved port access
- Unapproved endpoint calls

## 21. Host positioning

The current host must be treated only as a 20-user controlled pilot host.

It must not be treated as:

- a long-term formal production server;
- a 50-user formal deployment host;
- a formal generation host;
- a formal evidence host;
- a formal scoring-basis write host;
- a DOCX production host;
- a ZBid writeback host;
- a top local model upgrade target.

Before any production positioning, a separate deployment design, operational model, capacity assessment, rollback plan, permission boundary, logging strategy, and data-handling plan must be authorized.

## 22. Draft Step 261 authorization request

Suggested Step 261 authorization wording:

```text
执行 Step 261：ZDoc-ZBid 20-user controlled routine observation-period third-cycle authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填入 Step 260 完成后的实际 HEAD>

本步性质：
docs-only / authorization-request-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
基于 Step 257 与 Step 259 两轮观察期结果，以及 Step 260 两轮观察期 baseline archive，起草第三轮受控常态观察期授权请求。该文档只代表申请授权，不代表已启动第三轮观察期。

授权请求应限定：
- 20-user controlled routine pilot only。
- preview-only / no-write / no-evidence。
- 不开放正式生成链。
- 不开放正式 evidence。
- 不开放评分依据写入。
- 不开放 DOCX 导出。
- 不开放 review/apply。
- 不开放 ZBid 写回。
- 不写 output/job/export。
- 不进入 50 人正式部署设计。
- 不实施顶级模型升级。

严格禁止：
不得修改代码、tests、frontend、backend、既有 docs。
不得运行服务、Ollama、访问端口或调用 endpoint。
不得触发 /generate、/export_docx、/review/apply 或 ZBid 写回。
不得生成 DOCX。
不得写 output/job/export。
不得把 preview-only 结果作为 evidence 或评分依据。
不得进入 Step 262。
```
