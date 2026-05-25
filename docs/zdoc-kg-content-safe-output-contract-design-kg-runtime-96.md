# KG-RUNTIME-96 ZDoc KG content-safe output contract design

## Stage Scope

- Stage: KG-RUNTIME-96.
- Artifact type: docs-only output contract design.
- Allowed artifact: `docs/zdoc-kg-content-safe-output-contract-design-kg-runtime-96.md`.
- Purpose: define the ZDoc KG content-safe output field tiers after the KG-RUNTIME-94 PASS result and KG-RUNTIME-95 PASS freeze.

KG-RUNTIME-96 does not modify code, does not run a service, does not access an endpoint, does not read a real KG body, does not parse real KG JSON, does not enter ZDoc integration, and does not enter trial use.

## Frozen Input Facts

KG-RUNTIME-94 re-smoke conclusion: PASS.

The frozen KG-RUNTIME-94 PASS facts are:

- `structure_summary` 13 fields passed.
- `structural_profile_summary` 14 fields passed.
- `module_name_candidates` returned an empty list.
- `redaction_policy` returned the safe enum `0` / redacted.
- scalar full leaf overlap = `0`.
- substring overlap = `0`.

KG-RUNTIME-95 froze this PASS result as a docs-only audit package. KG-RUNTIME-95 did not enter real use, ZDoc integration, preview-only integration, generation, export, writeback, evidence use, scoring use, or trial use.

## Trial-Use Definition

Trial use may start only after all of the following are complete and separately accepted:

- KG safe access is complete.
- ZDoc preview-only chain is complete.
- The local model is upgraded to the latest available version.
- Stability validation after the model upgrade has passed.

Until those conditions are all satisfied, the current KG output contract remains design-only and preview-only scoped. KG-RUNTIME-96 itself does not satisfy or execute any trial-use prerequisite.

## Content-Safe Output Contract

This output contract serves ZDoc preview-only use only.

It must not be connected to:

- `/generate`.
- `/export_docx`.
- `/review/apply`.
- output, job, or export writes.
- ZBid writeback.
- evidence extraction or evidence storage.
- scoring.

It must not be treated as a generation-chain input, an export input, a writeback input, evidence, or scoring material.

## A. Fields Allowed For ZDoc Preview-Only Display

These fields may be displayed only in a preview-only ZDoc surface, and only as content-safe structural status, counts, buckets, flags, or codes.

### Top-level preview-only fields

- `structure_read_only`.
- `structure_summary`.
- `structural_profile_only`.
- `structural_profile_summary`.
- `structure_contract` safe enum / numeric-code fields.
- `structural_profile_contract` safe enum / numeric-code fields.

### `structure_summary` 13-field whitelist

- `top_level_type`.
- `top_level_key_names`.
- `top_level_key_count`.
- `dict_count`.
- `list_count`.
- `null_count`.
- `scalar_type_counts`.
- `selected_structure_paths`.
- `list_lengths`.
- `field_type_sets`.
- `max_depth_limited`.
- `authorized_target`.
- `allowlist_status`.

### `structural_profile_summary` 14-field whitelist

- `authorized_target`.
- `allowlist_status`.
- `profile_enabled`.
- `profile_scope`.
- `max_depth_limited`.
- `path_count`.
- `path_type_counts`.
- `depth_histogram`.
- `field_name_counts`.
- `field_type_sets`.
- `list_length_buckets`.
- `dict_key_count_buckets`.
- `module_name_candidates`.
- `redaction_policy`.

### Safe contract-code fields

For `structure_contract`, preview-only display may use only safe enum / numeric-code fields such as:

- `contract_scope`.
- `authorized_target`.
- `allowlist_status`.
- `target_policy`.
- `summary_field_whitelist`.
- `value_output_policy`.
- `scalar_policy`.
- `list_policy`.
- `dict_policy`.

For `structural_profile_contract`, preview-only display may use only safe enum / numeric-code fields such as:

- `contract_scope`.
- `authorized_target`.
- `allowlist_status`.
- `target_policy`.
- `summary_field_whitelist`.
- `profile_scope`.
- `redaction_policy`.
- `scalar_policy`.
- `list_policy`.
- `dict_policy`.
- `module_name_policy`.

Boolean guard states and runtime boundary flags may be shown only as audit status, not as正文, evidence, scoring, or generation content.

## B. Audit-Only Fields

These fields may be retained or shown only for operator audit, validation, and release-gate review. They must not enter正文, generation, export, writeback, evidence, or scoring.

- Feature flag status.
- `manual_trigger` status.
- `real_kg_read_only` status.
- `authorized_target` hit status.
- `allowlist_status`.
- route contract code.
- adapter contract code.
- validation result.
- overlap check result.
- no-write / no-evidence / no-scoring / no-rag / no-generation / no-export / no-ZBid-writeback boundary flags.

Audit-only fields may support a pass/fail gate, release note, or preview badge. They must not be transformed into natural-language KG content.

## C. Prohibited Fields And Content

The following must never enter正文, the generation chain, evidence, or scoring:

- KG scalar value.
- list item content.
- dict value content.
- business正文.
- entity正文.
- knowledge-entry正文.
- prompt.
- system instruction.
- evidence.
- scoring.
- any original KG text fragment.
- any string that can reverse-infer KG正文.

This prohibition applies even when the content appears inside a whitelisted container, audit log, contract object, validation object, or preview response. If a value can expose or reconstruct KG正文, it is prohibited.

## Downstream Binding Rules

The KG content-safe output contract is preview-only.

It explicitly does not permit:

- `/generate` integration.
- `/export_docx` integration.
- `/review/apply` integration.
- output, job, or export writes.
- ZBid writeback.
- evidence use.
- scoring use.
- RAG integration.
- registry integration.
- CI integration.
- real-use entry.
- trial-use entry.

Any future ZDoc UI display must preserve the A/B/C field tiers above and must not promote audit-only or prohibited content into正文, generation, export, writeback, evidence, or scoring.

## KG-RUNTIME-97 Authorization Gate Draft

KG-RUNTIME-97 is not entered by this document.

If KG-RUNTIME-97 is separately authorized later, it may only produce a minimal content-safe output contract implementation / adapter contract mapping draft under these limits:

- Allow only minimal modification of the adapter / route or addition of an independent contract helper.
- Do not run a service.
- Do not access an endpoint.
- Do not read a real KG.
- Do not parse real KG JSON.
- Do not run another directory scan.
- Do not run `pytest`.
- Do not run `py_compile`.
- Do not run Ollama.
- Do not integrate generation.
- Do not integrate export.
- Do not integrate writeback.
- Do not integrate RAG.
- Do not integrate registry.
- Do not integrate CI.
- Do not enter trial use.

KG-RUNTIME-97 must remain separate from KG-RUNTIME-96 and must require a new explicit authorization before any implementation or mapping work begins.

## KG-RUNTIME-96 Closeout Boundary

KG-RUNTIME-96 completes only the content-safe output contract design.

It does not:

- modify `backend/kg_read_only_preview_adapter.py`.
- modify `backend/app/routers/kg_read_only_preview.py`.
- modify `main.py`.
- modify frontend, tests, config, or JSON files.
- run a service.
- access a port.
- call `/health`.
- call `/kg/read-only-preview`.
- trigger `/generate`, `/export_docx`, or `/review/apply`.
- write output, job, or export files.
- trigger ZBid writeback.
- run Ollama.
- read real KG正文.
- parse real KG JSON.
- become evidence.
- become scoring.
- enter real use.
- enter ZDoc integration.
- enter trial use.
- enter KG-RUNTIME-97.
