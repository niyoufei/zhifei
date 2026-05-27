# KG-RUNTIME-108 no-server in-process preview-only response integration smoke validation

## Scope

- Task: KG-RUNTIME-108
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Baseline HEAD: `e85727baff7425541560f2f459e7e48406728664`
- Baseline remote tag: `v0.1.490-zdoc-kg-preview-only-response-integration-smoke-gate`
- Validation mode: no-server in-process smoke validation
- Persistent change allowed: this docs-only review file only

This review validates only the KG-RUNTIME-105 preview-only response integration
surface. It does not enter KG-RUNTIME-109, ZDoc integration, real use, or trial
use.

## Validation Input

The smoke used a synthetic, already content-safe adapter response shape. The
synthetic payload included safe structural summary codes and safe contract
codes, plus deliberately injected prohibited top-level and contract-local fields
such as prompt, evidence, scoring, KG scalar value, and business body labels to
confirm those fields did not enter the preview-only mapping.

No real KG file body was read. No real KG JSON was parsed.

## Execution Boundary

- Used one `PYTHONDONTWRITEBYTECODE=1 python3` no-server in-process invocation.
- Called adapter/helper preview-only response integration code directly.
- Checked route metadata passthrough constant for `preview_only_response`.
- Did not start `uvicorn`.
- Did not bind any TCP port.
- Did not access `127.0.0.1`.
- Did not call `/health`.
- Did not call `/kg/read-only-preview`.
- Did not run `pytest`.
- Did not run `py_compile`.
- Did not run `python3 -m json.tool`.
- Did not run Ollama.
- Did not run or access RAG, registry, or CI.

During the actual smoke call, file access, JSON parsing, and socket creation were
blocked by in-process guards. The smoke completed without triggering those
guards.

## Smoke Result

Conclusion: PASS

Observed output:

```text
KG_RUNTIME_108_SMOKE=PASS
preview_only_response_keys=preview_contract,preview_only_mapping,audit_only_mapping,prohibited_mapping
preview_only_mapping_top_keys=structural_profile_contract,structural_profile_only,structural_profile_summary,structure_contract,structure_read_only,structure_summary
audit_only_mapping_keys=adapter_contract_code,allowlist_status,authorized_target_hit_status,feature_flag_status,manual_trigger_status,overlap_check_result,real_kg_read_only_status,route_contract_code,validation_result
prohibited_mapping_count=12
content_read_performed=False
json_parse_performed=False
```

## Contract Checks

- `preview_only_response` was returned.
- `preview_only_response` contained exactly:
  - `preview_contract`
  - `preview_only_mapping`
  - `audit_only_mapping`
  - `prohibited_mapping`
- `preview_contract` reported integration source `105`, integration policy `1`,
  mapping source `100`, and mapping policy `1`.
- `preview_only_mapping` contained only preview-only allowed top-level fields:
  - `structure_read_only`
  - `structure_summary`
  - `structure_contract`
  - `structural_profile_only`
  - `structural_profile_summary`
  - `structural_profile_contract`
- `audit_only_mapping` contained only audit-only allowed response fields:
  - `feature_flag_status`
  - `manual_trigger_status`
  - `real_kg_read_only_status`
  - `authorized_target_hit_status`
  - `allowlist_status`
  - `route_contract_code`
  - `adapter_contract_code`
  - `validation_result`
  - `overlap_check_result`
- `prohibited_mapping` retained only the prohibited category list.
- `prohibited_mapping` did not enter `preview_only_mapping`.
- `preview_only_mapping` did not contain string values from KG scalar values,
  list item content, dict value content, business body, entity body, knowledge
  entry body, prompt, system instruction, evidence, scoring, original KG text
  fragments, or strings that can reverse-infer KG body content.

## Negative Confirmations

- Code was not modified.
- Adapter, route, helper, and `main.py` were not modified.
- Frontend, tests, config, and JSON files were not modified.
- No directory scan command was executed.
- Real KG file body was not read.
- Real KG JSON was not parsed.
- Service was not run.
- Endpoint was not called.
- `/generate` was not triggered or integrated.
- `/export_docx` was not triggered or integrated.
- `/review/apply` was not triggered or integrated.
- No output, job, or export path was written.
- ZBid writeback was not triggered.
- Ollama was not run.
- RAG, registry, and CI were not integrated.
- The result was not used as evidence.
- The result was not used as scoring.
- This did not enter ZDoc integration, real use, or trial use.
- This did not enter KG-RUNTIME-109.

## Review Conclusion

KG-RUNTIME-108 is PASS as a no-server in-process preview-only response
integration smoke validation. The result validates only content-safe response
contract behavior for the KG-RUNTIME-105 preview-only response integration
surface and does not prove ZDoc runtime integration, real KG use, trial use,
generation, export, writeback, evidence, scoring, RAG, registry, or CI behavior.
