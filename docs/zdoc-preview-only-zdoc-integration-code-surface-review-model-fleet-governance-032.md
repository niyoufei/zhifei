# MODEL-FLEET-GOVERNANCE-032: ZDoc Preview-Only Integration Code Surface Review

## 1. Node Baseline

- Task node: `MODEL-FLEET-GOVERNANCE-032-ZDOC-PREVIEW-ONLY-INTEGRATION-CODE-SURFACE-REVIEW`
- Node type: docs-only safe read-only ZDoc preview-only integration code surface review
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Start HEAD: `b9f30a6f7dbc0d646070ba4695d8448261b01360`
- Previous node: `MODEL-FLEET-GOVERNANCE-031`
- Previous decision: `ZDOC INTEGRATION IMPLEMENTATION AUTHORIZATION GATE FORMED / SURFACE REVIEW REQUIRED / NO TRIAL AUTHORIZED`

This node did not modify code, tests, runtime configuration, output files, job files, export files, KG data, model state, ZDoc service state, or endpoint state.

## 2. Inputs Reviewed

Required prior docs were reviewed:

- `docs/zdoc-preview-only-output-post-processing-zdoc-integration-implementation-authorization-gate-model-fleet-governance-031.md`
- `docs/zdoc-preview-only-validation-result-review-and-zdoc-integration-gate-model-fleet-governance-030.md`
- `docs/zdoc-preview-only-output-post-processing-validation-execution-record-model-fleet-governance-029.md`
- `docs/zdoc-output-post-processing-code-review-and-preview-only-validation-gate-model-fleet-governance-028.md`
- `docs/zdoc-single-model-output-post-processing-code-implementation-record-model-fleet-governance-027.md`
- `docs/zdoc-single-model-output-post-processing-code-implementation-authorization-gate-model-fleet-governance-026.md`

Safe repository review inputs were limited to allowlisted source/test/config/frontend paths generated from:

- `backend`
- `frontend`
- `tests`
- `config`

The review used only allowlisted file names and restricted keyword searches. No full-repository `rg` was run. No real KG directory, unknown JSON body, output artifact, job artifact, export artifact, service endpoint, model command, or runtime state was read or executed.

## 3. Safe Review Method

The safe review method was:

1. Capture baseline with `git status --short` and `git rev-parse HEAD`.
2. Read the six required prior governance docs.
3. Enumerate only safe candidate files under the allowlisted directories and extensions.
4. Exclude paths containing `知识图谱`, `AI知识图谱大全`, `KG`, `kg`, `graph`, `output`, `job`, `export`, `node_modules`, `__pycache__`, or `.pyc`.
5. Run restricted keyword searches only against the allowlisted file set.
6. Inspect candidate source/test files only with first-260-line reads.
7. Add only this target docs file.

The review did not run tests, start services, access endpoints, invoke Ollama, read or parse real KG, generate images, or trigger generation/export/write-back.

## 4. Candidate Backend Integration Surfaces

### 4.1 First-choice backend surface

`backend/app/routers/local_trial_preview_only.py`

- Route path: `/local-trial/preview-only`
- Identified role: strongest bounded backend integration surface for future preview-only work.
- Existing surface includes preview packet construction, validator result construction, combined `blocked_reasons`, output post-processing metadata, explicit `preview_only`, `no_write`, `no_evidence`, and false formal-chain flags.
- Safety posture: low relative formal-chain proximity because route tests assert no calls to generation, export, review-apply, ZBid writeback, output, job, export, Ollama, or external model APIs.
- Recommended future use: if a later node explicitly authorizes code implementation, this is the safest first backend surface for controlled preview-only integration.

### 4.2 Preview packet helper surface

`backend/zhifei_autoplan/zdoc_zbid_preview_packet.py`

- Identified role: helper surface for deterministic ZDoc to ZBid preview packet shape.
- Existing surface defines required packet fields, preview statuses, mapping statuses, scoring matrix statuses, and current-stage false formal flags.
- Existing blocked reasons include preview-only not being writeback permission and preview-only not being evidence.
- Safety posture: medium risk because it is closer to ZBid integration semantics, but still helper-level and preview-only.
- Recommended future use: safe as a packet contract/reference surface under separate implementation authorization.

### 4.3 Preview input validator surface

`backend/zhifei_autoplan/zbid_preview_input_validator.py`

- Identified role: helper surface for validating preview packet inputs before any future ZBid-facing preview display or handoff.
- Existing surface blocks missing required fields, missing tender/scoring/evidence references, unsafe evidence substitution, thinking-only fallback, unsupported response mode, high-risk unvalidated inputs, failed advisory quality gate, and formal write/export/review/writeback requests.
- Safety posture: medium risk because it encodes ZBid preview acceptance states, but it is validation-only and keeps current-stage formal flags false.
- Recommended future use: safe as a validation helper only; should not be extended toward writeback without a separate gate.

### 4.4 Outbound adapter surface

`backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`

- Identified role: ZDoc to ZBid preview-only outbound adapter and receiver configuration surface.
- Existing surface includes `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED`, `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT`, `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED`, receiver path `/local-llm/zdoc-preview-only/receive`, default-off behavior, endpoint allowlist checks, no-write false flags, and network-send status metadata.
- Safety posture: high caution because this module contains a network sender function and endpoint preparation logic, even though default behavior is disabled/configured-not-sent unless explicitly enabled.
- Recommended future use: not the first implementation surface. Only touch in a later explicit authorization gate that keeps network disabled by default and uses synthetic/fake receiver tests.

### 4.5 Secondary local LLM preview-safe surface

`backend/app/routers/local_llm_preview_safe.py`

- Route path: `/local-llm/preview-safe`
- Identified role: isolated preview-safe endpoint with feature flags and explicit no-write metadata.
- Existing surface includes `_safe_endpoint_flag_enabled`, `_safe_endpoint_ollama_flag_enabled`, fake-only/default-off handling, false formal-chain flags, and stripping formal output fields from responses.
- Safety posture: secondary only. It has real-adapter bridge code paths and Ollama-adjacent imports, so it should not be the first ZDoc preview-only integration implementation surface for this chain.

### 4.6 Broad app registration surface

`backend/app/main.py`

- Identified role: router registration surface.
- Safety posture: high blast-radius app entry surface.
- Recommended future use: avoid first implementation changes unless a later node explicitly authorizes route registration changes and proves no service/runtime execution is required.

### 4.7 Surfaces to avoid for first implementation

The following surfaces are formal-chain-adjacent or writeback/export-adjacent and should not be touched first:

- `backend/app/routers/actions_bridge.py`
- `backend/app/routers/zhifei_autoplan.py`
- `backend/zhifei_autoplan/zbid_isolation_guard.py`
- Any generation, export, review-apply, writeback, output, job, export, or real KG path

## 5. Candidate Frontend Integration Surfaces

No concrete frontend page/component implementation surface was identified by this node's safe allowlist review.

- The safe allowlist review did not identify a frontend file that currently calls `/local-trial/preview-only`.
- The safe allowlist review did not identify a frontend component that currently displays `preview_packet`, `validator_result`, or `blocked_reasons` from `/local-trial/preview-only`.
- `backend/tests/test_preview_only_route_frontend_integration_plan_schema.py` records a synthetic future frontend integration plan, but it is a backend test/schema planning artifact, not an actual frontend implementation surface.

Frontend implementation surface status: `未在本节点安全 allowlist 复核中查明`.

## 6. Candidate Test / Fixture Surfaces

The following safe synthetic test/fixture surfaces were identified:

- `backend/tests/test_local_trial_preview_only_route.py`: route-level preview-only/no-write metadata, preview packet, validator result, blocked reasons, output post-processing, and no output/job/export write assertions.
- `backend/tests/test_zdoc_zbid_preview_packet.py`: deterministic preview packet contract, enum locks, formal false flags, blocked evidence/writeback/export/review/output requests.
- `backend/tests/test_zdoc_zbid_preview_outbound.py`: outbound config default-disabled behavior, configured-not-sent behavior, disallowed endpoint blocking, payload no-write false flags, and synthetic sender/receiver handling.
- `backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py`: synthetic contract schema, required fields, audit fields, enum/status validation, false formal flags, and fake request metadata.
- `backend/tests/test_zbid_preview_input_validator.py`: preview input validator behavior and blocked-reason coverage.
- `backend/tests/test_local_llm_preview_safe_endpoint.py`: preview-safe endpoint flag/default-off behavior, no formal output fields, no-write metadata, fake helper behavior, and real-adapter bridge isolation checks.
- `backend/tests/test_preview_only_route_frontend_integration_plan_schema.py`: synthetic future frontend integration plan schema; useful as documentation of frontend expectations, not as actual frontend code.

No tests were run and no test files were modified in this node.

## 7. Candidate Config / Feature Flag Surfaces

Identified config/feature-flag-like surfaces:

- `backend/app/routers/local_trial_preview_only.py`: request-level `preview_output_post_processing_enabled` toggle for synthetic preview output post-processing.
- `backend/app/routers/local_llm_preview_safe.py`: `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` and `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` are read through safe endpoint feature-flag helpers; this remains secondary because of Ollama-adjacent adapter risk.
- `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`: `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED`, `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT`, and `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED` define outbound preview-only adapter behavior; network send is not first-choice and must remain default-off unless separately authorized.
- `backend/zhifei_autoplan/ollama_preview.py`: local LLM/Ollama-adjacent flag surface referenced by the safe endpoint; this is risky for this chain and should not be first-choice.

No unknown `.json` config body was read or parsed in this node. No direct config file implementation surface was identified as necessary for the next gate.

## 8. Risk Review

### Formal-chain risk

Formal-chain-adjacent files must be avoided unless a future node explicitly authorizes them. This includes generation, export, review-apply, writeback, `actions_bridge`, ZBid snapshot/writeback surfaces, and broad app entry changes.

### Output/job/export risk

Any implementation that writes `output/**`, `job/**`, `export/**`, generates DOCX, writes JSON/Markdown artifacts, or creates runtime job state is out of scope and remains NO-GO.

### Endpoint trigger risk

Outbound/network-capable surfaces, especially `zdoc_zbid_preview_outbound.py`, carry endpoint trigger risk. Existing default-off and configured-not-sent behavior is important and must not be weakened.

### Real KG risk

Real KG and graph data must remain unread and unparsed. Future preview-only implementation must not read `知识图谱/**`, `AI知识图谱大全/**`, KG, kg, graph, or unknown JSON source bodies.

### Frontend unknown risk

Actual frontend surface is not yet proven by this safe review. A later authorization gate should either bind implementation to the backend-only route surface first or separately authorize a narrow frontend file identification step before any frontend edit.

## 9. Recommended Implementation Path

Recommended next implementation path, if and only if a later node explicitly authorizes code changes:

1. Keep the first code implementation target on `backend/app/routers/local_trial_preview_only.py` or its directly associated synthetic tests.
2. Use `zdoc_zbid_preview_packet.py` and `zbid_preview_input_validator.py` as helper/reference surfaces only.
3. Keep all formal flags false and preserve `preview_only`, `no_write`, and `no_evidence`.
4. Do not introduce endpoint calls, service startup, model calls, real KG reads, output/job/export writes, DOCX export, review apply, or ZBid writeback.
5. Treat `zdoc_zbid_preview_outbound.py` as high-caution and not first-choice because of network-send capability.
6. Do not modify broad app registration unless separately authorized.
7. Do not implement frontend changes until a narrow frontend surface is identified or separately authorized.

## 10. NO-GO Statements

The following remain explicitly NO-GO after this node:

- NO-GO for trial.
- NO-GO for real use.
- NO-GO for ZDoc service startup.
- NO-GO for endpoint access.
- NO-GO for formal generation.
- NO-GO for export.
- NO-GO for review apply.
- NO-GO for write-back.
- NO-GO for output/job/export writing.
- NO-GO for real KG read/parse.
- NO-GO for unknown JSON body read/parse.
- NO-GO for Ollama commands, model pull/list/run/rm/serve, model replacement, model downloads, or latest pointer changes.
- NO-GO for image generation or image-model use.
- NO-GO for production, trial, preview execution, stability validation, concurrent validation, or performance validation.

## 11. Current Decision

`ZDOC PREVIEW-ONLY INTEGRATION SURFACE REVIEW COMPLETED / IMPLEMENTATION SURFACE IDENTIFIED / NO CODE CHANGE / NO TRIAL AUTHORIZED`

Backend, test/fixture, and config/feature-flag surfaces were identified. Concrete frontend implementation surface was `未在本节点安全 allowlist 复核中查明`.

## 12. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-033-ZDOC-PREVIEW-ONLY-INTEGRATION-CODE-IMPLEMENTATION-AUTHORIZATION-GATE`

The next node should remain an authorization gate unless ChatGPT explicitly authorizes a narrow code implementation scope. This node does not authorize implementation, trial, endpoint access, service startup, real KG access, output/job/export writing, formal generation, export, review apply, write-back, or model operations.
