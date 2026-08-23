# SYSTEM-AUTONOMY-009 Implementation Static Guard Scope Correction

## Node

- Node ID: `SYSTEM-AUTONOMY-009-IMPLEMENTATION-STATIC-GUARD-SCOPE-CORRECTION-NO-RUNTIME`
- Baseline HEAD: `8e27a0702c3984773c309b2c1fc6b697d9b0bf6e`
- Baseline tag: `v0.1.662-system-autonomy-009-scope-authorization-gate`

## Authorized Scope

The static changed-file allowlist is advanced to this node only:

- `backend/zhifei_autoplan/system_autonomy_static_guard.py`
- `backend/tests/test_system_autonomy_static_guard.py`
- `docs/zdoc-system-autonomy-009-implementation-static-guard-scope-correction-no-runtime.md`

Legacy `SYSTEM-AUTONOMY-008` documentation is no longer part of the static changed-file allowlist.

## Implementation Summary

- Updated `AUTHORIZED_CHANGED_FILES` to include the `SYSTEM-AUTONOMY-009` implementation record.
- Updated the changed-file rejection reason to `changed_file_outside_system_autonomy_009_static_guard_scope`.
- Updated the focused static guard tests to assert the `009` allowlist and reject the prior `008` implementation record.

## Verification

Required verification commands for this node:

- `python3 -B -m py_compile backend/zhifei_autoplan/system_autonomy_static_guard.py`
- `python3 -m pytest -q backend/tests/test_system_autonomy_static_guard.py`
- `git diff --check`

No runtime service, endpoint probing, model command, prompt input, live knowledge graph, real project data, secret material, generated output, job, export, or log workflow is required by this node.
