# ZDoc KG-RUNTIME-48 File-Stat Metadata Implementation Draft Frozen Audit Package And Controlled Route Smoke Authorization Gate

## 1. Stage Scope

KG-RUNTIME-48 is a docs-only frozen audit package and controlled route smoke authorization gate for the KG file-stat metadata implementation draft.

This stage only freezes the KG-RUNTIME-46 and KG-RUNTIME-47 results and defines the authorization boundary for any later KG-RUNTIME-49 route smoke validation. KG-RUNTIME-48 itself does not modify code, does not run the service, does not access endpoints, does not read real KG body content, and does not parse real KG JSON.

## 2. Frozen Prior Results

KG-RUNTIME-46 has completed the controlled minimal file-stat metadata implementation draft.

KG-RUNTIME-47 has completed the static compliance and no-runtime/no-IO review of that implementation draft.

The current implementation remains limited to metadata-only behavior. It must not be treated as runtime validation, functional availability proof, evidence material, scoring input, generation input, export input, writeback input, RAG input, prompt registry material, system instruction registry material, or knowledge-pack material.

## 3. Frozen File-Stat Metadata Whitelist

The file-stat metadata field whitelist remains limited to exactly:

- `authorized_target`
- `allowlist_status`
- `exists`
- `is_file`
- `size_bytes`
- `mtime`
- `mode`
- `permission`

No real KG body content, business body content, entity body content, knowledge entry body content, prompt content, system instruction content, evidence content, scoring content, generated document body content, export content, RAG-ready text, or writeback content is included in this whitelist.

## 4. Frozen Single Authorized Target

The only authorized target remains:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

No other KG file, directory, registry entry, knowledge pack, or `AI知识图谱大全` path is authorized by KG-RUNTIME-48.

## 5. Frozen Trigger Conditions

The file-stat metadata path must remain gated by all of the following conditions at the same time:

- the KG read-only preview feature flag is enabled;
- `manual_trigger = true`;
- `real_kg_read_only = true`;
- `authorized_target` strictly equals `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

If any condition is absent or false, the file-stat metadata path remains unauthorized.

## 6. Frozen Integration Boundaries

KG-RUNTIME-48 freezes the following KG-RUNTIME-47 static review conclusions:

- the implementation is not connected to the generation chain;
- the implementation is not connected to the export chain;
- the implementation is not connected to the writeback chain;
- the implementation is not connected to RAG;
- the implementation is not connected to the prompt registry;
- the implementation is not connected to the system instruction registry;
- the implementation is not used as evidence;
- the implementation is not used for scoring;
- the implementation adds no runtime entry;
- the implementation adds no background task;
- the implementation adds no auto-load path;
- the implementation adds no auto-registration path;
- the implementation adds no test hook;
- the implementation adds no CI hook.

## 7. KG-RUNTIME-48 Execution Boundary

During KG-RUNTIME-48, the audit package must remain docs-only.

KG-RUNTIME-48 does not authorize any of the following:

- modifying `backend/kg_read_only_preview_adapter.py`;
- modifying `backend/app/routers/kg_read_only_preview.py`;
- modifying `backend/app/main.py`;
- modifying frontend files, tests, config files, or JSON files;
- reading real KG file body content;
- parsing real KG JSON;
- running `python3 -m json.tool`;
- reading, copying, moving, or deleting `AI知识图谱大全`;
- loading a real knowledge pack;
- creating, registering, or enabling a registry or knowledge pack;
- running the service;
- accessing a port;
- calling `/health`;
- calling `/kg/read-only-preview`;
- calling `/generate`;
- calling `/export_docx`;
- calling `/review/apply`;
- triggering ZBid writeback;
- writing document body content;
- writing `output`, `job`, or `export`;
- running Ollama;
- upgrading, pulling, deleting, or replacing models;
- running `py_compile`;
- running `pytest`;
- connecting tests or CI;
- entering real usage.

## 8. KG-RUNTIME-49 Authorization Gate Draft

KG-RUNTIME-49 may only proceed if it is separately and explicitly authorized after KG-RUNTIME-48.

If KG-RUNTIME-49 is separately authorized, its controlled file-stat metadata route smoke validation boundary must be limited to:

- temporarily starting the service;
- temporarily enabling the KG read-only preview feature flag;
- calling `/health`;
- calling `/kg/read-only-preview`;
- sending a request with `manual_trigger = true`;
- sending a request with `real_kg_read_only = true`;
- setting `authorized_target` only to `知识图谱/ZF-KG-12-Municipal-Bridge.json`;
- verifying only whether the route returns file-stat metadata fields;
- not reading real KG body content;
- not parsing real KG JSON;
- not outputting business body content, entity body content, knowledge entry body content, prompt content, evidence content, or scoring content;
- not triggering generation, export, or writeback;
- not running Ollama;
- not connecting RAG, registry, or CI;
- stopping the service after smoke completion;
- confirming the port is released after shutdown.

KG-RUNTIME-49 must not broaden the authorized target, must not use file-stat metadata as evidence or scoring, and must not enter real KG usage.

## 9. Frozen Conclusion

KG-RUNTIME-48 is complete only as a docs-only frozen audit package and authorization gate.

The KG file-stat metadata implementation draft remains metadata-only, single-target, manually gated, preview-only, no-evidence, no-scoring, no-generation, no-export, no-writeback, no-RAG, no-registry, and no-CI.

KG-RUNTIME-48 does not enter KG-RUNTIME-49. Controlled route smoke validation remains blocked unless KG-RUNTIME-49 is separately authorized.
