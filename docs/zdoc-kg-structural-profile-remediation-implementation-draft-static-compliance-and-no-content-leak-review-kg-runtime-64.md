# ZDoc KG Structural Profile Remediation Draft Static Compliance And No-Content-Leak Review - KG-RUNTIME-64

## Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Review baseline HEAD: `e90f1f42482b8f7edc80dc214f6bac8b085e4b6e`
- Baseline tag: `v0.1.445-zdoc-kg-structural-profile-remediation-draft`
- Note: local tag ref is not required for this review because KG-RUNTIME-63 recorded that the remote tag was created by refspec.

## Review Method

- This was a static docs-only review.
- Read-only evidence was limited to:
  - `backend/kg_read_only_preview_adapter.py`
  - `backend/app/routers/kg_read_only_preview.py`
  - `docs/zdoc-kg-structural-profile-no-go-controlled-remediation-implementation-draft-kg-runtime-63-review.md`
  - git metadata for the current HEAD.
- No service, endpoint, port, pytest, py_compile, Ollama, real KG content read, or real KG JSON parse was executed.

## Static Findings

1. Whether KG-RUNTIME-63 only modified the authorized adapter file: yes. Current HEAD shows one code change in `backend/kg_read_only_preview_adapter.py` plus the KG-RUNTIME-63 review document.
2. Whether route / main.py / frontend / tests / config / JSON were not modified: yes. `backend/app/routers/kg_read_only_preview.py` was inspected read-only and was not part of the KG-RUNTIME-63 commit.
3. Whether the `structural_profile=true` branch now exposes all required fields: yes. The branch returns `structure_read_only`, `structure_summary`, `structure_contract`, `structural_profile_only`, `structural_profile_summary`, and `structural_profile_contract`.
4. Whether `structure_summary` whitelist remains 13 fields and was not expanded: yes. The whitelist remains:
   `top_level_type`, `top_level_key_names`, `top_level_key_count`, `dict_count`, `list_count`, `null_count`, `scalar_type_counts`, `selected_structure_paths`, `list_lengths`, `field_type_sets`, `max_depth_limited`, `authorized_target`, `allowlist_status`.
5. Whether `structural_profile_summary` whitelist remains 14 fields and was not expanded: yes. The whitelist remains:
   `authorized_target`, `allowlist_status`, `profile_enabled`, `profile_scope`, `max_depth_limited`, `path_count`, `path_type_counts`, `depth_histogram`, `field_name_counts`, `field_type_sets`, `list_length_buckets`, `dict_key_count_buckets`, `module_name_candidates`, `redaction_policy`.
6. Whether `module_name_candidates` is fixed empty and not derived from field names, path names, KG scalar values, list items, or dict values: yes. `_structural_profile_module_name_candidates(...)` ignores its inputs and returns an empty tuple.
7. Whether `redaction_policy` is a fixed strategy string and does not concatenate KG content: yes. `STRUCTURAL_PROFILE_REDACTION_POLICY` is a constant string.
8. Whether the implementation still reuses the existing controlled structure-read path: yes. The structural profile branch builds from `structure_summary = _authorized_real_kg_structure_summary(...)`.
9. Whether a second uncontrolled file read path was added: no. The only content read path visible in the adapter remains `AUTHORIZED_REAL_KG_TARGET_PATH.open(...)` inside the gated `_authorized_real_kg_structure_summary(...)` function.
10. Whether files are read during import: no import-time file read was found. The module defines constants and functions only.
11. Whether files are automatically read during service startup: no service-start auto-read was found in the inspected adapter or route. The route calls the adapter only inside request handling.
12. Whether directory scan, batch read, or allowlist expansion was added: no. No `glob`, `rglob`, `iterdir`, `listdir`, or `scandir` usage was found in the adapter.
13. Whether this review actually read real KG file content: no.
14. Whether this review actually parsed real KG JSON: no.
15. Whether this review ran service, accessed a port, or called an endpoint: no.
16. Whether this review ran pytest / py_compile / Ollama: no.
17. Whether generation, export, or writeback chains were connected: no.
18. Whether RAG / prompt registry / system instruction registry were connected: no.
19. Whether the draft was used as evidence or scoring: no.

## Boundary Judgment

- Static compliance review result: PASS for KG-RUNTIME-64 docs-only static compliance scope.
- No-content-leak boundary judgment: no boundary-breaking content leak path was found in the KG-RUNTIME-63 remediation draft under static review.
- The remediation keeps scalar output to type/count summaries, list output to length/type summaries, dict output to key/type summaries, fixes module candidates to empty, and keeps redaction policy constant.
- This review does not authorize live route execution or real KG parsing.

## Next Gate

- KG-RUNTIME-65 is still required for remediation frozen audit and re-smoke authorization gate.
- KG-RUNTIME-64 is only a static review and does not mean remediation smoke has passed.
- This stage did not enter KG-RUNTIME-65.
