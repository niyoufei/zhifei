# KG-RUNTIME-139 ZDoc Controlled Latest-Version Lookup Review

## Scope

- Stage: KG-RUNTIME-139
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD from task: `23468143029cf76606ff249f4cfd78ad6186645c`
- Baseline tag from task: `v0.1.521-zdoc-latest-version-lookup-readiness-gate`
- Prior stages reviewed: KG-RUNTIME-136, KG-RUNTIME-137, and KG-RUNTIME-138
- New artifact: this docs-only controlled latest-version lookup review file
- Stop line: do not enter KG-RUNTIME-140

KG-RUNTIME-139 is authorized only for read-only latest-version lookup. The lookup is limited to model families already present in the local model inventory recorded by KG-RUNTIME-136 and reviewed by KG-RUNTIME-137 / KG-RUNTIME-138.

KG-RUNTIME-139 does not run Ollama, does not execute `ollama list`, does not execute `ollama pull`, does not execute `ollama run`, does not execute `ollama rm`, does not execute `ollama serve`, does not upgrade, pull, delete, replace, or select a model for use, and does not enter real use or trial use.

## Authorized Lookup Boundary

Lookup was authorized only for the following existing local model families:

- `qwen3-next` series;
- `qwen3-coder` series;
- `qwen3` series;
- `deepseek-r1` series.

Lookup sources were limited to official model pages, official registries, official releases, the official Ollama library, and official model-provider materials. Social-media rumors, unofficial mirrors, and unofficial reposts were not used as version evidence.

KG-RUNTIME-139 forms a latest-version lookup result only. It does not form an upgrade execution, pull request for models, deletion decision, replacement decision, production-readiness decision, evidence basis, scoring basis, real-use authorization, or trial-use authorization.

## Query Time

- Query time recorded by this stage: `2026-05-30 19:05:56 CST`
- Query mode: read-only internet lookup
- Service/runtime mode: no local service started, no endpoint accessed
- Local model runtime mode: no Ollama command executed

## Local Model Inventory Basis

The local model inventory basis remains the KG-RUNTIME-136 user-mediated inventory:

| # | Local model |
|---:|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` |
| 2 | `qwen3-coder:30b` |
| 3 | `deepseek-r1:32b` |
| 4 | `qwen3:30b` |
| 5 | `qwen3:14b` |
| 6 | `qwen3:8b` |
| 7 | `qwen3:0.6b` |

KG-RUNTIME-139 did not rerun local inventory, did not execute `ollama list`, did not scan directories, and did not verify local model files.

## Lookup Result Summary

| Model family | Lookup success | Latest available version / tag found | Relationship to existing local model(s) | Human review still required |
|---|---|---|---|---|
| `qwen3-next` | yes | Official Ollama latest tag: `qwen3-next:latest` / `qwen3-next:80b`; provider model line includes `Qwen/Qwen3-Next-80B-A3B-Instruct` and `Qwen/Qwen3-Next-80B-A3B-Thinking`. | Local `qwen3-next:80b-a3b-instruct-q8_0` is in the same family and appears as an instruct quantized tag, while the Ollama latest alias points to the general `80b` tag. No local change was made. | yes |
| `qwen3-coder` | yes | Series-level official Ollama latest line: `qwen3-coder-next:latest`; existing local-library latest alias: `qwen3-coder:latest` / `qwen3-coder:30b`; provider materials also show `Qwen/Qwen3-Coder-Next` under the Qwen3-Coder line. | Local `qwen3-coder:30b` matches the official Ollama `qwen3-coder:30b` alias, but it is not the newer `qwen3-coder-next` line. No local change was made. | yes |
| `qwen3` | yes | Series-level official Ollama latest line: `qwen3.6:latest` / `qwen3.6:35b`; existing local-library latest alias: `qwen3:latest` / `qwen3:8b`; provider materials include `Qwen3.6-35B-A3B` and earlier `Qwen3-2507` model lines. | Local `qwen3:30b`, `qwen3:14b`, `qwen3:8b`, and `qwen3:0.6b` are in the same broad Qwen3 series but are not `qwen3.6`. No local change was made. | yes |
| `deepseek-r1` | yes | Official Ollama latest tag: `deepseek-r1:latest` / `deepseek-r1:8b`; provider current full model is `deepseek-ai/DeepSeek-R1-0528`; provider current small distilled model is `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`. | Local `deepseek-r1:32b` corresponds to the DeepSeek-R1 distilled Qwen 32B line, while the official Ollama latest alias points to the 0528 Qwen3 8B distilled line. No local change was made. | yes |

No lookup item is `blocked`. No lookup item is marked `insufficient-source` for version lookup, because each family had at least one official Ollama source and at least one official model-provider source or official model-provider registry source. The upgrade meaning of these findings still requires human review and a separate KG-RUNTIME-140 authorization before any candidate strategy is finalized.

## Per-Family Source Records

### qwen3-next

- Query sources:
  - Official Ollama library: `https://ollama.com/library/qwen3-next`
  - Official Qwen Hugging Face model page: `https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct`
  - Official Qwen Hugging Face model page: `https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Thinking`
- Query time: `2026-05-30 19:05:56 CST`
- Source credibility: high; official Ollama library plus official Qwen organization model pages.
- Latest available version / tag:
  - Ollama latest alias: `qwen3-next:latest`
  - Ollama size alias marked latest: `qwen3-next:80b`
  - Provider model line observed: `Qwen/Qwen3-Next-80B-A3B-Instruct` and `Qwen/Qwen3-Next-80B-A3B-Thinking`
- Relationship to local model:
  - Local model: `qwen3-next:80b-a3b-instruct-q8_0`
  - Relationship: same model family, local instruct quantized tag; official Ollama latest alias points to the general `80b` tag, not proof that the local model has been upgraded.
- Human review still required: yes.
- Status: lookup-success.

### qwen3-coder

- Query sources:
  - Official Ollama library: `https://ollama.com/library/qwen3-coder`
  - Official Ollama library: `https://ollama.com/library/qwen3-coder-next`
  - Official Qwen blog: `https://qwenlm.github.io/blog/qwen3-coder/`
  - Official Qwen Hugging Face model page: `https://huggingface.co/Qwen/Qwen3-Coder-Next`
- Query time: `2026-05-30 19:05:56 CST`
- Source credibility: high; official Ollama library plus official Qwen release / model-provider materials.
- Latest available version / tag:
  - Series-level Ollama latest line observed: `qwen3-coder-next:latest`
  - Existing local-library Ollama latest alias: `qwen3-coder:latest`
  - Existing local-library Ollama size alias marked latest: `qwen3-coder:30b`
  - Provider model line observed for newer code model family evolution: `Qwen/Qwen3-Coder-Next`
- Relationship to local model:
  - Local model: `qwen3-coder:30b`
  - Relationship: local model matches the official Ollama `qwen3-coder:30b` alias; `qwen3-coder-next` / `Qwen3-Coder-Next` is a newer official Qwen code-model line but is not treated here as an executed upgrade or selected runtime.
- Human review still required: yes.
- Status: lookup-success.

### qwen3

- Query sources:
  - Official Ollama library: `https://ollama.com/library/qwen3`
  - Official Ollama library: `https://ollama.com/library/qwen3.6`
  - Official Qwen blog: `https://qwenlm.github.io/blog/qwen3/`
  - Official Qwen blog: `https://qwen.ai/blog?id=qwen3.6-35b-a3b&lid=1qgBzVUzv0DLHy9oa`
  - Official Qwen Hugging Face model page: `https://huggingface.co/Qwen/Qwen3.6-35B-A3B`
  - Official Qwen Hugging Face model page: `https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507`
  - Official Qwen Hugging Face model page: `https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507`
- Query time: `2026-05-30 19:05:56 CST`
- Source credibility: high; official Ollama library plus official Qwen release / model-provider materials.
- Latest available version / tag:
  - Series-level Ollama latest line observed: `qwen3.6:latest`
  - Series-level Ollama size alias marked latest: `qwen3.6:35b`
  - Provider current open-weight model line observed: `Qwen3.6-35B-A3B`
  - Existing local-library Ollama latest alias: `qwen3:latest`
  - Existing local-library Ollama size alias marked latest: `qwen3:8b`
  - Earlier official Qwen3 updated model tags observed in family: `qwen3:30b`, `qwen3:235b`
  - Earlier provider updated model lines observed: `Qwen3-30B-A3B-Instruct-2507`, `Qwen3-235B-A22B-Instruct-2507`
- Relationship to local models:
  - Local models: `qwen3:30b`, `qwen3:14b`, `qwen3:8b`, `qwen3:0.6b`
  - Relationship: same broad Qwen3 series. Local models are in the `qwen3` local-library line, while the current series-level line observed is `qwen3.6`; this does not prove any local model has been upgraded and does not select `qwen3.6` for use.
- Human review still required: yes.
- Status: lookup-success.

### deepseek-r1

- Query sources:
  - Official Ollama library: `https://ollama.com/library/deepseek-r1`
  - Official DeepSeek Hugging Face model page: `https://huggingface.co/deepseek-ai/DeepSeek-R1-0528`
  - Official DeepSeek Hugging Face model page: `https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`
  - Official DeepSeek Hugging Face model page: `https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
- Query time: `2026-05-30 19:05:56 CST`
- Source credibility: high; official Ollama library plus official DeepSeek organization model pages.
- Latest available version / tag:
  - Ollama latest alias: `deepseek-r1:latest`
  - Ollama size alias marked latest: `deepseek-r1:8b`
  - Provider current full model line observed: `deepseek-ai/DeepSeek-R1-0528`
  - Provider current distilled small model line observed: `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`
- Relationship to local model:
  - Local model: `deepseek-r1:32b`
  - Relationship: same DeepSeek-R1 family, but local model is the distilled Qwen 32B line; the official Ollama latest alias points to the 0528 Qwen3 8B distilled line. This does not prove the local model has been upgraded or should be deleted.
- Human review still required: yes.
- Status: lookup-success.

## Blocked and Insufficient-Source Status

- `qwen3-next`: no `blocked`; no `insufficient-source` for latest-version lookup.
- `qwen3-coder`: no `blocked`; no `insufficient-source` for latest-version lookup.
- `qwen3`: no `blocked`; no `insufficient-source` for latest-version lookup.
- `deepseek-r1`: no `blocked`; no `insufficient-source` for latest-version lookup.

This stage does not use unofficial mirrors, social-media rumor, or non-official reposts as version evidence.

## Non-Upgrade and Non-Trial State

KG-RUNTIME-139 does not output a "must upgrade" conclusion.

KG-RUNTIME-139 does not recommend immediate model pull.

KG-RUNTIME-139 does not recommend deleting any old model.

KG-RUNTIME-139 does not judge that any model has been upgraded.

KG-RUNTIME-139 does not judge that the project may enter trial use.

KG-RUNTIME-139 only forms latest-version lookup results. It does not form or execute an upgrade.

Model upgrade has not been executed.

The project has not entered real use.

The project has not entered trial use.

The controlled trial target remains:

- KG safe integration is completed;
- the ZDoc preview-only chain is completed;
- the local model is upgraded to the latest available usable version;
- post-upgrade stability validation passes;
- only then may the project enter a 1 to 2 person controlled trial;
- only after that may the project expand to a 2 to 5 person small-concurrency trial.

## KG-RUNTIME-140 Authorization Gate Draft

KG-RUNTIME-140 is not executed by KG-RUNTIME-139.

If KG-RUNTIME-140 is separately authorized later, its boundary draft must be limited to:

- only use the KG-RUNTIME-139 lookup result and KG-RUNTIME-136 model inventory to prepare an upgrade candidate final strategy;
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

KG-RUNTIME-140, if later authorized, must still be docs-only strategy / gate work unless the user separately authorizes a narrower execution stage. It must not be treated as authorization for model pull, model deletion, model replacement, model upgrade execution, service runtime, endpoint access, real KG access, real KG JSON parsing, directory scanning, generation, export, writeback, evidence use, scoring use, real use, or trial use.

## Boundary Confirmation

- Latest-version lookup authorized in KG-RUNTIME-139: yes.
- Lookup limited to existing local model families: yes.
- Internet lookup performed for model version information: yes.
- Official sources used: yes.
- Social-media rumors used as version evidence: no.
- Unofficial mirrors used as version evidence: no.
- `blocked` lookup item: no.
- `insufficient-source` lookup item: no.
- Ollama run by KG-RUNTIME-139: no.
- `ollama list` run by KG-RUNTIME-139: no.
- `ollama pull` run by KG-RUNTIME-139: no.
- `ollama run` run by KG-RUNTIME-139: no.
- `ollama rm` run by KG-RUNTIME-139: no.
- `ollama serve` run by KG-RUNTIME-139: no.
- Model upgraded, pulled, deleted, or replaced by KG-RUNTIME-139: no.
- Adapter, route, helper, or `main.py` modified by KG-RUNTIME-139: no.
- Frontend, tests, config, or JSON modified by KG-RUNTIME-139: no.
- Directory scan executed again by KG-RUNTIME-139: no.
- Real KG file body content read by KG-RUNTIME-139: no.
- Real KG JSON parsed by KG-RUNTIME-139: no.
- ZDoc service run by KG-RUNTIME-139: no.
- Port accessed by KG-RUNTIME-139: no.
- Endpoint called by KG-RUNTIME-139: no.
- `/health` called by KG-RUNTIME-139: no.
- `/kg/read-only-preview` called by KG-RUNTIME-139: no.
- Generation triggered by KG-RUNTIME-139: no.
- Export triggered by KG-RUNTIME-139: no.
- Writeback triggered by KG-RUNTIME-139: no.
- `output`, `job`, or `export` written by KG-RUNTIME-139: no.
- RAG integrated by KG-RUNTIME-139: no.
- Registry integrated by KG-RUNTIME-139: no.
- CI integrated by KG-RUNTIME-139: no.
- Evidence use performed by KG-RUNTIME-139: no.
- Scoring use performed by KG-RUNTIME-139: no.
- Real use entered by KG-RUNTIME-139: no.
- Trial use entered by KG-RUNTIME-139: no.

## Explicit Completion State

KG-RUNTIME-139 completes only the docs-only controlled latest-version lookup review for existing local model families.

KG-RUNTIME-139 successfully records latest-version lookup results for the `qwen3-next`, `qwen3-coder`, `qwen3`, and `deepseek-r1` families.

KG-RUNTIME-139 does not execute model upgrade.

KG-RUNTIME-139 does not authorize model upgrade.

KG-RUNTIME-139 does not authorize real use.

KG-RUNTIME-139 does not authorize trial use.

KG-RUNTIME-140 was not entered.
