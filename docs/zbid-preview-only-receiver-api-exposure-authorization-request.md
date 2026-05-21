# ZBid Preview-Only Receiver API Exposure Authorization Request

## 1. Purpose

This document drafts an authorization request for a future ZBid preview-only receiver API exposure step.

This document is authorization-request-only. It does not authorize ZBid repository access, code changes, service startup, port access, endpoint calls, runtime smoke, real ZDoc/ZBid integration, ZBid writeback, DOCX generation, or `output/job/export` writes.

The future API exposure step must not begin until the user explicitly authorizes it.

## 2. Authorization Request Source

This request is based on:

- Step 209: ZBid preview-only receiver/helper code implementation.
- Step 210: ZBid preview-only receiver code implementation stage review.
- Step 211: ZDoc-ZBid preview-only cross-repository status consolidation.

These prior steps established that the ZBid side currently has a helper-level preview-only receiver, while API exposure and runtime smoke remain incomplete and unauthorized.

## 3. Current Confirmed ZBid Baseline

Current ZBid candidate repository information:

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Current baseline HEAD: `9dabb92854a5f45ec714f405315fa02993891ccc`

Completed ZBid preview-only receiver files:

- `app/engine/zdoc_zbid_preview_receiver.py`
- `tests/test_zdoc_zbid_preview_receiver.py`

Current ZBid receiver state:

- helper-only
- preview-only
- no-write
- no-evidence
- no API exposure
- not connected to formal chains
- not connected to storage
- not connected to writeback

## 4. Proposed Future API Exposure Scope

The future authorized implementation may expose exactly one ZBid-side preview-only receiver API.

Allowed scope should be limited to:

- one preview-only / no-write / no-evidence receive endpoint
- calling only `app/engine/zdoc_zbid_preview_receiver.py`
- receiving only:
  - `preview_packet`
  - `validator_result`
  - `blocked_reasons`
  - no-write / no-formal-chain flags
- returning preview-only / no-write / no-evidence receiver status
- keeping all formal-chain flags false

If `app/main.py` must be modified, that modification must be limited to registering one explicit preview-only route. It must not connect to scoring, evidence, DOCX export, storage, review/apply, writeback, or formal business-data paths.

## 5. Suggested API Boundary

The endpoint name should be explicitly preview-only, for example:

- `POST /local-llm/zdoc-preview-only/receive`

An equivalent name is acceptable only if it clearly communicates preview-only / no-write receiver behavior.

API boundary requirements:

- default disabled / default-off
- when disabled, return a preview-only disabled / no-write response
- do not auto-write database records
- do not write files
- do not create evidence
- do not create score basis records
- do not create qingtian results
- do not call external endpoints
- do not call ZDoc endpoints
- do not call any ZBid writeback endpoint
- do not fallback to formal generation, export, scoring, evidence, storage, or writeback

## 6. Files And Chains That Must Be Avoided

The future API exposure implementation must avoid modifying these files unless the user separately grants explicit file-level authorization:

- `app/engine/evidence.py`
- `app/engine/evidence_units.py`
- `app/engine/scorer.py`
- `app/engine/v2_scorer.py`
- `app/engine/docx_exporter.py`
- `app/storage.py`

The future implementation must avoid these chains:

- `score_text`
- `score_text_v2`
- `export_report_to_docx`
- `save_*` persistence chain
- writeback paths
- storage write paths
- scoring basis write paths
- qingtian results write paths

If `app/main.py` is modified, it must only add the single preview-only receiver route and must not register or expose any formal-chain endpoint.

## 7. Explicitly Forbidden Behavior

The future API exposure step must not:

- trigger `/generate`
- trigger `/export_docx`
- trigger `/review/apply`
- trigger ZBid writeback
- call ZBid writeback APIs
- generate DOCX
- write `output/job/export`
- write ZBid formal business data
- write ZDoc data
- write evidence records
- write scoring basis records
- write qingtian results
- treat advisory as evidence
- treat preview as evidence
- treat shadow output as evidence
- treat patch output as evidence
- treat diff output as evidence
- treat rollback output as evidence
- treat dry-run output as evidence
- start services
- access ports
- call endpoints
- perform runtime smoke unless separately authorized
- enter real ZDoc/ZBid integration
- enter 50-person deployment design

## 8. Proposed Next Step

The proposed next step is:

Step 213: ZBid preview-only receiver API exposure code implementation.

Step 213 must require explicit user authorization before execution. It must not default to service startup, port access, endpoint calls, runtime smoke, cross-system integration, or writeback.

## 9. Suggested Step 213 User Authorization Wording

The user may authorize Step 213 with wording equivalent to:

> I authorize Step 213: ZBid preview-only receiver API exposure code implementation. The authorized ZBid repository path is `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`; the authorized branch is `local-llm-integration-clean`; the required starting HEAD is `9dabb92854a5f45ec714f405315fa02993891ccc`; the worktree must be clean before starting. The allowed file scope is limited to the minimum files needed to expose one preview-only/no-write/no-evidence receiver route, preferably using `app/engine/zdoc_zbid_preview_receiver.py`; if `app/main.py` must be modified, it may only register one explicit preview-only receive endpoint. The implementation must not start services, access ports, call endpoints, run smoke, trigger `/generate`, `/export_docx`, `/review/apply`, ZBid writeback, DOCX generation, evidence writes, storage writes, score writes, or `output/job/export` writes.

If the future Step 213 preflight finds a different path, branch, HEAD, or non-clean worktree, it must stop and report the mismatch.

## 10. Safety Conclusion

This document only drafts the authorization request for a future ZBid preview-only receiver API exposure step.

It does not authorize Step 213 by itself. Any future API exposure must remain preview-only, no-write, no-evidence, default-off, and disconnected from formal scoring, evidence, DOCX export, storage, review/apply, writeback, runtime smoke, and real ZDoc/ZBid integration unless separately authorized.
