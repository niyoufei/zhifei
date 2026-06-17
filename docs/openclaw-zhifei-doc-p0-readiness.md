# OpenClaw / Zhifei Doc P0 Readiness

This document defines the first local-only P0 implementation surface.

## Boundary

- Does not start backend, frontend, launcher, Ollama, or any runtime.
- Does not visit `/health`, `/config`, `/openapi.json`, `/list_files`, `/read_file`, or business endpoints.
- Does not fetch, pull, merge, push, tag, release, or update remote refs.
- Does not read `.env`, credential-like files, auth source contents, mock config contents, or real business document bodies.
- Reports sensitive and real-data locations by path category only.

## Static Readiness Command

```bash
python3 scripts/p0_readiness.py --json
```

The command returns a P0 snapshot containing:

- local git state from existing refs only;
- required backend, workbench, launcher, script, test, and dependency entries;
- sanitized demo project availability;
- log diagnostic path availability without reading log contents;
- real data directory path categories without reading contents;
- forbidden-action negative proof.

## Status And Failures

The snapshot status has two expected values:

- `PASS_P0_READINESS_STATIC`: static local readiness checks passed. This is only a readiness signal for the next controlled gate.
- `NO-GO_P0_READINESS_STATIC`: one or more `failures` entries blocked static readiness.

The `failures` field is the reason list. Examples include:

- `required_entries_missing`: one or more required P0 files or entrypoints are absent.
- `sanitized_demo_project_missing_or_invalid`: the P0 sanitized demo is missing or does not declare the required safe metadata.
- `git_index_lock_present`: `.git/index.lock` exists and must be resolved before a clean gate.
- `worktree_not_clean`: git porcelain output is non-empty.

When P0 implementation files are present but not yet committed or otherwise closed out, `NO-GO_P0_READINESS_STATIC` with `worktree_not_clean` is expected. It proves the gate is refusing to treat an unclosed worktree as ready.

After the worktree is clean, rerun:

```bash
python3 scripts/p0_readiness.py --json
```

The clean-worktree acceptance condition is `status` equal to `PASS_P0_READINESS_STATIC`, `failures` empty, required entries present, the sanitized demo valid, and all boundary flags still false for runtime, endpoints, secrets, real business content, and remote ref refresh.

## Sanitized Demo

The demo project is `projects/_demo_p0/project.json`.

It is metadata-only and declares:

- `sanitized_demo: true`
- `real_business_material: false`
- `external_network_required: false`
- `secret_required: false`

## Next Gate

Runtime startup, endpoint smoke, launcher execution, and real output generation remain a separate P0 controlled runtime/endpoint smoke gate.

Endpoint smoke testing is not authorized by this static gate. Access to `/health`, `/p0/readiness`, `/openapi.json`, `/list_files`, `/read_file`, or business endpoints requires a separate runtime/endpoint gate.
