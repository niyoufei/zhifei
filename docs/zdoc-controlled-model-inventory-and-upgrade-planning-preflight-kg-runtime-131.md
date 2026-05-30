# KG-RUNTIME-131 ZDoc Controlled Model Inventory and Upgrade Planning Preflight

## Scope

- Stage: KG-RUNTIME-131
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD from task: `a4de7bd3178ac6dce1c600ab0a65b6d6b73b4e86`
- Baseline tag from task: `v0.1.513-zdoc-model-upgrade-readiness-gate`
- Prior stages reviewed: KG-RUNTIME-129 and KG-RUNTIME-130
- New artifact: this docs-only controlled model inventory and upgrade planning preflight file
- Stop line: do not enter KG-RUNTIME-132

KG-RUNTIME-131 is docs-only. It performs controlled model inventory and upgrade planning preflight only. It does not collect the local model inventory, does not execute a model upgrade, does not run Ollama, does not run `ollama list`, and does not pull, delete, replace, or upgrade any model.

KG-RUNTIME-130 has completed model-upgrade readiness review. The current model upgrade has not been executed. The current state must not enter real use and must not enter trial use.

## Review Basis

This document is based only on static reading of the authorized prior documents:

- `docs/zdoc-model-upgrade-readiness-review-and-controlled-upgrade-authorization-gate-kg-runtime-130.md`
- `docs/zdoc-kg-preview-only-controlled-completion-internal-validation-pass-frozen-audit-package-and-model-upgrade-readiness-authorization-gate-kg-runtime-129.md`

KG-RUNTIME-131 does not modify adapter, route, helper, or `main.py`. It does not modify frontend, tests, config, or JSON files.

KG-RUNTIME-131 does not start a service, bind or access a port, call `/health`, call `/kg/read-only-preview`, trigger `/generate`, trigger `/export_docx`, trigger `/review/apply`, trigger ZBid writeback, run Ollama, run `ollama list`, upgrade a model, pull a model, delete a model, replace a model, run `pytest`, run `py_compile`, integrate RAG, integrate a prompt registry, integrate a system instruction registry, or integrate CI.

KG-RUNTIME-131 does not read real KG file body content, does not parse real KG JSON, does not perform another directory scan, and does not read, copy, move, delete, or parse `AI知识图谱大全`.

## Completed Capability Recognized

The current completed capability set is limited to:

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

These completed items establish only a content-safe, preview-only, controlled completion internal validation boundary for ZDoc KG integration. They do not establish model-upgrade completion, production readiness, evidence readiness, scoring readiness, real-use readiness, or trial readiness.

## Not Yet Completed Capability

The following capabilities remain incomplete:

- local model inventory collection;
- latest available version confirmation;
- upgrade candidate model confirmation;
- pre-upgrade disk and backup checks;
- upgrade execution;
- post-upgrade stability validation;
- post-upgrade output quality regression;
- post-upgrade preview-only chain regression;
- 1 to 2 person controlled trial;
- 2 to 5 person small-concurrency trial.

No downstream stage may treat the current PASS state as model-upgrade completion, latest-version confirmation, output-quality completion, real-use readiness, or trial readiness.

## Model Inventory Collection Planning

KG-RUNTIME-131 does not collect the local model inventory.

If a later stage needs to collect the local model inventory, it must be separately authorized and limited to the minimum read-only command needed for inventory collection. The recommended next-stage boundary should allow only `ollama list` or an equivalent read-only model inventory command.

The following limits apply to KG-RUNTIME-131:

- do not run Ollama;
- do not run `ollama list`;
- do not read unnecessary directories;
- do not scan the full disk;
- do not read real KG file body content;
- do not parse real KG JSON.

## Version Confirmation Planning

KG-RUNTIME-131 does not determine the latest available version.

If a later stage needs to confirm the latest available version, it must be separately authorized and must state whether internet access is allowed and which source of truth may be used. Without that authorization:

- do not access the internet to confirm model versions;
- do not claim a concrete latest available version;
- do not pull models;
- do not upgrade models.

## Upgrade Candidate Principles

A later candidate selection stage should prefer a candidate model that:

- prioritizes stable versions;
- fits the local hardware and runtime constraints;
- can be rolled back cleanly;
- supports long documents, Chinese technical bid writing, and construction organization design scenarios;
- does not let "latest" override stability.

KG-RUNTIME-131 does not select an actual upgrade candidate.

## Disk, Backup, and Rollback Planning

Before any later upgrade is authorized, the upgrade plan must confirm:

- enough disk space for the retained old model, the candidate model, temporary download or extraction space if applicable, and authorized validation outputs;
- backup coverage for repository HEAD, branch, tag reference, and model-selection configuration if relevant;
- a rollback target before the upgrade starts;
- a no-deletion boundary for the old model unless later separately authorized.

The rollback plan must require:

- keep the old model before upgrade;
- record old model name, tag, size, and update time;
- roll back to the old model if upgrade, load, or validation fails;
- do not delete the old model unless later separately authorized.

KG-RUNTIME-131 does not inspect disk usage, does not create backups, and does not validate rollback.

## Stability Validation Plan

After a separately authorized upgrade, minimum stability validation should proceed in this order:

1. Run a local idle check.
2. Run a fixed prompt baseline check.
3. Run ZDoc preview-only chain regression.
4. Observe stability across continuous multi-turn use.
5. Only then prepare for small-scope trial authorization.

This validation plan is not executed in KG-RUNTIME-131.

## Output Quality Validation Plan

After a separately authorized upgrade, output quality validation should cover:

- Chinese long-document understanding;
- structured expression for technical bid content;
- construction organization design chapter-output stability;
- prohibition on fabricating engineering parameters;
- preservation of preview-only no-writeback behavior;
- preservation of KG safety boundaries.

Output quality validation must not use preview-only output as evidence or scoring unless a later stage separately authorizes that boundary. It must not read real KG file body content or parse real KG JSON unless a later safe boundary is explicitly authorized.

## Trial Target Wording

The trial-readiness target remains:

- KG safe integration is completed;
- the ZDoc preview-only chain is completed;
- the local model is upgraded to the latest available usable version;
- post-upgrade stability validation passes;
- only then may the project enter a 1 to 2 person controlled trial;
- only after that may the project expand to a 2 to 5 person small-concurrency trial.

Before model upgrade and post-upgrade stability validation pass, the system must remain outside real use and outside trial use.

## KG-RUNTIME-132 Controlled Local Model Inventory Collection Authorization Gate Draft

KG-RUNTIME-132 was not executed by KG-RUNTIME-131.

If KG-RUNTIME-132 is separately authorized later, its draft boundary must be limited to controlled local model inventory collection only:

- only allow minimum read-only model inventory collection;
- consider allowing only a single `ollama list` command;
- do not pull models;
- do not delete models;
- do not replace models;
- do not run upgrade;
- do not run a ZDoc service;
- do not access an endpoint;
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

KG-RUNTIME-131 only performs controlled model inventory and upgrade planning preflight.

KG-RUNTIME-131 does not execute model inventory collection.

KG-RUNTIME-131 does not execute model upgrade.

KG-RUNTIME-131 does not authorize model upgrade.

KG-RUNTIME-131 does not authorize real use.

KG-RUNTIME-131 does not authorize trial use.

KG-RUNTIME-132 was not entered.
