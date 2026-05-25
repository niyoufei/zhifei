# KG-RUNTIME-88 no-server in-process guard-field normalization re-smoke validation

## Scope

- Stage: `KG-RUNTIME-88`
- Goal: validate whether the KG-RUNTIME-85 guard/status/contract/policy field normalization eliminated residual substring overlap.
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `7617872844ba0b2a4064695b5f18121b851d9d8a`
- Baseline remote tag: `v0.1.470-zdoc-kg-guard-field-normalization-resmoke-gate`
- Authorized target only: `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- Review artifact only: `docs/zdoc-kg-no-server-in-process-guard-field-normalization-resmoke-validation-kg-runtime-88-review.md`

The remote baseline tag was verified by `git ls-remote --tags origin v0.1.470-zdoc-kg-guard-field-normalization-resmoke-gate` and pointed to the required start HEAD.

## Authorized payload

The single no-server in-process validation used a direct route call with this contract:

| Field | Value |
| --- | --- |
| `manual_trigger` | `true` |
| `real_kg_read_only` | `true` |
| `structure_read` | `true` |
| `structural_profile` | `true` |
| `authorized_target` | `知识图谱/ZF-KG-12-Municipal-Bridge.json` |

## Method

- Used one no-server Python process with `PYTHONDONTWRITEBYTECODE=1`.
- Called `kg_read_only_preview_route(payload)` directly in process.
- Did not use `TestClient`.
- Did not start `uvicorn`.
- Did not bind a TCP port.
- Did not access `127.0.0.1`.
- Did not run `pytest`.
- Did not run `py_compile`.
- Did not run `python3 -m json.tool`.
- Did not run Ollama.
- Did not connect to RAG, prompt registry, system instruction registry, or CI.
- Did not trigger `/generate`, `/export_docx`, or `/review/apply`.
- Did not write output, job, or export artifacts.

Runtime guards were installed around the direct route call to block socket creation, socket connections, socket pairs, directory listing/traversal APIs, unauthorized file reads, and file writes.

## Re-smoke result

| Check | Result |
| --- | --- |
| Direct route in-process call completed | PASS |
| Route status | `preview_only` |
| Route `ok` | `true` |
| Adapter status | `preview_only` |
| Route to adapter passthrough | PASS |
| `structure_read_only` returned | PASS |
| `structure_summary` returned | PASS |
| `structure_contract` returned | PASS |
| `structural_profile_only` returned | PASS |
| `structural_profile_summary` returned | PASS |
| `structural_profile_contract` returned | PASS |
| `structure_summary` whitelist field count | 13 |
| `structure_summary` whitelist order match | PASS |
| `structural_profile_summary` whitelist field count | 14 |
| `structural_profile_summary` whitelist order match | PASS |
| `module_name_candidates` empty list | PASS |
| `redaction_policy` equals `redacted` | PASS |
| Authorized source scalar string leaf count | 765 |
| Response scalar string leaf count | 11 |
| Scalar full leaf overlap | 0 |
| Substring overlap | 24 |

## NO-GO reason

KG-RUNTIME-88 is NO-GO because the required substring overlap value was `0`, but the strict re-smoke audit returned `24`.

The strict overlap audit used all unique non-empty string scalar leaf values collected from the single authorized KG parse and compared them against the serialized route response. No matched scalar values or substrings are printed in this review, and no business body, entity body, knowledge-entry body, prompt body, system-instruction body, evidence body, or scoring body is included here.

## Runtime and side-effect controls

| Control | Result |
| --- | --- |
| Uvicorn started | NO |
| TCP port bound | NO |
| `127.0.0.1` accessed | NO |
| Directory scan during route call | NO |
| Unauthorized KG file read | NO |
| Authorized target read count | 1 |
| File write attempt during route call | 0 |
| Socket attempt during route call | 0 |
| Directory scan attempt during route call | 0 |
| `AI知识图谱大全` read/copied/moved/deleted | NO |
| Output/job/export write | NO |
| Ollama run | NO |
| RAG/registry/CI connected | NO |

## File and code boundaries

| Boundary | Result |
| --- | --- |
| Code modified | NO |
| Adapter modified | NO |
| Route modified | NO |
| `main.py` modified | NO |
| Frontend modified | NO |
| Tests modified | NO |
| Config modified | NO |
| JSON modified | NO |
| Authorized target outside the single KG file read | NO |
| Scalar value output | NO |
| List item content output | NO |
| Dict value content output | NO |
| Business/entity/knowledge-entry body output | NO |
| Prompt/system-instruction/evidence/scoring output | NO |

## Conclusion

KG-RUNTIME-88 completed as a no-server in-process re-smoke validation and archival task, but the result is **NO-GO** because substring overlap remained nonzero.

No code repair was performed in this stage. KG-RUNTIME-89 was not entered.
