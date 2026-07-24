# OpenClaw / Zhifei Doc Phase 1 Local Baseline Index

## Purpose

This document is the Phase 1A local-only baseline index for Zhifei Doc autonomous build planning.
It records the current local integrated baseline, local entry points, readiness layers, demo boundary,
test boundary, config hold status, and the next write-gate route.

This is a docs-first index only. It does not authorize runtime startup, endpoint access, launcher
execution, push, real business material access, or held config content review.

## Local Baseline

- Phase 1 local-only baseline HEAD: `a241e68603d1be06c4b9412043760a5536f9c328`
- Merge parent 1, local P0 readiness commit: `019911fa6b0693a031c3c29109dc52e8f4eb8975`
- Merge parent 2, remote launcher/docs candidate: `bff0eed35d4df442a6450f3a6207cd3b34c8768d`
- P0 readiness status at entry: `PASS_P0_READINESS_STATIC`
- Required precondition for any following write gate: clean worktree before edits, no `.git/index.lock`,
  and a fresh post-edit audit when authorized changes make the worktree dirty.

## Entry Index

### Backend

- Backend application entry: `backend/app/main.py`
- App type: FastAPI
- Key route surface observed for planning: `/health`, `/p0/readiness`, `/capabilities`, `/config`,
  `/compose`, `/export`, `/audit`, `/retrieve`, score, autoplan, actions, KG preview, local LLM preview,
  and local trial preview-only routers.
- Phase 1A does not start this app and does not visit any route.

### Frontend And Workbench

- Streamlit workbench entry: `app.py`
- Tactical dashboard entry: `tactical_dashboard.py`
- Flask frontend entry: `frontend_web/app.py`
- Phase 1A treats these as entry metadata only. UI smoke, browser checks, and backend connection checks
  require separate runtime or launcher gates.

### Launcher

- Existing static launcher shell: `local_launcher/v1/README.md` and `local_launcher/v1/launcher-state.json`
- Merged remote static launcher shell: `local-launcher-v1/`
- Held config path: `local-launcher-v1/mock-config.json`
- Phase 1A does not run either launcher tree and does not read held config content.

### CLI And Scripts

- P0 readiness CLI: `scripts/p0_readiness.py`
- Endpoint smoke script, later gate only: `scripts/smoke_api.py`
- Web UI and launcher helper scripts exist under `scripts/`, but Phase 1A only records names and boundaries.
- Push, release, launchd, background start, endpoint smoke, and service management scripts remain out of
  scope unless a later gate authorizes them explicitly.

### Demo Project

- Sanitized demo project: `projects/_demo_p0/project.json`
- Demo metadata confirms `sanitized_demo: true`, no real business material, no external network requirement,
  no secret requirement, and safe-to-commit status.
- Phase 1A does not generate outputs from the demo. Demo workflow implementation belongs to a later write gate.

### Tests

- P0 targeted test command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_p0_readiness
```

- P0 static readiness commands:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json
```

- Full test expansion and endpoint smoke are not implied by Phase 1A.

### Docs And Runbook

- Main README: `README.md`
- Backend runbook: `backend/RUNBOOK.md`
- P0 readiness doc: `docs/openclaw-zhifei-doc-p0-readiness.md`
- This Phase 1A baseline index: `docs/openclaw-zhifei-doc-phase1-local-baseline.md`

## Readiness Layers

- P0 static readiness: local-only static gate; checks repo structure, git metadata, sanitized demo metadata,
  required entry presence, path-category sensitive handling, and forbidden-action flags.
- Phase 1 local-only readiness: planned next layer; should index local baseline, demo workflow, delivery index,
  static test matrix, log/error diagnostics, and continued forbidden-action proof.
- Runtime smoke gate: separate authorization; may start backend only when explicitly approved.
- Endpoint smoke gate: separate authorization; required before visiting `/health`, `/p0/readiness`,
  `/openapi.json`, `/list_files`, `/read_file`, or business endpoints.
- Launcher smoke gate: separate authorization; required before running local launcher or desktop launcher flow.
- Config content review gate: separate authorization; required before reading `local-launcher-v1/mock-config.json`
  content or using it for launcher/runtime decisions.

## Config Hold

- Held path: `local-launcher-v1/mock-config.json`
- Current handling: metadata-only checks are allowed; content remains unread.
- Observed object metadata at Phase 1 entry: blob, approximately `1043` bytes.
- Runtime, launcher, endpoint, and content review remain blocked while the hold is retained.
- Merging the file locally did not approve its content for use, display, execution, or propagation.

## Phase 1A Delivery Boundary

Phase 1A delivers only this local baseline index and minimal README/RUNBOOK pointers.

Allowed in Phase 1A:

- Write this document.
- Add README and RUNBOOK links to this document.
- Re-run P0 readiness tests and static readiness CLI.

Still forbidden in Phase 1A:

- Runtime startup.
- Launcher startup.
- Endpoint access.
- Real business material access.
- Secret or token reads.
- Held config content read.
- Push, fetch, merge, tag, release, or PR mutation.
- Production code or test code changes.

## Follow-Up Write Gates

- Phase 1B demo workflow gate: define a static sanitized demo workflow from project metadata to later runtime
  gate, without real business data.
- Phase 1C readiness / delivery index gate: add a Phase 1 readiness or local delivery index layer with tests.
- Phase 1D docs closure gate: close README, RUNBOOK, and docs wording across P0, Phase 1, runtime, endpoint,
  launcher, and config content review gates; see `docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md`.
- Phase 1E static test matrix gate: build a no-runtime test matrix and failure diagnostic checklist after
  Phase 1D docs / RUNBOOK closure; see `docs/openclaw-zhifei-doc-phase1e-static-test-matrix.md`.
- Phase 2A business input contract gate: after Phase 1 closeout and Phase 2 readonly planning approval,
  add only the static business input contract, synthetic fixture, validator, CLI, tests, and docs entry;
  see `docs/openclaw-zhifei-doc-phase2-business-input-contract.md`.

Every follow-up gate requires a separate ChatGPT approval and must restate allowed files, forbidden actions,
test commands, acceptance criteria, rollback or stop conditions, and sensitive-content handling.
