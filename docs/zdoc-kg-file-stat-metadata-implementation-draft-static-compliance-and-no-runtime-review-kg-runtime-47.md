# ZDoc KG-RUNTIME-47 File-Stat Metadata Implementation Draft Static Compliance And No-Runtime Review

## 1. Review Scope

KG-RUNTIME-47 is a docs-only static compliance review of the KG-RUNTIME-46 file-stat metadata implementation draft.

This review only inspected the authorized static texts:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`
- `docs/zdoc-kg-controlled-minimal-file-stat-metadata-implementation-draft-kg-runtime-46-review.md`

This review did not run the application, did not access ports, did not call endpoints, did not read real KG file body content, and did not parse real KG JSON.

## 2. Baseline

- Branch: `main`
- Start HEAD: `c15b02c4123047c88826cb09424ceb5907c44601`
- Start tag: `v0.1.427-zdoc-kg-file-stat-metadata-implementation-draft`

## 3. Static Evidence Reviewed

`git show --name-only HEAD` showed the KG-RUNTIME-46 commit touched only:

- `backend/app/routers/kg_read_only_preview.py`
- `backend/kg_read_only_preview_adapter.py`
- `docs/zdoc-kg-controlled-minimal-file-stat-metadata-implementation-draft-kg-runtime-46-review.md`

The implementation portion is therefore limited to the authorized adapter and route files. The third file is the KG-RUNTIME-46 docs-only review artifact.

## 4. Allowed Scope Check

Result: compliant for static draft scope.

- `backend/kg_read_only_preview_adapter.py` was modified by KG-RUNTIME-46.
- `backend/app/routers/kg_read_only_preview.py` was modified by KG-RUNTIME-46.
- `backend/app/main.py` was not modified.
- No frontend file was modified.
- No test file was modified.
- No config file was modified.
- No JSON file was modified.

## 5. File-Stat Metadata Field Whitelist

Result: compliant for the file-stat metadata fields.

The file-stat metadata fields are limited to:

- `authorized_target`
- `allowlist_status`
- `exists`
- `is_file`
- `size_bytes`
- `mtime`
- `mode`
- `permission`

The route pass-through also carries static contract and boundary metadata, but the file-stat metadata helper itself exposes only the eight fields above.

## 6. Single Authorized Target

Result: compliant.

The single authorized target remains exactly:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

No second KG file, directory, registry, knowledge pack, or `AI知识图谱大全` target is added.

## 7. Gate Conditions

Result: compliant.

The file-stat metadata helper remains gated by all of the following conditions:

- feature flag is enabled at the route gate and passed to the adapter;
- `manual_trigger` is exactly `True`;
- `real_kg_read_only` is exactly `True`;
- `authorized_target` strictly equals `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

If any condition is not met, the helper returns no file-stat metadata.

## 8. No Body Read Or JSON Parse Logic

Result: compliant in the reviewed code.

Static search of the adapter and route did not find real KG body-read or JSON-parse logic using:

- `open`
- `Path.open`
- `read_text`
- `read_bytes`
- `json.load`
- `json.loads`

The only filesystem metadata operation present in the implementation draft is the gated `Path.stat()` call for the single authorized target. KG-RUNTIME-47 did not execute that call.

## 9. No Real KG JSON Parsing

Result: compliant.

The reviewed adapter and route do not parse real KG JSON. They do not load, deserialize, or traverse KG JSON body content.

## 10. No Directory Scan Or Allowlist Expansion

Result: compliant.

The reviewed adapter and route do not add directory scanning, batch reading, recursive globbing, or allowlist expansion. The draft remains single-target only.

## 11. No Generation, Export, Or Writeback Integration

Result: compliant.

The reviewed adapter and route do not call or trigger:

- generation chain;
- export chain;
- review apply chain;
- ZBid writeback;
- document body writes;
- `output`, `job`, or `export` writes.

The route response continues to mark these capabilities as disabled or false.

## 12. No RAG Or Registry Integration

Result: compliant.

The reviewed adapter and route do not connect to:

- RAG;
- prompt registry;
- system instruction registry;
- knowledge-pack loading;
- registry creation;
- registry enablement.

Any registry-related fields in the legacy disabled-entity preview path remain static disabled contract fields, not real registry loading or registration.

## 13. No Evidence Or Scoring Use

Result: compliant.

The reviewed adapter and route continue to mark evidence and scoring as disallowed. The file-stat metadata draft is not connected to evidence production and is not connected to scoring.

## 14. No Runtime Entry Or Automation Expansion

Result: compliant.

KG-RUNTIME-46 did not modify `backend/app/main.py` and did not add a new runtime entry, background task, auto-load path, auto-registration path, test hook, or CI hook.

## 15. KG-RUNTIME-47 Execution Boundaries

During KG-RUNTIME-47, the review did not:

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
- run `python3 -m json.tool`;
- run `py_compile`;
- run `pytest`;
- load a real knowledge pack;
- read, copy, move, or delete `AI知识图谱大全`.

## 16. Remaining Gate

KG-RUNTIME-48 is still required for any separately authorized freeze audit and route smoke gate.

KG-RUNTIME-47 does not enter KG-RUNTIME-48 and does not authorize runtime use.

## 17. Conclusion

KG-RUNTIME-47 static review result: compliant as a metadata-only, controlled single-target implementation draft under the stated no-runtime review boundary.

This is a static review only. It does not prove that `/kg/read-only-preview` runs successfully, does not prove runtime file-stat behavior, and must not be used as evidence, scoring input, generation input, export input, writeback input, RAG input, or registry material.
