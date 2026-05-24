# KG-RUNTIME-52: ZDoc KG Real-KG Structure-Read Route Implementation Draft Static Compliance and No-Content-Leak Review

## 1. Step Identity

- Step: KG-RUNTIME-52.
- Name: ZDoc KG real-KG structure-read route implementation draft static compliance and no-content-leak review.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `47dde52845963a8ada29f9c6a138855737055d1e`.
- Start tag: `v0.1.432-zdoc-kg-structure-read-route-implementation-draft`.
- Review mode: docs-only static review.
- Runtime validation: not performed.
- Next step boundary: KG-RUNTIME-53 is still required for frozen audit and any authorized structure-read route smoke gate.

## 2. Static Texts Reviewed

Only the following static text surfaces were reviewed:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`
- `docs/zdoc-kg-real-kg-structure-read-route-controlled-implementation-draft-kg-runtime-51-review.md`

No real KG file body was read. No real KG JSON was parsed. No service was started. No endpoint was called.

## 3. KG-RUNTIME-51 Scope Compliance

KG-RUNTIME-51 changed only the authorized implementation draft surfaces:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`

KG-RUNTIME-51 added only its review document:

- `docs/zdoc-kg-real-kg-structure-read-route-controlled-implementation-draft-kg-runtime-51-review.md`

Static diff review found no KG-RUNTIME-51 changes to:

- `backend/app/main.py`
- `frontend`
- `tests`
- `config`
- JSON files

This satisfies the KG-RUNTIME-51 authorized adapter / route scope for the implementation draft.

## 4. Route Input Validation and Passthrough

The route draft adds `structure_read` to the allowed request field set and passes it through to the adapter only after the existing route gates have passed.

The route blocks:

- disabled feature flag;
- missing payload;
- illegal request fields;
- missing `manual_trigger = true`;
- `authorized_target` without `real_kg_read_only = true`;
- `real_kg_read_only` values other than `true`;
- `structure_read` values other than `true`;
- `structure_read = true` without `real_kg_read_only = true`;
- `structure_read = true` without `authorized_target`.

The route does not call service startup, generation, export, review apply, ZBid writeback, Ollama, external endpoints, RAG, prompt registry, system instruction registry, or knowledge-pack loading.

## 5. New Structure Draft Fields

The implementation draft adds the following structure-read draft fields:

- `structure_read`
- `structure_read_only`
- `structure_summary`
- `structure_contract`

The adapter response whitelist and route metadata passthrough whitelist include these fields. No additional runtime output fields were identified outside the declared structure-read draft surface.

## 6. Structure-Read Gate Review

The adapter structure-read branch remains jointly controlled by all of the following static gates:

- feature flag enabled;
- `manual_trigger = true`;
- `real_kg_read_only = true`;
- `structure_read = true`;
- `authorized_target` strictly equals `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

If the authorized target does not exactly match, the adapter returns blocked status before the structure summary path. If `structure_read` is true but the feature flag gate is not true, the adapter returns blocked status before the structure summary path.

KG-RUNTIME-52 did not execute this branch.

## 7. No Import-Time or Service-Start Read

Static review found no file body read at module import time.

The adapter defines the authorized path as a `Path` constant, but import-time code does not call `open`, `json.load`, directory scanning, registry loading, service calls, model calls, or writeback.

Static review found no service-start hook added by KG-RUNTIME-51. `backend/app/main.py` was not modified by KG-RUNTIME-51.

## 8. No Directory Scan, Batch Read, or Allowlist Expansion

The draft keeps a single authorized target:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

Static review found no `glob`, `rglob`, `listdir`, `os.walk`, batch read loop over a directory, allowlist expansion, registry creation, or knowledge-pack loading in the reviewed route / adapter draft.

## 9. Real KG Body Read and JSON Parse Boundary

KG-RUNTIME-52 did not actually read the real KG file body.

KG-RUNTIME-52 did not actually parse the real KG JSON.

Static code review confirms that the implementation draft contains a dormant, gated structure-read code path using the single authorized target path and `json.load` if all structure-read gates are satisfied. This KG-RUNTIME-52 review is therefore not a runtime approval and not proof that the structure-read route has passed smoke validation.

## 10. No Runtime Calls Performed

KG-RUNTIME-52 did not:

- run service startup;
- access any port;
- call `/health`;
- call `/kg/read-only-preview`;
- call `/generate`;
- call `/export_docx`;
- call `/review/apply`;
- trigger ZBid writeback;
- run Ollama;
- upgrade, pull, delete, or replace models;
- run `python3 -m json.tool`;
- run `py_compile`;
- run `pytest`;
- connect tests or CI.

## 11. Structure Summary Field Whitelist

The structure summary output is statically limited to:

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

No other structure summary fields were identified in the reviewed implementation draft.

## 12. No-Content-Leak Static Review

Within the structure summary whitelist, the draft keeps output structure-only:

- scalar values: type counts only, no scalar values;
- list values: list length and element type counts only, no element contents;
- dict values: key names, key count, selected structure paths, and field type sets only, no value contents;
- selected paths: structural path names and JSON type names only;
- no business body values;
- no entity body content;
- no knowledge-entry body content;
- no prompt content;
- no system instruction content;
- no evidence content;
- no scoring content.

The review did not identify any static output path that returns scalar text values, list element contents, dict value contents, prompt bodies, system instruction bodies, evidence bodies, scoring bodies, generated document body content, or RAG-ready text blocks.

## 13. No Generation, Export, Writeback, Evidence, or Scoring Coupling

Static review found no connection from the structure-read draft to:

- generation chain;
- export chain;
- writeback chain;
- ZBid writeback;
- evidence production;
- scoring production.

The route and adapter output keep the corresponding boundary fields false or no-op, including `no_generation`, `no_export`, `no_write`, `no_zbid_writeback`, `no_evidence`, `no_scoring`, and `no_rag`.

The result of KG-RUNTIME-52 must not be used as evidence or scoring.

## 14. No RAG or Registry Coupling

Static review found no new connection to:

- RAG;
- prompt registry;
- system instruction registry;
- knowledge-pack registry;
- manifest registration;
- runtime KG registry.

The route base response keeps registry and knowledge-pack loading permissions disabled.

## 15. No New Runtime Entry, Background Task, Test, or CI Hook

Static review found no new:

- runtime entrypoint;
- background task;
- automatic load hook;
- automatic registration hook;
- test hook;
- CI hook.

KG-RUNTIME-51 did not modify `backend/app/main.py`, frontend, tests, config, or JSON files.

## 16. KG-RUNTIME-53 Gate

KG-RUNTIME-53 is still required before any runtime confidence claim.

KG-RUNTIME-53 must remain the separate authorization gate for frozen audit and any structure-read route smoke. This KG-RUNTIME-52 review does not authorize entering real use, service validation, endpoint validation, evidence use, scoring use, generation, export, RAG, registry work, or writeback.

## 17. Static Compliance Conclusion

KG-RUNTIME-52 is complete as a docs-only static review.

Static review conclusion:

- KG-RUNTIME-51 stayed within the authorized adapter / route implementation draft scope.
- `main.py`, frontend, tests, config, and JSON files were not modified by KG-RUNTIME-51.
- The route added `structure_read` validation and passthrough.
- The adapter added `structure_read_only`, `structure_summary`, and `structure_contract` draft fields.
- The structure-read draft remains guarded by feature flag, manual trigger, real-KG read-only flag, structure-read flag, and strict single authorized target.
- No import-time read was identified.
- No service-start read was identified.
- No directory scan, batch read, or allowlist expansion was identified.
- KG-RUNTIME-52 did not actually read real KG body content.
- KG-RUNTIME-52 did not actually parse real KG JSON.
- KG-RUNTIME-52 did not run service, access ports, or call endpoints.
- Structure summary output is limited to the declared structure-only whitelist.
- No static content-leak output path was identified for scalar values, list contents, dict values, business正文, entity正文, knowledge entry正文, prompt content, system instruction content, evidence content, or scoring content.
- No generation, export, writeback, RAG, registry, evidence, scoring, runtime entrypoint, background task, automatic loading, test, or CI coupling was identified.

KG-RUNTIME-52 is a static compliance review only. It does not prove that the structure-read function or route has been run, smoke-tested, or accepted for real use.
