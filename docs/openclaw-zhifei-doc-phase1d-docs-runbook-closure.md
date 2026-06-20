# OpenClaw / Zhifei Doc Phase 1D Docs And Runbook Closure

## Purpose

Phase 1D closes the local static documentation route for Phase 1. It gives operators
a single docs map from README and RUNBOOK into P0 readiness, Phase 1 local baseline,
Phase 1B demo workflow, Phase 1C readiness / delivery index, and the next Phase 1E
static test matrix gate.

This is a docs-only closure. It does not authorize runtime startup, endpoint access,
launcher execution, held config content review, real business material reads, secret
reads, remote sync, push, tag, release, or PR mutation.

## Current Static Route

1. P0 static readiness proves local repository shape, existing git metadata, sanitized
   demo metadata, required entry presence, path-category sensitive handling, and
   forbidden-action flags.
2. Phase 1 local-only baseline records the local build starting point, entry points,
   readiness layers, demo boundary, test boundary, and config hold status.
3. Phase 1B static demo workflow connects the sanitized demo project to a no-runtime
   workflow and blocks output materialization before a later runtime or endpoint gate.
4. Phase 1C readiness / delivery index promotes P0 and Phase 1B evidence into a local
   delivery index and hard-gate matrix.
5. Phase 1D closes README, RUNBOOK, and docs navigation so the static route can be
   understood without prior thread context.
6. Phase 1E should add a no-runtime static test matrix and failure diagnostic checklist.

## Operator Entry Points

- README status and command entry: `README.md`
- Backend operator runbook: `backend/RUNBOOK.md`
- P0 readiness detail: `docs/openclaw-zhifei-doc-p0-readiness.md`
- Phase 1A local baseline: `docs/openclaw-zhifei-doc-phase1-local-baseline.md`
- Phase 1B static demo workflow: `docs/openclaw-zhifei-doc-phase1b-demo-workflow.md`
- Phase 1C readiness / delivery index: `docs/openclaw-zhifei-doc-phase1c-readiness-delivery-index.md`
- Phase 1D docs / RUNBOOK closure: `docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md`

## Static Verification Commands

Run these from the repository root. They do not start services.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_p0_readiness
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_demo_workflow
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_demo_workflow.py --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_delivery_index
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_delivery_index.py --json
```

Expected clean-worktree statuses:

- `PASS_P0_READINESS_STATIC`
- `PASS_PHASE1B_DEMO_WORKFLOW_STATIC`
- `PASS_PHASE1C_READINESS_DELIVERY_INDEX_STATIC`

While Phase 1D docs are dirty but not yet committed, P0, Phase 1B, and Phase 1C CLIs
may return their `NO-GO` statuses because they intentionally reject an unclosed
worktree. Commit the docs-only change locally, then rerun the commands.

## Failure Diagnostics

- `worktree_not_clean`: finish the authorized local closure in a docs-only commit, or
  stop for a separate decision before any out-of-scope cleanup.
- `git_index_lock_present`: stop for a separate git-lock decision before any commit
  attempt.
- `required_entries_missing`: restore or repair the missing static entry before moving
  to runtime, endpoint, or launcher gates.
- `sanitized_demo_project_missing_or_invalid`: repair only the sanitized demo metadata
  route; do not substitute real business documents.
- `p0_readiness_static_pass`: rerun P0 readiness first and inspect its `failures`.
- `phase1b_static_demo_workflow_pass`: rerun Phase 1B static workflow and inspect its
  failure list before Phase 1C.

## Hard Gates

These actions stay blocked unless a later manual gate explicitly authorizes them:

- push, fetch, pull, merge, rebase, squash, reset, clean, checkout, switch, stash, tag,
  release, or PR mutation;
- backend, frontend, launcher, Ollama, browser, or service runtime startup;
- endpoint access including `/health`, `/p0/readiness`, `/openapi.json`, `/list_files`,
  `/read_file`, and business endpoints;
- `.env`, token, secret, password, private key, auth store, or credential content reads;
- real business document body reads or real customer project connection;
- `local-launcher-v1/mock-config.json` content reads or use in launcher/runtime decisions.

`local-launcher-v1/mock-config.json` remains metadata-only. A future config content
review gate must define exact file scope, purpose, allowed readers, redaction handling,
and stop conditions before its body can be inspected.

## Gate Relationship

- P0 static readiness is the local static safety proof.
- Runtime smoke gate decides whether a service may be started.
- Endpoint smoke gate decides whether HTTP routes may be visited.
- Launcher smoke gate decides whether local launcher flows may run.
- Config content review gate decides whether the held mock config body may be read.

These gates are independent. Passing Phase 1D docs closure does not imply any of the
runtime, endpoint, launcher, or config content gates have passed.

## Phase 1E Entry

Phase 1E should build a static test matrix that remains no-runtime and no-endpoint.
The matrix should cover P0, Phase 1B, Phase 1C, docs links, expected clean-worktree
statuses, dirty-worktree NO-GO behavior, and hard-gate negative proofs.
