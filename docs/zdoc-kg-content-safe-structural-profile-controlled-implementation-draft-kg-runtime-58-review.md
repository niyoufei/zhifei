# KG-RUNTIME-58 content-safe structural profile controlled implementation draft review

## Scope

- Stage: KG-RUNTIME-58.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `5f65ccd8b87a1c798504803ece05da284de0e33d`.
- Start tag: `v0.1.439-zdoc-kg-route-layer-structure-read-frozen-gate`.
- This stage adds a controlled implementation draft only.
- This stage does not enter KG-RUNTIME-59.

## Actual Modified Files

- Modified code files:
  - `backend/kg_read_only_preview_adapter.py`
  - `backend/app/routers/kg_read_only_preview.py`
- Added review document:
  - `docs/zdoc-kg-content-safe-structural-profile-controlled-implementation-draft-kg-runtime-58-review.md`

The code changes are limited to the authorized adapter and route files. No other code file is intentionally modified by this stage.

## Untouched Areas

- `backend/app/main.py` is not modified.
- `frontend` is not modified.
- `tests` is not modified.
- `config` is not modified.
- JSON files are not modified.
- No output, job, or export artifact is written.
- No `.pyc` or `__pycache__` artifact is intentionally added.

## Runtime And Data Boundary

- No service is started.
- No port is accessed.
- `/health` is not called.
- `/kg/read-only-preview` is not called.
- `/generate`, `/export_docx`, and `/review/apply` are not called.
- ZBid writeback is not triggered.
- Ollama is not run.
- `pytest` is not run.
- `py_compile` is not run.
- No real KG file body content is actually read during this stage.
- No real KG JSON is actually parsed during this stage.
- The new `structural_profile` branch is not executed during this stage.
- RAG, prompt registry, system instruction registry, and CI are not connected.

## Added Structural Profile Fields

Controlled request fields added or recognized:

- `structural_profile`
- `structural_profile_only`

Controlled adapter and route response fields added:

- `structural_profile`
- `structural_profile_only`
- `structural_profile_summary`
- `structural_profile_contract`

The `structural_profile` branch remains gated by:

- feature flag enabled
- `manual_trigger = true`
- `real_kg_read_only = true`
- `structure_read = true`
- `structural_profile = true`
- `authorized_target = 知识图谱/ZF-KG-12-Municipal-Bridge.json`

The branch reuses the existing controlled `structure_read` summary path and does not add a second file-read or JSON-parse path.

## Structural Profile Output Field Whitelist

`structural_profile_summary` is limited to:

- `authorized_target`
- `allowlist_status`
- `profile_enabled`
- `profile_scope`
- `max_depth_limited`
- `path_count`
- `path_type_counts`
- `depth_histogram`
- `field_name_counts`
- `field_type_sets`
- `list_length_buckets`
- `dict_key_count_buckets`
- `module_name_candidates`
- `redaction_policy`

Allowed structural information only:

- paths
- field names
- types
- counts
- hierarchy levels
- module-name candidates
- allowlist hit status

## Content Leak Prevention Rules

- Scalar handling: scalar data may produce type and count only; scalar values are not output.
- List handling: list data may produce length buckets and type summaries only; list item content is not output.
- Dict handling: dict data may produce key names, key counts, and type sets only; dict value content is not output.
- `module_name_candidates` may be derived only from field names or path names, not from scalar values, list item content, or dict value content.

Explicitly prohibited from the structural profile output:

- business body text
- entity body text
- knowledge-entry body text
- prompt content
- system instruction content
- evidence content
- scoring content
- generated document body content

## Chain And Registry Boundary

- The generation chain is not connected.
- The export chain is not connected.
- The writeback chain is not connected.
- RAG is not connected.
- Prompt registry is not connected.
- System instruction registry is not connected.
- CI is not connected.
- The structural profile is not evidence.
- The structural profile is not scoring input.

## Review Conclusion

KG-RUNTIME-58 is a content-safe structural profile controlled implementation draft only.

This stage cannot be used to conclude that the `structural_profile` feature is ready, available, runtime-validated, safe for real use, connected to generation/export/writeback, usable as evidence, or usable for scoring.

KG-RUNTIME-59 is still required for static compliance review before any later runtime validation or real-use authorization.
