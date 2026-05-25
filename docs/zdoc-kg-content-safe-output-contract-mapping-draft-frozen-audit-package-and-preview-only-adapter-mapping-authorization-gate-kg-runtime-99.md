# KG-RUNTIME-99 content-safe output contract mapping draft frozen audit package and preview-only adapter mapping authorization gate

## Scope

- Stage: KG-RUNTIME-99.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `186ba1fa18eea72606205dafad2d07ff13a3ce75`.
- Start baseline tag: `v0.1.481-zdoc-kg-content-safe-contract-mapping-static-review`.
- Baseline note: the local baseline tag was absent in this environment, and the remote tag was verified to point to the start HEAD.
- This stage is docs-only frozen audit and authorization-gate drafting.
- This stage does not execute KG-RUNTIME-100.

## Frozen Audit Package

KG-RUNTIME-97 completed the content-safe output contract mapping controlled implementation draft.

KG-RUNTIME-98 completed the static compliance and no-runtime / no-output-chain review of that draft.

The current mapping remains a static draft. It does not mean ZDoc has integrated the mapping, does not mean the mapping is in real use, and does not mean the mapping has entered trial use.

## Current Mapping Classes

The current content-safe output contract mapping is divided into three classes:

- `preview_only`
- `audit_only`
- `prohibited`

`preview_only` is limited to content-safe structure summaries and safe enum / numeric-code fields.

`audit_only` is limited to audit information, including feature flag, `manual_trigger`, `real_kg_read_only`, `authorized_target`, `allowlist_status`, contract code, validation result, and overlap check result.

`prohibited` explicitly covers:

- KG scalar value
- list item 内容
- dict value 内容
- 业务正文
- 实体正文
- 知识条目正文
- prompt
- system instruction
- evidence
- scoring
- 原始 KG 文本片段
- 可反推 KG 正文的字符串

## Static Confirmation

Confirmed for the frozen KG-RUNTIME-97 / KG-RUNTIME-98 state:

- PASS: the helper is only a static mapping helper.
- PASS: the adapter only binds the static draft constant.
- PASS: the route added no pass-through for this mapping.
- PASS: the mapping was not added to the output whitelist.
- PASS: the mapping was not connected to `/generate`.
- PASS: the mapping was not connected to `/export_docx`.
- PASS: the mapping was not connected to `/review/apply`.
- PASS: the mapping did not write output, job, or export files.
- PASS: the mapping was not connected to RAG, registry, or CI.
- PASS: the mapping was not used as evidence.
- PASS: the mapping was not used as scoring.

Current state must not be recognized as:

- ZDoc integrated.
- Real use.
- Trial use.
- Model upgraded.
- Available for small-group trial.

## KG-RUNTIME-100 Authorization Gate

KG-RUNTIME-100 may proceed only if it is separately and explicitly authorized after this document.

If separately authorized, KG-RUNTIME-100 is limited to a preview-only adapter mapping controlled implementation draft with these boundaries:

- Only minimal changes to adapter, route, and helper are allowed.
- No generation-chain integration.
- No export-chain integration.
- No writeback-chain integration.
- No evidence integration.
- No scoring integration.
- Only preview-only field filtering / mapping draft work is allowed.
- No service run.
- No endpoint access.
- No real KG read.
- No real KG JSON parse.
- No directory scan rerun.
- No `pytest`.
- No `py_compile`.
- No Ollama.
- No RAG integration.
- No registry integration.
- No CI integration.
- No real-use stage.
- No trial-use stage.

KG-RUNTIME-99 only sets the preview-only adapter mapping authorization gate. It does not execute implementation.

## KG-RUNTIME-99 Non-Runtime Record

Not performed in this stage:

- No adapter, route, helper, or `main.py` modification.
- No frontend, tests, config, or JSON modification.
- No directory scan rerun.
- No real KG file body read.
- No real KG JSON parse.
- No service run.
- No port access.
- No endpoint call.
- No `/health` call.
- No `/kg/read-only-preview` call.
- No `/generate` call.
- No `/export_docx` call.
- No `/review/apply` call.
- No ZBid writeback.
- No output, job, or export write.
- No Ollama.
- No RAG, registry, or CI integration.
- No evidence use.
- No scoring use.

## Stop Line

KG-RUNTIME-99 freezes the KG-RUNTIME-97 / KG-RUNTIME-98 content-safe output contract mapping draft audit package and sets the KG-RUNTIME-100 preview-only adapter mapping authorization gate.

It does not enter KG-RUNTIME-100.
