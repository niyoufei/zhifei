# ZDoc-ZBid 20-user three-cycle observation-period review and controlled routine operation baseline archive

## 1. Step 257, Step 259, Step 261 three-cycle recap

This archive consolidates the controlled routine observation-period results from Step 257, Step 259, and Step 261.

- Step 257 completed the first controlled routine observation-period execution.
- Step 259 completed the second controlled routine observation-period execution under the Step 258 controlled routine baseline.
- Step 261 completed the third controlled routine observation-period execution under the Step 260 two-cycle observation baseline.
- All three cycles remained limited to preview-only / no-write / no-evidence validation.
- None of the three cycles opened formal generation, formal evidence, scoring-basis write, DOCX export, review/apply, ZBid writeback, or 50-user formal deployment design.

## 2. Effective observation-period result summary

The three effective observation-period cycles are summarized below. These figures include only final effective observation-period requests and exclude all preflight payload calibration, payload-shape checks, invalid enum checks, blocked calibration payloads, and preview-only calibration calls.

| Cycle | Effective requests | Batches | Simulated users | Role / scenario categories | Abnormal / boundary inputs | ZDoc HTTP 200 | ZBid HTTP 200 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Step 257 | 50 | 5 | 20 | 11 | 12 | 50/50 | 50/50 |
| Step 259 | 60 | 6 | 20 | 11 | 18 | 60/60 | 60/60 |
| Step 261 | 70 | 7 | 20 | 11 | 20 | 70/70 | 70/70 |
| Total | 180 | 18 | 20 | 11 | 50 | 180/180 | 180/180 |

Conclusion: the three effective observation-period cycles completed 180 effective requests across 18 batches, 20 simulated users, 11 role / scenario categories, and 50 abnormal / boundary inputs.

## 3. Three-cycle HTTP 200 result

- Effective ZDoc preview-only entry result: 180/180 HTTP 200.
- Effective ZBid receiver result: 180/180 HTTP 200.
- No effective observation-period request required rollback.
- No effective observation-period request fell back to a formal endpoint.

## 4. preview-only / no-write / no-evidence review

Across Step 257, Step 259, and Step 261:

- `preview_only=true`: confirmed for all 180 effective observation-period requests.
- `no_write=true`: confirmed for all 180 effective observation-period requests.
- `no_evidence=true`: confirmed for all 180 effective observation-period requests.

This confirms that the observation-period traffic remained inside the preview-only / no-write / no-evidence lane.

## 5. Five no-write / no-formal-chain flags review

Across the three effective observation-period cycles, the five safety flags remained false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

Any future non-false value for any of these flags must be treated as a stop condition, not as an acceptable trial variation.

## 6. Consistency with Step 256, Step 258, and Step 260 baselines

The three-cycle observation-period result remains consistent with the prior baselines:

- Step 256 established the three-cycle stable pilot baseline and required long-term preview-only / no-write / no-evidence boundaries.
- Step 258 updated the controlled routine baseline with explicit separation between effective observation-period requests and preflight payload calibration.
- Step 260 archived the two-cycle observation-period baseline and required continued separation of calibration records, invalid enum blocking, and no-write boundary checks.
- Step 257, Step 259, and Step 261 all preserved the same effective-request isolation, preview-only boundary, and five false flags requirement.

## 7. Regression conclusion

No regression was observed across Step 257, Step 259, and Step 261.

- HTTP 200 behavior remained stable for effective requests.
- `preview_only=true`, `no_write=true`, and `no_evidence=true` remained stable.
- The five no-write / no-formal-chain flags remained false.
- Invalid enum and payload-shape calibration paths remained separated from effective observation-period traffic.
- No formal generation, evidence, scoring, export, review/apply, writeback, DOCX generation, or `output/job/export` write was observed.

## 8. Preflight payload calibration summary table

Preflight calibration is recorded separately from effective observation-period traffic.

| Source step | Calibration category | Calibration count | Sent to ZBid receiver | Blocked by adapter | Counted as effective observation-period request |
| --- | --- | ---: | ---: | ---: | --- |
| Step 257 | Invalid ZBid status enum calibration | 50 | 0 | 50 | No |
| Step 259 | Invalid ZBid status enum calibration | 8 | 0 | 8 | No |
| Step 261 | Illegal enum calibration | 10 | 0 | 10 | No |
| Step 261 | Pre-effective payload-shape calibration | 70 | 25 | 45 | No |
| Total | All calibration records | 138 | 25 | 113 | No |

## 9. Step 257 preflight payload calibration

Step 257 recorded 50 preflight payload calibration records.

- Calibration cause: `zbid_input_status`, `zbid_mapping_status`, and `zbid_scoring_matrix_status` used non-enum values.
- ZDoc preview-only route returned HTTP 200 for the calibration checks.
- The outbound adapter blocked the invalid enum payloads before network-send.
- ZBid receiver was not called for these 50 calibration records.
- These 50 records are not effective observation-period requests.
- These 50 records are not evidence, not scoring basis, and not writeback data.

## 10. Step 259 preflight payload calibration

Step 259 recorded 8 preflight payload calibration records.

- Calibration cause: invalid ZBid status enum payload verification.
- The outbound adapter blocked the invalid enum payloads before network-send.
- ZBid receiver was not called for these 8 calibration records.
- These 8 records are not effective observation-period requests.
- These 8 records are not evidence, not scoring basis, and not writeback data.

## 11. Step 261 preflight calibration classification

Step 261 recorded two separate calibration groups:

| Step 261 calibration group | Count | Result | Classification |
| --- | ---: | --- | --- |
| Illegal enum calibration | 10 | 10/10 blocked by outbound adapter before network-send | Invalid enum calibration, not effective traffic |
| Pre-effective payload-shape calibration | 70 | 25 preview-only payloads sent to ZBid receiver; 45 blocked by adapter | Payload-shape calibration, not effective traffic |

The 25 payloads sent to ZBid receiver in the pre-effective payload-shape calibration are classified only as preview-only calibration calls. They must not be counted as effective observation-period requests, evidence, scoring basis, writeback data, formal business data, or formal chain verification.

## 12. Calibration exclusion rule

All preflight payload calibration records must remain excluded from effective observation-period request counts.

This rule applies to:

- Step 257 calibration records.
- Step 259 calibration records.
- Step 261 illegal enum calibration records.
- Step 261 pre-effective payload-shape calibration records.
- Step 261 preview-only calibration calls that reached ZBid receiver.

## 13. Step 261 preview-only calibration calls

The 25 Step 261 pre-effective payload-shape records that reached ZBid receiver are archived as preview-only calibration calls only.

They are not:

- effective observation-period requests;
- evidence;
- scoring basis;
- writeback data;
- formal business data;
- proof of formal generation readiness;
- proof of DOCX export readiness;
- proof of review/apply readiness.

They remain useful only for preview-only payload-shape calibration and must be counted separately in future reports.

## 14. Invalid ZBid status enum blocking archive

Invalid ZBid status enum payloads were blocked by the outbound adapter before ZBid receiver invocation.

This confirms:

- invalid enum payloads did not reach ZBid receiver in Step 257, Step 259, or the Step 261 illegal enum group;
- invalid enum payloads did not fall back to any formal endpoint;
- invalid enum payloads did not trigger writeback;
- invalid enum payloads did not generate DOCX;
- invalid enum payloads did not write `output/job/export`;
- invalid enum payloads did not become evidence or scoring basis.

## 15. Verified capability list

The following capabilities have been verified within the preview-only / no-write / no-evidence boundary:

- ZDoc preview-only entry can return HTTP 200 for effective observation-period requests.
- ZDoc outbound adapter can send valid preview-only payloads to ZBid receiver.
- ZBid receiver can return HTTP 200 for effective preview-only payloads.
- `preview_packet`, `validator_result`, and `blocked_reasons` remain readable.
- Effective observation-period requests preserve `preview_only=true`, `no_write=true`, and `no_evidence=true`.
- The five no-write / no-formal-chain flags remain false.
- Invalid enum payloads are blocked before ZBid receiver invocation.
- Payload-shape calibration can be separated from effective observation-period traffic.
- No DOCX generation, `output/job/export` write, ZBid writeback, formal evidence write, or scoring-basis write was observed.

## 16. Unverified capability list

The following capabilities remain unverified and must not be inferred from this archive:

- Formal `/generate` chain.
- Formal `/export_docx` chain.
- Formal `/review/apply` chain.
- ZBid writeback chain.
- Formal evidence ingestion.
- Formal scoring-basis write.
- DOCX generation.
- `output/job/export` write path.
- Long-term production server operation.
- 50-user formal deployment.
- Top local model upgrade.
- Real business data integration.

## 17. Issues and observations

No blocker was found in the effective preview-only observation-period path.

Observed items:

- Preflight calibration volume became large across the observation-period work and must remain strictly separated from effective requests.
- Step 261 included 25 preview-only calibration calls that reached ZBid receiver, and those must remain categorized as calibration calls only.
- Payload construction must continue using legal preview-only enum values and accepted payload-shape values.
- Future reports need explicit columns for effective request count, calibration count, adapter-blocked count, and preview-only calibration call count.

## 18. Issue severity classification

| Severity | Current status |
| --- | --- |
| Blocking | None found in the effective preview-only observation-period path. |
| High risk | None observed. No formal chain, writeback, DOCX, evidence, scoring-basis, or `output/job/export` trigger was found. |
| Medium risk | None observed as an active defect. Future mixing of calibration calls into effective counts would become a medium-risk reporting issue. |
| Low risk | Payload-shape calibration requires continued operator attention and clear report templates. |
| Observation | Preflight calibration volume is relatively large, and counting boundaries must remain strict. |

## 19. Required observation item

The following item is explicitly listed as an observation:

- Preflight calibration scale is relatively large, and the reporting boundary must be strictly distinguished.

This is an observation item, not an authorization to change code, change tests, expand the trial, open formal chains, or modify production behavior.

## 20. Future preflight calibration control requirements

Future preflight calibration must follow these controls:

- Keep calibration quantity as small as reasonably possible.
- Count calibration separately from effective observation-period requests.
- Archive calibration separately from effective traffic.
- Record whether each calibration payload was blocked by the adapter or sent as a preview-only calibration call.
- Do not mix calibration payloads into effective observation-period totals.
- Do not count preview-only calibration calls as evidence or scoring basis.
- Do not use calibration records to justify formal chain opening.

## 21. 20-user controlled routine observation-period stage conclusion

The 20-user controlled routine observation-period stage has established a stable preview-only / no-write / no-evidence baseline across three cycles.

The current conclusion is:

- Effective observation-period traffic is stable across 180 requests.
- The preview-only boundary remains intact.
- No formal chain was triggered.
- No writeback occurred.
- No DOCX was generated.
- No `output/job/export` write occurred.
- Calibration records are now explicitly separated from effective observation-period requests.

This archive supports continued controlled routine pilot operation, but does not authorize formal production use.

## 22. Conditions for continuing controlled routine pilot operation

Controlled routine pilot operation may continue only if all conditions remain true:

- Traffic remains preview-only / no-write / no-evidence.
- The five no-write / no-formal-chain flags remain false.
- Calibration records are counted and archived separately.
- Invalid enum or malformed payloads are blocked without fallback to formal endpoints.
- Services are started only under explicit authorization.
- Ports are accessed only under explicit authorization.
- Endpoint calls are limited to authorized preview-only endpoints.
- No DOCX is generated.
- No `output/job/export` write occurs.
- No ZBid writeback occurs.
- No preview-only result is used as evidence or scoring basis.

## 23. Mandatory pause triggers

The routine pilot must pause immediately if any of the following occurs:

- `generate_called` is not false.
- `export_docx_called` is not false.
- `review_apply_called` is not false.
- `zbid_writeback_called` is not false.
- `output_job_export_written` is not false.
- `/generate` is called.
- `/export_docx` is called.
- `/review/apply` is called.
- Any ZBid writeback endpoint is called.
- DOCX is generated.
- `output/job/export` is written.
- preview-only result is stored as evidence.
- preview-only result is stored as scoring basis.
- Calibration records are mixed into effective observation-period totals.
- Unknown endpoints are called.
- A payload falls back to a formal endpoint.

## 24. Rollback conditions

Rollback must be recorded and executed according to the controlled routine baseline if:

- a forbidden endpoint is called;
- a formal write occurs;
- a DOCX file is generated;
- `output/job/export` changes;
- evidence or scoring-basis writes are detected;
- ZBid writeback is detected;
- preview-only / no-write / no-evidence flags are missing or false;
- calibration and effective request counts cannot be separated;
- service shutdown or port release cannot be confirmed.

Rollback records must include time, operator role, service state, endpoint list, request category, affected payload count, observed risk, and final stop decision.

## 25. Long-term preview-only / no-write / no-evidence boundary

The long-term boundary remains:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

These flags are boundary controls for preview-only operation. They are not formal evidence, not scoring basis, not production approval, and not writeback authorization.

## 26. Forbidden interfaces, writes, evidence, and scoring

The following remain forbidden unless separately authorized in a later step:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- DOCX generation
- `output/job/export` write
- storing preview-only output as evidence
- storing preview-only output as scoring basis
- writing formal business data
- falling back from preview-only to formal endpoints
- using calibration records as effective observation-period requests

## 27. Host positioning

The current host must be treated only as a 20-user pilot host.

It is not:

- a long-term formal production server;
- a 50-user formal deployment host;
- a formal evidence server;
- a formal scoring server;
- a DOCX generation server;
- a writeback server;
- a top local model upgrade target.

Any change to that positioning requires separate authorization.

## 28. Step 263 authorization request draft

The following draft may be copied into a future authorization request. It is not an authorization by itself.

```text
执行 Step 263：ZDoc-ZBid 20-user controlled routine operation continuation authorization request

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 262 结束后 HEAD>

本步性质：
docs-only / authorization-request-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

授权请求来源：
- Step 257、Step 259、Step 261 三轮观察期已完成。
- 三轮有效观察期合计 180 条请求、18 个批次、20 个模拟用户、11 类角色 / 场景、50 条异常 / 边界输入。
- 有效观察期 ZDoc 与 ZBid 均 HTTP 200。
- preview_only=true、no_write=true、no_evidence=true。
- 五个 no-write / no-formal-chain flags 均为 false。
- 前置 payload 校准已单独计数、单独归档，不计入有效观察期请求。

拟申请范围：
- 继续在 20 人受控常态试运行范围内运行。
- 继续保持 preview-only / no-write / no-evidence。
- 如需启动服务、访问端口或调用 endpoint，必须在后续执行步中明确授权。
- 不进入 50 人正式部署设计。
- 不实施顶级模型升级。

必须继续禁止：
- 不触发 /generate。
- 不触发 /export_docx。
- 不触发 /review/apply。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 output/job/export。
- 不将 preview-only 结果作为 evidence。
- 不将 preview-only 结果作为评分依据。
- 不将前置校准计入有效观察期请求。
```
