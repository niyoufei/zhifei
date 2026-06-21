# SYSTEM-AUTONOMY-012 Scope And Authorization Gate

## 1. Node

Node:

`SYSTEM-AUTONOMY-012-SCOPE-AUTHORIZATION-GATE`

Nature:

1. docs-only authorization preparation
2. code-read-only inputs limited to the authorized static guard files
3. no code modification
4. no test modification
5. no runtime
6. no endpoint
7. no Ollama
8. no model inference
9. no prompt input
10. no real KG / real project data read
11. no secrets / output / job / export / log body reading
12. stopped before `SYSTEM-AUTONOMY-012-IMPLEMENTATION`
13. stopped before `SYSTEM-AUTONOMY-013`
14. stopped before `LOCAL-LAUNCHER-026` or any other route

## 2. Current Baseline

Start HEAD:

`50c863983e410f6a181bfd8d67da783a0a8cdabf`

Start tag:

`v0.1.671-system-autonomy-011-revalidation-gate`

Branch:

`main`

Start `git status --short`:

clean.

## 3. Authorized Inputs Reviewed

Read-only inputs for this gate:

1. `docs/zdoc-system-autonomy-011-scope-and-authorization-gate.md`
2. `docs/zdoc-system-autonomy-011-implementation-static-guard-scope-correction-no-runtime.md`
3. `docs/zdoc-system-autonomy-011-revalidation-static-validation-only-gate.md`
4. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
5. `backend/tests/test_system_autonomy_static_guard.py`

No runtime, endpoint, Ollama, model, prompt, real KG, real project data, secrets, output, job, export, or log body was read.

## 4. SYSTEM-AUTONOMY-011 Closure Baseline

011 is closed at the current baseline.

Evidence chain:

1. `SYSTEM-AUTONOMY-011-SCOPE-AUTHORIZATION-GATE` positioned 011 as a controlled static-guard scope advancement and explicitly stopped before implementation and `LOCAL-LAUNCHER-026`.
2. `SYSTEM-AUTONOMY-011-IMPLEMENTATION-STATIC-GUARD-SCOPE-CORRECTION-NO-RUNTIME` completed a no-runtime implementation record for the 011 static guard scope.
3. The 011 implementation record states the modified scope was limited to:
   - `backend/zhifei_autoplan/system_autonomy_static_guard.py`
   - `backend/tests/test_system_autonomy_static_guard.py`
   - `docs/zdoc-system-autonomy-011-implementation-static-guard-scope-correction-no-runtime.md`
4. The current static guard contains the 011 authorized changed-file allowlist:
   - `backend/zhifei_autoplan/system_autonomy_static_guard.py`
   - `backend/tests/test_system_autonomy_static_guard.py`
   - `docs/zdoc-system-autonomy-011-implementation-static-guard-scope-correction-no-runtime.md`
5. The current static guard uses the 011 changed-file rejection reason `changed_file_outside_system_autonomy_011_static_guard_scope`.
6. The focused tests assert the 011 allowlist and reject legacy `010`, `009`, and earlier `008` implementation docs as outside the current scope.
7. The focused tests retain static blocking coverage for runtime, Web UI, endpoint, Ollama, model, prompt, real KG, real project data, secrets, output, job, export, and log boundaries.
8. `SYSTEM-AUTONOMY-011-REVALIDATION-1-STATIC-VALIDATION-ONLY-GATE` recorded:
   - `python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_static_guard.py` - PASS
   - `python3 -m pytest -q backend/tests/test_system_autonomy_static_guard.py` - PASS (`5 passed in 0.03s`)
   - `git diff --check` - PASS
9. The 011 revalidation recorded that no runtime startup script, Web UI, launcher, endpoint/API, curl/HTTP/localhost probe, Ollama command, model command, model inference, prompt workflow, real KG body, real project data body, secret, output, job, export, or log body was touched.
10. The current baseline HEAD and tag are `50c863983e410f6a181bfd8d67da783a0a8cdabf` and `v0.1.671-system-autonomy-011-revalidation-gate`, confirming the repository is positioned after the 011 revalidation gate.

## 5. SYSTEM-AUTONOMY-012 Suggested Positioning

Suggest positioning `SYSTEM-AUTONOMY-012` as:

`controlled static-guard scope advancement / authorization-only implementation gate`

012 should remain a narrow static-guard scope advancement from the closed 011 baseline. It should not be treated as runtime ready, endpoint ready, dry-run ready, trial ready, KG ready, real-project ready, prompt ready, model ready, or production ready.

This scope gate does not implement 012. It only prepares authorization for a later independent implementation node.

## 6. Recommendation On Entering Implementation

Recommendation:

enter implementation only after explicit ChatGPT controller authorization.

Suggested independent implementation node name:

`SYSTEM-AUTONOMY-012-IMPLEMENTATION-STATIC-GUARD-SCOPE-CORRECTION-NO-RUNTIME`

This node must be executed separately. This document does not authorize immediate implementation inside the current scope gate.

## 7. Suggested Allowed Files For 012 Implementation

If the later implementation node is explicitly authorized, suggest limiting modifications to:

1. `backend/zhifei_autoplan/system_autonomy_static_guard.py`
2. `backend/tests/test_system_autonomy_static_guard.py`
3. `docs/zdoc-system-autonomy-012-implementation-static-guard-scope-correction-no-runtime.md`

Suggested allowed implementation work:

1. Advance `AUTHORIZED_CHANGED_FILES` from the 011 implementation record to the 012 implementation record.
2. Advance the changed-file rejection reason from `changed_file_outside_system_autonomy_011_static_guard_scope` to a 012-specific reason.
3. Update or add focused tests that assert the 012 allowlist and reject the prior 011 implementation record as outside scope.
4. Add one docs-only 012 implementation record.

## 8. Suggested Validation For 012 Implementation

Suggested validation commands for the later implementation node:

1. `python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_static_guard.py`
2. `python3 -m pytest -q backend/tests/test_system_autonomy_static_guard.py`
3. `git diff --check`

These commands must not be expanded into runtime, endpoint, Ollama, model inference, prompt input, real KG, real project data, output, job, export, or log workflows.

## 9. Prohibited Scope For 012 Implementation

The later implementation node should continue to prohibit touching:

1. runtime startup scripts: `scripts/run_web_ui.sh`, `scripts/start_web_ui_background.sh`, `scripts/stop_web_ui_background.sh`, `scripts/web_ui_watchdog.sh`
2. Web UI / launcher: `local-launcher-v1/`, `frontend_web/`, `frontend/`
3. endpoint / API: `backend/app/routers/`, `backend/app/main.py`, `api/server.py`
4. model integration: `providers/`, `llm_client.py`, `ollama_preview.py`
5. KG integration or real KG paths: `kg/`, `kg_packs/`, `backend/kg_packs/`, `backend/data/kg/`
6. real project data paths: `backend/data/uploads/`, `backend/data/extracts/`, `data/uploads/`, `data/extracts/`
7. secrets / credentials: `.env*`, `secrets/`, `tokens/`, `credentials/`
8. output / job / export / log paths: `output/`, `outputs/`, `job/`, `jobs/`, `export/`, `exports/`, `log/`, `logs/`, `.runtime/docgen/`
9. configuration files, runtime scripts, non-authorized tests, non-authorized docs, generated results, exports, and log bodies

## 10. Runtime And Data Boundary

Runtime boundary:

No service, background process, watchdog, Web UI, launcher, local server, or runtime workflow may be started or modified by this gate or by the suggested implementation scope.

Endpoint boundary:

No endpoint may be registered, modified, accessed, probed, or validated. No curl, HTTP request, localhost access, or port probing is in scope.

Ollama / model inference boundary:

No Ollama command, model provider command, model inference, model routing, model download, or model readiness check is in scope.

Prompt boundary:

No prompt may be entered, generated, tested, or executed against a model workflow.

Real KG / real project data boundary:

No real KG, KG pack, project upload, project extract, tender file, drawing, BOQ, project sample, or business data body may be read.

Secrets boundary:

No secrets, credentials, tokens, private keys, or env-sensitive contents may be read.

Output / job / export / log boundary:

No generated output, job state, export artifact, audit output, runtime output, or log body may be read or modified.

## 11. Authorization Ambiguity Check

No implementation ambiguity blocks this scope gate.

Items requiring explicit ChatGPT controller confirmation before any next step:

1. Whether to enter `SYSTEM-AUTONOMY-012-IMPLEMENTATION-STATIC-GUARD-SCOPE-CORRECTION-NO-RUNTIME`.
2. Whether the suggested three-file implementation allowlist is accepted exactly as written.
3. Whether the suggested validation commands are accepted exactly as written.

Until those are confirmed, no implementation work is authorized.

## 12. Stop Condition

This node completes only the 012 scope authorization gate.

It must stop here.

It does not enter `SYSTEM-AUTONOMY-012-IMPLEMENTATION`.

It does not enter `SYSTEM-AUTONOMY-013`.

It does not enter `LOCAL-LAUNCHER-026`.

It does not enter any other later node or route.

## 13. Conclusion

`SYSTEM-AUTONOMY-012 SCOPE AUTHORIZATION PREPARED / DOCS ONLY / NO CODE MODIFIED / NO TEST MODIFIED / NO RUNTIME / NO ENDPOINT / NO OLLAMA / NO MODEL INFERENCE / NO PROMPT / NO REAL KG / NO REAL PROJECT DATA / NO SECRETS / NO OUTPUT JOB EXPORT LOG / STOPPED BEFORE IMPLEMENTATION`
