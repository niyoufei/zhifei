# KG-RUNTIME-51: ZDoc KG Real-KG Structure-Read Route Controlled Implementation Draft Review

## 1. Step Identity

- Step: KG-RUNTIME-51.
- Name: ZDoc KG real-KG structure-read route controlled implementation draft.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `abe96bf51bfba02051167b060bcd0b9d78cfed90`.
- Start tag: `v0.1.431-zdoc-kg-file-stat-smoke-frozen-audit-gate`.
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

## 2. Actual Modified Files

Actual modified files:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`

Actual added file:

- `docs/zdoc-kg-real-kg-structure-read-route-controlled-implementation-draft-kg-runtime-51-review.md`

This step modified only the authorized adapter / route files and added this one authorized review document.

## 3. Explicit Unmodified Surfaces

- `backend/app/main.py`: not modified.
- `frontend`: not modified.
- `tests`: not modified.
- `config`: not modified.
- JSON files: not modified.
- `AI知识图谱大全`: not read, copied, moved, deleted, registered, or loaded.

## 4. Implementation Draft Scope

`backend/kg_read_only_preview_adapter.py` adds a dormant controlled structure-read draft branch.

New structure-read related fields / constants include:

- `structure_read`
- `structure_read_only`
- `structure_summary`
- `structure_contract`
- `REAL_KG_STRUCTURE_READ_POLICY`
- `REAL_KG_STRUCTURE_TARGET_POLICY`
- `STRUCTURE_SUMMARY_FIELD_WHITELIST`

The structure-read branch is gated by all of the following conditions:

- feature flag enabled;
- `manual_trigger = true`;
- `real_kg_read_only = true`;
- `structure_read = true`;
- `authorized_target` strictly equals `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

The code contains a controlled structure summary function, but this KG-RUNTIME-51 step did not execute it.

## 5. Route Scope

`backend/app/routers/kg_read_only_preview.py` adds only minimal route field passthrough and validation for:

- `structure_read`

The route still requires the existing feature flag and `manual_trigger = true` before adapter dispatch. The structure-read request path also requires `real_kg_read_only = true` and the single authorized target.

## 6. Structure Output Whitelist

The structure summary output is limited to:

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

## 7. Anti-Leakage Rules

The implementation draft keeps the structure summary metadata-only / structure-only:

- scalar values: output type only, never the scalar value;
- list values: output length and element type summary only, never element content;
- dict values: output key names, key count, and field type sets only, never value content;
- no entity body content;
- no knowledge-entry body content;
- no prompt content;
- no system instruction content;
- no evidence content;
- no scoring content;
- no JSON string values, long text values, or rule body values.

## 8. Non-Execution Confirmation

- Actual real KG body read in this step: no.
- Actual real KG JSON parse in this step: no.
- `python3 -m json.tool`: not run.
- Service startup: not run.
- Port access: not performed.
- `/health`: not called.
- `/kg/read-only-preview`: not called.
- `/generate`: not called.
- `/export_docx`: not called.
- `/review/apply`: not called.
- ZBid writeback: not triggered.
- `output/job/export`: not written.
- Ollama: not run.
- Model upgrade, pull, delete, or replacement: not performed.
- `pytest`: not run.
- `py_compile`: not run.
- Tests / CI: not connected.

## 9. Runtime Boundary

This step does not connect the structure-read draft to:

- generation chain;
- export chain;
- writeback chain;
- RAG;
- prompt registry;
- system instruction registry;
- knowledge-pack registry;
- CI.

The result must not be used as evidence or scoring.

## 10. Single-Target Boundary

The authorized target remains a single target only:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

No allowlist expansion was made. No directory scanning or batch file reading was added.

## 11. Validation Boundary

Only static diff hygiene is authorized for this step:

- `git diff --check`
- `git diff --cached --check`

The structure-read function was not run. The route was not smoke-tested. The endpoint was not called. Therefore this step cannot certify that structure-read is operational.

## 12. Next Gate

KG-RUNTIME-52 is still required as a separate static compliance review.

This KG-RUNTIME-51 step does not enter KG-RUNTIME-52 and does not authorize real structure-read use, service validation, endpoint validation, evidence use, scoring use, generation, export, RAG, registry work, or writeback.

## 13. Final Boundary Conclusion

KG-RUNTIME-51 is only a controlled implementation draft.

It cannot be treated as proof that the structure-read route is usable. It only adds dormant, gated structure-read draft code and documents the boundary for later review.
