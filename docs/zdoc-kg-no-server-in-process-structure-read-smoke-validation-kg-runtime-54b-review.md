# ZDoc KG no-server in-process structure-read smoke validation KG-RUNTIME-54B review

## Result

KG-RUNTIME-54B completed.

This stage performed one no-server in-process structure-read smoke validation for the single authorized KG target:

`知识图谱/ZF-KG-12-Municipal-Bridge.json`

The validation used a direct adapter in-process call. It did not use FastAPI TestClient, did not import `backend/app/main.py`, did not start `uvicorn`, did not bind a TCP port, and did not access any `127.0.0.1` port.

This stage did not enter KG-RUNTIME-55.

## Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `3d2332a11c769e5132201e9def190cfe16818488`
- Start tag: `v0.1.435-zdoc-kg-structure-read-smoke-blocked-audit-gate`

## Authorized request shape

The in-process call used the route-equivalent gate values:

```text
manual_trigger = true
real_kg_read_only = true
structure_read = true
authorized_target = 知识图谱/ZF-KG-12-Municipal-Bridge.json
```

The call invoked `build_kg_read_only_preview(...)` directly with:

- `manual_trigger=True`
- `real_kg_read_only=True`
- `real_kg_target="知识图谱/ZF-KG-12-Municipal-Bridge.json"`
- `feature_flag_enabled=True`
- `structure_read=True`

## Validation output

The smoke command printed only safe validation status and counts, not KG scalar values, list elements, dict values, business body text, entity body text, knowledge entry text, prompts, system instructions, scoring content, or generated document text.

```text
IN_PROCESS_SMOKE=PASS
CALL_MODE=direct_adapter_in_process
AUTHORIZED_TARGET=知识图谱/ZF-KG-12-Municipal-Bridge.json
STATUS=preview_only
STRUCTURE_READ_ONLY=true
STRUCTURE_SUMMARY_PRESENT=true
STRUCTURE_CONTRACT_PRESENT=true
SUMMARY_KEYS_EXACT_WHITELIST=true
SUMMARY_FIELD_COUNT=13
SELECTED_STRUCTURE_PATH_COUNT=80
LIST_LENGTH_PATH_COUNT=8
FIELD_TYPE_SET_PATH_COUNT=17
NO_WRITE=true
NO_EVIDENCE=true
NO_SCORING=true
NO_RAG=true
NO_GENERATION=true
NO_EXPORT=true
NO_ZBID_WRITEBACK=true
NO_SCALAR_VALUE_OUTPUT_SHAPE_CHECK=PASS
NO_LIST_ELEMENT_CONTENT_OUTPUT_SHAPE_CHECK=PASS
NO_DICT_VALUE_CONTENT_OUTPUT_SHAPE_CHECK=PASS
```

## Structure summary whitelist

`structure_summary` returned exactly these fields and no others:

- `top_level_type`
- `top_level_key_names`
- `top_level_key_count`
- `dict_count`
- `list_count`
- `null_count`
- `scalar_type_counts`
- `selected_structure_paths`
- `list_lengths`
- `field_type_sets`
- `max_depth_limited`
- `authorized_target`
- `allowlist_status`

The shape checks confirmed:

- `selected_structure_paths` entries contain only `path` and `type`.
- `list_lengths` entries contain only list length and element type counts.
- `field_type_sets` entries contain only field names and JSON type names.
- `scalar_type_counts` contains type names and counts only.

No raw JSON scalar values, list element content, or dict value content was printed or written by this review.

## Boundary confirmation

- `uvicorn` startup: no.
- TCP bind: no.
- `127.0.0.1` port access: no.
- FastAPI TestClient: no.
- Direct route/adapter in-process call: yes, direct adapter.
- Authorized KG file parsed: yes, only `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- Any other KG file read: no.
- `AI知识图谱大全` read/copy/move/delete: no.
- Code modified: no.
- Adapter/route/main.py modified: no.
- Frontend/tests/config/JSON modified: no.
- `/generate`, `/export_docx`, `/review/apply` triggered: no.
- ZBid writeback triggered: no.
- Output/job/export write: no.
- Ollama run: no.
- Model pull/upgrade/delete/replace: no.
- RAG, prompt registry, system instruction registry, knowledge package registry, CI: no.

## Bytecode and cache note

The smoke command was run with `PYTHONDONTWRITEBYTECODE=1`.

After the smoke, `backend/__pycache__/kg_read_only_preview_adapter.cpython-313.pyc` was observed with mtime `2026-05-24 22:40:28 +0800`, predating this review write-up. `git status --short` showed no `.pyc` or `__pycache__` changes. No cache cleanup was performed.

## Git checks

Required checks for this stage:

- `git diff --check`
- `git diff --cached --check`

Final commit and tag are recorded in the task closeout response.
