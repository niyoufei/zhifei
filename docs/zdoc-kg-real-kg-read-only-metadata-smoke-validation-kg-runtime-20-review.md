# KG-RUNTIME-20: ZDoc KG Real-KG Read-Only Metadata Smoke Validation

## 1. Step Identity

- Step: KG-RUNTIME-20.
- Name: ZDoc KG real-KG read-only metadata smoke validation.
- Nature: docs-only review plus metadata-level read-only file inspection.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `cb2d2c9ce0687c82e4764ab2b39a25ed009db81e`.
- Start tag: `v0.1.400-zdoc-kg-real-read-metadata-smoke-authorization-gate`.

## 2. KG-RUNTIME-18 Target Discovery Summary

KG-RUNTIME-18 was a docs-only static discovery and minimal future read plan.

It identified one primary minimal candidate for a future metadata-level smoke:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

It also recorded a broader real KG candidate pool by file name only, metadata or package-manifest candidate paths, and disabled candidate or controlled-entity reference paths.

KG-RUNTIME-18 did not read candidate real KG file contents, did not read real KG JSON, and did not read `AI知识图谱大全` contents. All candidate paths were treated as path names only.

## 3. KG-RUNTIME-19 Authorization Gate Summary

KG-RUNTIME-19 authorized only a future real KG metadata-level smoke under a separate explicit request.

The KG-RUNTIME-19 recommended first target remained:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

KG-RUNTIME-19 required the next step to inspect only an explicitly named KG path, read file-level metadata only, report only pre-agreed metadata-level fields, and preserve read-only/no-write/no-evidence/no-scoring boundaries.

## 4. Metadata Smoke Execution Scope

This KG-RUNTIME-20 execution inspected only file-level metadata for one explicitly authorized candidate path.

Observed fields were limited to:

- existence;
- path;
- type: `file` / `directory` / `missing`;
- permissions;
- file size;
- modification time;
- whether the path is within the authorized candidate scope.

No file body, JSON payload, KG payload, business正文, registry payload, or knowledge-pack payload was read.

## 5. Candidate Target Source

The candidate target came from:

- KG-RUNTIME-18 review document candidate path list;
- KG-RUNTIME-19 authorization gate target;
- existing git/review-document path references.

No temporary candidate expansion was performed.

## 6. Candidate Target Path List

Only one path was inspected:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

Metadata smoke candidate target count: `1`.

## 7. Metadata Results

| Path | Exists | Type | Permissions | Size | Mtime | Within Authorized Candidate Scope |
| --- | --- | --- | --- | --- | --- | --- |
| `知识图谱/ZF-KG-12-Municipal-Bridge.json` | yes | file | `-rw-r--r--` | `362710` bytes | `Apr 28 15:25:11 2026` | yes |

Command-level metadata observations:

- `test -e '知识图谱/ZF-KG-12-Municipal-Bridge.json' && echo exists || echo missing`: `exists`.
- `test -f '知识图谱/ZF-KG-12-Municipal-Bridge.json' && echo file || true`: `file`.
- `test -d '知识图谱/ZF-KG-12-Municipal-Bridge.json' && echo directory || true`: no output.
- `ls -ld '知识图谱/ZF-KG-12-Municipal-Bridge.json'`: `-rw-r--r--  1 youfeini  staff  362710 Apr 28 15:25 知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- `stat '知识图谱/ZF-KG-12-Municipal-Bridge.json'`: size `362710`, mtime `Apr 28 15:25:11 2026`.

These observations are metadata-only and must not be used as evidence or scoring.

## 8. Negative Execution Confirmation

This KG-RUNTIME-20 step did not read real KG file body content.

This KG-RUNTIME-20 step did not parse real KG JSON.

This KG-RUNTIME-20 step did not run `python3 -m json.tool`.

This KG-RUNTIME-20 step did not read `AI知识图谱大全` content.

This KG-RUNTIME-20 step did not copy, move, or delete `AI知识图谱大全`.

This KG-RUNTIME-20 step did not load a real knowledge package.

This KG-RUNTIME-20 step did not create a real registry.

This KG-RUNTIME-20 step did not register, enable, or load a knowledge package.

This KG-RUNTIME-20 step did not run a service.

This KG-RUNTIME-20 step did not access a port.

This KG-RUNTIME-20 step did not call `/health`.

This KG-RUNTIME-20 step did not call `/kg/read-only-preview`.

This KG-RUNTIME-20 step did not trigger `/generate`, `/export_docx`, or `/review/apply`.

This KG-RUNTIME-20 step did not trigger ZBid writeback.

This KG-RUNTIME-20 step did not write document body content.

This KG-RUNTIME-20 step did not write `output/job/export`.

This KG-RUNTIME-20 step did not run Ollama.

This KG-RUNTIME-20 step did not upgrade or pull a model.

This KG-RUNTIME-20 step did not modify code, JSON, tests, frontend, or config.

This KG-RUNTIME-20 step did not connect RAG, prompt registry, or system instruction registry.

This KG-RUNTIME-20 step did not connect tests or CI.

This KG-RUNTIME-20 step did not add `.pyc` or `__pycache__` changes.

The metadata smoke result must not be treated as evidence.

The metadata smoke result must not be treated as scoring.

## 9. Next-Stage Recommendation

KG-RUNTIME-21, if separately authorized, should remain gated by a new explicit instruction.

Recommended boundary for the next step:

- do not enter real use automatically;
- do not load or register a knowledge package automatically;
- do not parse or validate JSON unless explicitly authorized by a later gate;
- do not call `/kg/read-only-preview` unless explicitly authorized by a later gate;
- keep no-evidence, no-scoring, no-RAG, no-generation, no-export, and no-ZBid-writeback invariants.

## 10. Validation Results

- `git diff --check`: passed with exit code 0.
- `git diff --cached --check`: passed with exit code 0 after staging only this target docs file.

## 11. Final Boundary Conclusion

KG-RUNTIME-20 completed only a real KG read-only metadata-level smoke validation for one authorized candidate path.

Only the target docs review file was added.

No code, JSON, tests, frontend, config, output/job/export artifact, `.pyc`, or `__pycache__` change was introduced.

KG-RUNTIME-20 did not enter KG-RUNTIME-21.
