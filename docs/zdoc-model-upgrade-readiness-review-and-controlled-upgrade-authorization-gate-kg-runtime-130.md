# KG-RUNTIME-130 ZDoc Model-Upgrade Readiness Review and Controlled Upgrade Authorization Gate

## Scope

- Stage: KG-RUNTIME-130
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD from task: `c4736f344743cbfa9be2a0a4bbf56899681bd88d`
- Baseline tag from task: `v0.1.512-zdoc-kg-controlled-completion-pass-model-upgrade-readiness-gate`
- Prior stages reviewed: KG-RUNTIME-128 and KG-RUNTIME-129
- New artifact: this docs-only readiness review file
- Stop line: do not enter KG-RUNTIME-131

KG-RUNTIME-130 is docs-only. It performs model-upgrade readiness review and sets the next controlled model inventory / upgrade planning authorization gate. It does not execute model upgrade, does not run Ollama, and does not pull, delete, replace, or select a concrete latest model version.

## Review Basis

This document is based only on static reading of the authorized prior documents and helper / adapter / route files:

- `docs/zdoc-kg-preview-only-controlled-completion-internal-validation-pass-frozen-audit-package-and-model-upgrade-readiness-authorization-gate-kg-runtime-129.md`
- `docs/zdoc-kg-preview-only-integration-controlled-completion-internal-no-server-validation-kg-runtime-128-review.md`
- `backend/kg_content_safe_output_contract.py`
- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`

KG-RUNTIME-130 did not modify adapter, route, helper, or `main.py`. It did not modify frontend, tests, config, or JSON files.

KG-RUNTIME-130 did not start a service, bind or access a port, call `/health`, call `/kg/read-only-preview`, trigger `/generate`, trigger `/export_docx`, trigger `/review/apply`, trigger ZBid writeback, run Ollama, upgrade a model, pull a model, delete a model, replace a model, run `pytest`, run `py_compile`, integrate RAG, integrate a prompt registry, integrate a system instruction registry, or integrate CI.

KG-RUNTIME-130 did not read real KG file body content, did not parse real KG JSON, did not perform another directory scan, and did not read, copy, move, delete, or parse `AI知识图谱大全`.

## Prior Stage State

KG-RUNTIME-128 internal no-server validation has PASS status.

KG-RUNTIME-129 froze the KG-RUNTIME-128 PASS result as an internal technical validation artifact and set a later model-upgrade readiness authorization gate.

The KG-RUNTIME-128 / KG-RUNTIME-129 result remains internal validation only. It does not authorize real use, trial use, evidence use, scoring use, model upgrade, generation, export, writeback, RAG, registry integration, or CI integration.

## Completed Capability Recognized

The current completed capability set is limited to the following:

- KG content-safe route-layer PASS;
- `preview_only` / `audit_only` / `prohibited` mapping;
- `preview_only_response`;
- `zdoc_preview_only_integration`;
- `build_zdoc_preview_only_payload`;
- `build_zdoc_preview_only_adapter_payload`;
- route envelope / metadata pass-through basis;
- helper / adapter layer no-server smoke PASS;
- route-layer no-server smoke PASS;
- preview-only controlled completion internal validation PASS.

These completed items establish only a content-safe, preview-only, controlled completion internal validation boundary for ZDoc KG integration. They do not establish model-upgrade completion or trial readiness.

## Not Yet Completed Capability

The following capabilities remain incomplete:

- local model upgrade;
- post-upgrade stability validation;
- post-upgrade output quality regression;
- post-upgrade performance / response-time observation;
- post-upgrade failure rollback validation;
- formal 1 to 2 person controlled trial;
- 2 to 5 person small-concurrency trial.

No downstream stage may treat the current PASS state as model-upgrade completion, production readiness, evidence readiness, scoring readiness, or trial readiness.

## Trial Target Wording

The trial-readiness target is:

- KG safe integration is completed;
- the ZDoc preview-only chain is completed;
- the local model is upgraded to the latest available usable version;
- post-upgrade stability validation passes;
- only then may the project enter a 1 to 2 person controlled trial;
- only after that may the project expand to a 2 to 5 person small-concurrency trial.

Before model upgrade and post-upgrade stability validation pass, the system must remain outside real use and outside trial use.

## Model-Upgrade Readiness Review

### Pre-Upgrade Backup Requirements

Before any later model operation is authorized, the operator must have a rollback-ready baseline that covers:

- current repository HEAD, branch, and tag reference;
- current application configuration relevant to model selection;
- current local model inventory, if separately authorized to query it;
- current disk usage and available free space;
- a written rollback target and rollback command plan;
- a record of which model artifacts are retained and must not be deleted.

The backup requirement is planning-only in KG-RUNTIME-130. This stage does not create, delete, move, export, or validate model artifacts.

### Current Model Inventory Boundary

KG-RUNTIME-130 does not read the current local model inventory.

A future inventory step requires separate authorization. If that step needs Ollama or another local model command, the authorization must explicitly allow the exact command and must still prohibit pull, delete, replacement, and upgrade operations unless separately approved.

### Latest Available Version Confirmation Boundary

KG-RUNTIME-130 does not determine a concrete latest model version.

If latest available versions must be confirmed later, that must be separately authorized and must state whether internet access is allowed, whether local model inventory may be queried, and which source of truth may be used. Without that authorization, no document or workflow may claim a concrete latest model version.

### Upgrade Candidate Selection Principles

A later candidate-selection plan should prefer a model candidate that:

- is compatible with the local runtime and hardware;
- fits available disk and rollback space;
- has a stable release or tag suitable for controlled validation;
- can be compared against the current baseline without changing generation, export, writeback, RAG, or registry chains;
- supports preview-only validation first;
- can be rolled back without deleting the prior usable model.

KG-RUNTIME-130 does not select the actual candidate.

### Disk Space and Rollback Space Requirements

Any later upgrade plan must confirm enough space for:

- the existing model retained for rollback;
- the candidate model artifact;
- temporary download or extraction space, if applicable;
- logs or validation outputs explicitly authorized for the upgrade stage;
- emergency rollback without deleting the previous model.

No model may be deleted in order to make space unless a separate deletion authorization explicitly names the model and rollback impact.

### Upgrade Failure Rollback Plan

A later upgrade plan must define rollback before upgrade begins:

- stop the upgrade attempt if pull, verification, load, or smoke validation fails;
- keep the pre-upgrade model available;
- restore model selection to the pre-upgrade model;
- re-run only the separately authorized minimum stability checks;
- record failure mode, rollback action, and resulting state;
- keep the system outside trial use until rollback state is validated.

KG-RUNTIME-130 does not perform rollback validation.

### Post-Upgrade Minimum Stability Validation Plan

After a separately authorized upgrade, minimum stability validation should confirm:

- the selected model can be listed or resolved by the local runtime;
- the model can complete a minimal controlled prompt only if explicitly authorized for that stage;
- the runtime does not crash, hang, or exceed agreed timeout thresholds;
- repeated minimal calls produce structurally valid responses;
- failure states are observable and recoverable;
- the application remains disconnected from generation, export, writeback, RAG, registry, CI, and real KG content.

This plan is not executed in KG-RUNTIME-130.

### Post-Upgrade Output Quality Validation Plan

After a separately authorized upgrade, output quality validation should compare the candidate model against the existing baseline using controlled, non-real-KG prompts only, unless a later stage explicitly authorizes a different safe dataset.

The validation should assess:

- instruction following;
- refusal and boundary compliance;
- structure stability;
- hallucination risk;
- response completeness;
- Chinese technical writing quality if applicable;
- no evidence or scoring claims unless a later stage explicitly authorizes such use.

This plan must not read real KG bodies or parse real KG JSON.

### Post-Upgrade Preview-Only Regression Plan

After a separately authorized upgrade and stability check, preview-only regression should confirm the ZDoc KG boundary still preserves:

- default-off behavior;
- manual-trigger requirement;
- read-only boundary;
- `preview_only` / `audit_only` / `prohibited` separation;
- `preview_only_response`;
- `zdoc_preview_only_integration`;
- route envelope / metadata pass-through;
- no generation, export, writeback, evidence, scoring, RAG, registry, or CI integration.

Any preview-only regression must remain no-real-KG unless a later stage explicitly authorizes a safe real-KG boundary.

### No Direct Trial After Upgrade

Model upgrade alone must not move the project into real use or trial use.

The minimum gate after upgrade is:

- upgrade completed under separate authorization;
- rollback path retained and verified;
- minimum stability validation passed;
- output quality regression passed;
- preview-only regression passed;
- no connection to generation, export, or writeback chains;
- separate trial authorization issued.

Without all of these, 1 to 2 person controlled trial remains blocked. The 2 to 5 person small-concurrency trial remains blocked until after the 1 to 2 person controlled trial is separately completed and reviewed.

### Generation / Export / Writeback Prohibition

Before and after model upgrade, the KG / ZDoc preview-only chain must not connect to:

- `/generate`;
- `/export_docx`;
- `/review/apply`;
- ZBid writeback;
- output, job, or export writes;
- document body writes;
- RAG;
- prompt registry;
- system instruction registry;
- CI.

Model upgrade readiness does not weaken the preview-only boundary.

## KG-RUNTIME-131 Controlled Model Inventory / Upgrade Planning Authorization Gate Draft

KG-RUNTIME-131 was not executed by KG-RUNTIME-130.

If KG-RUNTIME-131 is separately authorized later, its draft boundary must be limited to controlled model inventory / version strategy / upgrade planning review only:

- only allow model inventory, version strategy, and upgrade-plan level controlled review;
- do not pull models;
- do not delete models;
- do not replace models;
- do not run formal upgrade;
- if running Ollama to query the local model inventory is needed, require separate authorization;
- do not run a service;
- do not access a ZDoc endpoint;
- do not read real KG;
- do not parse real KG JSON;
- do not execute another directory scan;
- do not integrate frontend;
- do not integrate `/generate`;
- do not integrate `/export_docx`;
- do not integrate `/review/apply`;
- do not write `output`, `job`, or `export`;
- do not run `pytest` or `py_compile`;
- do not integrate RAG, registry, or CI;
- do not enter real use or trial use.

This draft does not authorize model pull, deletion, replacement, upgrade execution, service runtime, endpoint access, real KG access, test execution, CI integration, or trial use.

## Explicit Non-Completion State

KG-RUNTIME-130 only performs readiness review and sets an authorization gate.

KG-RUNTIME-130 does not execute model upgrade.

KG-RUNTIME-130 does not authorize model upgrade.

KG-RUNTIME-130 does not determine the latest available model version.

KG-RUNTIME-130 does not authorize real use.

KG-RUNTIME-130 does not authorize trial use.

KG-RUNTIME-130 does not authorize evidence.

KG-RUNTIME-130 does not authorize scoring.

KG-RUNTIME-130 does not enter KG-RUNTIME-131.

## Conclusion

KG-RUNTIME-130 completes a docs-only model-upgrade readiness review and controlled upgrade authorization gate.

The project may recognize KG-RUNTIME-128 internal no-server validation as PASS and KG-RUNTIME-129 as the frozen PASS package with a model-upgrade readiness gate. The model upgrade itself remains unexecuted, the latest model version remains undetermined, post-upgrade stability and quality validation remain incomplete, and real use / trial use remain blocked.

KG-RUNTIME-131 was not entered.
