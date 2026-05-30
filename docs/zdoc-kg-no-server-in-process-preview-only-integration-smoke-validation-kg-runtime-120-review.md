# KG-RUNTIME-120 ZDoc KG no-server in-process preview-only integration smoke validation review

## Scope

- Stage: KG-RUNTIME-120
- Stop line: do not enter KG-RUNTIME-121
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `6a4db1b30c890bc9565db4ce0854fb2ebb17a978`
- Baseline tag from task: `v0.1.502-zdoc-kg-preview-only-integration-smoke-gate`
- Target review file only: `docs/zdoc-kg-no-server-in-process-preview-only-integration-smoke-validation-kg-runtime-120-review.md`

## Baseline Checks

- `pwd`: `/Users/youfeini/Desktop/文档生成系统`
- `git branch --show-current`: `main`
- `git rev-parse HEAD`: `6a4db1b30c890bc9565db4ce0854fb2ebb17a978`
- `git status --short`: clean
- Local baseline tag check: no local ref was present for `v0.1.502-zdoc-kg-preview-only-integration-smoke-gate`.
- Remote baseline tag live check was attempted with `git ls-remote --tags origin v0.1.502-zdoc-kg-preview-only-integration-smoke-gate`, but sandbox SSH access returned `Operation not permitted`; a narrow escalated retry was requested twice and both auto-review attempts timed out. No full access mode was used.

## Smoke Method

One no-server in-process Python smoke was executed with:

- `PYTHONDONTWRITEBYTECODE=1`
- `python3 -B`
- no uvicorn
- no TCP bind
- no localhost or `127.0.0.1` access
- no endpoint call
- no real KG file body read
- no real KG JSON parse
- synthetic / content-safe response-shaped input only

The smoke directly called:

- `build_preview_only_payload`
- `build_preview_only_adapter_mapping`
- `build_preview_only_response_integration_payload`
- `build_zdoc_preview_only_payload`
- `build_zdoc_preview_only_adapter_payload`
- `_real_kg_contract_response` only as an in-process adapter response wrapper to verify the returned `zdoc_preview_only_integration` field without service startup, endpoint access, real KG read, or JSON parse.

No route endpoint was called.

## Synthetic Input

The input was a synthetic content-safe response shape containing only structure / structural-profile summaries, contract metadata, audit status codes, and deliberate trap fields such as prompt, system instruction, evidence, scoring, raw KG text, KG scalar value, list item body, dict value body, business body, entity body, knowledge entry body, and reconstructable KG body markers.

Those trap fields were used only to prove that preview-only and audit-only mapping filters do not leak prohibited content.

## Smoke Output Evidence

The smoke returned:

```text
KG_RUNTIME_120_SMOKE=PASS
python_no_server_in_process=true
uvicorn_started=false
tcp_bound=false
localhost_accessed=false
endpoint_called=false
real_kg_body_read=false
real_kg_json_parsed=false
synthetic_content_safe_input=true
zdoc_preview_only_integration_returned=true
build_zdoc_preview_only_payload_shape=pass
build_zdoc_preview_only_adapter_payload_shape=pass
preview_only_response_reused=true
preview_contract_reused=true
preview_only_mapping_reused=true
audit_only_mapping_reused=true
prohibited_mapping_reused=true
preview_only_allowed_fields_only=true
audit_only_allowed_fields_only=true
prohibited_category_list_only=true
prohibited_not_in_preview_only=true
kg_value_body_evidence_scoring_not_in_preview_only=true
preview_only_response_keys=['audit_only_mapping', 'preview_contract', 'preview_only_mapping', 'prohibited_mapping']
zdoc_preview_only_integration_keys=['audit_only_mapping', 'preview_contract', 'preview_only_mapping', 'prohibited_mapping']
```

## Validation Results

- No uvicorn was started.
- No TCP port was bound.
- No `127.0.0.1` or localhost access was performed.
- No real endpoint was called.
- No `/health` call was performed.
- No `/kg/read-only-preview` call was performed.
- No real KG file body was read.
- No real KG JSON was parsed.
- No `python3 -m json.tool` was run.
- No `pytest` was run.
- No `py_compile` was run.
- No Ollama was run.
- No frontend integration was performed.
- No `/generate` integration was performed.
- No `/export_docx` integration was performed.
- No `/review/apply` integration was performed.
- No output/job/export write was performed.
- No ZBid writeback was triggered.
- No RAG, registry, or CI integration was performed.
- No evidence path was introduced.
- No scoring path was introduced.
- No code, adapter, route, helper, `main.py`, frontend, tests, config, or JSON file was modified.
- No directory scan command such as `find ..`, `find /`, or `find AI知识图谱大全` was run.
- No ZDoc completion, real-use, or trial stage was entered.

## Shape Checks

- `build_zdoc_preview_only_payload` returned the expected ZDoc integration structure.
- `build_zdoc_preview_only_adapter_payload` returned the expected ZDoc adapter structure.
- `zdoc_preview_only_integration` was returned by the in-process adapter response wrapper.
- `preview_only_response` was reused.
- `preview_contract` was reused.
- `preview_only_mapping` was reused.
- `audit_only_mapping` was reused.
- `prohibited_mapping` was reused.
- `preview_only` output contained only allowed preview fields.
- `audit_only` output contained only allowed audit fields.
- `prohibited` / `prohibited_mapping` retained only the prohibited category list.
- `prohibited` did not enter preview-only output.
- Preview-only output did not contain KG scalar value, list item content, dict value content, business body, entity body, knowledge entry body, prompt, system instruction, evidence, scoring, raw KG text fragment, or reconstructable KG body marker.

## Conclusion

KG-RUNTIME-120 smoke conclusion: PASS.

This is only a no-server in-process preview-only integration smoke validation of the KG-RUNTIME-117 ZDoc preview-only draft structure. It is not ZDoc integration completion, real use, trial use, evidence, or scoring.

KG-RUNTIME-121 was not entered.
