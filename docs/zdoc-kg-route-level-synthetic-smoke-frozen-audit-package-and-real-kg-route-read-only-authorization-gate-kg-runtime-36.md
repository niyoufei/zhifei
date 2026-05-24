# KG-RUNTIME-36: ZDoc KG Route-Level Synthetic Smoke Frozen Audit Package and Real-KG Route-Level Read-Only Authorization Gate

## 1. Step Identity

- Step: KG-RUNTIME-36.
- Name: ZDoc KG route-level synthetic smoke frozen audit package and real-KG route-level read-only authorization gate.
- Nature: docs-only frozen audit and next-stage authorization gate.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `e722f783ac6606eb947a28046003decb6b537088`.
- Start tag: `v0.1.416-zdoc-kg-route-level-synthetic-smoke-validation`.
- Start `git status --short`: clean.

## 2. KG-RUNTIME-35 Review Conclusion Summary

KG-RUNTIME-35 has been completed.

KG-RUNTIME-35 completed only a controlled route-level synthetic smoke validation.

KG-RUNTIME-35 temporarily enabled only:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`

KG-RUNTIME-35 called only:

- `GET /health`
- `POST /kg/read-only-preview`

KG-RUNTIME-35 used only an inline synthetic disabled payload.

KG-RUNTIME-35 did not read a real KG file, did not read `AI知识图谱大全`, did not load a real knowledge package, did not create a real registry, did not run Ollama, did not upgrade or pull models, did not modify adapter code, did not modify route code, and did not modify `backend/app/main.py`.

KG-RUNTIME-35 results are frozen only as route-level synthetic smoke records.

KG-RUNTIME-35 results must not be used as evidence.

KG-RUNTIME-35 results must not be used as scoring.

## 3. KG-RUNTIME-34 Authorization Gate Summary

KG-RUNTIME-34 authorized KG-RUNTIME-35 only as a later controlled route-level synthetic smoke validation.

The KG-RUNTIME-34 authorization boundary was limited to temporarily starting the service, enabling only the KG read-only preview route feature flag, calling `/health`, calling `/kg/read-only-preview` with an inline synthetic disabled payload, validating route-to-adapter behavior, validating contract metadata only output, validating output field whitelist behavior, validating no-write / no-evidence / no-scoring / no-RAG / no-generation / no-export / no-ZBid-writeback, stopping the service, and releasing the port.

KG-RUNTIME-34 did not authorize real KG reads, `AI知识图谱大全` reads, real knowledge package loading, registry creation, generation, export, review apply, ZBid writeback, RAG, prompt registry, system instruction registry, Ollama, model changes, code changes, JSON changes, tests, frontend changes, config changes, or entry into real KG use.

## 4. KG-RUNTIME-33 Pure-Function Smoke Summary

KG-RUNTIME-33 completed only a no-service synthetic pure-function smoke validation of the existing adapter contract mapping draft.

KG-RUNTIME-33 called only the adapter pure-function entry:

- `build_kg_read_only_preview`

KG-RUNTIME-33 used only inline synthetic disabled manifest and registry dictionaries.

KG-RUNTIME-33 did not run a service, did not access a port, did not call `/kg/read-only-preview`, did not read real KG content, and did not read `AI知识图谱大全`.

KG-RUNTIME-33 returned contract metadata only.

KG-RUNTIME-33 output field whitelist check passed.

KG-RUNTIME-33 unexpected top-level keys were none.

KG-RUNTIME-33 validated:

- `no_write=true`
- `no_evidence=true`
- `no_scoring=true`
- `no_rag=true`
- `no_generation=true`
- `no_export=true`
- `no_zbid_writeback=true`

KG-RUNTIME-33 results remain synthetic smoke records only and must not be used as evidence or scoring.

## 5. KG-RUNTIME-35 Route-Level Synthetic Smoke Result Frozen Record

The KG-RUNTIME-35 route-level synthetic smoke result is frozen as follows:

- KG-RUNTIME-35 completed: yes.
- Route-level smoke type: controlled route-level synthetic smoke validation.
- Request payload type: inline synthetic disabled payload only.
- Route-level adapter draft call: passed.
- Adapter called by route: yes.
- `detail.status`: `preview_only`.
- `adapter_status`: `preview_only`.
- Contract metadata only: passed.
- Output field whitelist: passed.
- Unexpected top-level keys: none beyond the current route contract metadata fields, `adapter_status`, and `detail` adapter contract metadata.
- Business正文 output: none.
- Entity output: none.
- Knowledge output: none.
- Prompt output: none.
- System instruction output: none.
- Evidence output: none.
- Scoring output: none.
- Real KG read: no.
- `AI知识图谱大全` read: no.
- Real KG use: not entered.

## 6. `/health` Result Frozen Record

The KG-RUNTIME-35 `/health` result is frozen as follows:

- Endpoint: `GET /health`.
- HTTP status: `200 OK`.
- `ok`: `true`.
- `service`: `文档生成系统`.
- `audit_ready`: `true`.
- Boundary: health check only.
- Real KG read: no.
- Generation: no.
- Export: no.
- Review apply: no.
- ZBid writeback: no.
- Ollama: no.
- Model operation: no.

This KG-RUNTIME-36 step did not call `/health`; it only freezes the KG-RUNTIME-35 recorded result.

## 7. `/kg/read-only-preview` Result Frozen Record

The KG-RUNTIME-35 `/kg/read-only-preview` result is frozen as follows:

- Endpoint: `POST /kg/read-only-preview`.
- HTTP status: `200 OK`.
- `ok`: `true`.
- `enabled`: `true`.
- `status`: `preview_only`.
- `reason`: `adapter_preview_ready`.
- Request boundary: inline synthetic disabled payload only.
- Adapter called: yes.
- Adapter call proof: route response contained `detail.status="preview_only"` and `adapter_status="preview_only"`.
- Adapter detail reason: `adapter_contract_mapping_draft_static_only`.
- Returned result type: route contract metadata plus adapter contract metadata nested under `detail`.

This KG-RUNTIME-36 step did not call `/kg/read-only-preview`; it only freezes the KG-RUNTIME-35 recorded result.

## 8. Route-Level Adapter Draft Call Frozen Record

The route-level smoke called the adapter draft through the route.

The adapter draft entry remains:

- `build_kg_read_only_preview`

The route-level response confirmed the adapter result through:

- `detail.status="preview_only"`
- `adapter_status="preview_only"`

The route-level reason was:

- `reason="adapter_preview_ready"`

The adapter detail reason was:

- `reason="adapter_contract_mapping_draft_static_only"`

## 9. Contract Metadata Only Result

Contract metadata only result: passed.

The route-level response contained only route contract metadata, endpoint metadata, feature-flag metadata, read-only/no-write guard flags, chain-call guard flags, registry/load guard flags, `adapter_status`, and nested adapter contract metadata in `detail`.

The route-level response did not expose:

- business正文;
- KG entity body values;
- knowledge body values;
- prompt text;
- system instruction text;
- evidence content;
- scoring content;
- generated document正文;
- RAG text;
- export content;
- ZBid writeback content.

## 10. Output Field Whitelist Check Result

Output field whitelist check result: passed.

The route-level response top-level fields were limited to current route contract metadata fields returned by `_base_response()`, plus route-added `adapter_status`, plus nested adapter contract metadata under `detail`.

The nested adapter `detail` fields were limited to:

- `ok`
- `enabled`
- `status`
- `reason`
- `source`
- `contract_scope`
- `module_contract_count`
- `adapter_structural_path_whitelist_count`
- `allowed_path_count`
- `blocked_path_count`
- `value_output_policy`
- `no_write`
- `no_evidence`
- `no_scoring`
- `no_rag`
- `no_generation`
- `no_export`
- `no_zbid_writeback`

Unexpected top-level keys: none beyond route contract metadata fields, `adapter_status`, and `detail` adapter contract metadata.

Contract labels such as `evidence_allowed`, `scoring_allowed`, `rag_allowed`, `prompt_registry_allowed`, `system_instruction_registry_allowed`, and `knowledge_pack_load_allowed` were metadata flags with false values, not evidence, scoring, RAG text, prompt content, system instruction content, or knowledge content.

## 11. Forbidden Output Check Result

Forbidden output check result: passed.

The KG-RUNTIME-35 route-level synthetic smoke response did not output:

- business正文;
- entity正文;
- entity;
- knowledge-entry正文;
- knowledge;
- prompt content;
- prompt;
- system instruction content;
- system instruction;
- evidence body;
- evidence;
- scoring body;
- scoring;
- RAG text;
- generation body;
- export payload;
- ZBid writeback payload;
- real KG path body content;
- `AI知识图谱大全` content.

Contract metadata labels and boolean guard fields were present only as boundary metadata.

## 12. No-Write, No-Evidence, and No-Scoring Result

The KG-RUNTIME-35 route-level synthetic smoke checks are frozen as passed:

- `no_write`: passed.
- `no_evidence`: passed.
- `no_scoring`: passed.

The route returned `no_write=true`, `output_write_allowed=false`, `writes_output=false`, `writes_job=false`, `writes_export=false`, and `writes_document_body=false`.

The route returned `evidence_allowed=false`, and adapter detail returned `no_evidence=true`.

The route returned `scoring_allowed=false`, and adapter detail returned `no_scoring=true`.

KG-RUNTIME-35 route-level smoke result must not be used as evidence.

KG-RUNTIME-35 route-level smoke result must not be used as scoring.

## 13. No-RAG, No-Generation, No-Export, and No-ZBid-Writeback Result

The KG-RUNTIME-35 route-level synthetic smoke checks are frozen as passed:

- `no_rag`: passed.
- `no_generation`: passed.
- `no_export`: passed.
- `no_zbid_writeback`: passed.

The route returned `rag_allowed=false`, and adapter detail returned `no_rag=true`.

The route returned `calls_generate_route=false`, `triggers_generation_chain=false`, `affects_generation=false`, and adapter detail returned `no_generation=true`.

The route returned `calls_export_docx_route=false`, `triggers_export_chain=false`, `affects_export=false`, `writes_export=false`, and adapter detail returned `no_export=true`.

The route returned `writeback_allowed=false`, `affects_zbid_writeback=false`, and adapter detail returned `no_zbid_writeback=true`.

## 14. KG-RUNTIME-35 Negative Runtime Closure Frozen Record

KG-RUNTIME-35 frozen closure:

- Adapter modified: no.
- Route / `backend/app/main.py` modified: no.
- Real KG read: no.
- `AI知识图谱大全` read: no.
- Ollama run: no.
- Model upgraded or pulled: no.
- Service stopped: yes.
- Port released: yes.
- Route/adapter `.pyc` generated during KG-RUNTIME-35: exactly two route/adapter-related `.pyc` files.
- Route/adapter `.pyc` cleanup: only those two newly generated files were removed.
- Final route/adapter `.pyc` residue: none.

## 15. Current Adapter Draft State

The current adapter draft remains isolated in:

- `backend/kg_read_only_preview_adapter.py`

Static review in this KG-RUNTIME-36 step confirmed that the adapter remains a minimal draft adapter with pure functions only.

The adapter entry remains:

- `build_kg_read_only_preview`

The adapter still returns contract metadata through the adapter whitelist:

- `OUTPUT_FIELD_WHITELIST`

The adapter output policy remains:

- `contract_metadata_only_no_entity_knowledge_prompt_instruction_evidence_scoring_generation_or_rag_text`

The adapter draft remains read-only, no-write, no-evidence, no-scoring, no-RAG, no-generation, no-export, and no-ZBid-writeback.

This KG-RUNTIME-36 step did not modify the adapter.

This KG-RUNTIME-36 step did not run the adapter.

## 16. Current Route-Level Verified Scope

The current route draft remains in:

- `backend/app/routers/kg_read_only_preview.py`

The route-level behavior validated by KG-RUNTIME-35 is limited to:

- feature-flag controlled route access;
- manual-trigger request boundary;
- inline synthetic disabled payload handling;
- route-to-adapter call;
- route-level response with `adapter_status`;
- nested adapter contract metadata in `detail`;
- contract metadata only response;
- output field whitelist behavior;
- no-write / no-evidence / no-scoring boundary flags;
- no-RAG / no-generation / no-export / no-ZBid-writeback boundary flags.

This KG-RUNTIME-36 step only statically viewed the route for audit packaging.

This KG-RUNTIME-36 step did not modify the route.

This KG-RUNTIME-36 step did not modify `backend/app/main.py`.

## 17. Current Real-KG Route-Level Unverified Scope

Real KG route-level read-only behavior remains unverified.

The current record has not validated route-level read-only behavior against the real KG target:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

The current record has not validated:

- real KG file read boundaries;
- real KG body-value suppression;
- real entity body suppression;
- real knowledge-entry body suppression;
- real prompt content suppression;
- real system instruction content suppression;
- real evidence suppression;
- real scoring suppression;
- real route contract metadata only behavior against the real target;
- real registry creation behavior, because registry creation is still not allowed;
- real knowledge package loading behavior, because loading remains not allowed.

This KG-RUNTIME-36 step did not read, open, or parse the real KG file body content.

## 18. Why Real Use Is Still Not Allowed

The system still cannot enter real KG use because the validated path is synthetic only.

KG-RUNTIME-35 proved only that the route can call the adapter draft with an inline synthetic disabled payload and return contract metadata only.

KG-RUNTIME-35 did not prove that a real KG file can be safely read at route level.

KG-RUNTIME-35 did not prove that real KG body values are suppressed at route level.

KG-RUNTIME-35 did not prove that real KG output remains contract metadata only at route level.

KG-RUNTIME-35 did not authorize real registry creation, knowledge package loading, RAG, prompt registry, system instruction registry, evidence production, scoring production, generation, export, or ZBid writeback.

Therefore current validation is insufficient for real KG use.

## 19. Why Current Results Cannot Be Evidence or Scoring

KG-RUNTIME-35 used only an inline synthetic disabled payload.

KG-RUNTIME-35 did not read real KG content.

KG-RUNTIME-35 did not validate a source claim, business fact, entity assertion, knowledge-entry assertion, citation rule, extraction rule, or human approval boundary for evidence production.

KG-RUNTIME-35 did not validate a scoring rubric, scoring input contract, score interpretation rule, threshold policy, extraction rule, or human approval boundary for scoring production.

Therefore KG-RUNTIME-35 route-level smoke results cannot be used as evidence.

Therefore KG-RUNTIME-35 route-level smoke results cannot be used as scoring.

## 20. KG-RUNTIME-37 Authorization Conditions

KG-RUNTIME-37, if separately authorized, may only be a real-KG route-level read-only authorization gate or a minimal real KG route-level read-only smoke authorization gate.

KG-RUNTIME-37 must not be inferred from this KG-RUNTIME-36 document.

KG-RUNTIME-37 requires a separate explicit user authorization.

KG-RUNTIME-37 must not directly enter real use.

KG-RUNTIME-37 must begin from an authorization gate or the smallest separately authorized real KG route-level read-only smoke.

## 21. KG-RUNTIME-37 Allowed Boundary

If separately authorized, KG-RUNTIME-37 may only define or validate a real-KG route-level read-only boundary.

The only authorized real KG target may be:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

Real KG access, if authorized, must remain:

- feature-flag controlled;
- manual-trigger;
- read-only;
- contract metadata only;
- no-write;
- no-evidence;
- no-scoring;
- no-RAG;
- no-generation;
- no-export;
- no-ZBid-writeback;
- no-Ollama;
- no-model-upgrade.

If a service run is separately authorized, it must be temporary, limited to the necessary route-level smoke, stopped immediately after validation, and followed by port-release confirmation.

The smoke result must not be used as evidence.

The smoke result must not be used as scoring.

## 22. KG-RUNTIME-37 Forbidden Boundary

If separately authorized, KG-RUNTIME-37 must not:

- directly enter real use;
- trigger `/generate`;
- trigger `/export_docx`;
- trigger `/review/apply`;
- trigger ZBid writeback;
- write document正文;
- write `output/job/export`;
- run Ollama;
- upgrade or pull models;
- connect RAG;
- connect prompt registry;
- connect system instruction registry;
- use any real KG target other than `知识图谱/ZF-KG-12-Municipal-Bridge.json`;
- output business正文 values;
- output entity body values;
- output knowledge body values;
- output prompt content;
- output system instruction content;
- output evidence;
- output scoring;
- return anything beyond contract metadata only;
- create a real registry unless separately authorized by a later step;
- register, enable, or load a knowledge package unless separately authorized by a later step;
- treat smoke results as evidence;
- treat smoke results as scoring.

## 23. KG-RUNTIME-36 Negative Execution Confirmation

- 本步骤未修改 adapter。
- 本步骤未修改 route / `backend/app/main.py`。
- 本步骤未读取真实 KG 文件正文内容。
- 本步骤未打开 `知识图谱/ZF-KG-12-Municipal-Bridge.json` 内容。
- 本步骤未解析真实 KG JSON。
- 本步骤未运行 `python3 -m json.tool`。
- 本步骤未读取 `AI知识图谱大全` 内容。
- 本步骤未复制、移动、删除 `AI知识图谱大全`。
- 本步骤未加载真实知识包。
- 本步骤未创建真实 registry。
- 本步骤未注册、启用或加载知识包。
- 本步骤未运行服务。
- 本步骤未访问端口。
- 本步骤未调用 `/health`。
- 本步骤未调用 `/kg/read-only-preview`。
- 本步骤未触发 `/generate`、`/export_docx`、`/review/apply`。
- 本步骤未触发 ZBid 写回。
- 本步骤未写正文。
- 本步骤未写 `output/job/export`。
- 本步骤未生成 DOCX。
- 本步骤未运行 Ollama。
- 本步骤未升级或拉取模型。
- 本步骤未修改 JSON、tests、frontend、config。
- 本步骤未接入 RAG / prompt registry / system instruction registry。
- 本步骤未接入测试或 CI。
- 本步骤未新增 `.pyc` / `__pycache__`。
- KG-RUNTIME-35 route-level smoke 结果不得作为 evidence。
- KG-RUNTIME-35 route-level smoke 结果不得作为 scoring。

## 24. Validation Results

- `git diff --check`: passed with exit code 0 for the docs-only working tree diff.
- `git diff --cached --check`: passed with exit code 0 before staging and passed with exit code 0 after staging only the target KG-RUNTIME-36 docs file.

## 25. Final Boundary Conclusion

KG-RUNTIME-36 is complete as a docs-only frozen audit package and real-KG route-level read-only authorization gate.

Only this target docs file is added:

- `docs/zdoc-kg-route-level-synthetic-smoke-frozen-audit-package-and-real-kg-route-read-only-authorization-gate-kg-runtime-36.md`

No adapter, route, `backend/app/main.py`, code, JSON, tests, frontend, config, `output/job/export`, `.pyc`, or `__pycache__` change is introduced.

KG-RUNTIME-35 route-level synthetic smoke results are frozen only as non-evidence and non-scoring records.

KG-RUNTIME-37 is not entered.
