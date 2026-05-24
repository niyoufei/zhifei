# KG-RUNTIME-19: ZDoc KG Real-KG Read-Only Metadata Smoke Authorization Gate

## 1. Step Identity

- Step: KG-RUNTIME-19.
- Name: ZDoc KG real-KG read-only metadata smoke authorization gate.
- Nature: docs-only authorization gate.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `e9363909353ba35379bc3bb72fd021b96696b957`.
- Start tag: `v0.1.399-zdoc-kg-real-read-target-discovery-plan`.

## 2. KG-RUNTIME-18 Audit Conclusion Summary

KG-RUNTIME-18 was limited to docs-only static discovery and a minimal future read plan.

KG-RUNTIME-18 froze the KG-RUNTIME-17 and KG-RUNTIME-16-R2 conclusions that the current validated KG read-only preview behavior is limited to inline synthetic disabled entities. It did not prove real KG reading, real KG parsing, real KG metadata extraction, real KG payload safety, `AI知识图谱大全` reading, real registry creation, registry enablement, knowledge-pack loading, evidence use, scoring use, RAG use, generation, export, review apply, ZBid writeback, Ollama use, or model operations.

KG-RUNTIME-18 did not read candidate real KG file contents, did not read real KG JSON, and did not read `AI知识图谱大全` contents. All real KG candidates identified by KG-RUNTIME-18 were path names only.

## 3. KG-RUNTIME-18 Candidate Read Target Summary

KG-RUNTIME-18 identified one primary minimal candidate for a separately authorized future metadata-level smoke:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

The primary candidate was identified because existing disabled pilot naming references a municipal-bridge KG context and the git index contains a matching real KG file name. KG-RUNTIME-18 treated this only as a candidate path name and did not read the file.

KG-RUNTIME-18 also identified a broader candidate pool by file name only:

- real KG path family: `知识图谱/ZF-KG-01-...json` through `知识图谱/ZF-KG-57-...json`;
- metadata or package-manifest candidate paths: `kg_config.json`, `backend/kg_config.json`, `manifest.json`, `backend/manifest.json`, `kg_packs/kgpack-20251227_104512/manifest.json`, and `backend/kg_packs/kgpack-20251227_104512/manifest.json`;
- disabled candidate or controlled-entity reference paths under `docs/kg-controlled-entities/`, `docs/kg-manifest-candidates/`, and `docs/kg-registry-candidates/`.

Those disabled reference paths remain not evidence, not scoring input, not enabled registries, and not runtime-loadable knowledge packages.

## 4. Current Read-Only Preview Route State

The current `/kg/read-only-preview` route state is validated only for:

- default-off route behavior before explicit enablement;
- manual-trigger request shape;
- inline synthetic disabled manifest entity;
- inline synthetic disabled registry entity;
- preview-only response;
- read-only response;
- no-write response;
- no evidence use;
- no scoring use;
- no RAG;
- no generation;
- no export;
- no `/review/apply`;
- no ZBid writeback;
- no Ollama or model operation.

This route state does not prove real KG access, real KG JSON parsing, real KG metadata safety, real KG payload safety, or real KG integration.

## 5. Current Adapter State

The current adapter state is validated only as a pure preview adapter path for inline synthetic disabled entities.

The adapter has not been validated against:

- real KG files;
- `AI知识图谱大全`;
- real KG entity JSON;
- real knowledge packages;
- registry-backed runtime data;
- evidence-producing paths;
- scoring-producing paths;
- generation paths;
- export paths;
- ZBid writeback paths.

The validated adapter boundary remains preview-only, read-only, no-write, no-evidence, no-scoring, no-RAG, no-generation, no-export, and no-ZBid-writeback.

## 6. Verified and Unverified Scope

Current verified scope:

- inline synthetic disabled entities;
- manual-trigger success path;
- route-to-adapter preview-only response;
- no-write response fields.

Current unverified scope:

- real KG metadata-level read;
- real KG file content reading;
- real KG JSON parsing;
- real KG metadata extraction;
- `AI知识图谱大全` content reading;
- knowledge-pack loading;
- registry creation, registration, enablement, or loading;
- evidence use;
- scoring use;
- RAG use;
- generation use;
- export use;
- ZBid writeback use.

## 7. Next-Stage Metadata-Level Smoke Authorization Conditions

Any future real KG metadata-level smoke requires separate explicit authorization before execution.

The future authorization must name in advance:

- the exact single KG path allowed for inspection;
- the exact command list allowed to run;
- the exact metadata-level fields allowed to be observed;
- the exact expected output boundary;
- whether any document may be created;
- whether any git operation is allowed;
- explicit confirmation that no service, port, route, generation, export, writeback, registry load, RAG, scoring path, Ollama path, or model operation may run.

The recommended first target remains only a candidate path unless separately authorized:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

## 8. Next-Stage Metadata-Level Smoke Allowed Boundary

If separately authorized, the next-stage real KG metadata-level smoke may only:

- inspect one explicitly named KG path;
- perform one manual-trigger read-only metadata inspection;
- read file-level metadata only;
- report only pre-agreed metadata-level fields;
- preserve default-off behavior outside the explicit smoke context;
- preserve manual-trigger execution;
- preserve read-only and no-write behavior;
- avoid persistent cache or runtime state mutation.

The next-stage smoke may not summarize KG facts, may not extract business正文, and may not use KG contents for any user-facing business answer.

## 9. Next-Stage Metadata-Level Smoke Forbidden Boundary

The next-stage smoke must not:

- read business正文 content;
- load a real knowledge package;
- create a real registry;
- register a knowledge package;
- enable a knowledge package;
- load a knowledge package;
- connect RAG;
- connect prompt registry;
- connect system instruction registry;
- use KG data as evidence;
- use KG data for scoring;
- generate document body content;
- export a document;
- call `/review/apply`;
- trigger ZBid writeback;
- write document body content;
- write `output/job/export`;
- run Ollama;
- upgrade, pull, delete, or replace a model;
- run service startup unless a later gate explicitly authorizes it;
- access a port unless a later gate explicitly authorizes it;
- call `/health` unless a later gate explicitly authorizes it;
- call `/kg/read-only-preview` unless a later gate explicitly authorizes it;
- call `/generate`, `/export_docx`, or `/review/apply`;
- connect tests or CI;
- add `.pyc` or `__pycache__` changes;
- enter a real-use phase.

## 10. Mandatory Future Invariants

Any future real KG metadata-level smoke must remain:

- default-off;
- manual-trigger;
- read-only;
- no-write;
- no-evidence;
- no-scoring;
- no-RAG;
- no-generation;
- no-export;
- no-ZBid-writeback;
- no-Ollama;
- no-model-upgrade.

Any future real KG read can only be a metadata-level smoke. It must not enter real use.

## 11. KG-RUNTIME-19 Negative Execution Confirmation

This KG-RUNTIME-19 step did not read real KG file contents.

This KG-RUNTIME-19 step did not read real KG JSON.

This KG-RUNTIME-19 step did not read `AI知识图谱大全` contents.

This KG-RUNTIME-19 step did not run a service.

This KG-RUNTIME-19 step did not access a port.

This KG-RUNTIME-19 step did not call `/health`.

This KG-RUNTIME-19 step did not call `/kg/read-only-preview`.

This KG-RUNTIME-19 step did not trigger `/generate`, `/export_docx`, or `/review/apply`.

This KG-RUNTIME-19 step did not trigger ZBid writeback.

This KG-RUNTIME-19 step did not write document body content.

This KG-RUNTIME-19 step did not write `output/job/export`.

This KG-RUNTIME-19 step did not generate DOCX.

This KG-RUNTIME-19 step did not run Ollama.

This KG-RUNTIME-19 step did not upgrade or pull models.

This KG-RUNTIME-19 step did not delete or replace models.

This KG-RUNTIME-19 step did not modify code, JSON, tests, frontend, or config.

This KG-RUNTIME-19 step did not connect RAG, prompt registry, or system instruction registry.

This KG-RUNTIME-19 step did not connect tests or CI.

This KG-RUNTIME-19 step did not create a real registry.

This KG-RUNTIME-19 step did not register, enable, or load a knowledge package.

This KG-RUNTIME-19 step did not add `.pyc` or `__pycache__` changes.

## 12. Validation Results

- `git diff --check`: passed with exit code 0 before staging this target docs file.
- `git diff --cached --check`: passed with exit code 0 after staging only this target docs file.

## 13. Final Boundary Conclusion

KG-RUNTIME-19 is limited to this docs-only authorization gate.

The next stage, if separately authorized, can only be a real KG metadata-level smoke that reads file-level metadata only. It must not read business正文 content, load a real knowledge package, create a real registry, register, enable, or load knowledge packages, connect RAG, connect prompt registry, connect system instruction registry, generate, export, write back, score, create evidence, run Ollama, upgrade models, or enter real use.

KG-RUNTIME-19 did not enter KG-RUNTIME-20.
