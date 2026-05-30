# KG-RUNTIME-122 ZDoc KG route-layer no-server in-process preview-only integration smoke validation review

## Scope

- Stage: KG-RUNTIME-122
- Stop line: do not enter KG-RUNTIME-123
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `4fc722ea4fc817028121762e3dd038d6e3cce8be`
- Baseline tag from task: `v0.1.504-zdoc-kg-preview-only-integration-pass-route-gate`
- Target review file only: `docs/zdoc-kg-route-layer-no-server-in-process-preview-only-integration-smoke-validation-kg-runtime-122-review.md`

## Baseline Checks

- `pwd`: `/Users/youfeini/Desktop/文档生成系统`
- `git branch --show-current`: `main`
- `git rev-parse HEAD`: `4fc722ea4fc817028121762e3dd038d6e3cce8be`
- `git status --short`: clean
- Local `git tag --points-at HEAD`: no local tag was present.
- The baseline tag was taken from the task statement as the remote baseline tag.

## Smoke Method

One no-server in-process Python command was executed with:

- `PYTHONDONTWRITEBYTECODE=1`
- `python3 -B`
- direct in-process invocation of `kg_read_only_preview_route`
- synthetic adapter stub replacing the route module's `build_kg_read_only_preview`
- synthetic / content-safe response-shaped input only
- file IO, JSON load/loads, and socket guards active during the direct route calls

No uvicorn was started. No TCP port was bound. No localhost or `127.0.0.1` access was performed. No real endpoint was called. No real KG file body was read. No real KG JSON was parsed.

## Synthetic Route Validation

The smoke validated route-layer pass-through for both ZDoc structures inside one Python process:

- `build_zdoc_preview_only_payload` structure passed through the route envelope.
- `build_zdoc_preview_only_adapter_payload` structure passed through the route envelope.

The route returned envelope dictionaries with:

- `ok=True`
- `enabled=True`
- `adapter_status=preview_only`
- `preview_only_response`
- `zdoc_preview_only_integration`
- copied route metadata fields
- no generation, export, writeback, endpoint, Ollama, registry, RAG, evidence, or scoring flags enabled

## Smoke Output Evidence

```text
KG_RUNTIME_122_SMOKE=PASS
python_no_server_in_process=true
uvicorn_started=false
tcp_bound=false
localhost_accessed=false
endpoint_called=false
real_kg_body_read=false
real_kg_json_parsed=false
synthetic_content_safe_input=true
direct_route_in_process=true
synthetic_adapter_stub=true
route_returned_envelope_dict=true
zdoc_preview_only_integration_returned=true
zdoc_preview_only_integration_expected_structure=true
build_zdoc_preview_only_payload_route_passthrough=pass
build_zdoc_preview_only_adapter_payload_route_passthrough=pass
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
route_call_count=2
route_top_level_keys_checked=true
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

- Route returned an envelope dict.
- `zdoc_preview_only_integration` was returned and passed through from the synthetic adapter result.
- `zdoc_preview_only_integration` contained the expected structure.
- `build_zdoc_preview_only_payload` corresponding structure passed through the route layer.
- `build_zdoc_preview_only_adapter_payload` corresponding structure passed through the route layer.
- `preview_only_response` was reused.
- `preview_contract` was reused.
- `preview_only_mapping` was reused.
- `audit_only_mapping` was reused.
- `prohibited_mapping` was reused.
- Preview-only output contained only allowed preview fields.
- Audit-only output contained only allowed audit fields.
- `prohibited_mapping` retained only the prohibited category list.
- Prohibited fields did not enter preview-only output.
- Preview-only output did not contain KG scalar value, list item content, dict value content, business body, entity body, knowledge entry body, prompt, system instruction, evidence, scoring, raw KG text fragment, or reconstructable KG body marker.

## Conclusion

KG-RUNTIME-122 smoke conclusion: PASS.

This is only a route-layer no-server in-process ZDoc preview-only integration smoke validation using synthetic content-safe input and a synthetic adapter stub. It is not ZDoc integration completion, real use, trial use, evidence, or scoring.

KG-RUNTIME-123 was not entered.
