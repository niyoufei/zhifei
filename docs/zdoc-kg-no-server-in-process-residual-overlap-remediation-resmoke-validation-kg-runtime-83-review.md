# KG-RUNTIME-83 no-server in-process residual overlap remediation re-smoke validation review

## Scope

- Stage: KG-RUNTIME-83.
- Goal: validate the KG-RUNTIME-80 residual-overlap remediation through one no-server direct route in-process call.
- Explicit stop boundary: do not enter KG-RUNTIME-84.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `a40f45b8111be25c0173848d14c9b6695a1e801a`.
- Baseline tag: `v0.1.465-zdoc-kg-residual-overlap-resmoke-gate`.
- Baseline tag state: no local tag ref existed; the remote tag was verified to point to `a40f45b8111be25c0173848d14c9b6695a1e801a`.

## Authorized target and payload

- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- Payload fields used:
  - `manual_trigger=true`
  - `real_kg_read_only=true`
  - `structure_read=true`
  - `structural_profile=true`
  - `authorized_target=知识图谱/ZF-KG-12-Municipal-Bridge.json`

No `structural_profile_only` request field was added; the check required it to be returned by the route/adapter response.

## Invocation method

- Python invocation count for the re-smoke: 1.
- Invocation mode: direct async in-process call to `kg_read_only_preview_route(payload)`.
- Environment guard: `PYTHONDONTWRITEBYTECODE=1`.
- Feature flag: `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`.
- Server mode: no uvicorn.
- TCP mode: socket bind/connect/getaddrinfo/create_connection guarded and unused.
- Directory scan guard: `os.scandir`, `os.walk`, `glob.glob`, and `Path.iterdir` guarded and unused during the route call.
- File guard: `Path.open` allowed read access only to the single authorized target and blocked writes.
- JSON parse guard: `json.load` was wrapped during the route call to count source string scalar leaves without printing them.

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
| Scalar full leaf overlap | 0 |
| Substring overlap | 24 |

## NO-GO reason

KG-RUNTIME-83 is NO-GO because the required substring overlap value was `0`, but the strict re-smoke audit returned `24`.

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
| `/generate` triggered | NO |
| `/export_docx` triggered | NO |
| `/review/apply` triggered | NO |
| ZBid writeback triggered | NO |
| `output/`, `job/`, or `export/` written | NO |
| Ollama called | NO |
| RAG connected | NO |
| Prompt registry connected | NO |
| System instruction registry connected | NO |
| CI connected | NO |

## File scope

- Code modified: NO.
- Adapter modified: NO.
- Route modified: NO.
- `main.py` modified: NO.
- Frontend modified: NO.
- Tests modified: NO.
- Config modified: NO.
- JSON modified: NO.
- KG files modified: NO.
- `AI知识图谱大全` read/copied/moved/deleted: NO.
- New file intended for this stage: `docs/zdoc-kg-no-server-in-process-residual-overlap-remediation-resmoke-validation-kg-runtime-83-review.md`.

## Cache state

The run used `PYTHONDONTWRITEBYTECODE=1`. Existing route/adapter `__pycache__` directories were present before the run and retained their previous timestamp after the run. No cleanup was required for this stage.

## Conclusion

Re-smoke conclusion: NO-GO.

Stop condition: KG-RUNTIME-83 is archived as a NO-GO review. Do not enter KG-RUNTIME-84 without separate authorization.
