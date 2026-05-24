# KG-RUNTIME-39: ZDoc KG Real-KG Route-Level Read-Only Controlled Implementation Draft Review

## 1. Step Identity

- Step: KG-RUNTIME-39.
- Name: ZDoc KG real-KG route-level read-only controlled implementation draft.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `0034d61fe421744a0c543db9a552285174d5adf5`.
- Start tag: `v0.1.419-zdoc-kg-real-route-controlled-implementation-gate`.
- Start `git status --short`: clean.

## 2. Authorization And Prior Gates

KG-RUNTIME-38 authorization gate summary:

- KG-RUNTIME-39 may only be a minimal adapter / route controlled implementation draft.
- The implementation must remain feature-flag controlled, manual-trigger, read-only, and contract metadata only.
- The only authorized target identifier is `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- The target may be written only as allowlist metadata / target identifier.
- The implementation must not read the real KG file, parse real KG JSON, scan `AI知识图谱大全`, create registry, load knowledge packages, run services, call endpoints, generate, export, score, produce evidence, or write back to ZBid.

KG-RUNTIME-37 minimal implementation plan summary:

- Real-KG route-level read-only behavior remained unverified before this step.
- Any later implementation must fail blocked / disabled / preview-only when a gate is not satisfied.
- Any later implementation must not fallback to real use, generation, export, RAG, evidence, scoring, registry loading, knowledge package loading, or ZBid writeback.

KG-RUNTIME-36 frozen audit summary:

- KG-RUNTIME-35 was frozen only as a route-level synthetic smoke record.
- KG-RUNTIME-36 did not read, open, or parse the real KG file body content.
- KG-RUNTIME-35 / KG-RUNTIME-36 route-level smoke results remain non-evidence and non-scoring records only.

## 3. Changed Files

Actual modified files:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`

Actual added file:

- `docs/zdoc-kg-real-kg-route-level-read-only-controlled-implementation-draft-kg-runtime-39-review.md`

No other file is intentionally modified.

## 4. Adapter Implementation Scope

`backend/kg_read_only_preview_adapter.py` adds only a metadata-only real-KG route-level read-only branch.

The adapter now declares the single authorized target identifier:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

The adapter exposes this target only as contract metadata. It does not perform file IO, directory scanning, JSON parsing, service calls, model calls, retrieval, registry access, knowledge package loading, writeback, evidence production, scoring production, generation, export, or ZBid writeback.

The existing synthetic disabled manifest / registry payload path remains compatible through the same `build_kg_read_only_preview` entry.

## 5. Route Implementation Scope

`backend/app/routers/kg_read_only_preview.py` adds only controlled request metadata for the real-KG read-only draft:

- `real_kg_read_only`
- `authorized_target`

The route remains:

- feature-flag controlled by `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED`;
- manual-trigger controlled by `manual_trigger=true`;
- read-only;
- contract metadata only.

The route passes the real-KG request only as metadata-only intent into the adapter. It does not read the real KG file, parse real KG JSON, read `AI知识图谱大全`, call generation, export, review apply, RAG, prompt registry, system instruction registry, Ollama, or ZBid writeback.

## 6. Contract Metadata Only Boundary

The real-KG controlled branch may return only contract metadata, including:

- `ok`
- `enabled`
- `status`
- `reason`
- `source`
- `adapter_status`
- `contract_scope`
- `authorized_target`
- `target_policy`
- `read_policy`
- `value_output_policy`
- `content_read_performed`
- `json_parse_performed`
- `no_write`
- `no_evidence`
- `no_scoring`
- `no_rag`
- `no_generation`
- `no_export`
- `no_zbid_writeback`

The value output policy remains contract metadata only. The branch must not output business正文, entity content, knowledge content, prompt content, system instruction content, evidence content, scoring content, generation-ready content, RAG-ready content, export content, or ZBid writeback content.

## 7. Negative Execution Confirmation

- 是否读取真实 KG 文件正文内容：否。
- 是否打开 `知识图谱/ZF-KG-12-Municipal-Bridge.json` 内容：否。
- 是否解析真实 KG JSON：否。
- 是否运行 `python3 -m json.tool`：否。
- 是否读取 `AI知识图谱大全` 内容：否。
- 是否复制、移动、删除 `AI知识图谱大全`：否。
- 是否加载真实知识包：否。
- 是否创建真实 registry：否。
- 是否注册、启用或加载知识包：否。
- 是否运行服务：否。
- 是否访问端口：否。
- 是否调用 `/health`：否。
- 是否调用 `/kg/read-only-preview`：否。
- 是否触发 `/generate`、`/export_docx`、`/review/apply`：否。
- 是否触发 ZBid 写回：否。
- 是否写正文：否。
- 是否写 `output/job/export`：否。
- 是否生成 DOCX：否。
- 是否运行 Ollama：否。
- 是否升级或拉取模型：否。
- 是否修改 JSON、tests、frontend、config：否。
- 是否修改 `backend/app/main.py`：否。
- 是否接入 RAG / prompt registry / system instruction registry：否。
- 是否接入测试或 CI：否。
- 是否新增 `.pyc` / `__pycache__`：否。

## 8. Evidence And Scoring Boundary

- 本步骤结果不得作为 evidence。
- 本步骤结果不得作为 scoring。
- KG-RUNTIME-35 / KG-RUNTIME-36 / KG-RUNTIME-37 / KG-RUNTIME-38 结果不得作为 evidence。
- KG-RUNTIME-35 / KG-RUNTIME-36 / KG-RUNTIME-37 / KG-RUNTIME-38 结果不得作为 scoring。

## 9. Validation Results

- `git diff --check`: passed with exit code 0.
- `git diff --cached --check`: passed with exit code 0 before staging and after staging only the allowed files.

## 10. Next Stage Recommendation

KG-RUNTIME-40, if separately authorized later, should remain a separate gate. This KG-RUNTIME-39 step does not authorize real KG content reads, JSON parsing, service runs, endpoint calls, evidence, scoring, generation, export, RAG, registry creation, knowledge package loading, or ZBid writeback.

## 11. Final Boundary Conclusion

KG-RUNTIME-39 is complete as a controlled implementation draft only.

The real KG target exists only as allowlist metadata / target identifier:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

No real KG body content was read. No real KG JSON was parsed. No service or endpoint was run. No real use was entered.

KG-RUNTIME-40 is not entered.
