# KG-RUNTIME-136 ZDoc User-Mediated Local Model Inventory Intake Review

## Scope

- Stage: KG-RUNTIME-136
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD from task: `627d4f343783e24a99f0cb03b80f9f800e1d5b83`
- Baseline tag from task: `v0.1.518-zdoc-ollama-list-blocked-user-mediated-inventory-gate`
- Prior stages reviewed: KG-RUNTIME-132, KG-RUNTIME-134, and KG-RUNTIME-135
- New artifact: this docs-only user-mediated local model inventory intake review file
- Stop line: do not enter KG-RUNTIME-137

KG-RUNTIME-136 is docs-only. It only records the user's manually provided `ollama list` screenshot/text result as a user-mediated local model inventory intake.

KG-RUNTIME-136 did not run Ollama, did not execute `ollama list`, did not execute any other Ollama command, did not upgrade, pull, delete, or replace models, did not query model versions online, and did not enter KG-RUNTIME-137.

## User-Mediated Intake Source

The model inventory below is based only on the user's manually provided `ollama list` screenshot/text result.

KG-RUNTIME-136 did not run a command to re-check or reproduce the inventory.

User-mediated collection status:

- User manually collected local model inventory: yes
- User manually provided `ollama list` screenshot/text result: yes
- KG-RUNTIME-136 accepted the user-provided result for docs-only intake: yes
- KG-RUNTIME-136 executed `ollama list`: no
- KG-RUNTIME-136 executed any other Ollama command: no

The user's supplementary screenshot information also indicates:

- the Ollama server can be manually started by the user;
- the server listens on `127.0.0.1:11434`;
- the Ollama version appears to be approximately `0.21.2`;
- the device information appears to be Apple Metal / Apple M5 Max with approximately `107.5 GiB` GPU memory information.

This supplementary information is recorded only for model inventory intake context. KG-RUNTIME-136 did not start the Ollama service, did not access the port, did not confirm a latest available model version, and did not execute or authorize any model upgrade.

## User-Provided Model Inventory

Current model count recorded from the user-provided result: `7`.

| # | Name | ID | Size | Modified |
|---:|---|---|---:|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `fc9e251d7f37` | `84 GB` | `5 weeks ago` |
| 2 | `qwen3-coder:30b` | `06c1097efce0` | `18 GB` | `5 weeks ago` |
| 3 | `deepseek-r1:32b` | `edba8017331d` | `19 GB` | `5 weeks ago` |
| 4 | `qwen3:30b` | `ad815644918f` | `18 GB` | `5 weeks ago` |
| 5 | `qwen3:14b` | `bddb181c33f2` | `9.3 GB` | `5 weeks ago` |
| 6 | `qwen3:8b` | `500a1f067a9f` | `5.2 GB` | `5 weeks ago` |
| 7 | `qwen3:0.6b` | `7df6b6e09427` | `522 MB` | `5 weeks ago` |

Approximate total recorded model size: about `154 GB`.

This total is a rough sum of the `SIZE` values shown in the user-provided screenshot/text result. It is not a fresh disk measurement, not a runtime capacity check, and not a GPU memory allocation measurement.

## Boundary Confirmation

- Ollama run by KG-RUNTIME-136: no
- `ollama list` run by KG-RUNTIME-136: no
- Other Ollama command run by KG-RUNTIME-136: no
- `ollama pull` run by KG-RUNTIME-136: no
- `ollama run` run by KG-RUNTIME-136: no
- `ollama rm` run by KG-RUNTIME-136: no
- `ollama serve` run by KG-RUNTIME-136: no
- Model upgraded, pulled, deleted, or replaced by KG-RUNTIME-136: no
- Model upgrade executed by KG-RUNTIME-136: no
- Internet model-version lookup performed by KG-RUNTIME-136: no
- Latest available version confirmed by KG-RUNTIME-136: no
- ZDoc service run by KG-RUNTIME-136: no
- Endpoint accessed by KG-RUNTIME-136: no
- `/health` called by KG-RUNTIME-136: no
- `/kg/read-only-preview` called by KG-RUNTIME-136: no
- Real KG file body content read by KG-RUNTIME-136: no
- Real KG JSON parsed by KG-RUNTIME-136: no
- Directory scan executed again by KG-RUNTIME-136: no
- Generation triggered by KG-RUNTIME-136: no
- Export triggered by KG-RUNTIME-136: no
- Writeback triggered by KG-RUNTIME-136: no
- `output`, `job`, or `export` written by KG-RUNTIME-136: no
- Real use entered by KG-RUNTIME-136: no
- Trial use entered by KG-RUNTIME-136: no
- Adapter, route, helper, or `main.py` modified by KG-RUNTIME-136: no
- Frontend, tests, config, or JSON modified by KG-RUNTIME-136: no
- `pytest` run by KG-RUNTIME-136: no
- `py_compile` run by KG-RUNTIME-136: no
- RAG integrated by KG-RUNTIME-136: no
- Registry integrated by KG-RUNTIME-136: no
- CI integrated by KG-RUNTIME-136: no
- Evidence use performed by KG-RUNTIME-136: no
- Scoring use performed by KG-RUNTIME-136: no

KG-RUNTIME-136 only records the user-mediated model inventory intake. It does not authorize model pull, model deletion, model replacement, model upgrade execution, internet version lookup, service runtime, endpoint access, real KG access, real KG JSON parsing, directory scanning, output writing, generation, export, writeback, evidence use, scoring use, real use, or trial use.

## Current Non-Upgrade State

KG-RUNTIME-136 confirms that the user manually provided a local model inventory containing seven models.

KG-RUNTIME-136 does not confirm whether any listed model is the latest available version.

KG-RUNTIME-136 does not confirm whether a newer usable version exists.

KG-RUNTIME-136 does not select an upgrade candidate.

KG-RUNTIME-136 does not execute model upgrade.

KG-RUNTIME-136 does not authorize model upgrade.

KG-RUNTIME-136 does not authorize real use.

KG-RUNTIME-136 does not authorize trial use.

## KG-RUNTIME-137 Authorization Boundary Draft

KG-RUNTIME-137 is not executed by KG-RUNTIME-136.

If KG-RUNTIME-137 is separately authorized later, it may only do model inventory review and upgrade candidate strategy within this boundary:

- analyze version strategy only from the user-mediated model inventory recorded by KG-RUNTIME-136;
- do not pull models;
- do not delete models;
- do not replace models;
- do not execute upgrade;
- whether internet lookup of latest model versions is allowed must be separately authorized later;
- do not run the ZDoc service;
- do not access an endpoint;
- do not read real KG;
- do not parse real KG JSON;
- do not execute another directory scan;
- do not integrate generation;
- do not integrate export;
- do not integrate writeback;
- do not enter real use;
- do not enter trial use.

This draft does not authorize model pull, model deletion, model replacement, model upgrade execution, internet version lookup, service runtime, endpoint access, real KG access, real KG JSON parsing, directory scanning, output writing, generation, export, writeback, evidence use, scoring use, real use, or trial use.

## Explicit Completion State

KG-RUNTIME-136 completed only the docs-only user-mediated local model inventory intake review.

KG-RUNTIME-136 successfully recorded the user's manually provided local model inventory.

KG-RUNTIME-136 recorded seven models with name, id, size, and modified time.

KG-RUNTIME-136 did not run Ollama.

KG-RUNTIME-136 did not execute `ollama list`.

KG-RUNTIME-136 did not execute any other Ollama command.

KG-RUNTIME-136 did not confirm a latest available model version.

KG-RUNTIME-136 did not execute model upgrade.

KG-RUNTIME-136 did not authorize model upgrade.

KG-RUNTIME-136 did not authorize real use.

KG-RUNTIME-136 did not authorize trial use.

KG-RUNTIME-137 was not entered.
