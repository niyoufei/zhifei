# ZDoc KG-RUNTIME-46 Controlled Minimal File-Stat Metadata Implementation Draft Review

## 1. Stage Scope

KG-RUNTIME-46 is a controlled minimal implementation draft for authorized target file-stat metadata.

This stage does not prove runtime availability. It only records the static implementation draft needed for a later separately authorized review or smoke gate.

## 2. Actual Modified Files

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`

## 3. Actual New File

- `docs/zdoc-kg-controlled-minimal-file-stat-metadata-implementation-draft-kg-runtime-46-review.md`

## 4. Allowed-File Check

The implementation draft only modifies the allowed adapter file and the allowed route pass-through file.

`backend/app/main.py` was not modified.

Frontend files, tests, config files, and JSON files were not modified.

## 5. File-Stat Metadata Field Whitelist

The file-stat metadata field whitelist is limited to:

- `authorized_target`
- `allowlist_status`
- `exists`
- `is_file`
- `size_bytes`
- `mtime`
- `mode`
- `permission`

No body content, business content, entity content, knowledge entry content, prompt content, system instruction content, evidence content, scoring content, generated document body content, RAG-ready text, export content, or writeback content is added.

## 6. Single Authorized Target

The single authorized target remains:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

The implementation draft keeps a static, explicit, single-target allowlist. It does not scan directories and does not expand authorization to any other KG file, directory, registry, knowledge pack, or `AI知识图谱大全`.

## 7. Boundary Controls

The file-stat metadata helper is gated by all of the following conditions:

- feature flag is enabled at the route gate and passed into the adapter as `feature_flag_enabled=True`;
- `manual_trigger` is exactly `True`;
- `real_kg_read_only` is exactly `True`;
- `authorized_target` is strictly equal to `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

If these conditions are not met, the file-stat helper returns no file-stat metadata.

## 8. Metadata-Only Implementation

The adapter draft uses file-stat metadata access only through `Path.stat()` for the single authorized target.

It does not use `open`, `Path.open`, `read_text`, `read_bytes`, `json.load`, or `json.loads`.

The draft does not parse real KG JSON and does not read real KG body content.

## 9. Commands And Runtime Not Run

KG-RUNTIME-46 did not:

- run a service;
- access a port;
- call `/health`;
- call `/kg/read-only-preview`;
- call `/generate`;
- call `/export_docx`;
- call `/review/apply`;
- trigger ZBid writeback;
- write document body content;
- write `output`, `job`, or `export`;
- run Ollama;
- upgrade, pull, delete, or replace models;
- run `pytest`;
- run `py_compile`;
- run integration tests or CI.

## 10. No Integration Expansion

The draft does not connect generation, export, writeback, evidence, scoring, RAG, prompt registry, system instruction registry, knowledge-pack loading, registry creation, registry enablement, or CI.

## 11. Route Pass-Through

`backend/app/routers/kg_read_only_preview.py` only adds pass-through for the file-stat metadata whitelist fields and passes the already-checked feature-flag state into the adapter.

No route registration, endpoint path, service startup behavior, request shape beyond existing allowed fields, or runtime chain is changed.

## 12. Remaining Review Requirement

KG-RUNTIME-47 is still required as a separate static compliance review before any runtime validation or functional claim.

KG-RUNTIME-46 does not enter KG-RUNTIME-47.

## 13. Draft-Only Conclusion

This stage is only an implementation draft.

It cannot be used as evidence, cannot be used for scoring, and cannot be treated as proof that `/kg/read-only-preview` functionality is available or correct.
