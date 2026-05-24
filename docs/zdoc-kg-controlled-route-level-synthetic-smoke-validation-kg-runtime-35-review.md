# KG-RUNTIME-35: ZDoc KG Controlled Route-Level Synthetic Smoke Validation

## 1. Step Identity

- Step: KG-RUNTIME-35.
- Name: ZDoc KG controlled route-level synthetic smoke validation.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `20267be8b4714f621c2a70ce7853377f6d63b4bb`.
- Start tag: `v0.1.415-zdoc-kg-adapter-no-service-smoke-frozen-audit-gate`.
- Start `git status --short`: clean.

## 2. KG-RUNTIME-34 Authorization Gate Summary

KG-RUNTIME-34 authorized only a later controlled route-level synthetic smoke validation.

The authorized KG-RUNTIME-35 scope was limited to temporarily starting the ZDoc backend service with only `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`, calling `/health`, calling `/kg/read-only-preview` with an inline synthetic disabled payload, validating route-to-adapter behavior, validating contract metadata only output, validating output field boundaries, stopping the service, releasing the port, and adding this review document.

KG-RUNTIME-34 did not authorize real KG reads, `AI知识图谱大全` reads, real knowledge package loading, registry creation, generation, export, review apply, ZBid writeback, RAG, prompt registry, system instruction registry, Ollama, model changes, code changes, JSON changes, tests, frontend changes, config changes, or entry into real KG use.

## 3. KG-RUNTIME-33 Pure-Function Smoke Summary

KG-RUNTIME-33 completed only a no-service synthetic pure-function smoke validation of `build_kg_read_only_preview`.

KG-RUNTIME-33 used inline synthetic disabled manifest and registry payloads only, did not run a service, did not access a port, did not call `/kg/read-only-preview`, did not read real KG content, and did not read `AI知识图谱大全`.

The pure-function output was contract metadata only. Its adapter output field whitelist passed, unexpected top-level keys were none, and the boundary flags were returned as `no_write=true`, `no_evidence=true`, `no_scoring=true`, `no_rag=true`, `no_generation=true`, `no_export=true`, and `no_zbid_writeback=true`.

KG-RUNTIME-33 results remain synthetic smoke records only and must not be used as evidence or scoring.

## 4. Route-Level Smoke Execution Scope

This KG-RUNTIME-35 step executed only a controlled route-level synthetic smoke validation.

The only runtime feature flag enabled for the temporary service was:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`

The service command was:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`

The only HTTP endpoints called were:

- `GET /health`
- `POST /kg/read-only-preview`

No `/generate`, `/export_docx`, or `/review/apply` endpoint was called.

## 5. Inline Synthetic Disabled Payload Boundary

The KG route request used an inline synthetic disabled payload only.

The route schema allowed only these request fields:

- `request_id`
- `manual_trigger`
- `manifest_entity`
- `registry_entity`

The payload used:

- `request_id="kg-runtime-35-route-level-synthetic-smoke"`
- `manual_trigger=true`
- `manifest_entity.entity_id="synthetic-inline-disabled-manifest"`
- `registry_entity.entity_id="synthetic-inline-disabled-registry"`
- disabled flags required by the current adapter: `enabled=false`, `runtime_loadable=false`, `evidence_allowed=false`, `scoring_allowed=false`
- `registration_status="not_registered"`

The payload did not contain a real KG path, `知识图谱/ZF-KG-12-Municipal-Bridge.json`, `AI知识图谱大全`, real business knowledge, business正文, prompt content, system instruction content, evidence content, scoring content, generation-ready content, export-ready content, or ZBid writeback content.

## 6. `/health` Validation Result

- Endpoint: `GET /health`.
- HTTP status: `200 OK`.
- Result summary: response returned `ok=true`, `service="文档生成系统"`, `system_id="docgen-system"`, repository workspace root, config version metadata, and `audit_ready=true`.
- Boundary result: health check only; no KG read, no generation, no export, no review apply, no writeback, no Ollama, no model operation.

## 7. `/kg/read-only-preview` Validation Result

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
- Route-level returned result type: `dict` JSON response containing route contract metadata plus adapter contract metadata in `detail`.

## 8. Top-Level Output Fields

The route-level response top-level fields were:

- `adapter_status`
- `affects_export`
- `affects_generation`
- `affects_zbid_writeback`
- `calls_export_docx_route`
- `calls_external_endpoint`
- `calls_generate_route`
- `calls_ollama`
- `calls_review_apply_route`
- `creates_registry`
- `default_off`
- `detail`
- `downloads_models`
- `enabled`
- `endpoint_path`
- `evidence_allowed`
- `feature_flag`
- `kg_runtime_registered`
- `knowledge_pack_load_allowed`
- `loads_knowledge_pack`
- `manual_trigger_required`
- `no_write`
- `ok`
- `output_write_allowed`
- `preview_only`
- `prompt_registry_allowed`
- `pulls_models`
- `rag_allowed`
- `read_only`
- `reason`
- `registers_manifest`
- `request_id`
- `route_name`
- `route_registered`
- `runtime_access`
- `scoring_allowed`
- `source`
- `status`
- `system_instruction_registry_allowed`
- `triggers_export_chain`
- `triggers_generation_chain`
- `writeback_allowed`
- `writes_document_body`
- `writes_export`
- `writes_job`
- `writes_output`

## 9. Output Field Whitelist Check

The route-level output matched the current route contract fields returned by `_base_response()`, plus route-added `adapter_status`, and adapter contract metadata nested under `detail`.

The nested adapter `detail` fields matched the adapter contract metadata whitelist:

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

Whitelist check result: passed.

Unexpected top-level keys: none beyond the current route contract metadata fields, `adapter_status`, and `detail` adapter contract metadata.

Any fields containing labels such as `evidence_allowed`, `scoring_allowed`, `rag_allowed`, `prompt_registry_allowed`, `system_instruction_registry_allowed`, and `knowledge_pack_load_allowed` were contract metadata flags with false values, not evidence, scoring, RAG text, prompt content, system instruction content, or knowledge content.

## 10. Forbidden Text Hits Check

Forbidden content hits: none.

The response did not contain:

- a real KG path;
- `知识图谱/ZF-KG-12-Municipal-Bridge.json`;
- `AI知识图谱大全`;
- real business正文;
- entity正文;
- knowledge-entry正文;
- prompt content;
- system instruction content;
- evidence body;
- scoring body;
- RAG text block;
- generation body;
- export payload;
- ZBid writeback payload.

Contract metadata labels and boolean guard fields were present only as boundary metadata.

## 11. Contract Metadata Only Check

Contract metadata only result: passed.

The route-level response contained route metadata, endpoint metadata, feature-flag metadata, read-only/no-write guard flags, chain-call guard flags, registry/load guard flags, and nested adapter contract metadata.

The response did not expose business content, KG entity body values, knowledge body values, prompt text, system instruction text, evidence content, scoring content, generated document正文, RAG text, export content, or ZBid writeback content.

## 12. Boundary Flag Checks

- `no_write`: passed, route returned `no_write=true`, `output_write_allowed=false`, `writes_output=false`, `writes_job=false`, `writes_export=false`, and `writes_document_body=false`.
- `no_evidence`: passed, route returned `evidence_allowed=false` and adapter detail returned `no_evidence=true`.
- `no_scoring`: passed, route returned `scoring_allowed=false` and adapter detail returned `no_scoring=true`.
- `no_rag`: passed, route returned `rag_allowed=false` and adapter detail returned `no_rag=true`.
- `no_generation`: passed, route returned `calls_generate_route=false`, `triggers_generation_chain=false`, `affects_generation=false`, and adapter detail returned `no_generation=true`.
- `no_export`: passed, route returned `calls_export_docx_route=false`, `triggers_export_chain=false`, `affects_export=false`, `writes_export=false`, and adapter detail returned `no_export=true`.
- `no_zbid_writeback`: passed, route returned `writeback_allowed=false`, `affects_zbid_writeback=false`, and adapter detail returned `no_zbid_writeback=true`.

## 13. Negative Execution Confirmation

- 本步骤是否读取真实 KG 文件正文内容：否。
- 本步骤是否解析真实 KG JSON：否。
- 本步骤是否运行 `python3 -m json.tool`：否。
- 本步骤是否读取 `AI知识图谱大全` 内容：否。
- 本步骤是否复制、移动、删除 `AI知识图谱大全`：否。
- 本步骤是否加载真实知识包：否。
- 本步骤是否创建真实 registry：否。
- 本步骤是否注册、启用或加载知识包：否。
- 本步骤是否运行服务：是，仅临时运行本地 ZDoc 后端服务。
- 本步骤是否访问端口：是，仅访问 `127.0.0.1:8000`。
- 本步骤是否调用 `/health`：是，返回 `200 OK`。
- 本步骤是否调用 `/kg/read-only-preview`：是，返回 `200 OK`。
- 本步骤是否触发 `/generate`、`/export_docx`、`/review/apply`：否。
- 本步骤是否触发 ZBid 写回：否。
- 本步骤是否写正文：否；仅新增本 KG-RUNTIME-35 review 文档，未写生成文档正文。
- 本步骤是否写 `output/job/export`：否。
- 本步骤是否运行 Ollama：否。
- 本步骤是否升级或拉取模型：否。
- 本步骤是否修改 adapter：否。
- 本步骤是否修改 route / `main.py`：否。
- 本步骤是否修改 JSON、tests、frontend、config：否。
- 本步骤是否接入 RAG / prompt registry / system instruction registry：否。
- 本步骤是否接入测试或 CI：否。

## 14. `.pyc` / `__pycache__` Confirmation

Before service startup, no route/adapter-specific bytecode file was found by:

- `find backend -name '*kg_read_only_preview*.pyc' -print`

The temporary service run generated exactly these route/adapter-related bytecode files:

- `backend/app/routers/__pycache__/kg_read_only_preview.cpython-313.pyc`
- `backend/__pycache__/kg_read_only_preview_adapter.cpython-313.pyc`

Only those two newly generated files were removed.

After cleanup, `find backend -name '*kg_read_only_preview*.pyc' -print` returned no output.

Final `.pyc` / `__pycache__` conclusion:本步骤新增 route/adapter `.pyc`，已仅清理本次新增项，最终无新增残留。

## 15. Service Stop and Port Release

- Service stopped: yes.
- Stop method: stopped the temporary uvicorn process for this smoke run.
- Server shutdown log summary: application shutdown completed and server process finished.
- Port release check: `lsof -nP -iTCP:8000 -sTCP:LISTEN` returned no output.
- `127.0.0.1:8000` listener after stop: none.

## 16. Evidence and Scoring Boundary

The route-level smoke result is not evidence.

The route-level smoke result must not be used as evidence.

The route-level smoke result is not scoring.

The route-level smoke result must not be used as scoring.

This step did not connect the smoke result to evidence, scoring, RAG, generation, export, or ZBid writeback.

## 17. Validation Results

- `git diff --check`: passed with exit code 0 for the docs-only working tree diff.
- `git diff --cached --check`: passed with exit code 0 after staging only the target KG-RUNTIME-35 review document.

## 18. Next Stage Recommendation

Any later KG-RUNTIME-36 step must be separately authorized.

KG-RUNTIME-36 must not be inferred from this KG-RUNTIME-35 smoke.

This KG-RUNTIME-35 smoke does not authorize real KG reads, `AI知识图谱大全` reads, registry creation, knowledge package loading, RAG, prompt registry, system instruction registry, evidence, scoring, generation, export, ZBid writeback, Ollama, model changes, code changes, or real KG use.

## 19. Final Boundary Conclusion

KG-RUNTIME-35 completed only a controlled route-level synthetic smoke validation.

Only this target docs file is added:

- `docs/zdoc-kg-controlled-route-level-synthetic-smoke-validation-kg-runtime-35-review.md`

No adapter, route, `main.py`, code, JSON, tests, frontend, config, `output/job/export`, `.pyc`, or `__pycache__` change remains.

The route-level response called the adapter draft and returned contract metadata only.

The inline synthetic disabled route-level smoke result must not be used as evidence or scoring.

KG-RUNTIME-35 did not enter KG-RUNTIME-36.
