# ZDoc-ZBid 20-user controlled routine observation-period second-cycle execution report

## 1. Step 259 execution summary

This report archives Step 259: ZDoc-ZBid 20-user controlled routine observation-period second-cycle execution.

The execution was performed under the following boundary:

- Scope: controlled routine observation-period second-cycle execution.
- Mode: preview-only / no-write / no-evidence.
- ZDoc repository: `/Users/youfeini/Desktop/文档生成系统`.
- ZDoc branch: `main`.
- ZDoc start HEAD: `602e70c5bf7827b309638c71f41d1f6193e9ab6e`.
- ZBid repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`.
- ZBid branch: `local-llm-integration-clean`.
- ZBid start HEAD: `378355755372e03ac4f4064af59b287054984c25`.
- Effective observation-period requests: 60.
- Preflight payload calibration requests: 8.
- Batch count: 6.
- Simulated users covered: 20.
- Role / scenario categories covered: 11.
- Abnormal / boundary effective requests: 18.

The second-cycle observation period completed successfully. All effective requests returned HTTP 200 from ZDoc preview-only entry and ZBid receiver, kept `preview_only=true`, `no_write=true`, and `no_evidence=true`, and kept all five no-write / no-formal-chain flags false.

This report does not authorize Step 260. This report does not open any formal generation, evidence, scoring, export, review/apply, writeback, DOCX, or output/job/export chain.

## 2. Runtime environment and port record

ZDoc service:

- Startup command: `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766`
- Working directory: `/Users/youfeini/Desktop/文档生成系统`
- PID: `76167`
- Host and port: `127.0.0.1:18766`
- Purpose: serve the authorized ZDoc preview-only entry for this controlled observation-period run.

ZBid service:

- Startup command: `PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767`
- Working directory: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- PID: `76168`
- Host and port: `127.0.0.1:18767`
- Purpose: serve the authorized ZBid preview-only receiver endpoint for this controlled observation-period run.

Temporary ZDoc environment variables:

- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- `PYTHONDONTWRITEBYTECODE=1`

These settings were used only for the current controlled observation-period run. They were not written to `.env`, application configuration, or persistent files.

## 3. Second-cycle observation-period batch arrangement

| Batch | Name | Effective requests | Worker shape | Purpose |
| --- | --- | ---: | --- | --- |
| B1 | Startup verification batch | 10 | sequential | Confirm service readiness and baseline preview-only behavior. |
| B2 | Routine usage batch | 12 | grouped routine flow | Exercise common role flows under routine use. |
| B3 | Continuous observation batch | 12 | grouped routine flow | Observe consistency across continued preview-only calls. |
| B4 | Boundary blocking batch | 10 | boundary-focused flow | Exercise boundary-style payloads while preserving preview-only status. |
| B5 | Abnormal input batch | 8 | abnormal-focused flow | Exercise abnormal input handling and readable blocked reasons. |
| B6 | Pre-shutdown verification batch | 8 | closing routine flow | Reconfirm stable behavior before service shutdown. |

## 4. 20-user and role coverage

The effective observation-period run covered 20 simulated users:

- `obs2-user-01`
- `obs2-user-02`
- `obs2-user-03`
- `obs2-user-04`
- `obs2-user-05`
- `obs2-user-06`
- `obs2-user-07`
- `obs2-user-08`
- `obs2-user-09`
- `obs2-user-10`
- `obs2-user-11`
- `obs2-user-12`
- `obs2-user-13`
- `obs2-user-14`
- `obs2-user-15`
- `obs2-user-16`
- `obs2-user-17`
- `obs2-user-18`
- `obs2-user-19`
- `obs2-user-20`

The run covered 11 role / scenario categories:

1. 总控管理员
2. 技术标主编
3. 施工组织设计编制人员
4. 专项施工方案编制人员
5. 进度计划编制人员
6. 质量安全复核人员
7. 商务 / 清单协同人员
8. 项目资料整理人员
9. ZBid 评标辅助观察人员
10. 普通试用人员
11. 异常输入 / 边界输入场景

## 5. Per-batch validation result

| Batch | HTTP result | Preview-only result | Boundary result | Rollback required |
| --- | --- | --- | --- | --- |
| B1 | ZDoc 10/10 HTTP 200; ZBid 10/10 HTTP 200 | 10/10 `preview_only=true`, `no_write=true`, `no_evidence=true` | All five flags false | No |
| B2 | ZDoc 12/12 HTTP 200; ZBid 12/12 HTTP 200 | 12/12 `preview_only=true`, `no_write=true`, `no_evidence=true` | All five flags false | No |
| B3 | ZDoc 12/12 HTTP 200; ZBid 12/12 HTTP 200 | 12/12 `preview_only=true`, `no_write=true`, `no_evidence=true` | All five flags false | No |
| B4 | ZDoc 10/10 HTTP 200; ZBid 10/10 HTTP 200 | 10/10 `preview_only=true`, `no_write=true`, `no_evidence=true` | All five flags false | No |
| B5 | ZDoc 8/8 HTTP 200; ZBid 8/8 HTTP 200 | 8/8 `preview_only=true`, `no_write=true`, `no_evidence=true` | All five flags false | No |
| B6 | ZDoc 8/8 HTTP 200; ZBid 8/8 HTTP 200 | 8/8 `preview_only=true`, `no_write=true`, `no_evidence=true` | All five flags false | No |

## 6. Per-scenario validation result

All scenarios below used desensitized / simulated / preview-only payloads. No real tender evidence, formal scoring basis, DOCX, writeback data, or formal business data was used.

| Scenario | Batch | User | Role / scenario | Payload type | HTTP result | Preview-only result | Manual review |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | B1 | `obs2-user-01` | 总控管理员 | `admin_control_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S02 | B1 | `obs2-user-02` | 技术标主编 | `chief_editor_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S03 | B1 | `obs2-user-03` | 施工组织设计编制人员 | `construction_org_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S04 | B1 | `obs2-user-04` | 专项施工方案编制人员 | `special_plan_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S05 | B1 | `obs2-user-05` | 进度计划编制人员 | `schedule_planner_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S06 | B1 | `obs2-user-06` | 质量安全复核人员 | `quality_safety_reviewer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S07 | B1 | `obs2-user-07` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S08 | B1 | `obs2-user-08` | 项目资料整理人员 | `document_controller_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S09 | B1 | `obs2-user-09` | ZBid 评标辅助观察人员 | `zbid_observer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S10 | B1 | `obs2-user-10` | 普通试用人员 | `general_user_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S11 | B2 | `obs2-user-11` | 总控管理员 | `admin_control_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S12 | B2 | `obs2-user-12` | 技术标主编 | `chief_editor_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S13 | B2 | `obs2-user-13` | 施工组织设计编制人员 | `construction_org_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S14 | B2 | `obs2-user-14` | 专项施工方案编制人员 | `special_plan_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S15 | B2 | `obs2-user-15` | 进度计划编制人员 | `schedule_planner_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S16 | B2 | `obs2-user-16` | 质量安全复核人员 | `quality_safety_reviewer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S17 | B2 | `obs2-user-17` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S18 | B2 | `obs2-user-18` | 项目资料整理人员 | `document_controller_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S19 | B2 | `obs2-user-19` | ZBid 评标辅助观察人员 | `zbid_observer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S20 | B2 | `obs2-user-20` | 普通试用人员 | `general_user_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S21 | B2 | `obs2-user-01` | 总控管理员 | `admin_control_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S22 | B2 | `obs2-user-02` | 技术标主编 | `chief_editor_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S23 | B3 | `obs2-user-03` | 施工组织设计编制人员 | `construction_org_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S24 | B3 | `obs2-user-04` | 专项施工方案编制人员 | `special_plan_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S25 | B3 | `obs2-user-05` | 进度计划编制人员 | `schedule_planner_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S26 | B3 | `obs2-user-06` | 质量安全复核人员 | `quality_safety_reviewer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S27 | B3 | `obs2-user-07` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S28 | B3 | `obs2-user-08` | 项目资料整理人员 | `document_controller_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S29 | B3 | `obs2-user-09` | ZBid 评标辅助观察人员 | `zbid_observer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S30 | B3 | `obs2-user-10` | 普通试用人员 | `general_user_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S31 | B3 | `obs2-user-11` | 总控管理员 | `admin_control_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S32 | B3 | `obs2-user-12` | 技术标主编 | `chief_editor_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S33 | B3 | `obs2-user-13` | 施工组织设计编制人员 | `construction_org_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S34 | B3 | `obs2-user-14` | 专项施工方案编制人员 | `special_plan_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S35 | B4 | `obs2-user-15` | 进度计划编制人员 | `schedule_planner_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S36 | B4 | `obs2-user-16` | 异常输入 / 边界输入场景 | `boundary_input_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S37 | B4 | `obs2-user-17` | 质量安全复核人员 | `quality_safety_reviewer_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S38 | B4 | `obs2-user-18` | 商务 / 清单协同人员 | `commercial_boq_collab_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S39 | B4 | `obs2-user-19` | 异常输入 / 边界输入场景 | `boundary_input_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S40 | B4 | `obs2-user-20` | 项目资料整理人员 | `document_controller_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S41 | B4 | `obs2-user-01` | ZBid 评标辅助观察人员 | `zbid_observer_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S42 | B4 | `obs2-user-02` | 异常输入 / 边界输入场景 | `boundary_input_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S43 | B4 | `obs2-user-03` | 普通试用人员 | `general_user_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S44 | B4 | `obs2-user-04` | 总控管理员 | `admin_control_boundary_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S45 | B5 | `obs2-user-05` | 异常输入 / 边界输入场景 | `boundary_input_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S46 | B5 | `obs2-user-06` | 技术标主编 | `chief_editor_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S47 | B5 | `obs2-user-07` | 施工组织设计编制人员 | `construction_org_writer_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S48 | B5 | `obs2-user-08` | 异常输入 / 边界输入场景 | `boundary_input_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S49 | B5 | `obs2-user-09` | 专项施工方案编制人员 | `special_plan_writer_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S50 | B5 | `obs2-user-10` | 进度计划编制人员 | `schedule_planner_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S51 | B5 | `obs2-user-11` | 异常输入 / 边界输入场景 | `boundary_input_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S52 | B5 | `obs2-user-12` | 质量安全复核人员 | `quality_safety_reviewer_abnormal_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S53 | B6 | `obs2-user-13` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S54 | B6 | `obs2-user-14` | 项目资料整理人员 | `document_controller_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S55 | B6 | `obs2-user-15` | ZBid 评标辅助观察人员 | `zbid_observer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S56 | B6 | `obs2-user-16` | 普通试用人员 | `general_user_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S57 | B6 | `obs2-user-17` | 总控管理员 | `admin_control_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S58 | B6 | `obs2-user-18` | 技术标主编 | `chief_editor_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S59 | B6 | `obs2-user-19` | 施工组织设计编制人员 | `construction_org_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |
| S60 | B6 | `obs2-user-20` | 专项施工方案编制人员 | `special_plan_writer_routine_second_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass | Pass |

For all 60 effective records:

- ZDoc outbound sent the preview-only payload.
- ZBid receiver accepted the preview-only payload.
- `blocked_reasons` was readable.
- `validator_result` was readable.
- No scenario required rollback.
- No scenario triggered a prohibited flag.

## 7. HTTP result summary

Effective observation-period requests:

- ZDoc preview-only entry: 60/60 HTTP 200.
- ZBid preview-only receiver endpoint: 60/60 HTTP 200.
- Non-200 responses: 0.

Preflight payload calibration requests:

- ZDoc preview-only entry: 8/8 HTTP 200.
- ZBid receiver calls: 0/8, because invalid ZBid status enum payloads were blocked before network-send.
- Calibration requests were not counted as effective observation-period requests.

Observed latency summary:

- ZDoc preview-only entry latency: minimum 0.55 ms, median 1.35 ms, maximum 3.21 ms.
- ZDoc outbound to ZBid receiver latency: minimum 1.12 ms, median 2.73 ms, maximum 5.50 ms.

These latency observations are local controlled-run observations only. They are not a formal production performance benchmark.

## 8. Preview-only / no-write / no-evidence review result

All 60 effective observation-period requests returned or preserved:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

The result remains limited to preview-only display and review. It is not evidence, not scoring basis, not writeback authorization, and not formal business data.

## 9. Forbidden endpoint and forbidden write review

Authorized endpoints called:

- ZDoc: `POST /local-trial/preview-only`
- ZBid: `POST /local-llm/zdoc-preview-only/receive`

Forbidden endpoints not called:

- `/generate`
- `/export_docx`
- `/review/apply`
- Any ZBid writeback endpoint
- Any unknown business endpoint outside the authorized preview-only path

Forbidden write results:

- DOCX generated: no.
- `output/job/export` written: no.
- Formal evidence written: no.
- Formal scoring basis written: no.
- ZBid writeback triggered: no.
- Formal business data written: no.

## 10. ZDoc to ZBid send and receive result

Effective observation-period requests:

- ZDoc outbound sent: 60/60.
- ZBid receiver received: 60/60.
- Target endpoint: `POST /local-llm/zdoc-preview-only/receive`.
- Payload scope: preview_packet, validator_result, blocked_reasons, and no-write / no-formal-chain flags.

The outbound adapter did not send evidence, DOCX, formal scoring result, writeback data, or formal business data.

## 11. Step 258 controlled routine baseline execution

The run matched the Step 258 controlled routine baseline:

- Effective requests were kept separate from preflight calibration.
- Invalid ZBid status enum payloads were blocked before network-send.
- Effective requests remained preview-only / no-write / no-evidence.
- Five no-write / no-formal-chain flags remained false.
- ZDoc and ZBid service use stayed temporary and local.
- No `.env`, persistent config, or code path was changed.
- Service shutdown and port release were verified after the run.
- No writeback, evidence, scoring, DOCX, or output/job/export path was opened.

## 12. Comparison with Step 257 first observation-period result

Step 257 first observation period established a controlled observation-period baseline with 50 effective requests, 5 batches, 20 simulated users, 11 role / scenario categories, and 12 abnormal / boundary inputs.

Step 259 second observation period extended that baseline:

- Effective requests increased from 50 to 60.
- Batches increased from 5 to 6.
- Simulated user coverage remained 20.
- Role / scenario coverage remained 11 categories.
- Abnormal / boundary inputs increased from 12 to 18.
- HTTP 200 result remained consistent.
- `preview_only=true`, `no_write=true`, and `no_evidence=true` remained consistent.
- Five no-write / no-formal-chain flags remained false.
- No DOCX, writeback, evidence, scoring basis, or output/job/export write appeared.

## 13. Regression conclusion

No regression was observed against Step 257.

The second-cycle observation period preserved the same preview-only / no-write / no-evidence safety posture while increasing request count, batch count, and abnormal / boundary coverage.

## 14. Preflight payload calibration and boundary block record

Preflight payload calibration was performed before the effective observation-period run:

- Calibration request count: 8.
- Calibration ZDoc result: 8/8 HTTP 200.
- Calibration ZBid receiver sends: 0.
- Calibration requests counted as effective observation-period requests: no.
- Calibration triggered formal fallback: no.
- Calibration triggered writeback, evidence, scoring, DOCX, or output/job/export write: no.

Calibration blocked reasons included:

- `invalid_zbid_input_status`
- `invalid_zbid_mapping_status`
- `invalid_zbid_scoring_matrix_status`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

## 15. Invalid ZBid status enum blocking result

Invalid ZBid status enum payloads were blocked by the ZDoc outbound adapter before network-send.

Blocking result:

- Invalid enum blocked: 8/8.
- Blocked payload sent to ZBid receiver: no.
- Fallback to formal endpoint: no.
- Writeback triggered: no.
- Evidence generated: no.
- Scoring basis generated: no.
- DOCX generated: no.
- `output/job/export` written: no.

This confirms the boundary that invalid preview-only ZBid status enum payloads must stop inside the preview-only adapter path and must not fall through to any formal chain.

## 16. Abnormal input and boundary input behavior

The effective observation-period run included 18 abnormal / boundary requests across the boundary blocking and abnormal input batches.

Observed abnormal / boundary behavior:

- HTTP result remained 200 for controlled preview-only responses.
- `preview_only=true`, `no_write=true`, and `no_evidence=true` remained present.
- `blocked_reasons` remained readable.
- `validator_result` remained readable.
- ZDoc outbound sent only preview-only payloads.
- ZBid receiver accepted only preview-only payloads.
- No rollback was required.

Representative boundary reasons included:

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`
- `unverifiable_scoring_clause_refs`
- `missing_evidence_anchor`
- `high_input_risk_not_validated`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

## 17. Manual review workflow usability

Manual review remained usable for the second-cycle observation-period run.

Reviewable fields:

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- `preview_only`
- `no_write`
- `no_evidence`
- `generate_called`
- `export_docx_called`
- `review_apply_called`
- `zbid_writeback_called`
- `output_job_export_written`

Manual review conclusion:

- Reviewers can confirm preview-only status before considering any result.
- Reviewers can see blocked reasons for boundary and abnormal inputs.
- Reviewers can confirm the five false flags without relying on formal chain signals.
- Review output must remain advisory and must not be treated as evidence or scoring basis.

## 18. Error prompt and blocked_reasons readability

Error prompts and `blocked_reasons` remained readable in the controlled run.

Readability observations:

- Invalid enum calibration was clearly represented as blocked before network-send.
- Boundary inputs produced visible blocked reasons.
- Abnormal inputs preserved preview-only / no-write / no-evidence status.
- The blocked reasons were suitable for manual review and issue-list recording.

Observation item:

- Future documentation or UI text may continue improving how trial users interpret the difference between configuration, input, boundary, and formal-chain-risk blocked reasons. Any UI, logging, backend, or receiver change must be separately authorized.

## 19. Concurrency and response risk observation

The second-cycle run used grouped batches and local preview-only calls. It is not a formal production load test.

Observed local response profile:

- Effective requests: 60.
- Batches: 6.
- Maximum observed ZDoc preview-only latency: 3.21 ms.
- Maximum observed ZDoc outbound to ZBid receiver latency: 5.50 ms.
- HTTP failures: 0.
- Regression against Step 257: none observed.

Risk note:

- These results support controlled 20-user pilot observation continuity, but they do not establish long-term production-server capacity, 50-user formal deployment capacity, or formal concurrent load guarantees.

## 20. Findings

Blocking issues:

- None observed in this second-cycle observation-period run.

High-risk issues:

- None observed.

Medium-risk issues:

- None observed.

Low-risk issues:

- None observed.

Observation items:

- Continue recording blocked reason readability.
- Continue separating preflight calibration from effective observation-period calls.
- Continue requiring no-write / no-evidence confirmation before any manual review conclusion.
- Continue confirming service shutdown and port release after each controlled run.

## 21. Risk levels

| Risk level | Current result | Handling |
| --- | --- | --- |
| Blocking | None observed | Continue controlled observation only. |
| High | None observed | Keep formal-chain prohibition active. |
| Medium | None observed | Continue baseline checks. |
| Low | None observed | Continue routine observation. |
| Observation | Readability and logging interpretation can still be improved | Requires separate authorization before any code, UI, logging, or document workflow change. |

## 22. Rollback record

Rollback was not required.

Stop conditions were checked:

- Formal-chain flag non-false: not observed.
- DOCX generation: not observed.
- `output/job/export` write: not observed.
- ZBid writeback: not observed.
- Evidence generation: not observed.
- Scoring basis generation: not observed.
- Unknown endpoint call: not observed.
- Fallback to formal endpoint: not observed.

## 23. Service shutdown and port release result

The services started for this step were stopped after the observation-period run.

Shutdown result:

- ZDoc PID `76167`: stopped.
- ZBid PID `76168`: stopped.
- `127.0.0.1:18766`: no listener after shutdown.
- `127.0.0.1:18767`: no listener after shutdown.

Output path check:

- ZDoc `output/job/export`: no new write observed; path was not present during the final check.
- ZBid `output/job/export`: no new write observed; path was not present during the final check.

## 24. Step 260 recommendation

Step 260 can be considered as a docs-only second-cycle observation-period review and controlled routine baseline update.

Step 260 should remain:

- docs-only.
- no-code-change.
- no-service.
- no-port-access.
- no-endpoint-call.
- no-writeback.
- no-DOCX.
- no-output/job/export.
- no-formal-chain.
- no-50-user-formal-deployment-design.
- no-top-model-upgrade.

Step 260 should archive:

- Step 259 second-cycle observation-period result.
- 60 effective requests, 6 batches, 20 simulated users, 11 role / scenario categories, 18 abnormal / boundary requests.
- 8 preflight payload calibration requests and invalid ZBid enum blocking.
- HTTP 200 result.
- Preview-only / no-write / no-evidence result.
- Five false flags result.
- No regression against Step 257.
- No DOCX, no writeback, no evidence, no scoring basis, no output/job/export write.
- Service shutdown and port release result.

## 25. Draft Step 260 authorization request

Suggested authorization wording for Step 260:

```text
执行 Step 260：ZDoc-ZBid 20-user observation-period second-cycle review and controlled routine baseline update。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<由 Step 259 完成后实际 HEAD 填入>

本步性质：
docs-only / review-and-baseline-update-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

授权范围：
仅允许新增 1 个 docs 文件，用于归档 Step 259 第二轮受控常态观察期执行结果、与 Step 257 第一轮观察期对比、前置 payload 校准与非法 ZBid status 枚举阻断说明、preview-only / no-write / no-evidence 边界复核、五个 false flags 复核、问题分级、继续观察条件和暂停条件。

严格禁止：
不得修改代码、tests、frontend、backend、既有 docs。
不得运行服务、访问端口、运行 Ollama 或调用任何 endpoint。
不得触发 /generate、/export_docx、/review/apply 或 ZBid 写回。
不得生成 DOCX。
不得写 output/job/export。
不得把 preview-only 结果作为 evidence。
不得把 preview-only 结果作为评分依据。
不得进入 50 人正式部署设计。
不得实施顶级模型升级。
不得进入 Step 261。
```
