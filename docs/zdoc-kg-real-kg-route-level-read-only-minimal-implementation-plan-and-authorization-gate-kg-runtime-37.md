# KG-RUNTIME-37: ZDoc KG Real-KG Route-Level Read-Only Minimal Implementation Plan and Authorization Gate

## 1. Step Identity

- Step: KG-RUNTIME-37.
- Name: ZDoc KG real-KG route-level read-only minimal implementation plan and authorization gate.
- Nature: docs-only real-KG route-level read-only minimal implementation plan and next-stage authorization gate.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `50356298f23a345e91acc0a08e7af1eff0457e2c`.
- Start tag: `v0.1.417-zdoc-kg-route-synthetic-smoke-frozen-audit-gate`.
- Start `git status --short`: clean.

## 2. KG-RUNTIME-36 Review Conclusion Summary

KG-RUNTIME-36 has been completed as a docs-only frozen audit package and real-KG route-level read-only authorization gate.

KG-RUNTIME-36 froze KG-RUNTIME-35 as a route-level synthetic smoke record only.

KG-RUNTIME-36 set the real-KG route-level read-only authorization boundary for a later step.

KG-RUNTIME-36 did not read the real KG file, did not run a service, did not call `/health`, did not call `/kg/read-only-preview`, and did not modify `backend/kg_read_only_preview_adapter.py`, `backend/app/routers/kg_read_only_preview.py`, or `backend/app/main.py`.

KG-RUNTIME-36 did not authorize real KG use, evidence production, scoring production, generation, export, ZBid writeback, RAG, prompt registry, system instruction registry, Ollama, model changes, registry creation, or knowledge package loading.

## 3. KG-RUNTIME-35 Route-Level Synthetic Smoke Summary

KG-RUNTIME-35 completed only a controlled route-level synthetic smoke validation.

The temporary route-level smoke enabled only:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`

The only endpoints called during KG-RUNTIME-35 were:

- `GET /health`
- `POST /kg/read-only-preview`

The `/health` result was:

- HTTP status: `200 OK`.
- `ok`: `true`.
- `service`: `文档生成系统`.
- `audit_ready`: `true`.

The `/kg/read-only-preview` result was:

- HTTP status: `200 OK`.
- `ok`: `true`.
- `enabled`: `true`.
- `status`: `preview_only`.
- `reason`: `adapter_preview_ready`.

The route-level smoke called the adapter draft.

The adapter call was reflected by:

- `detail.status="preview_only"`.
- `adapter_status="preview_only"`.

The KG-RUNTIME-35 route-level response was contract metadata only.

The output field whitelist check passed.

The response did not output business正文, entity正文, knowledge正文, prompt content, system instruction content, evidence content, scoring content, generation-ready text, RAG-ready text, export content, or ZBid writeback content.

The KG-RUNTIME-35 checks passed for:

- no-write.
- no-evidence.
- no-scoring.
- no-RAG.
- no-generation.
- no-export.
- no-ZBid-writeback.

KG-RUNTIME-35 stopped the temporary service and released the port.

KG-RUNTIME-35 generated exactly two route/adapter-related `.pyc` files during the temporary service run, removed only those newly generated files, and ended with no route/adapter `.pyc` residue.

KG-RUNTIME-35 did not read real KG content, did not read `AI知识图谱大全`, did not load a real knowledge package, did not create a registry, did not run Ollama, did not upgrade or pull models, and did not modify adapter, route, or `backend/app/main.py`.

## 4. KG-RUNTIME-34 Authorization Gate Summary

KG-RUNTIME-34 authorized KG-RUNTIME-35 only as a controlled route-level synthetic smoke validation.

The authorized KG-RUNTIME-35 boundary was limited to temporarily starting the service, enabling only the KG read-only preview route feature flag, calling `/health`, calling `/kg/read-only-preview` with an inline synthetic disabled payload, validating route-to-adapter behavior, validating contract metadata only output, validating output field whitelist behavior, validating no-write / no-evidence / no-scoring / no-RAG / no-generation / no-export / no-ZBid-writeback, stopping the service, and releasing the port.

KG-RUNTIME-34 did not authorize real KG reads, `AI知识图谱大全` reads, real knowledge package loading, registry creation, generation, export, review apply, ZBid writeback, RAG, prompt registry, system instruction registry, Ollama, model changes, code changes, JSON changes, tests, frontend changes, config changes, or entry into real KG use.

## 5. Current Route-Level Verified Scope

The current verified route-level scope is synthetic only.

The verified route-level behavior covers only:

- feature-flag controlled route access.
- manual-trigger request boundary.
- inline synthetic disabled payload handling.
- route-to-adapter call.
- route-level response with `adapter_status`.
- nested adapter contract metadata in `detail`.
- contract metadata only response.
- output field whitelist behavior.
- no-write / no-evidence / no-scoring boundary flags.
- no-RAG / no-generation / no-export / no-ZBid-writeback boundary flags.

No verified route-level behavior currently covers a real KG file.

## 6. Current Real-KG Route-Level Unverified Scope

Real-KG route-level read-only behavior remains unverified.

The system has not validated route-level read-only behavior against:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

The system has not validated:

- real KG file read boundaries.
- real KG body-value suppression.
- real entity body suppression.
- real knowledge-entry body suppression.
- real prompt content suppression.
- real system instruction content suppression.
- real evidence suppression.
- real scoring suppression.
- real route contract metadata only behavior against the real target.
- real registry creation behavior, because registry creation remains unauthorized.
- real knowledge package loading behavior, because loading remains unauthorized.

## 7. Current Unique Real KG Authorization Candidate

The only real KG target candidate for a later separately authorized step is:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

No later step may expand this target to `AI知识图谱大全`.

No later step may automatically scan other knowledge packages.

No later step may infer permission to read, register, enable, load, copy, move, delete, or transform any other knowledge package.

## 8. Current Adapter Draft State

The current adapter draft remains isolated in:

- `backend/kg_read_only_preview_adapter.py`

The adapter entry remains:

- `build_kg_read_only_preview`

Static review in this KG-RUNTIME-37 step confirms the adapter remains a minimal draft adapter with pure functions only.

The adapter output remains limited by:

- `OUTPUT_FIELD_WHITELIST`

The adapter output policy remains:

- `contract_metadata_only_no_entity_knowledge_prompt_instruction_evidence_scoring_generation_or_rag_text`

The adapter draft remains read-only, no-write, no-evidence, no-scoring, no-RAG, no-generation, no-export, and no-ZBid-writeback.

This KG-RUNTIME-37 step did not modify the adapter.

This KG-RUNTIME-37 step did not run the adapter.

## 9. Current Route Status

The current route draft remains in:

- `backend/app/routers/kg_read_only_preview.py`

The route path remains:

- `/kg/read-only-preview`

The route feature flag remains:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED`

The route remains default-off through the feature flag.

The route still requires manual trigger before adapter delegation.

The route still allows only these request fields:

- `manifest_entity`
- `registry_entity`
- `manual_trigger`
- `request_id`

The route still returns route contract metadata and, when valid, nested adapter contract metadata in `detail`.

The route metadata still marks generation, export, review apply, ZBid writeback, RAG, prompt registry, system instruction registry, knowledge package loading, registry creation, Ollama, external endpoint calls, and model downloads/pulls as disallowed.

This KG-RUNTIME-37 step did not modify the route.

This KG-RUNTIME-37 step did not modify `backend/app/main.py`.

## 10. Why Real Use Is Still Not Allowed

The system still cannot enter real KG use because the current route-level validation is synthetic only.

KG-RUNTIME-35 proved only that the route can call the adapter draft with an inline synthetic disabled payload and return contract metadata only.

KG-RUNTIME-35 did not prove that a real KG file can be safely read at route level.

KG-RUNTIME-35 did not prove that real KG body values are suppressed at route level.

KG-RUNTIME-35 did not prove that real KG output remains contract metadata only at route level.

KG-RUNTIME-35 did not authorize real registry creation, knowledge package loading, RAG, prompt registry, system instruction registry, evidence production, scoring production, generation, export, or ZBid writeback.

KG-RUNTIME-36 froze these limits and set an authorization gate only; it did not implement real-KG route-level reads.

Therefore the system must not enter real KG use.

## 11. Why Current Results Cannot Be Evidence or Scoring

KG-RUNTIME-35 used only an inline synthetic disabled payload.

KG-RUNTIME-35 did not read real KG content.

KG-RUNTIME-35 did not validate a source claim, business fact, entity assertion, knowledge-entry assertion, citation rule, extraction rule, or human approval boundary for evidence production.

KG-RUNTIME-35 did not validate a scoring rubric, scoring input contract, score interpretation rule, threshold policy, extraction rule, or human approval boundary for scoring production.

KG-RUNTIME-36 only froze KG-RUNTIME-35 as a route-level synthetic smoke record and authorization boundary.

Therefore KG-RUNTIME-35 and KG-RUNTIME-36 results must not be used as evidence.

Therefore KG-RUNTIME-35 and KG-RUNTIME-36 results must not be used as scoring.

## 12. Real-KG Route-Level Read-Only Minimal Implementation Goal

If a later step is separately authorized, the minimal real-KG route-level read-only implementation goal may only be to define and gate a safe route-level path that can prove contract metadata only behavior against the single real KG target without entering real use.

The minimum goal must remain:

- feature-flag controlled.
- manual-trigger.
- read-only.
- contract metadata only.
- no-write.
- no-evidence.
- no-scoring.
- no-RAG.
- no-generation.
- no-export.
- no-ZBid-writeback.
- no-Ollama.
- no-model-upgrade.

The minimum goal must not include business正文 generation, document正文 generation, evidence production, scoring production, registry enablement, knowledge package runtime loading, prompt registry integration, system instruction registry integration, RAG integration, export, review apply, ZBid writeback, Ollama, or model operations.

## 13. Real-KG Route-Level Read-Only Allowed Boundary

If later separately authorized, the only real KG target may be:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

The later boundary must remain:

- feature-flag controlled.
- manual-trigger.
- read-only.
- contract metadata only.
- no-write.
- no-evidence.
- no-scoring.
- no-RAG.
- no-generation.
- no-export.
- no-ZBid-writeback.
- no-Ollama.
- no-model-upgrade.

Any later implementation must remain default-off.

Any later implementation must fail blocked if the feature flag is absent or disabled.

Any later implementation must fail blocked if manual trigger is absent.

Any later implementation must fail blocked if the requested target is not the single authorized real KG target.

Any later implementation must fail blocked rather than fallback into generation, export, RAG, evidence, scoring, registry loading, knowledge package loading, or real use.

## 14. Real-KG Route-Level Read-Only Forbidden Boundary

Any later real-KG route-level read-only step must not output:

- real business正文 values.
- entity正文.
- knowledge正文.
- prompt content.
- system instruction content.
- evidence content.
- scoring content.
- text directly usable by `/generate`.
- text blocks directly usable by RAG.

Any later real-KG route-level read-only step must not:

- directly enter real use.
- trigger `/generate`.
- trigger `/export_docx`.
- trigger `/review/apply`.
- trigger ZBid writeback.
- write document正文.
- write `output/job/export`.
- run Ollama.
- upgrade, pull, delete, replace, or configure models.
- connect RAG.
- connect prompt registry.
- connect system instruction registry.
- modify frontend.
- modify tests.
- modify config.
- register, enable, or load a knowledge package unless separately authorized by a later step.
- create a real registry unless separately authorized by a later step.
- expand beyond `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- read or scan `AI知识图谱大全`.
- treat any smoke result as evidence.
- treat any smoke result as scoring.

## 15. Feature-Flag Controlled Design Requirement

Any later real-KG route-level read-only design must remain default-off.

The route must require an explicit feature flag before any real KG route-level read-only path can be considered.

If the flag is disabled or absent, the route must return a blocked or disabled contract metadata response only.

The disabled response must not read a real KG file.

The disabled response must not load a knowledge package.

The disabled response must not create or consult a real registry.

## 16. Manual-Trigger Design Requirement

Any later real-KG route-level read-only design must require `manual_trigger=true`.

If manual trigger is absent or false, the route must return blocked contract metadata only.

The blocked response must not read a real KG file.

The blocked response must not load a knowledge package.

The blocked response must not create or consult a real registry.

Manual trigger must not be inferred from environment state, service startup, branch state, tag state, or prior smoke success.

## 17. Contract Metadata Only Design Requirement

Any later real-KG route-level read-only design must return only contract metadata.

Allowed output may describe only:

- route status.
- adapter status.
- feature flag status.
- manual trigger status.
- authorized target identity as metadata.
- read-only status.
- output policy status.
- whitelist/count/status summaries that do not expose real business values.
- no-write / no-evidence / no-scoring flags.
- no-RAG / no-generation / no-export / no-ZBid-writeback flags.
- no-Ollama / no-model-upgrade flags.

The response must not expose real KG body values, entity body values, knowledge-entry body values, prompt text, system instruction text, evidence text, scoring text, generation-ready正文, RAG-ready text blocks, export content, or ZBid writeback content.

## 18. No-Write, No-Evidence, and No-Scoring Design Requirement

Any later real-KG route-level read-only design must preserve:

- no-write.
- no-evidence.
- no-scoring.

The route must not write to `output`, `job`, `export`, document正文, caches, generated registries, generated prompts, generated instructions, evidence stores, scoring stores, or ZBid writeback targets.

The route must not create evidence records.

The route must not create scoring records.

The route must not allow KG-RUNTIME-35, KG-RUNTIME-36, or later real-KG read-only smoke results to be promoted into evidence or scoring.

## 19. No-RAG, No-Generation, No-Export, and No-ZBid-Writeback Design Requirement

Any later real-KG route-level read-only design must preserve:

- no-RAG.
- no-generation.
- no-export.
- no-ZBid-writeback.

The route must not connect to RAG.

The route must not trigger `/generate`.

The route must not trigger `/export_docx`.

The route must not trigger `/review/apply`.

The route must not trigger ZBid writeback.

The route must not return text that can be directly passed into generation, export, RAG, or writeback chains.

## 20. No-Ollama and No-Model-Upgrade Design Requirement

Any later real-KG route-level read-only design must preserve:

- no-Ollama.
- no-model-upgrade.

The route must not call Ollama.

The route must not start Ollama.

The route must not upgrade, pull, delete, replace, or configure any model.

The route must not use model availability as fallback behavior.

## 21. KG-RUNTIME-38 Authorization Recommendation

KG-RUNTIME-38, if continued later, should only be one of the following docs-only authorization steps:

- docs-only real-KG route-level read-only implementation authorization gate.
- adapter/route minimal implementation plan authorization gate.

KG-RUNTIME-38 must not directly modify code unless a later separate user authorization explicitly changes the scope.

KG-RUNTIME-38 must not directly enter real KG use.

If a later code implementation phase is separately authorized after KG-RUNTIME-38, it must not exceed the following boundary:

- must not directly enter real use.
- must not trigger `/generate`.
- must not trigger `/export_docx`.
- must not trigger `/review/apply`.
- must not trigger ZBid writeback.
- must not write document正文.
- must not write `output/job/export`.
- must not run Ollama.
- must not upgrade models.
- must not connect RAG.
- must not connect prompt registry.
- must not connect system instruction registry.
- must not modify frontend.
- must not modify tests.
- must not modify config.
- must preserve default-off / feature-flag controlled behavior.
- must preserve manual-trigger behavior.
- must preserve contract metadata only output.
- must fail blocked and must not fallback to any real-use chain.

## 22. KG-RUNTIME-37 Negative Execution Confirmation

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
- KG-RUNTIME-35 / KG-RUNTIME-36 结果不得作为 evidence。
- KG-RUNTIME-35 / KG-RUNTIME-36 结果不得作为 scoring。

## 23. Validation Results

- `git diff --check`: passed with exit code 0 for the docs-only working tree diff.
- `git diff --cached --check`: passed with exit code 0 before staging and passed with exit code 0 after staging only the target KG-RUNTIME-37 docs file.

## 24. Final Boundary Conclusion

KG-RUNTIME-37 is complete as a docs-only real-KG route-level read-only minimal implementation plan and authorization gate.

Only this target docs file is added:

- `docs/zdoc-kg-real-kg-route-level-read-only-minimal-implementation-plan-and-authorization-gate-kg-runtime-37.md`

No adapter, route, `backend/app/main.py`, code, JSON, tests, frontend, config, `output/job/export`, `.pyc`, or `__pycache__` change is introduced.

KG-RUNTIME-35 and KG-RUNTIME-36 results are frozen only as non-evidence and non-scoring route-level authorization records.

KG-RUNTIME-38 may only proceed after separate explicit authorization and should remain docs-only authorization planning unless later separately expanded.

KG-RUNTIME-38 is not entered.
