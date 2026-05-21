# ZDoc-ZBid Preview-Only Cross-Repository Status Consolidation

## 1. Scope

This document consolidates the current cross-repository status for the ZDoc and ZBid preview-only integration track.

This step is ZDoc docs-only / cross-repo-status-only. It does not modify code, tests, frontend files, existing docs, services, ports, APIs, writeback paths, `output/job/export`, or deployment design.

This document is a status record only. It does not authorize API exposure, service startup, endpoint calls, cross-system runtime smoke, real ZDoc/ZBid integration, or any writeback behavior.

## 2. ZDoc Current State

ZDoc repository:

- Path: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Current baseline HEAD before this consolidation: `4f88cef544d07f1a101a53316af0e0ceeed6425e`

ZDoc completed preview-only capabilities:

- `/local-trial/preview-only` backend route has been implemented.
- The frontend same-origin proxy for `/local-trial/preview-only` has been implemented.
- The frontend can dynamically display:
  - `preview_packet`
  - `validator_result`
  - `blocked_reasons`
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- The ZDoc-side default-off preview-only outbound adapter has been implemented.

ZDoc status remains preview-only and no-write. It does not authorize formal generation, DOCX export, review/apply, ZBid writeback, formal writeback, or output writes.

## 3. ZBid Current State

ZBid candidate repository:

- Path: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Step 209 receiver implementation HEAD: `54ce21fdad53bcda0cadd40711dd691499d316d1`
- Step 210 stage review HEAD: `9dabb92854a5f45ec714f405315fa02993891ccc`

ZBid completed preview-only receiver work:

- Added `app/engine/zdoc_zbid_preview_receiver.py`
- Added `tests/test_zdoc_zbid_preview_receiver.py`

The ZBid receiver is currently only a preview-only helper. It:

- receives preview-only metadata payloads
- normalizes `preview_packet`
- normalizes `validator_result`
- normalizes `blocked_reasons`
- preserves no-write / no-formal-chain flags
- returns preview-only / no-write / no-evidence status

The ZBid receiver does not:

- expose an API
- start services
- access ports
- call endpoints
- write business data
- write back to ZDoc
- produce evidence
- produce writeback
- connect to the scoring chain
- connect to the evidence chain
- connect to the DOCX export chain
- connect to the storage chain
- connect to any formal writeback chain

## 4. Completed Preview-Only Loop Evidence

The following preview-only loops have been completed:

- ZDoc preview-only route runtime smoke passed.
- ZDoc frontend same-origin proxy controlled smoke passed.
- ZDoc frontend dynamic display of `preview_packet`, `validator_result`, `blocked_reasons`, and five false flags passed.
- ZDoc outbound adapter unit tests passed.
- ZBid receiver/helper unit tests passed.

These completed loops are limited to preview-only and no-write validation. They do not prove or authorize formal generation, DOCX export, review/apply, ZBid writeback, or real cross-system production integration.

## 5. Not Yet Completed

The following items remain incomplete:

- ZBid preview-only receiver API has not been exposed.
- ZDoc -> ZBid cross-system runtime smoke has not been performed.
- Real ZDoc/ZBid integration has not been performed.
- ZBid writeback has not been authorized.
- ZBid formal business-data writeback has not been authorized.
- ZDoc formal writeback has not been authorized.
- DOCX export has not been opened.
- review/apply has not been opened.
- `/generate` has not been opened.
- 50-person deployment design has not been started.

## 6. Strict Boundary

The following actions remain forbidden unless a later step grants separate explicit authorization:

- Trigger `/generate`
- Trigger `/export_docx`
- Trigger `/review/apply`
- Trigger ZBid writeback
- Call any ZBid endpoint
- Generate DOCX
- Write `output/job/export`
- Enter formal generation chain
- Enter DOCX export chain
- Enter review/apply chain
- Enter evidence promotion chain
- Enter scoring basis write path
- Enter storage write path
- Enter qingtian results write path
- Enter real ZDoc/ZBid integration
- Enter 50-person deployment design

Advisory, preview, shadow, patch, diff, rollback, and dry-run outputs must not be treated as evidence.

## 7. Current Cross-Repository Interpretation

The current cross-repository state is:

- ZDoc can construct and display preview-only metadata locally.
- ZDoc can prepare default-off preview-only outbound metadata without sending network requests.
- ZBid can receive and validate a preview-only metadata payload at helper level.
- ZBid cannot yet receive that payload through an exposed service API.
- ZDoc and ZBid have not yet performed a live cross-system preview-only runtime smoke.

This is a staged preview-only integration foundation, not a real writeback integration.

## 8. Recommended Next Steps

Possible next steps:

- Step 212 may draft a ZBid preview-only receiver API exposure authorization request.
- Alternatively, Step 212 may draft a ZDoc-ZBid preview-only cross-system smoke authorization request if API exposure is already separately planned.

Any of the following require separate explicit authorization before execution:

- API exposure
- service startup
- port access
- endpoint calls
- cross-system runtime smoke
- real ZDoc/ZBid integration
- writeback-related behavior

## 9. Safety Conclusion

The ZDoc side currently has a preview-only route, same-origin frontend proxy, dynamic frontend display, and default-off outbound adapter.

The ZBid side currently has a preview-only receiver/helper and focused unit tests.

The cross-repository state is ready for a future authorization request around API exposure or controlled preview-only smoke, but it is not ready for writeback, formal generation, DOCX export, review/apply, evidence promotion, or 50-person deployment design.

This step stops at cross-repository status consolidation and does not enter Step 212.
