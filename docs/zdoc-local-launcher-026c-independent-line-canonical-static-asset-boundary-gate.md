# LOCAL-LAUNCHER-026C Independent Line Canonical Static Asset Boundary Gate

## 1. Node Metadata

| Field | Value |
| --- | --- |
| Node | `LOCAL-LAUNCHER-026C-INDEPENDENT-LINE-CANONICAL-STATIC-ASSET-BOUNDARY-GATE` |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `main` |
| Baseline HEAD | `27581549eb048819992d68f7a929058041ca12d0` |
| Baseline Tag | `v0.1.701-local-launcher-026b-governance-boundary-documentation-gate` |
| Previous Gates | `LOCAL-LAUNCHER-026-INDEPENDENT-LINE-PREFLIGHT-AUDIT`; `LOCAL-LAUNCHER-026A-INDEPENDENT-LINE-GOVERNANCE-ENTRY-DESIGN`; `LOCAL-LAUNCHER-026B-INDEPENDENT-LINE-GOVERNANCE-BOUNDARY-DOCUMENTATION-GATE` |
| Execution Type | Canonical static asset boundary gate; narrow write only; no development; no runtime |
| Write Scope | `docs/zdoc-local-launcher-026c-independent-line-canonical-static-asset-boundary-gate.md`; `local_launcher/v1/CANONICAL_STATIC_ASSET_BOUNDARY.md` |
| Runtime Policy | No runtime execution is authorized |
| Service Policy | No service start, stop, restart, preflight, health check, watchdog, or background process is authorized |
| Localhost Policy | No `localhost`, `127.0.0.1`, port, HTTP, endpoint, browser, or Web UI access is authorized |
| Model/Ollama Policy | No Ollama command, model inventory, model inference, prompt input, model pull, or model run is authorized |

## 2. Purpose

This node is not a development node.

This node is not a runtime node.

This node is not a runtime preflight.

This node is not an endpoint authorization.

This node is not an Ollama or model inference authorization.

This node only confirms the canonical static asset boundary for the LOCAL-LAUNCHER independent line.

This node only allows adding or updating the specified docs gate document and the canonical static asset boundary file.

This node does not authorize changes to runtime code, startup scripts, `.app` launchers, endpoints, local ports, Ollama, model inference, tests, builds, installs, generated artifacts, logs, PID files, output, job, export, real project data, secrets, tokens, credentials, or SYSTEM-AUTONOMY governance artifacts.

## 3. Canonical Static Asset Decision

`local_launcher/v1/` is the current LOCAL-LAUNCHER canonical static asset candidate boundary.

`local_launcher/v1/CANONICAL_STATIC_ASSET_BOUNDARY.md` is the canonical static boundary file added by this node.

`local_launcher/v1/README.md` is not modified by this node and remains a static reading reference for the V1 no-runtime boundary.

`local_launcher/v1/launcher-state.json` is not modified by this node and remains a static disabled-state reference.

`local-launcher-v1/` is a historical-reference path. This node does not modify it and does not treat it as a new write target.

`scripts/` and both `.app` entry bundles are forbidden-runtime surfaces. This node does not modify, execute, inspect runtime state through, or validate them.

021A, 021B, 025, and 026B governance documents are read-only references. This node cites their boundary role and does not rewrite them.

## 4. Static Asset Boundary Table

| Path | Classification | Current Role | 026C Action | Future Write Policy | Restriction | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `local_launcher/v1/` | canonical-static | Current V1 professional static console candidate | Confirmed as canonical static candidate root | Later writes require an explicit static asset node and exact allowlist | No runtime, endpoint, localhost, Ollama, or model capability may be enabled | Current README and state file define a static, disabled console. |
| `local_launcher/v1/CANONICAL_STATIC_ASSET_BOUNDARY.md` | canonical-boundary-doc | Canonical static boundary marker for the V1 candidate | Added by this node | May be updated only by later governance nodes | Must remain documentation only | This file makes the canonical boundary discoverable inside the asset root. |
| `local_launcher/v1/README.md` | static-read-only | Static console safety and usage boundary | Read only; not modified | Candidate for 026D alignment only if explicitly allowed | Must not be changed in 026C | It states the console is not runtime preflight and does not access endpoints or Ollama. |
| `local_launcher/v1/launcher-state.json` | static-read-only | Static disabled permission state | Read only; not modified | Candidate for 026D alignment only if explicitly allowed | Must not be changed in 026C; must not be enabled without separate authorization | It records disabled service, endpoint, port, log, config, Ollama, trial, generation, export, write-back, and controlled execution flags. |
| `local-launcher-v1/` | historical-reference | Historical 017-R1 professional static UI skeleton | No action | Read-only unless a migration/archive node explicitly allows it | No double-write with canonical path | It is useful historical evidence but should not remain a parallel active write line. |
| `local-launcher-v1/README.md` | historical-reference | Historical no-op/mock/disabled boundary | No action | Read-only unless migration/archive node allows it | No 026C write | It documents historical static intent. |
| `local-launcher-v1/app.js` | historical-reference | Historical pure frontend no-op script | No action | Read-only unless migration/archive node allows it | No 026C write or behavior extension | It is not the current canonical write target. |
| `scripts/run_web_ui.sh` | forbidden-runtime | Real Web UI startup entry | No action | Not writable in static governance nodes | Must not be executed or modified | It can start backend and Streamlit, write runtime files, and open local URLs. |
| `scripts/start_web_ui_background.sh` | forbidden-runtime | Background startup wrapper | No action | Not writable in static governance nodes | Must not be executed or modified | It delegates to `run_web_ui.sh --background` and writes control logs. |
| `文档生成系统.app/` | forbidden-runtime | Desktop launcher surface | No action | Not writable in static governance nodes | Must not be executed or modified | It can trigger runtime startup through shell and Terminal. |
| `施组专家系统.app/` | forbidden-runtime | Quick launcher surface | No action | Not writable in static governance nodes | Must not be executed or modified | It contains local URLs, health checks, retry behavior, and startup delegation. |
| `docs/zdoc-local-launcher-026b-independent-line-governance-boundary-documentation-gate.md` | governance-reference | Previous governance boundary gate | Read only; not modified | No direct modification in 026C | It remains historical governance evidence | It authorized 026C only as a no-runtime static canonical boundary gate. |

## 5. No-Runtime Control Matrix

| Control Item | Prohibited Action | Allowed Action | Verification Method | Breach Response |
| --- | --- | --- | --- | --- |
| `localhost` / `127.0.0.1` | Access, browser open, curl, health check, smoke check, endpoint call | Static text reference only | Confirm no command output indicates network or local URL access | Stop and report unauthorized access path |
| runtime | Start runtime, inspect runtime status, read PID/log/output/job/export bodies | Static governance documentation only | Confirm diff excludes runtime paths | Stop and report touched path |
| endpoint | Call, probe, smoke, validate, or route-test endpoint | Static documentation of prohibition only | Confirm no HTTP command was run | Stop and report command |
| Ollama | Run, serve, inventory, pull, invoke, or inspect model state | Static documentation of prohibition only | Confirm no Ollama command was run | Stop and report command |
| model inference | Prompt input, generation, model run, output inspection | Static documentation of prohibition only | Confirm no model command was run | Stop and report model surface |
| service start | Start backend, frontend, Streamlit, uvicorn, watchdog, launchd, background process | None in 026C | Confirm no service command was run | Stop and report command |
| port probe | `lsof`, curl, health URL, browser open, local port scan | None in 026C | Confirm no port command was run | Stop and report command |
| `.app` launcher | Execute, open, inspect runtime through launcher, alter bundle | Static path classification only | Confirm diff excludes `.app` paths | Stop and report touched path |
| `run_web_ui.sh` | Execute, modify, source, or use for validation | Static path classification only | Confirm diff excludes script path | Stop and report touched path |
| `start_web_ui_background.sh` | Execute, modify, source, or use for validation | Static path classification only | Confirm diff excludes script path | Stop and report touched path |
| tests/build/install | Run pytest, npm, pnpm, playwright, build, install, update, migrate, format, lint --fix | None in 026C | Confirm no such command was run | Stop and report command |
| scripts mutation | Modify any `scripts/` file | None in 026C | Confirm `git diff --name-only` excludes `scripts/` | Stop and report diff scope |

## 6. 026D Entry Conditions

| Field | Value |
| --- | --- |
| 026D Recommended Node Name | `LOCAL-LAUNCHER-026D-INDEPENDENT-LINE-STATIC-README-STATE-ALIGNMENT-GATE` |
| 026D Entry Status | Allowed only after 026C is committed, tagged, pushed, and the worktree is clean |
| Required Preconditions | Exact baseline HEAD and tag; clean `main`; explicit file allowlist; no-runtime policy; no-service policy; no-localhost policy; no-Ollama/model policy |
| Allowed Write Scope Recommendation | `local_launcher/v1/README.md`; `local_launcher/v1/launcher-state.json`; the 026D docs gate document |
| Forbidden Scope Recommendation | `scripts/`, `.app` bundles, `.runtime/`, `local-launcher-v1/`, README, RUNBOOK, backend/frontend runtime, endpoint, Ollama, model, SYSTEM-AUTONOMY docs, 025, 026B, and 026C unless explicitly listed for read-only reference |
| Acceptance Recommendation | `git diff --name-only`, targeted diff for allowed files, `git diff --check`, `git status --short --branch`; no tests, builds, or runtime checks |
| Rollback Recommendation | If any unauthorized file appears in diff, stop immediately and report the file list and diff scope before corrective action |
| Still Forbidden Actions | Starting services; accessing localhost or 127.0.0.1; touching runtime, endpoint, Ollama, model inference, scripts, `.app`, `local-launcher-v1/`; running tests, builds, installs, model calls, endpoint calls, or port probes |

026D may align the canonical README and disabled-state file with this canonical boundary, but it must remain a static documentation/state alignment gate.

026D must not start services.

026D must not access localhost.

026D must not touch runtime, endpoint, Ollama, or model inference.

026D must not modify scripts or `.app` bundles.

026D must not modify the `local-launcher-v1/` historical directory.

026D must not execute tests, build, install, or model calls.

## 7. Risk Register

| Risk ID | Risk Description | Level | Evidence | Control Rule | Blocking Status |
| --- | --- | --- | --- | --- | --- |
| R-026C-01 | Canonical static asset boundary is not physically recorded in the asset root | B2 | Before this node, 026B documented the boundary but no `local_launcher/v1/CANONICAL_STATIC_ASSET_BOUNDARY.md` marker existed | Add this boundary marker and keep it documentation-only | Resolved by this node for static governance |
| R-026C-02 | Two local launcher directories coexist | B2 | `local_launcher/` and `local-launcher-v1/` both exist | Treat `local_launcher/v1/` as canonical static candidate and `local-launcher-v1/` as historical-reference | Not blocking if future writes target only the authorized canonical path |
| R-026C-03 | Historical `local-launcher-v1/` may be accidentally edited | B1 | Historical path contains README, app.js, index.html, styles.css, and mock config | Classify historical path as read-only historical-reference | Blocking if it appears in diff |
| R-026C-04 | `scripts/` or `.app` launchers may be executed or modified | B1 | 026B identifies startup scripts and app bundles as forbidden-runtime | Keep scripts and `.app` surfaces outside static governance write scope | Blocking for runtime work; not blocking this docs-only node |
| R-026C-05 | `launcher-state.json` may be mistakenly changed to enable runtime, endpoint, Ollama, or model behavior | B1 | Current state file contains disabled flags for service, endpoint, health, Ollama, trial, generation, export, write-back, and controlled execution | 026C does not modify it; 026D may only preserve or strengthen disabled state under exact allowlist | Blocking if enabled without explicit runtime authorization |
| R-026C-06 | 026D may be misread as a runtime development entry | B2 | 026C recommends 026D as README/state alignment | State 026D as static alignment only and repeat no-runtime/no-endpoint/no-Ollama boundaries | Not blocking if 026D stays static |

## 8. Acceptance Criteria

This node is accepted only if all of the following are true:

1. Only these two target files are added or updated:
   - `docs/zdoc-local-launcher-026c-independent-line-canonical-static-asset-boundary-gate.md`
   - `local_launcher/v1/CANONICAL_STATIC_ASSET_BOUNDARY.md`
2. `git diff --name-only` shows only the two target files before staging.
3. `git diff --check` passes.
4. No service is started.
5. No `localhost` or `127.0.0.1` access occurs.
6. No runtime, endpoint, Ollama, model inference, prompt, port, PID, log body, output, job, export, real project data, or real KG is touched.
7. No tests, build, install, dependency update, migration, formatting, generation, export, or write-back commands are run.
8. No `local_launcher/v1/README.md`, `local_launcher/v1/launcher-state.json`, `local-launcher-v1/`, `scripts/`, `.app`, README, RUNBOOK, 021A, 021B, 025, 026B, runtime code, endpoint code, model code, or configuration file is modified.
9. Commit is created with message `docs: define local launcher 026c canonical static asset boundary`.
10. Tag `v0.1.702-local-launcher-026c-canonical-static-asset-boundary-gate` points to the new commit.
11. `main` and the tag are pushed.
12. Final worktree and staging area are clean.

## 9. Final Conclusion

026C completes the canonical static asset boundary gate for the LOCAL-LAUNCHER independent line.

026C allows entry into 026D only as a static README/state alignment gate:

`LOCAL-LAUNCHER-026D-INDEPENDENT-LINE-STATIC-README-STATE-ALIGNMENT-GATE`

026D may recommend narrow writes to `local_launcher/v1/README.md`, `local_launcher/v1/launcher-state.json`, and its own docs gate file only.

026D must remain non-runtime, non-endpoint, non-Ollama, non-model-inference, non-service, no-localhost, no-test, no-build, no-install, no-scripts, no-`.app`, and no historical-directory mutation unless a future explicit node separately authorizes a narrower exception.

This node does not authorize any runtime, endpoint, Ollama, model inference, service startup, localhost access, port probe, script execution, `.app` execution, tests, builds, installs, or generated-output behavior.
