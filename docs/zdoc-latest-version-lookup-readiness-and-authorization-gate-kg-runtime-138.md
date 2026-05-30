# KG-RUNTIME-138 ZDoc Latest-Version Lookup Readiness and Authorization Gate

## Scope

- Stage: KG-RUNTIME-138
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD from task: `f81a24fed6e858d63891e863c600c47c8af33f1c`
- Baseline tag from task: `v0.1.520-zdoc-model-inventory-upgrade-candidate-strategy`
- Prior stages reviewed: KG-RUNTIME-130, KG-RUNTIME-136, and KG-RUNTIME-137
- New artifact: this docs-only latest-version lookup readiness and authorization gate file
- Stop line: do not enter KG-RUNTIME-139

KG-RUNTIME-138 is docs-only. It evaluates whether a later latest-version lookup may be authorized and defines the KG-RUNTIME-139 authorization gate draft. It does not perform latest-version lookup, does not run Ollama, does not execute `ollama list`, does not upgrade, pull, delete, or replace models, and does not enter real use or trial use.

## Review Basis

KG-RUNTIME-136 completed user-mediated local model inventory intake.

KG-RUNTIME-137 completed model inventory review and upgrade candidate strategy.

KG-RUNTIME-138 is based only on the archived KG-RUNTIME-136 model inventory intake, the archived KG-RUNTIME-137 upgrade candidate strategy, and the earlier KG-RUNTIME-130 model-upgrade readiness gate.

KG-RUNTIME-138 does not rerun or re-check local inventory. It does not query model versions online. It does not claim any model is the latest available version.

## Current Local Model Inventory

Current model count recorded from KG-RUNTIME-136 and reviewed by KG-RUNTIME-137: `7`.

| # | Name | Recorded Size |
|---:|---|---:|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `84 GB` |
| 2 | `qwen3-coder:30b` | `18 GB` |
| 3 | `deepseek-r1:32b` | `19 GB` |
| 4 | `qwen3:30b` | `18 GB` |
| 5 | `qwen3:14b` | `9.3 GB` |
| 6 | `qwen3:8b` | `5.2 GB` |
| 7 | `qwen3:0.6b` | `522 MB` |

Approximate total recorded model size: about `154 GB`.

This total is a rough sum of the `SIZE` values shown in the user-provided screenshot/text result recorded by KG-RUNTIME-136. It is not a fresh disk measurement, not a runtime allocation check, and not a latest-version confirmation.

## Current Non-Lookup and Non-Upgrade State

- Latest available versions confirmed by KG-RUNTIME-138: no
- Internet model-version lookup performed by KG-RUNTIME-138: no
- Ollama run by KG-RUNTIME-138: no
- `ollama list` run by KG-RUNTIME-138: no
- Other Ollama command run by KG-RUNTIME-138: no
- Model upgraded, pulled, deleted, or replaced by KG-RUNTIME-138: no
- Model upgrade executed by KG-RUNTIME-138: no
- Real use entered by KG-RUNTIME-138: no
- Trial use entered by KG-RUNTIME-138: no

Current latest-version status remains unknown. KG-RUNTIME-138 must not be read as a version confirmation, upgrade recommendation, deletion recommendation, pull recommendation, production-readiness decision, evidence basis, scoring basis, real-use authorization, or trial-use authorization.

## Latest-Version Lookup Readiness Review

### Whether Internet Lookup Is Needed

A later latest-version lookup would require internet access because KG-RUNTIME-136 and KG-RUNTIME-137 only record local inventory and strategy. The archived local inventory does not prove whether newer official versions exist.

KG-RUNTIME-138 does not authorize that lookup. It only records that any latest-version confirmation requires a separate KG-RUNTIME-139 authorization that explicitly allows network access for model-version information lookup.

### Query Object Scope

The later query scope should be limited to the local model families already present on this machine:

- `qwen3-next` series;
- `qwen3-coder` series;
- `qwen3` series;
- `deepseek-r1` series.

The later lookup must stay around existing local model families and must not expand to unrelated model families.

### Query Source Boundary

The later lookup source boundary should be:

- prioritize official model pages, official registries, and official releases;
- may reference the official Ollama library;
- do not use social-media rumors as version evidence;
- do not use third-party unofficial mirrors as upgrade evidence;
- whether these sources may be accessed online must be separately authorized by KG-RUNTIME-139.

KG-RUNTIME-138 does not access those sources.

### Query Result Archiving

If KG-RUNTIME-139 is separately authorized later, the lookup result should be archived as a docs-only record with:

- query date and stage identifier;
- exact model family queried;
- source URL or official registry name;
- latest available version or tag as reported by the authorized source;
- source boundary notes;
- explicit statement that lookup did not pull, run, delete, replace, or upgrade a model.

The archive should remain a planning artifact unless a later stage separately authorizes model operations.

### Candidate Strategy Input Only

Any KG-RUNTIME-139 lookup result may only feed the upgrade candidate strategy. It must not directly change the local model set, runtime selection, ZDoc service behavior, generation chain, export chain, writeback chain, RAG, registry, CI, evidence use, scoring use, real use, or trial use.

### Direct Pull and Direct Upgrade Prohibition

A latest-version lookup must not imply permission to pull or upgrade a model.

KG-RUNTIME-139, if later authorized, must prohibit:

- direct model pull;
- direct model upgrade;
- direct model replacement;
- direct model deletion;
- direct runtime use or trial use.

### Rollback Retention Requirement

The existing local models should remain available as rollback and comparison references unless a later stage separately authorizes a named deletion with rollback impact. KG-RUNTIME-138 does not recommend deleting any old model.

### Pre-Upgrade Quality Baseline Requirement

Before any later upgrade is authorized, a quality baseline should be established and frozen. That baseline should cover Chinese long-document understanding, technical bid / construction organization design output quality, structure stability, boundary compliance, response-time and failure behavior, and rollback comparison.

This requirement is planning-only in KG-RUNTIME-138. No quality baseline is executed here, and no model upgrade is executed here.

## KG-RUNTIME-139 Latest-Version Lookup Authorization Boundary Draft

KG-RUNTIME-139 is not executed by KG-RUNTIME-138.

If KG-RUNTIME-139 is separately authorized later, its boundary must be limited to:

- only allow internet lookup of model latest-version information;
- only allow lookup of latest versions for local model families already present on this machine;
- do not run Ollama;
- do not execute `ollama list`;
- do not execute `ollama pull`;
- do not execute `ollama run`;
- do not execute `ollama rm`;
- do not execute `ollama serve`;
- do not upgrade models;
- do not pull models;
- do not delete models;
- do not replace models;
- do not run the ZDoc service;
- do not access an endpoint;
- do not read real KG;
- do not parse real KG JSON;
- do not execute another directory scan;
- do not connect generation;
- do not connect export;
- do not connect writeback;
- do not enter real use or trial use.

KG-RUNTIME-139 must not be treated as authorization for model pull, model deletion, model replacement, model upgrade execution, service runtime, endpoint access, real KG access, real KG JSON parsing, directory scanning, generation, export, writeback, evidence use, scoring use, real use, or trial use.

## Controlled Trial Target Wording

The controlled trial target remains:

- KG safe integration is completed;
- the ZDoc preview-only chain is completed;
- the local model is upgraded to the latest available usable version;
- post-upgrade stability validation passes;
- only then may the project enter a 1 to 2 person controlled trial;
- only after that may the project expand to a 2 to 5 person small-concurrency trial.

KG-RUNTIME-138 does not complete latest-version confirmation, does not complete local model upgrade, does not complete post-upgrade stability validation, and does not authorize real use or trial use.

## Explicit Completion State

KG-RUNTIME-138 completes only the docs-only latest-version lookup readiness review and authorization gate.

KG-RUNTIME-138 confirms that KG-RUNTIME-136 completed user-mediated local model inventory intake.

KG-RUNTIME-138 confirms that KG-RUNTIME-137 completed model inventory review and upgrade candidate strategy.

KG-RUNTIME-138 records the current local model inventory as seven models with an approximate total size of about `154 GB`, based on a rough sum of the user screenshot/text `SIZE` values recorded by KG-RUNTIME-136.

KG-RUNTIME-138 does not confirm the latest available version of any model.

KG-RUNTIME-138 does not query latest model versions online.

KG-RUNTIME-138 does not run Ollama.

KG-RUNTIME-138 does not execute `ollama list`.

KG-RUNTIME-138 does not execute any other Ollama command.

KG-RUNTIME-138 does not pull, upgrade, delete, or replace any model.

KG-RUNTIME-138 does not modify adapter, route, helper, `main.py`, frontend, tests, config, or JSON files.

KG-RUNTIME-138 does not run a service, access a port, call an endpoint, read real KG file body content, parse real KG JSON, execute another directory scan, trigger generation, trigger export, trigger writeback, write `output`, `job`, or `export`, integrate RAG, integrate registry, integrate CI, use preview-only output as evidence, or use preview-only output as scoring.

KG-RUNTIME-138 remains outside real use and outside trial use.

KG-RUNTIME-139 was not entered.
