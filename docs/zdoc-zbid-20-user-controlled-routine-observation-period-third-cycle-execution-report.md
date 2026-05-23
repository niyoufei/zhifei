# ZDoc-ZBid 20-user controlled routine observation-period third-cycle execution report

## 1. Step 261 execution summary

This report archives Step 261: ZDoc-ZBid 20-user controlled routine observation-period third-cycle execution.

Execution boundary:

- Mode: preview-only / no-write / no-evidence.
- ZDoc repository: `/Users/youfeini/Desktop/文档生成系统`.
- ZDoc branch: `main`.
- ZDoc start HEAD: `3851fbfbc870b78596c0dd80078f2b4ab6a7ff19`.
- ZBid repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`.
- ZBid branch: `local-llm-integration-clean`.
- ZBid start HEAD: `378355755372e03ac4f4064af59b287054984c25`.

Final effective third-cycle observation result:

- Effective observation-period requests: 70.
- Batches: 7.
- Simulated users covered: 20.
- Role / scenario categories covered: 11.
- Abnormal / boundary effective requests: 20.
- ZDoc effective HTTP result: 70/70 HTTP 200.
- ZBid effective HTTP result: 70/70 HTTP 200.
- `preview_only=true`: 70/70.
- `no_write=true`: 70/70.
- `no_evidence=true`: 70/70.
- Five no-write / no-formal-chain flags false: 70/70.
- Rollback required: no.
- Regression against Step 257 and Step 259: none observed.

Pre-effective calibration and payload-shape checks were recorded separately and are not counted as final effective observation-period requests.

This report does not authorize Step 262. It does not authorize formal generation, formal evidence, scoring basis write, DOCX export, review/apply, ZBid writeback, `output/job/export` write, 50-user formal deployment design, or top model upgrade implementation.

## 2. Runtime environment and port record

ZDoc service:

- Startup command: `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766`
- Working directory: `/Users/youfeini/Desktop/文档生成系统`
- PID: `80330`
- Host and port: `127.0.0.1:18766`

ZBid service:

- Startup command: `PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767`
- Working directory: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- PID: `80342`
- Host and port: `127.0.0.1:18767`

Temporary ZDoc environment variables:

- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- `PYTHONDONTWRITEBYTECODE=1`

These settings were only used for Step 261. They were not written to `.env`, configuration files, source code, tests, frontend, backend, or existing docs.

## 3. Third-cycle observation-period batch arrangement

| Batch | Name | Effective requests | Batch purpose |
| --- | --- | ---: | --- |
| B1 | 启动复核批次 | 10 | Confirm startup readiness and baseline preview-only behavior. |
| B2 | 常态使用批次 | 12 | Exercise routine role flows. |
| B3 | 连续观察批次 | 12 | Observe continuity across repeated preview-only calls. |
| B4 | 边界阻断批次 | 10 | Exercise boundary-style payloads while remaining preview-only. |
| B5 | 异常输入批次 | 10 | Exercise abnormal input handling and readable blocked reasons. |
| B6 | 稳定性复核批次 | 8 | Recheck stability after boundary and abnormal batches. |
| B7 | 关闭前复核批次 | 8 | Reconfirm baseline behavior before shutdown. |

## 4. 20-user / role coverage

Simulated users:

- `obs3-user-01`
- `obs3-user-02`
- `obs3-user-03`
- `obs3-user-04`
- `obs3-user-05`
- `obs3-user-06`
- `obs3-user-07`
- `obs3-user-08`
- `obs3-user-09`
- `obs3-user-10`
- `obs3-user-11`
- `obs3-user-12`
- `obs3-user-13`
- `obs3-user-14`
- `obs3-user-15`
- `obs3-user-16`
- `obs3-user-17`
- `obs3-user-18`
- `obs3-user-19`
- `obs3-user-20`

Role / scenario categories:

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

| Batch | ZDoc HTTP 200 | ZBid HTTP 200 | preview-only / no-write / no-evidence | Five flags false | Rollback |
| --- | ---: | ---: | ---: | ---: | ---: |
| B1 | 10/10 | 10/10 | 10/10 | 10/10 | 0 |
| B2 | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| B3 | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| B4 | 10/10 | 10/10 | 10/10 | 10/10 | 0 |
| B5 | 10/10 | 10/10 | 10/10 | 10/10 | 0 |
| B6 | 8/8 | 8/8 | 8/8 | 8/8 | 0 |
| B7 | 8/8 | 8/8 | 8/8 | 8/8 | 0 |

## 6. Per-scenario validation result

All scenarios used desensitized / simulated / preview-only payloads. No real tender evidence, formal evidence, scoring basis, DOCX, writeback data, or formal business data was used.

| Scenario | Batch | User | Role / scenario | Payload type | HTTP result | Boundary result |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | B1 | `obs3-user-01` | 总控管理员 | `admin_control_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S02 | B1 | `obs3-user-02` | 技术标主编 | `chief_editor_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S03 | B1 | `obs3-user-03` | 施工组织设计编制人员 | `construction_org_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S04 | B1 | `obs3-user-04` | 专项施工方案编制人员 | `special_plan_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S05 | B1 | `obs3-user-05` | 进度计划编制人员 | `schedule_planner_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S06 | B1 | `obs3-user-06` | 质量安全复核人员 | `quality_safety_reviewer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S07 | B1 | `obs3-user-07` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S08 | B1 | `obs3-user-08` | 项目资料整理人员 | `document_controller_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S09 | B1 | `obs3-user-09` | ZBid 评标辅助观察人员 | `zbid_observer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S10 | B1 | `obs3-user-10` | 普通试用人员 | `general_user_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S11 | B2 | `obs3-user-11` | 异常输入 / 边界输入场景 | `boundary_input_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S12 | B2 | `obs3-user-12` | 总控管理员 | `admin_control_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S13 | B2 | `obs3-user-13` | 技术标主编 | `chief_editor_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S14 | B2 | `obs3-user-14` | 施工组织设计编制人员 | `construction_org_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S15 | B2 | `obs3-user-15` | 专项施工方案编制人员 | `special_plan_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S16 | B2 | `obs3-user-16` | 进度计划编制人员 | `schedule_planner_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S17 | B2 | `obs3-user-17` | 质量安全复核人员 | `quality_safety_reviewer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S18 | B2 | `obs3-user-18` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S19 | B2 | `obs3-user-19` | 项目资料整理人员 | `document_controller_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S20 | B2 | `obs3-user-20` | ZBid 评标辅助观察人员 | `zbid_observer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S21 | B2 | `obs3-user-01` | 普通试用人员 | `general_user_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S22 | B2 | `obs3-user-02` | 异常输入 / 边界输入场景 | `boundary_input_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S23 | B3 | `obs3-user-03` | 总控管理员 | `admin_control_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S24 | B3 | `obs3-user-04` | 技术标主编 | `chief_editor_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S25 | B3 | `obs3-user-05` | 施工组织设计编制人员 | `construction_org_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S26 | B3 | `obs3-user-06` | 专项施工方案编制人员 | `special_plan_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S27 | B3 | `obs3-user-07` | 进度计划编制人员 | `schedule_planner_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S28 | B3 | `obs3-user-08` | 质量安全复核人员 | `quality_safety_reviewer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S29 | B3 | `obs3-user-09` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S30 | B3 | `obs3-user-10` | 项目资料整理人员 | `document_controller_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S31 | B3 | `obs3-user-11` | ZBid 评标辅助观察人员 | `zbid_observer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S32 | B3 | `obs3-user-12` | 普通试用人员 | `general_user_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S33 | B3 | `obs3-user-13` | 异常输入 / 边界输入场景 | `boundary_input_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S34 | B3 | `obs3-user-14` | 总控管理员 | `admin_control_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S35 | B4 | `obs3-user-15` | 技术标主编 | `chief_editor_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S36 | B4 | `obs3-user-16` | 异常输入 / 边界输入场景 | `boundary_input_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S37 | B4 | `obs3-user-17` | 专项施工方案编制人员 | `special_plan_writer_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S38 | B4 | `obs3-user-18` | 进度计划编制人员 | `schedule_planner_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S39 | B4 | `obs3-user-19` | 异常输入 / 边界输入场景 | `boundary_input_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S40 | B4 | `obs3-user-20` | 商务 / 清单协同人员 | `commercial_boq_collab_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S41 | B4 | `obs3-user-01` | 项目资料整理人员 | `document_controller_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S42 | B4 | `obs3-user-02` | 异常输入 / 边界输入场景 | `boundary_input_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S43 | B4 | `obs3-user-03` | 普通试用人员 | `general_user_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S44 | B4 | `obs3-user-04` | 异常输入 / 边界输入场景 | `boundary_input_boundary_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S45 | B5 | `obs3-user-05` | 总控管理员 | `admin_control_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S46 | B5 | `obs3-user-06` | 异常输入 / 边界输入场景 | `boundary_input_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S47 | B5 | `obs3-user-07` | 施工组织设计编制人员 | `construction_org_writer_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S48 | B5 | `obs3-user-08` | 专项施工方案编制人员 | `special_plan_writer_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S49 | B5 | `obs3-user-09` | 异常输入 / 边界输入场景 | `boundary_input_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S50 | B5 | `obs3-user-10` | 质量安全复核人员 | `quality_safety_reviewer_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S51 | B5 | `obs3-user-11` | 商务 / 清单协同人员 | `commercial_boq_collab_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S52 | B5 | `obs3-user-12` | 异常输入 / 边界输入场景 | `boundary_input_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S53 | B5 | `obs3-user-13` | ZBid 评标辅助观察人员 | `zbid_observer_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S54 | B5 | `obs3-user-14` | 普通试用人员 | `general_user_abnormal_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S55 | B6 | `obs3-user-15` | 异常输入 / 边界输入场景 | `boundary_input_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S56 | B6 | `obs3-user-16` | 总控管理员 | `admin_control_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S57 | B6 | `obs3-user-17` | 技术标主编 | `chief_editor_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S58 | B6 | `obs3-user-18` | 施工组织设计编制人员 | `construction_org_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S59 | B6 | `obs3-user-19` | 专项施工方案编制人员 | `special_plan_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S60 | B6 | `obs3-user-20` | 进度计划编制人员 | `schedule_planner_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S61 | B6 | `obs3-user-01` | 质量安全复核人员 | `quality_safety_reviewer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S62 | B6 | `obs3-user-02` | 商务 / 清单协同人员 | `commercial_boq_collab_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S63 | B7 | `obs3-user-03` | 项目资料整理人员 | `document_controller_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S64 | B7 | `obs3-user-04` | ZBid 评标辅助观察人员 | `zbid_observer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S65 | B7 | `obs3-user-05` | 普通试用人员 | `general_user_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S66 | B7 | `obs3-user-06` | 异常输入 / 边界输入场景 | `boundary_input_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S67 | B7 | `obs3-user-07` | 总控管理员 | `admin_control_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S68 | B7 | `obs3-user-08` | 技术标主编 | `chief_editor_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S69 | B7 | `obs3-user-09` | 施工组织设计编制人员 | `construction_org_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |
| S70 | B7 | `obs3-user-10` | 专项施工方案编制人员 | `special_plan_writer_routine_third_cycle_observation_preview_payload` | ZDoc 200; ZBid 200 | Pass |

For every final effective scenario:

- ZDoc outbound sent the preview-only payload.
- ZBid receiver received the preview-only payload.
- `preview_packet` was readable.
- `validator_result` was readable.
- `blocked_reasons` was readable.
- `preview_only=true`.
- `no_write=true`.
- `no_evidence=true`.
- The five prohibited flags were false.
- No rollback was required.

## 7. HTTP result summary

Final effective third-cycle run:

- ZDoc `POST /local-trial/preview-only`: 70/70 HTTP 200.
- ZBid `POST /local-llm/zdoc-preview-only/receive`: 70/70 HTTP 200.
- Non-200 effective responses: 0.

Pre-effective records:

- Explicit illegal enum calibration: 10 ZDoc HTTP 200, 0 ZBid sends, 10/10 blocked before network-send.
- Initial payload-shape check: 70 ZDoc HTTP 200, 25 preview-only ZBid sends, 45 adapter blocks due payload binding-status calibration. This initial shape check is not counted as final effective observation-period traffic.

Observed latency for the final effective run:

- ZDoc preview-only entry latency: minimum 0.528 ms, median 1.607 ms, maximum 3.401 ms.
- ZDoc outbound to ZBid receiver latency: minimum 1.043 ms, median 3.076 ms, maximum 5.551 ms.

These latency values are local controlled-run observations only. They are not production capacity or formal load-test results.

## 8. Preview-only / no-write / no-evidence review

Final effective third-cycle result:

- `preview_only=true`: 70/70.
- `no_write=true`: 70/70.
- `no_evidence=true`: 70/70.

Boundary meaning:

- The results are preview-only.
- The results are advisory only.
- The results are not evidence.
- The results are not scoring basis.
- The results do not authorize writeback.
- The results do not authorize formal business data write.

## 9. Forbidden endpoint and forbidden write review

Authorized endpoints called:

- ZDoc: `POST /local-trial/preview-only`.
- ZBid: `POST /local-llm/zdoc-preview-only/receive`.

Forbidden endpoints not called:

- `/generate`
- `/export_docx`
- `/review/apply`
- Any ZBid writeback endpoint
- Any unknown business endpoint outside the authorized preview-only path

Forbidden writes not observed:

- DOCX generation: no.
- `output/job/export` write: no.
- Formal evidence write: no.
- Formal scoring-basis write: no.
- ZBid writeback: no.
- Formal business data write: no.

## 10. ZDoc to ZBid send and receive result

Final effective third-cycle run:

- ZDoc outbound sent: 70/70.
- ZBid receiver received: 70/70.
- Target endpoint: `POST /local-llm/zdoc-preview-only/receive`.
- Payload scope: `preview_packet`, `validator_result`, `blocked_reasons`, and no-write / no-formal-chain flags.

The outbound adapter did not send formal evidence, DOCX, formal scoring result, writeback data, or formal business data.

## 11. Step 260 two-cycle baseline execution

The third-cycle final effective run complied with the Step 260 two-cycle observation baseline:

- Effective observation-period requests were separated from calibration and payload-shape checks.
- Final effective requests remained preview-only / no-write / no-evidence.
- Illegal ZBid enum calibration was blocked before network-send.
- Five no-write / no-formal-chain flags remained false.
- No formal endpoint fallback occurred.
- No writeback, evidence, scoring, DOCX, or `output/job/export` path was opened.
- Service use was temporary and local.
- Services were stopped after the run.
- Ports were released after shutdown.

## 12. Comparison with Step 257 and Step 259

| Cycle | Effective requests | Batches | Simulated users | Role / scenario categories | Abnormal / boundary requests | HTTP 200 | Regression |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Step 257 | 50 | 5 | 20 | 11 | 12 | ZDoc 50/50; ZBid 50/50 | None |
| Step 259 | 60 | 6 | 20 | 11 | 18 | ZDoc 60/60; ZBid 60/60 | None |
| Step 261 | 70 | 7 | 20 | 11 | 20 | ZDoc 70/70; ZBid 70/70 | None |

Three-cycle cumulative observation state after Step 261:

- Effective requests: 180.
- Batches: 18.
- Simulated users: 20.
- Role / scenario categories: 11.
- Abnormal / boundary effective requests: 50.
- Effective ZDoc HTTP 200: 180/180.
- Effective ZBid HTTP 200: 180/180.
- Preview-only / no-write / no-evidence: 180/180.
- Five prohibited flags false: 180/180.

## 13. Regression conclusion

No regression was observed against Step 257 or Step 259.

The third-cycle final effective run increased the observation scope while preserving:

- HTTP 200 behavior.
- ZDoc outbound send success.
- ZBid receiver acceptance.
- `preview_only=true`.
- `no_write=true`.
- `no_evidence=true`.
- Five prohibited flags false.
- No DOCX generation.
- No `output/job/export` write.
- No ZBid writeback.
- No formal-chain fallback.

## 14. Preflight payload calibration and boundary blocking record

Pre-effective records were separated from the final effective observation-period count.

Explicit illegal enum calibration:

- Count: 10.
- ZDoc result: 10/10 HTTP 200.
- Invalid enum blocked: 10/10.
- Sent to ZBid: 0/10.
- Formal fallback: no.
- Writeback: no.
- Evidence: no.
- Scoring basis: no.

Initial payload-shape check:

- Count: 70.
- Purpose: verify payload field compatibility before the final effective run.
- ZDoc result: 70/70 HTTP 200.
- Preview-only ZBid sends during shape check: 25.
- Adapter blocks during shape check: 45.
- Reason: initial test payload used a binding-status value outside the current preview-only enum.
- Counted as final effective observation-period requests: no.
- Code changed to resolve this: no.
- Tests/frontend/backend changed to resolve this: no.

The final effective run used legal preview-only field values and completed 70/70 successful ZDoc to ZBid preview-only transmissions.

## 15. Illegal ZBid status enum blocking result

Illegal ZBid status enum calibration produced the expected preview-only block:

- `invalid_zbid_input_status`: observed.
- `invalid_zbid_mapping_status`: observed.
- `invalid_zbid_scoring_matrix_status`: observed.
- Blocked before network-send: yes.
- Sent to ZBid receiver: no.
- Fallback to formal endpoint: no.
- Formal write: no.
- Evidence creation: no.
- Scoring-basis write: no.

Representative calibration blocked reasons:

- `invalid_zbid_input_status`
- `invalid_zbid_mapping_status`
- `invalid_zbid_scoring_matrix_status`
- `missing_tender_file_refs`
- `unverifiable_scoring_clause_refs`
- `missing_evidence_anchor`

## 16. Abnormal input and boundary input behavior

The final effective third-cycle run included 20 abnormal / boundary requests.

Observed behavior:

- All abnormal / boundary effective requests returned ZDoc HTTP 200.
- All abnormal / boundary effective requests returned ZBid HTTP 200.
- All remained preview-only / no-write / no-evidence.
- `blocked_reasons` remained readable.
- `validator_result` remained readable.
- No formal endpoint fallback appeared.
- No rollback was required.

Boundary and abnormal results remain advisory. They must not be treated as evidence or scoring basis.

## 17. Manual review workflow usability

Manual review remained usable for the final effective run.

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

- Reviewers can confirm the preview-only / no-write / no-evidence boundary.
- Reviewers can confirm five false flags.
- Reviewers can inspect `blocked_reasons` for abnormal and boundary requests.
- Reviewers must not convert preview-only output into evidence or scoring basis.

## 18. Error prompt and blocked_reasons readability

Readability remained acceptable in the final effective run.

Observed readability:

- Illegal enum calibration was clearly represented as blocked before ZBid network-send.
- Boundary inputs preserved readable `blocked_reasons`.
- Abnormal inputs preserved readable `blocked_reasons`.
- The initial payload-shape check exposed a field enum mismatch without formal fallback or code change.

Observation item:

- Future trial instructions should continue distinguishing payload-shape calibration from final effective observation traffic.
- Any UI, logging, backend, receiver, or adapter behavior change requires separate authorization.

## 19. Concurrency and response risk observation

The third-cycle run used grouped local calls and is not a production load test.

Final effective latency summary:

- ZDoc latency: min 0.528 ms, median 1.607 ms, max 3.401 ms.
- ZDoc outbound to ZBid receiver latency: min 1.043 ms, median 3.076 ms, max 5.551 ms.
- HTTP failures: 0.
- Regression against Step 257 / Step 259: none.

Risk note:

- The result supports controlled 20-user pilot observation continuity.
- It does not establish long-term production-server capacity.
- It does not establish 50-user formal deployment capacity.
- It does not authorize production concurrency assumptions.

## 20. Findings

Blocking findings:

- None in the final effective third-cycle run.

High-risk findings:

- None in the final effective third-cycle run.

Medium-risk findings:

- None in the final effective third-cycle run.

Low-risk findings:

- None in the final effective third-cycle run.

Observation items:

- Initial payload-shape check found a non-accepted evidence binding status value in trial data construction and the adapter blocked affected payloads. This was resolved by using legal preview-only payload values, without code changes.
- Continue separating calibration and payload-shape checks from effective observation-period counts.
- Continue recording illegal enum blocking.
- Continue checking service shutdown and port release.

## 21. Risk levels

| Risk level | Current result | Handling |
| --- | --- | --- |
| Blocking | None in final effective run | Continue controlled observation only. |
| High risk | None in final effective run | Keep formal-chain prohibition active. |
| Medium risk | None in final effective run | Continue baseline checks and records. |
| Low risk | None in final effective run | Continue routine observation. |
| Observation | Payload-shape calibration must be kept separate from effective counts | Track in future reports; no code/UI/logging change without authorization. |

## 22. Rollback record

Rollback was not required.

Stop conditions checked:

- Formal-chain flag non-false: not observed.
- `/generate` call: not observed.
- `/export_docx` call: not observed.
- `/review/apply` call: not observed.
- ZBid writeback: not observed.
- DOCX generation: not observed.
- `output/job/export` write: not observed.
- Evidence creation: not observed.
- Scoring basis creation: not observed.
- Unknown endpoint call: not observed.
- Formal fallback: not observed.

## 23. Service shutdown and port release result

Services started in Step 261 were stopped after execution:

- ZDoc PID `80330`: stopped.
- ZBid PID `80342`: stopped.
- `127.0.0.1:18766`: no listener after shutdown.
- `127.0.0.1:18767`: no listener after shutdown.

Output path check:

- ZDoc `output/job/export`: no new write observed; path was not present in final check.
- ZBid `output/job/export`: no new write observed; path was not present in final check.

## 24. Step 262 recommendation

Step 262 can be considered as a docs-only third-cycle observation-period review and controlled routine baseline update.

Step 262 should remain:

- docs-only.
- no-code-change.
- no-service.
- no-port-access.
- no-endpoint-call.
- no-writeback.
- no-DOCX.
- no-`output/job/export`.
- no-formal-chain.
- no-50-user-formal-deployment-design.
- no-top-model-upgrade.

Step 262 should archive:

- Step 261 third-cycle effective result.
- 70 effective requests.
- 7 batches.
- 20 simulated users.
- 11 role / scenario categories.
- 20 abnormal / boundary requests.
- 10 illegal enum calibration records.
- Initial payload-shape calibration record.
- HTTP 200 results.
- Preview-only / no-write / no-evidence results.
- Five false flags.
- No regression against Step 257 and Step 259.
- No DOCX, no writeback, no evidence, no scoring basis, no `output/job/export` write.
- Service shutdown and port release result.

## 25. Draft Step 262 authorization request

Suggested Step 262 authorization wording:

```text
执行 Step 262：ZDoc-ZBid 20-user observation-period third-cycle review and controlled routine baseline update。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填入 Step 261 完成后的实际 HEAD>

本步性质：
docs-only / review-and-baseline-update-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
归档 Step 261 第三轮受控观察期执行结果，包括 70 条有效请求、7 个批次、20 个模拟用户、11 类角色 / 场景、20 条异常 / 边界输入、10 条非法枚举校准、payload-shape 校准记录、HTTP 200 结果、preview-only / no-write / no-evidence 复核、五个 false flags 复核、与 Step 257 / Step 259 对比、是否退化结论、问题分级、继续受控观察条件和暂停条件。

严格禁止：
不得修改代码、tests、frontend、backend、既有 docs。
不得运行服务、Ollama、访问端口或调用 endpoint。
不得触发 /generate、/export_docx、/review/apply 或 ZBid 写回。
不得生成 DOCX。
不得写 output/job/export。
不得把 preview-only 结果作为 evidence 或评分依据。
不得进入 50 人正式部署设计。
不得实施顶级模型升级。
不得进入 Step 263。
```
