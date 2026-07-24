# OpenClaw / Zhifei Doc Phase 2F Output Pre-Index

## Purpose

Phase 2F builds a deterministic static output pre-index. It does not generate
reports, files, delivery packages, official scores, or formal writeback. It only
describes future output entries that may be requested by later gates after Phase
2 closeout.

The pre-index is preview-only metadata. It does not start runtime, visit
endpoints, run launchers, read real tender files, drawings, bills of quantities,
customer materials, secrets, or `local-launcher-v1/mock-config.json` content.

## Input Boundary

The Phase 2F engine reads only a synthetic fixture and existing static Phase 2A
through Phase 2E validators. The default fixture is:

- `projects/_demo_phase2_output_pre_index/project.json`

The fixture is mock metadata only. It is not a real project input and must not be
replaced with real tender, drawing, BOQ, or customer content in this phase.

## Output Entry Contract

Each output pre-index entry contains:

- `output_id`: stable output index id.
- `output_type`: one of the declared output type enum values.
- `title`: human-readable static title.
- `source_phase`: `P2A`, `P2B`, `P2C`, `P2D`, `P2E`, or `cross_phase`.
- `source_inputs`: static upstream references.
- `intended_consumer`: later reviewer or controller role.
- `allowed_format_descriptor`: terminal preview metadata only in this phase.
- `export_status`: `blocked` or `preview_only`.
- `writeback_status`: not `performed`.
- `official_score_status`: not `generated`.
- `artifact_generation_status`: not `generated`.
- `data_boundary`: synthetic-only boundary flags.
- `trace_links`: refs traceable to Phase 2A through Phase 2E or synthetic fixture.
- `blocker_reason`: reason formal output remains blocked.

## Output Type Enum

Phase 2F covers:

- `final_review_report`
- `scoring_matrix`
- `issue_list`
- `audit_index`
- `delivery_package_index`
- `handoff_summary`
- `evidence_trace_index`

## Blocking Rules

The engine enforces these static rules:

- export blocked;
- file artifact generation blocked;
- formal writeback blocked;
- official score blocked;
- real business document body blocked;
- held config body blocked;
- runtime and endpoint blocked;
- secret material blocked.

The CLI prints terminal preview text or JSON-like metadata only. It must not
write DOCX, PDF, Excel, PPTX, HTML, Markdown deliverables, or any formal output
artifact.

## Static Engine

The engine and CLI are:

- `backend/zhifei_autoplan/phase2_output_pre_index.py`
- `scripts/phase2_output_pre_index.py`

The engine checks:

- required output entry fields;
- output type enum validity and enum coverage;
- export status is `blocked` or `preview_only`;
- formal writeback is not performed;
- official score is not generated;
- file artifact generation is not generated;
- data boundary does not claim held config body, real business body, runtime,
  endpoint, or secret reads;
- trace links are present and known to Phase 2A through Phase 2E or synthetic
  fixture objects;
- upstream Phase 2A, 2B, 2C, 2D, and 2E static validators pass on the same
  synthetic fixture;
- readable validation errors are returned for missing fields and blocked claims.

Clean status:

- `PASS_PHASE2F_OUTPUT_PRE_INDEX_STATIC`

Blocked status:

- `NO-GO_PHASE2F_OUTPUT_PRE_INDEX_STATIC`

## Commands

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_output_pre_index
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_output_pre_index.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_output_pre_index.py --json
```

These commands are static only. They do not start services, visit endpoints, run
launchers, read held config content, read real business document bodies, read
secret material, export files, write formal results, refresh remotes, or connect
to a real Qingtian system.

## Phase 2E Handoff

Phase 2E supplies the final review issue list and blocking issue ids used by the
Phase 2F pre-index. Phase 2F does not change Phase 2E conclusions. It adds only
the next static layer: future output categories and traceable preview metadata.

## Closeout and Phase 3 Boundary

Phase 2F passing is not release-ready, not official-score-ready, and not a real
document ingestion approval. Before Phase 3, a separate Phase 2 closeout must
run as a read-only gate and confirm the committed static scope, forbidden-action
boundary, and traceability chain.
