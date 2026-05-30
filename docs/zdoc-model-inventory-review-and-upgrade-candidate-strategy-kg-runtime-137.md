# KG-RUNTIME-137 ZDoc Model Inventory Review and Upgrade Candidate Strategy

## Scope

- Stage: KG-RUNTIME-137
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD from task: `e2b900e9f896931d5e8e69375f2c44f127558740`
- Baseline tag from task: `v0.1.519-zdoc-user-mediated-model-inventory-intake`
- Prior stages reviewed: KG-RUNTIME-130, KG-RUNTIME-131, and KG-RUNTIME-136
- New artifact: this docs-only model inventory review and upgrade candidate strategy file
- Stop line: do not enter KG-RUNTIME-138

KG-RUNTIME-137 is docs-only. It reviews the model inventory recorded from KG-RUNTIME-136 and defines an upgrade candidate strategy. It does not run Ollama, does not execute `ollama list`, does not query model versions online, does not pull, upgrade, delete, or replace models, and does not enter real use or trial use.

## Review Basis

This document is based only on the user-mediated local model inventory recorded by KG-RUNTIME-136 and the prior planning boundaries recorded by KG-RUNTIME-130 and KG-RUNTIME-131.

KG-RUNTIME-136 completed user-mediated local model inventory intake. KG-RUNTIME-136 did not run Ollama, did not execute `ollama list`, did not execute any other Ollama command, did not upgrade, pull, delete, or replace models, and did not query model versions online.

KG-RUNTIME-137 does not rerun or re-check the local inventory. It does not run a ZDoc service, does not access an endpoint, does not call `/health`, does not call `/kg/read-only-preview`, does not read real KG file body content, does not parse real KG JSON, and does not execute another directory scan.

## User-Mediated Model Inventory

Current model count recorded from KG-RUNTIME-136: `7`.

| # | Name | Recorded Size | Initial Role |
|---:|---|---:|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `84 GB` | Large primary model candidate |
| 2 | `qwen3-coder:30b` | `18 GB` | Programming and toolchain support |
| 3 | `deepseek-r1:32b` | `19 GB` | Reasoning and review support |
| 4 | `qwen3:30b` | `18 GB` | Medium stable baseline |
| 5 | `qwen3:14b` | `9.3 GB` | Medium fallback baseline |
| 6 | `qwen3:8b` | `5.2 GB` | Lightweight validation |
| 7 | `qwen3:0.6b` | `522 MB` | Minimal smoke and fast fallback |

Approximate total recorded model size: about `154 GB`.

This total is a rough sum of the `SIZE` values from the user-provided screenshot/text recorded by KG-RUNTIME-136. It is not a fresh disk measurement, not a runtime allocation check, and not a latest-version confirmation.

## Current Latest-Version Boundary

KG-RUNTIME-137 must not determine which model is the latest available version.

KG-RUNTIME-137 must not query latest model versions because internet version lookup has not been authorized.

KG-RUNTIME-137 must not pull, upgrade, delete, or replace any model.

Any later latest-version confirmation must be separately authorized and must state whether internet access is allowed. Before that authorization exists, no model in the current inventory may be described as the confirmed latest available version.

## Model Purpose Layer Review

| Layer | Current Models | Review Position |
|---|---|---|
| Large primary layer | `qwen3-next:80b-a3b-instruct-q8_0` | Candidate primary model for Chinese long-document understanding and high-quality ZDoc output, subject to later stability and latency validation. |
| Programming / toolchain support layer | `qwen3-coder:30b` | Candidate retained code-assist model for repository work, script review, and implementation support. It should not replace document-quality validation. |
| Reasoning / review layer | `deepseek-r1:32b` | Candidate retained review model for reasoning-heavy checks, plan critique, and output consistency review, subject to later prompt baseline comparison. |
| Medium stable layer | `qwen3:30b`, `qwen3:14b` | Candidate stable baselines for controlled comparison, fallback, and lower-resource long-text testing. |
| Lightweight fast validation layer | `qwen3:8b`, `qwen3:0.6b` | Candidate smoke models for fast no-write checks, runtime availability checks, and quick failure isolation. |
| Retain / rollback layer | All seven current models | Current models should remain available as rollback and comparison references unless a later stage separately authorizes deletion. |

This purpose-layer review is only a planning classification. It does not select a final production model, does not execute model switching, and does not authorize a trial.

## ZDoc Scenario Evaluation

| Scenario | Evaluation Focus | Current Strategy |
|---|---|---|
| Chinese long-document understanding | Long context following, section structure retention, and low hallucination risk | Prefer testing the large primary layer first, then compare with medium stable models before any upgrade decision. |
| Technical bid / construction organization design long-text output | Chinese technical writing quality, chapter completeness, and engineering-appropriate structure | Use fixed prompts for technical bid and construction organization sections before accepting any upgrade candidate. |
| KG preview-only chain response stability | Preserve preview-only, no-write, no-output-chain, no-evidence, and no-scoring boundaries | Validate only through later separately authorized preview-only checks; KG-RUNTIME-137 does not run services or endpoints. |
| Code assistance capability | Repository-aware edits, toolchain reasoning, and bug-risk review | Retain `qwen3-coder:30b` as a specialized support model and compare it separately from document-generation models. |
| Local resource occupancy | Fit under the approximately `107 GB` unified-memory environment and preserve rollback space | Prefer stable candidates that can run reliably without deleting current rollback models. |
| Pre-trial stability | Repeatability, failure recovery, timeout behavior, and boundary compliance | Require fixed baseline prompts and failure-rate records before moving toward controlled trial. |

## Upgrade Candidate Strategy

KG-RUNTIME-137 proposes only a principle-level strategy. It does not execute an upgrade.

The later upgrade candidate strategy should:

- prioritize retaining existing rollback models;
- prefer stable versions over blindly following the newest tag;
- prioritize Chinese long-document understanding and construction organization design output quality;
- prioritize runnability in the approximately `107 GB` unified-memory environment;
- retain at least one lightweight model for fast smoke checks;
- retain at least one code model for development assistance;
- compare candidate quality against fixed ZDoc prompt baselines before model switching;
- preserve the preview-only no-write boundary before any trial authorization.

This strategy does not claim that any listed model is current, latest, best, or production-ready.

## Initial Retention Strategy

The current initial retention strategy is:

- Temporarily retain `qwen3-next:80b-a3b-instruct-q8_0` as the large primary candidate and rollback reference.
- Temporarily retain `qwen3-coder:30b` as the code-assist model.
- Temporarily retain `deepseek-r1:32b` as the reasoning and review model.
- Temporarily retain `qwen3:30b` and `qwen3:14b` as medium stable baselines.
- Treat `qwen3:8b` and `qwen3:0.6b` mainly as lightweight validation and smoke candidates.
- Require later quality baseline validation before deciding whether any model should become the preferred ZDoc model.
- Do not recommend deleting any model in KG-RUNTIME-137.

No deletion, cleanup, replacement, or upgrade should occur unless a later stage separately authorizes the exact model operation and rollback impact.

## Pre-Upgrade Quality Baseline Recommendation

Before any later model upgrade is authorized, define and freeze a minimum quality baseline:

- fixed Chinese technical bid prompt;
- fixed construction organization design chapter prompt;
- fixed KG preview-only structure check;
- fixed long-text summary and structured-output check;
- fixed response-time and failure-rate record;
- fixed no-write / no-output-chain check.

The quality baseline should compare candidate output against the current retained model set without reading real KG file body content, parsing real KG JSON, writing outputs, or connecting generation, export, writeback, RAG, registry, or CI chains unless a later stage separately authorizes a narrower boundary.

## Later Latest-Version Confirmation Method

KG-RUNTIME-138, if separately authorized later, may be a docs-only latest-version lookup readiness / authorization gate.

That later gate should decide whether internet lookup is allowed. If internet lookup is not separately authorized, the workflow must not query latest versions and must not claim a latest available version.

Before KG-RUNTIME-138 or another separately authorized stage allows internet lookup, the system must continue to state only that current latest-version status is unknown.

## Controlled Trial Target Wording

The controlled trial target remains:

- KG safe integration is completed;
- the ZDoc preview-only chain is completed;
- the local model is upgraded to the latest available usable version;
- post-upgrade stability validation passes;
- only then may the project enter a 1 to 2 person controlled trial;
- only after that may the project expand to a 2 to 5 person small-concurrency trial.

KG-RUNTIME-137 does not complete model upgrade, does not complete latest-version confirmation, does not complete post-upgrade stability validation, and does not authorize real use or trial use.

## KG-RUNTIME-138 Authorization Boundary Draft

KG-RUNTIME-138 is not executed by KG-RUNTIME-137.

If KG-RUNTIME-138 is separately authorized later, its boundary draft must be limited to:

- docs-only;
- may propose whether latest-version internet lookup is needed;
- do not query the internet unless the user separately authorizes it;
- do not run Ollama;
- do not execute `ollama list`;
- do not pull models;
- do not delete models;
- do not replace models;
- do not execute upgrade;
- do not run a ZDoc service;
- do not access an endpoint;
- do not read real KG;
- do not parse real KG JSON;
- do not execute another directory scan;
- do not connect generation;
- do not connect export;
- do not connect writeback;
- do not trigger `/generate`;
- do not trigger `/export_docx`;
- do not trigger `/review/apply`;
- do not write `output`, `job`, or `export`;
- do not use preview-only output as evidence;
- do not use preview-only output as scoring;
- do not integrate RAG;
- do not integrate registry;
- do not integrate CI;
- do not enter real use;
- do not enter trial use.

This KG-RUNTIME-138 draft does not authorize model pull, deletion, replacement, upgrade execution, internet lookup, service runtime, endpoint access, real KG access, real KG JSON parsing, directory scanning, generation, export, writeback, evidence use, scoring use, real use, or trial use.

## Explicit Completion State

KG-RUNTIME-137 completes only the docs-only model inventory review and upgrade candidate strategy.

KG-RUNTIME-137 confirms that KG-RUNTIME-136 completed user-mediated local model inventory intake and recorded seven current models with an approximate total size of `154 GB` based on the user-provided screenshot/text size values.

KG-RUNTIME-137 does not run Ollama.

KG-RUNTIME-137 does not execute `ollama list`.

KG-RUNTIME-137 does not execute any other Ollama command.

KG-RUNTIME-137 does not query latest model versions online.

KG-RUNTIME-137 does not determine which model is the latest available version.

KG-RUNTIME-137 does not pull, upgrade, delete, or replace any model.

KG-RUNTIME-137 does not modify adapter, route, helper, `main.py`, frontend, tests, config, or JSON files.

KG-RUNTIME-137 does not run a service, access a port, call an endpoint, read real KG file body content, parse real KG JSON, execute another directory scan, trigger generation, trigger export, trigger writeback, write `output`, `job`, or `export`, integrate RAG, integrate registry, integrate CI, use preview-only output as evidence, or use preview-only output as scoring.

KG-RUNTIME-137 remains outside real use and outside trial use.

KG-RUNTIME-138 was not entered.
