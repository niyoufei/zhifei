# ZDoc Real Ollama Preview Runtime Smoke Plan

## 1. Purpose

This document records the ZDoc Step 19 real-Ollama preview runtime smoke plan.

The current stage is docs-only. It plans a future runtime smoke but does not execute runtime smoke, does not modify code, does not add or modify tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not access `127.0.0.1:11434`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately execute runtime smoke.

## 2. Baseline inherited from ZDoc Step 18

ZDoc Step 18 archived the real-Ollama preview adapter fake transport stage review in:

```text
docs/zdoc-real-ollama-preview-adapter-fake-transport-stage-review.md
```

The inherited baseline is:

- ZDoc has completed the fake-only local-LLM preview stage.
- The isolated safe endpoint exists as `POST /local-llm/preview-safe`.
- The isolated safe endpoint fake-only service smoke has passed.
- ZDoc has completed the real-Ollama adapter / transport fake-only implementation.
- The adapter has a preview top-level feature flag: `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The adapter has a subordinate real adapter / transport feature flag: `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`.
- The adapter fake transport tests passed.
- ZDoc still has not truly accessed Ollama.
- ZDoc still has not run a real model.
- ZDoc still has not connected the formal generation chain.
- ZDoc still has not connected the export chain.
- ZDoc still has not connected ZBid formal writeback.

The Step 17 deterministic test command was:

```text
python3 -m pytest backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

The Step 17 final test result was:

```text
115 passed in 3.04s
```

## 3. Runtime smoke objective

A future runtime smoke may verify whether the real-Ollama preview adapter can safely interact with a local Ollama runtime.

The objective is narrow:

- verify local Ollama reachability only through `127.0.0.1:11434`;
- inspect the locally available model list without downloading or pulling models;
- verify disabled behavior when the top-level preview flag is absent or disabled;
- verify adapter-disabled behavior when the top-level preview flag is enabled but the adapter flag is disabled;
- verify real-adapter-enabled behavior only through the isolated safe endpoint;
- confirm responses remain preview-only and no-write;
- confirm no generation, export, or ZBid writeback path is touched;
- confirm all service processes are stopped and ports are released after smoke.

The runtime smoke objective is not to validate production generation quality, UI adoption, formal正文 updates, export artifacts, or ZBid writeback.

## 4. Required 2号窗口 boundary

Future real runtime smoke must be separately authorized before it starts.

If `ollama serve` is needed, it must be run only in 2号窗口.

2号窗口 is allowed only for:

```text
ollama serve
```

2号窗口 must not:

- run git commands;
- run pytest;
- modify code;
- modify tests;
- commit;
- tag;
- push;
- download models;
- pull models;
- run `ollama pull`;
- start any non-Ollama service;
- access external model/API providers.

If 2号窗口 requires any command beyond `ollama serve`, the smoke must stop and report the condition.

## 5. Codex execution boundary

Codex may only perform the specifically authorized smoke operations in the future smoke step.

Codex execution must remain bounded by:

- only accessing `127.0.0.1:11434` for Ollama;
- not accessing external model/API transports;
- not calling OpenAI;
- not calling Spark;
- not calling Gemini;
- not accessing arbitrary hostnames;
- not downloading models;
- not pulling models;
- not executing `ollama pull`;
- not writing `output/job/export`;
- not triggering formal generation;
- not triggering formal export;
- not connecting ZBid formal writeback.

If a FastAPI service must be started for the smoke, it must listen only on:

```text
127.0.0.1
```

It must not listen on:

```text
0.0.0.0
```

## 6. Ollama reachability check plan

Scenario A is the Ollama reachability check.

Prerequisites:

- Step 19 plan is archived.
- A later Step 20 smoke is explicitly authorized.
- 2号窗口 is available if `ollama serve` is required.
- No model download or model pull is needed.

Planned 2号窗口 action:

```text
ollama serve
```

Planned Codex check:

```text
GET http://127.0.0.1:11434/api/tags
```

The reachability check must record:

- HTTP status;
- whether the response is valid JSON;
- whether a `models` list exists;
- a concise local model summary;
- whether a usable local model is already present;
- whether no download or pull was performed.

The reachability check must not:

- call `/api/generate`;
- call `/api/chat`;
- call external model/API transports;
- download models;
- pull models;
- execute `ollama pull`;
- write files.

If no local model is available, the smoke must stop with a model-unavailable result. It must not download or pull a model.

## 7. Local model selection plan

The future runtime smoke may use only a model already present in the local Ollama model list.

Model selection must follow this order:

1. If a future smoke request explicitly names a model and that model exists in `/api/tags`, use it.
2. If no model is explicitly named, select the first suitable model from the local `/api/tags` list.
3. If no model exists, return a stable model-unavailable result and stop.

Model selection must not:

- pull missing models;
- download models;
- use external model providers;
- infer that a missing model can be installed during smoke;
- persist model selection to files;
- write model output to `output/job/export`.

The smoke report must record the selected model name or the model-unavailable reason.

## 8. Safe endpoint request plan

Future runtime smoke is allowed to request only the isolated safe endpoint:

```text
POST /local-llm/preview-safe
```

The smoke must not request:

```text
/generate
/export_docx
/review/apply
```

The request payload must be minimal and synthetic. It must not include real bid documents, real tender documents, formal generation job ids, output paths, export paths, or ZBid writeback parameters.

Allowed payload shape should remain limited to preview inputs such as:

- `section_title`;
- `section_text`;
- `context_summary`;
- `request_id`.

Response checks must verify:

- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- no formal output path fields;
- no formal generated正文 fields;
- no ZBid writeback fields.

## 9. Disabled / enabled feature flag scenarios

Future runtime smoke must cover four scenarios.

### Scenario A: Ollama reachability check

Scenario A verifies local runtime availability only.

Planned behavior:

- 2号窗口 runs `ollama serve`.
- Codex sends `GET http://127.0.0.1:11434/api/tags`.
- Codex records HTTP status.
- Codex records whether the response is valid JSON.
- Codex records a local model summary.
- Codex does not download models.
- Codex does not pull models.
- Codex does not execute `ollama pull`.

Scenario A must not call model generation.

### Scenario B: endpoint disabled

Scenario B verifies the top-level default-off boundary.

Feature flag state:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED unset or false-like
```

Expected behavior:

- request `POST /local-llm/preview-safe`;
- response is disabled;
- even if Ollama is reachable, no real Ollama generate call is made;
- no write to `output/job/export`;
- no generation-chain trigger;
- no export-chain trigger;
- no ZBid writeback.

### Scenario C: adapter flag disabled

Scenario C verifies the subordinate adapter default-off boundary.

Feature flag state:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED unset or false-like
```

Expected behavior:

- request `POST /local-llm/preview-safe`;
- response remains fake-only or disabled according to the current safe endpoint wiring;
- no real Ollama access is made for generation;
- no write to `output/job/export`;
- no generation-chain trigger;
- no export-chain trigger;
- no ZBid writeback.

### Scenario D: real adapter enabled

Scenario D verifies the real adapter path only after explicit authorization.

Feature flag state:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
```

Expected behavior:

- Codex may access only `127.0.0.1:11434`;
- Codex requests only `POST /local-llm/preview-safe`;
- response must be preview-only;
- response must be no-write;
- response must include `affects_generation=false`;
- response must include `affects_export=false`;
- response must not trigger formal generation;
- response must not trigger export;
- response must not connect ZBid writeback.

If the currently implemented endpoint still routes only to fake-only safe helper behavior, the smoke report must state that real adapter invocation is not yet wired through the endpoint and must not force a code change during smoke.

## 10. No-write verification

Future runtime smoke must verify that no file writes occur in:

```text
output/
job/
export/
```

Recommended verification:

- record pre-smoke file counts for `output/`, `job/`, and `export/`;
- run the smoke scenarios;
- record post-smoke file counts;
- report any difference;
- stop immediately if new files appear.

The smoke must also verify that responses do not include formal output fields such as:

- `job_id`;
- `output_path`;
- `export_path`;
- `docx_path`;
- `markdown_path`;
- `json_path`;
- `generated_sections`.

## 11. No-generation-chain verification

Future runtime smoke must prove that the generation chain is not touched.

Verification must include:

- no request to `/generate`;
- no formal generation job id;
- no generated section write;
- no formal正文 replacement;
- no generated artifact path.

If any generation-chain signal appears, the smoke must stop.

## 12. No-export-chain verification

Future runtime smoke must prove that the export chain is not touched.

Verification must include:

- no request to `/export_docx`;
- no DOCX output;
- no JSON output;
- no Markdown output;
- no export path;
- no export artifact.

If any DOCX / JSON / Markdown formal export artifact appears, the smoke must stop.

## 13. No-ZBid-writeback verification

Future runtime smoke must prove that ZBid formal writeback is not touched.

Verification must include:

- no request to `/review/apply`;
- no ZBid writeback payload;
- no formal apply operation;
- no mutation of ZBid formal writeback state;
- no modification of `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.

If any ZBid writeback signal appears, the smoke must stop.

## 14. Failure stop conditions

Future runtime smoke must stop immediately and report if any of the following occurs:

- a model must be downloaded;
- a model must be pulled;
- `ollama pull` is required;
- external network access is required;
- an external model/API provider is required;
- OpenAI / Spark / Gemini access is required;
- a service must listen on `0.0.0.0`;
- the smoke request accidentally targets `/generate`;
- the smoke request accidentally targets `/export_docx`;
- the smoke request accidentally targets `/review/apply`;
- new files appear in `output/`;
- new files appear in `job/`;
- new files appear in `export/`;
- DOCX / JSON / Markdown formal export artifacts appear;
- ZBid writeback evidence appears;
- code files change unexpectedly;
- test files change unexpectedly;
- service process cannot be stopped;
- service port cannot be released;
- 2号窗口 requires any command other than `ollama serve`.

## 15. Smoke report format

The future smoke report must include at least:

1. 当前目录
2. 当前分支
3. 开始前 HEAD
4. 是否启用 2号窗口
5. Ollama 可达性检查结果
6. 本机模型摘要
7. 使用模型名
8. feature flag 场景
9. FastAPI 启动命令
10. 服务监听地址
11. 服务 PID
12. 请求 endpoint
13. 响应摘要
14. 是否访问 `127.0.0.1:11434`
15. 是否请求 `/generate`
16. 是否请求 `/export_docx`
17. 是否请求 `/review/apply`
18. 是否写 output/job/export
19. 是否触发正式导出
20. 是否接 ZBid 写回
21. 是否停止服务
22. 端口是否释放
23. `git status after`
24. 风险说明

The report must state explicitly whether each scenario passed, failed, or stopped early.

## 16. Recommended next ZDoc step

The recommended next step is:

```text
ZDoc Step 20: real-Ollama preview runtime smoke + smoke report
```

Step 20 must not enter the formal generation chain, export chain, or ZBid writeback. It may only perform the separately authorized runtime smoke described by this plan.

## 17. Closure statement

ZDoc Step 19 defines the guardrails for a future real-Ollama runtime smoke. It keeps runtime execution separate from planning, requires 2号窗口 discipline for `ollama serve`, limits Codex to `127.0.0.1`, forbids model downloads and pulls, restricts smoke requests to `POST /local-llm/preview-safe`, and preserves preview-only / no-write / no-generation / no-export / no-ZBid boundaries.

No runtime smoke was executed in this step.
