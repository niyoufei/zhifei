# OpenClaw / Zhifei Doc Phase 1E Static Test Matrix

## Purpose

Phase 1E establishes the no-runtime static test matrix for the Phase 1 local
static chain. It makes P0, Phase 1B, Phase 1C, and Phase 1D repeatable from one
operator entry without starting services, visiting endpoints, running launchers,
reading held config content, reading secrets, or reading real business documents.

## Static Matrix Command

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_static_matrix.py --json
```

Clean-worktree acceptance status:

- `PASS_PHASE1E_STATIC_TEST_MATRIX`

While authorized Phase 1E files are dirty and not yet committed, P0 readiness may
return `NO-GO_P0_READINESS_STATIC` with `worktree_not_clean`. That is the expected
dirty-worktree gate. After the local Phase 1E commit, rerun the matrix and P0
commands; they must return PASS.

## Matrix Coverage

The static matrix covers:

1. P0 readiness clean PASS chain.
2. Dirty worktree `worktree_not_clean` NO-GO expectation.
3. Phase 1B demo workflow static entry.
4. Phase 1C readiness / delivery index static entry.
5. Phase 1D docs / RUNBOOK closure static entry.
6. Docs link and docs presence checks across README, RUNBOOK, and Phase 1 docs.
7. Failure diagnostics for P0, Phase 1B, Phase 1C, docs presence, and git lock cases.
8. Forbidden-action proof for runtime, endpoint, launcher, held config body, secret,
   real business document, and remote sync boundaries.
9. Post-commit P0 PASS verification.

## Required Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_p0_readiness
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_demo_workflow
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_delivery_index
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_static_matrix
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_demo_workflow.py --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_delivery_index.py --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_static_matrix.py --json
git diff --check
```

## Failure Diagnostics

- `worktree_not_clean`: expected while authorized Phase 1E files are dirty; create
  the local Phase 1E commit and rerun the static checks.
- `git_index_lock_present`: stop for a separate git-lock decision before committing.
- `required_entries_missing`: restore the missing static entry before any runtime,
  endpoint, launcher, or closeout gate.
- `sanitized_demo_project_missing_or_invalid`: repair sanitized demo metadata only;
  do not substitute real business material.
- `p0_readiness_static_pass`: inspect P0 JSON `failures` first.
- `phase1b_static_demo_workflow_pass`: inspect Phase 1B JSON `failures` first.
- `phase1c_readiness_delivery_index_pass`: inspect Phase 1C JSON `failures` first.
- `docs_presence_complete`: restore README, RUNBOOK, and Phase 1 doc links.

## Hard Gates

Phase 1E does not authorize:

- push, fetch, pull, merge, rebase, squash, reset, clean, checkout, switch, stash,
  tag, release, or PR mutation;
- backend, frontend, launcher, Ollama, browser, or service runtime startup;
- endpoint access including `/health`, `/p0/readiness`, `/openapi.json`, `/list_files`,
  `/read_file`, and business endpoints;
- `.env`, token, secret, password, private key, auth store, or credential content reads;
- real business document body reads or real customer project connection;
- `local-launcher-v1/mock-config.json` content reads or use in launcher/runtime decisions.

## Next Gate

If Phase 1E passes after local commit, the next suggested gate is
`PHASE1_LOCAL_STATIC_BASELINE_CLOSEOUT_READONLY`. That closeout should be readonly
and must not enter Phase 2 code construction automatically.
