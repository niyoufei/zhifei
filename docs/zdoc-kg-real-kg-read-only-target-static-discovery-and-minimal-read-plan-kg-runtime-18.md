# KG-RUNTIME-18: ZDoc KG Real-KG Read-Only Target Static Discovery and Minimal Read Plan

## 1. Step Identity

- Step: KG-RUNTIME-18.
- Name: ZDoc KG real-KG read-only target static discovery and minimal read plan.
- Nature: docs-only static discovery and minimal read authorization plan.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `96e0dcbefb9ace30f319cb4a654e71e5ed1eacc1`.
- Start tag: `v0.1.398-zdoc-kg-read-only-preview-frozen-audit-gate`.

## 2. KG-RUNTIME-17 Audit Conclusion Summary

KG-RUNTIME-17 froze the KG-RUNTIME-16-R2 success-path smoke validation as a docs-only audit package.

The frozen conclusion was limited to the inline synthetic disabled entities success path. It did not prove real KG reading, real KG parsing, real KG safety, `AI知识图谱大全` reading, registry creation, registry enablement, knowledge-pack loading, evidence use, scoring use, RAG use, generation, export, review apply, ZBid writeback, Ollama use, or model operations.

KG-RUNTIME-17 did not run a service, did not access a port, did not call `/health`, did not call `/kg/read-only-preview`, and did not enter KG-RUNTIME-18.

## 3. KG-RUNTIME-16-R2 Success-Path Validation Summary

KG-RUNTIME-16-R2 validated only the manual-trigger success path for `/kg/read-only-preview` through a temporary local backend service and inline synthetic disabled manifest and registry entities.

The validated result was:

- HTTP `/health` success in the prior KG-RUNTIME-16-R2 smoke only;
- HTTP `/kg/read-only-preview` success in the prior KG-RUNTIME-16-R2 smoke only;
- `ok: true`;
- `enabled: true`;
- `status: preview_only`;
- `adapter_status: preview_only`;
- `manual_trigger_required: true`;
- `preview_only: true`;
- `read_only: true`;
- `no_write: true`.

KG-RUNTIME-16-R2 did not read real KG files, did not read `AI知识图谱大全`, did not load a real knowledge pack, did not use results as evidence or scoring, did not connect RAG, did not connect prompt registry, did not connect system instruction registry, did not generate, did not export, did not review-apply, did not trigger ZBid writeback, did not write document body content, did not write `output/job/export`, did not run Ollama, and did not modify code, JSON, tests, frontend, or config.

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

The adapter is not validated against:

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

Verified scope:

- inline synthetic disabled entities;
- manual-trigger success path;
- route-to-adapter preview-only response;
- no-write response fields.

Unverified scope:

- real KG file discovery beyond file-name-level static discovery;
- real KG JSON reading;
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

## 7. Candidate Real KG Read-Only Target Paths

The following candidate paths are identified only from git-index file names, git history metadata, KG-RUNTIME-16-R2 review records, KG-RUNTIME-17 review records, and existing document references.

Primary minimal candidate for a future metadata-level smoke, if separately authorized:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

Reason: the existing disabled pilot naming references a municipal-bridge KG context, and the git index contains a matching real KG file name. This is only a candidate path name. This step did not read that file.

Broader real KG candidate pool discovered by file name only:

- `知识图谱/ZF-KG-01-Housing-Master.json`
- `知识图谱/ZF-KG-02-Hospital-Special.json`
- `知识图谱/ZF-KG-03-Decoration-Master.json`
- `知识图谱/ZF-KG-04-Hospital-Deco.json`
- `知识图谱/ZF-KG-05-Exterior-Ancillary.json`
- `知识图谱/ZF-KG-06-Municipal-Drainage.json`
- `知识图谱/ZF-KG-07-Urban-Renewal.json`
- `知识图谱/ZF-KG-08-Municipal-Road.json`
- `知识图谱/ZF-KG-09-Landscape-Master.json`
- `知识图谱/ZF-KG-10-Municipal-Gas.json`
- `知识图谱/ZF-KG-11-Municipal-WTP.json`
- `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- `知识图谱/ZF-KG-13-River-Improvement.json`
- `知识图谱/ZF-KG-14-Sponge-City.json`
- `知识图谱/ZF-KG-15-Highway.json`
- `知识图谱/ZF-KG-16-Municipal-Tunnel.json`
- `知识图谱/ZF-KG-17-Water-Hydro.json`
- `知识图谱/ZF-KG-18-District-Heating.json`
- `知识图谱/ZF-KG-19-Power-Energy.json`
- `知识图谱/ZF-KG-20-Hydraulic-Hub.json`
- `知识图谱/ZF-KG-21-Waste-To-Energy.json`
- `知识图谱/ZF-KG-22-Rail-Transit.json`
- `知识图谱/ZF-KG-23-Petrochemical.json`
- `知识图谱/ZF-KG-24-Data-Center.json`
- `知识图谱/ZF-KG-25-Airport.json`
- `知识图谱/ZF-KG-26-Port-Harbor.json`
- `知识图谱/ZF-KG-27-Railway.json`
- `知识图谱/ZF-KG-28-Smart-Hospital.json`
- `知识图谱/ZF-KG-29-Industrial-Pipeline.json`
- `知识图谱/ZF-KG-30-Utility-Tunnel.json`
- `知识图谱/ZF-KG-31-Waterproofing.json`
- `知识图谱/ZF-KG-32-Intelligent-Weak-Current.json`
- `知识图谱/ZF-KG-33-Water-Fire-Water.json`
- `知识图谱/ZF-KG-34-HVAC.json`
- `知识图谱/ZF-KG-35-Fire-Protection.json`
- `知识图谱/ZF-KG-36-Communication.json`
- `知识图谱/ZF-KG-37-MEP.json`
- `知识图谱/ZF-KG-38-Existing-Building-Reinforcement.json`
- `知识图谱/ZF-KG-39-Steel-Structure.json`
- `知识图谱/ZF-KG-40-Prefabricated-Building.json`
- `知识图谱/ZF-KG-41-Deep-Excavation.json`
- `知识图谱/ZF-KG-42-Crane-Installation.json`
- `知识图谱/ZF-KG-43-Large-Lifting.json`
- `知识图谱/ZF-KG-44-Demolition.json`
- `知识图谱/ZF-KG-45-Curtain-Wall.json`
- `知识图谱/ZF-KG-46-SmartOM-FM.json`
- `知识图谱/ZF-KG-47-Scaffolding-Formwork.json`
- `知识图谱/ZF-KG-48-BIM-DigitalConstruction.json`
- `知识图谱/ZF-KG-49-SafetyCivilization.json`
- `知识图谱/ZF-KG-50-General-FourNew.json`
- `知识图谱/ZF-KG-51-SmartSite-General.json`
- `知识图谱/ZF-KG-52-FoundationEngineering.json`
- `知识图谱/ZF-KG-53-OffshoreWind-Marine.json`
- `知识图谱/ZF-KG-54-TemporaryWorks-SiteLayout.json`
- `知识图谱/ZF-KG-55-GreenConstruction.json`
- `知识图谱/ZF-KG-56-SmartOM-FM-Universe-SuperKG.json`
- `知识图谱/ZF-KG-57-NetworkGraph-Quantum-Carbon.json`

Metadata or package-manifest candidate paths discovered by file name only:

- `kg_config.json`
- `backend/kg_config.json`
- `manifest.json`
- `backend/manifest.json`
- `kg_packs/kgpack-20251227_104512/manifest.json`
- `backend/kg_packs/kgpack-20251227_104512/manifest.json`

Disabled candidate or controlled-entity reference paths discovered by file name only:

- `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json`
- `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json`
- `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`
- `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json`

These disabled reference paths are not treated as evidence, scoring input, enabled registries, or runtime-loadable knowledge packages.

## 8. Candidate Path Source Boundary

Candidate path sources used in this step:

- `git ls-files` file names;
- `git log --oneline` metadata;
- `git show --name-only --stat --oneline` metadata;
- KG-RUNTIME-16-R2 review document;
- KG-RUNTIME-17 review document;
- existing document file-name references.

This step did not read candidate real KG file contents.

This step did not read real KG JSON.

This step did not read `AI知识图谱大全` contents.

This step did not run `cat`, `sed`, `head`, `tail`, `python json.load`, or `python3 -m json.tool` against any real KG JSON.

## 9. Minimal Future Authorization Recommendation

If a later step separately authorizes real KG reading, the minimum authorization should be limited to one metadata-level smoke against one named path:

- preferred first target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`;
- allowed operation class: metadata-level read-only inspection only;
- allowed trigger: manual-trigger only;
- allowed runtime state: default-off unless explicitly enabled only for the manual smoke context;
- allowed output: a short smoke report containing only metadata-level fields agreed in advance;
- forbidden output: no document body content, no evidence payload, no scoring payload, no generated text, no exported document, no registry state mutation, no knowledge-pack registration, no runtime-use result.

The future authorization must name the exact command list before execution.

## 10. Minimal Future Request Boundary

The future request boundary should remain:

- one manual request only;
- one explicitly named KG path only;
- metadata-level inspection only;
- no content summarization of KG facts;
- no business-answer generation;
- no cross-file traversal;
- no directory-wide parse;
- no automatic registry lookup;
- no automatic knowledge-pack loading;
- no writes;
- no persistent cache;
- no output/job/export writes.

The future smoke may confirm only pre-agreed metadata-level properties, such as path presence, top-level parse eligibility if separately authorized, and disabled/no-evidence/no-scoring/no-write guard fields if those fields are explicitly part of the future authorization.

## 11. Future Forbidden Boundary

Any later real KG read step must continue to forbid:

- RAG connection;
- prompt registry connection;
- system instruction registry connection;
- evidence use;
- scoring use;
- generation;
- export;
- review apply;
- ZBid writeback;
- document body writing;
- `output/job/export` writing;
- Ollama use;
- model upgrade, model pull, model deletion, or model replacement;
- service startup unless explicitly authorized in that later step;
- port access unless explicitly authorized in that later step;
- `/health` access unless explicitly authorized in that later step;
- `/kg/read-only-preview` access unless explicitly authorized in that later step;
- `/generate`, `/export_docx`, or `/review/apply` access;
- tests or CI integration;
- `.pyc` or `__pycache__` changes;
- entry into real-use phase.

## 12. Required Future Real KG Read Invariants

Any future real KG read stage must remain:

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

## 13. KG-RUNTIME-18 Negative Execution Confirmation

This KG-RUNTIME-18 step did not run a service.

This KG-RUNTIME-18 step did not access a port.

This KG-RUNTIME-18 step did not call `/health`.

This KG-RUNTIME-18 step did not call `/kg/read-only-preview`.

This KG-RUNTIME-18 step did not trigger `/generate`, `/export_docx`, or `/review/apply`.

This KG-RUNTIME-18 step did not trigger ZBid writeback.

This KG-RUNTIME-18 step did not write document body content.

This KG-RUNTIME-18 step did not write `output/job/export`.

This KG-RUNTIME-18 step did not generate DOCX.

This KG-RUNTIME-18 step did not run Ollama.

This KG-RUNTIME-18 step did not upgrade or pull models.

This KG-RUNTIME-18 step did not delete or replace models.

This KG-RUNTIME-18 step did not modify code, JSON, tests, frontend, or config.

This KG-RUNTIME-18 step did not connect RAG, prompt registry, or system instruction registry.

This KG-RUNTIME-18 step did not connect tests or CI.

This KG-RUNTIME-18 step did not create a real registry.

This KG-RUNTIME-18 step did not register, enable, or load a knowledge package.

This KG-RUNTIME-18 step did not add `.pyc` or `__pycache__` changes.

## 14. Validation Results

- `git diff --check`: passed with exit code 0.
- `git diff --cached --check`: passed with exit code 0 after staging only this target docs file.

## 15. Final Boundary Conclusion

KG-RUNTIME-18 is limited to docs-only static discovery and a minimal future read plan.

The only primary future target recommended by this plan is `知识图谱/ZF-KG-12-Municipal-Bridge.json`, and even that path remains un-read in this step.

All candidate paths in this document are path names only. This step did not read candidate file contents, did not read real KG JSON, did not read `AI知识图谱大全`, did not load knowledge packages, did not create or use a registry, and did not use any KG result as evidence or scoring.

Any future real KG read must require a separate authorization gate and remain default-off, manual-trigger, read-only, no-write, no-evidence, no-scoring, no-RAG, no-generation, no-export, no-ZBid-writeback, no-Ollama, no-model-upgrade, and metadata-level smoke only.

KG-RUNTIME-18 did not enter KG-RUNTIME-19.
