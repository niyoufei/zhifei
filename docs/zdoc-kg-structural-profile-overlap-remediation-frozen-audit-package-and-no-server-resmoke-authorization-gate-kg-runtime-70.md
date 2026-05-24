# KG-RUNTIME-70 structural-profile overlap remediation frozen audit package and no-server re-smoke authorization gate

## Scope

- Stage: KG-RUNTIME-70
- Target: ZDoc KG structural-profile overlap remediation frozen audit package and no-server re-smoke authorization gate
- Baseline HEAD: `d887d4a95d8827c7c705a5313cba49aa05ff1d30`
- Baseline tag: `v0.1.451-zdoc-kg-structural-profile-overlap-remediation-static-review`
- New tag target: `v0.1.452-zdoc-kg-structural-profile-overlap-resmoke-gate`
- New docs-only file: `docs/zdoc-kg-structural-profile-overlap-remediation-frozen-audit-package-and-no-server-resmoke-authorization-gate-kg-runtime-70.md`

## Stage result

- KG-RUNTIME-68 has completed the structural-profile overlap-source controlled remediation implementation draft.
- KG-RUNTIME-69 has completed the static compliance and no-content-leak review for that remediation draft.
- KG-RUNTIME-69 is only a static review pass. It does not represent, imply, or replace a successful re-smoke.
- KG-RUNTIME-70 only freezes the audit package and sets the KG-RUNTIME-71 authorization gate. It does not execute re-smoke.

## KG-RUNTIME-68 remediation freeze

- `structure_summary` keeps the 13-field whitelist:
  - `top_level_type`
  - `top_level_key_names`
  - `top_level_key_count`
  - `dict_count`
  - `list_count`
  - `null_count`
  - `scalar_type_counts`
  - `selected_structure_paths`
  - `list_lengths`
  - `field_type_sets`
  - `max_depth_limited`
  - `authorized_target`
  - `allowlist_status`
- `structural_profile_summary` keeps the 14-field whitelist:
  - `authorized_target`
  - `allowlist_status`
  - `profile_enabled`
  - `profile_scope`
  - `max_depth_limited`
  - `path_count`
  - `path_type_counts`
  - `depth_histogram`
  - `field_name_counts`
  - `field_type_sets`
  - `list_length_buckets`
  - `dict_key_count_buckets`
  - `module_name_candidates`
  - `redaction_policy`
- When `structural_profile=true`, the response shape still returns:
  - `structure_read_only`
  - `structure_summary`
  - `structure_contract`
  - `structural_profile_only`
  - `structural_profile_summary`
  - `structural_profile_contract`
- `top_level_key_names` was changed to placeholder or non-body-derived output.
- `selected_structure_paths` was changed to placeholder, depth/type structural signature, or non-body-derived output.
- `list_lengths` keeps only lengths, bucket statistics, or non-body paths.
- `field_type_sets` no longer uses real field names or real path names as keys.
- `field_name_counts` no longer outputs real field names.
- `path_type_counts` no longer outputs real paths.
- `module_name_candidates` remains a fixed empty list-compatible value.
- `redaction_policy` remains a fixed policy string and does not concatenate KG content.

## KG-RUNTIME-69 static review freeze

- No second uncontrolled file-read path was added.
- No import-time file read was added.
- No service-start automatic file read was added.
- No directory scan, batch read, or allowlist expansion was added.
- The remediation draft was not connected to generation, export, or writeback chains.
- The remediation draft was not connected to RAG, prompt registry, or system instruction registry.
- The remediation draft was not used as evidence.
- The remediation draft was not used as scoring.
- KG-RUNTIME-69 did not read real KG file body content.
- KG-RUNTIME-69 did not parse real KG JSON.
- KG-RUNTIME-69 did not run a service, bind a TCP port, access `127.0.0.1`, call `/health`, or call `/kg/read-only-preview`.
- KG-RUNTIME-69 did not run `pytest`, `py_compile`, `python3 -m json.tool`, Ollama, CI, generation, export, writeback, RAG, prompt registry, or system instruction registry.

## KG-RUNTIME-71 authorization gate draft

KG-RUNTIME-71 may only be executed if it is separately authorized in a later stage. The allowed future action would be a no-server in-process structural-profile overlap remediation re-smoke with the following hard boundary:

- Do not start `uvicorn`.
- Do not bind any TCP port.
- Do not access `127.0.0.1`.
- Prefer direct route in-process invocation.
- Payload must include `manual_trigger=true`.
- Payload must include `real_kg_read_only=true`.
- Payload must include `structure_read=true`.
- Payload must include `structural_profile=true`.
- `authorized_target` must strictly equal `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- Only the single authorized target may be read and parsed, and only for producing whitelisted `structure_summary`, `structural_profile_summary`, and `structural_profile_contract`.
- Verify that `structure_summary` returns exactly the 13 whitelisted fields.
- Verify that `structural_profile_summary` returns exactly the 14 whitelisted fields.
- Verify that `module_name_candidates` is an empty list-compatible value.
- Verify that `redaction_policy` is the fixed policy string.
- Verify scalar full leaf overlap is `0`.
- Verify substring overlap is `0`.
- Do not output business body text, entity body text, knowledge entry body text, prompt text, system instruction text, evidence, or scoring.
- Do not trigger generation, export, or writeback.
- Do not write output, job, or export artifacts.
- Do not run Ollama.
- Do not run `pytest` or `py_compile`.
- Do not connect to RAG, registry, or CI.
- Do not enter real-use stage.

## KG-RUNTIME-70 execution boundary

- This stage is docs-only.
- This stage does not modify adapter, route, or `main.py`.
- This stage does not modify frontend, tests, config, or JSON files.
- This stage does not read real KG file body content.
- This stage does not parse real KG JSON.
- This stage does not run a service.
- This stage does not bind a TCP port.
- This stage does not access `127.0.0.1`.
- This stage does not call `/health`.
- This stage does not call `/kg/read-only-preview`.
- This stage does not trigger `/generate`, `/export_docx`, `/review/apply`, or ZBid writeback.
- This stage does not write business body content.
- This stage does not write output, job, or export artifacts.
- This stage does not run Ollama.
- This stage does not connect to RAG, prompt registry, system instruction registry, tests, or CI.
- This stage does not create evidence or scoring.
- This stage does not enter KG-RUNTIME-71.

## Frozen conclusion

- KG-RUNTIME-68 remediation draft is frozen as the implementation basis.
- KG-RUNTIME-69 static compliance and no-content-leak review is frozen as the static review basis.
- KG-RUNTIME-69 remains static-only and does not claim re-smoke success.
- KG-RUNTIME-71 remains unauthorized until a separate later request explicitly authorizes the no-server in-process overlap remediation re-smoke under the boundary above.
