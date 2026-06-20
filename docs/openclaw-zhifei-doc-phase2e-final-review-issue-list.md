# OpenClaw / Zhifei Doc Phase 2E Final Review Issue List

## Purpose

Phase 2E builds a deterministic static final review issue list. It combines the
Phase 2A business input contract, Phase 2B scoring response matrix, Phase 2C
risk-object binding, and Phase 2D Qingtian-friendly checklist into preview-only
review issues.

The issue list is not a formal final review conclusion. It does not write back
files, export deliverables, generate an official score, connect to a real
Qingtian system, read real tender files, drawings, bills of quantities, customer
materials, secrets, or `local-launcher-v1/mock-config.json` content. It does not
start runtime, visit endpoints, run launchers, push, fetch, pull, or merge.

## Issue Item Contract

Each final review issue item contains:

- `issue_id`: stable issue id.
- `issue_title`: static review issue title.
- `issue_category`: issue category such as contract, traceability, parseability,
  or hard-gate boundary.
- `severity`: one of `info`, `low`, `medium`, `high`, or `blocking`.
- `source_phase`: one of `P2A`, `P2B`, `P2C`, `P2D`, or `cross_phase`.
- `linked_scoring_item_ids`: scoring item ids found in the Phase 2B matrix.
- `linked_engineering_object_ids`: engineering object ids found in the fixture.
- `linked_risk_ids`: risk ids found in the Phase 2C binding.
- `linked_checklist_ids`: checklist ids found in the Phase 2D checklist.
- `issue_reason`: non-empty deterministic issue reason.
- `diagnostic_evidence`: non-empty static evidence notes.
- `recommended_action`: non-empty next action for a reviewer.
- `responsible_review_role`: review role responsible for inspecting the item.
- `review_status`: `pass_static`, `warning_static`, or `blocking_static`.
- `blocking_level`: `pass`, `warning`, or `blocking`.
- `audit_traceability_id`: deterministic Phase 2E trace id.
- `formal_writeback_allowed`: always false.
- `export_allowed`: always false.
- `official_score_claim`: always false.

## Synthetic Fixture

The Phase 2E synthetic fixture is:

- `projects/_demo_phase2_final_review_issue_list/project.json`

It reuses the static Phase 2A through Phase 2D synthetic chain and adds
`final_review_issue_metadata`. The fixture uses mock metadata only and must not
be replaced with real tender, drawing, BOQ, or customer content.

## Static Engine

The engine and CLI are:

- `backend/zhifei_autoplan/phase2_final_review_issue_list.py`
- `scripts/phase2_final_review_issue_list.py`

The engine checks:

- required top-level sections and section types;
- required final review issue fields;
- synthetic fixture declaration;
- Phase 2A, Phase 2B, Phase 2C, and Phase 2D static pass statuses from the same
  synthetic fixture;
- non-empty issue items;
- unique issue ids;
- presence of pass, warning, and blocking issue classes;
- allowed severity and source phase values;
- known linked scoring item, engineering object, risk, and checklist ids;
- non-empty issue reason, diagnostic evidence, and recommended action;
- valid review status and blocking level values;
- `formal_writeback_allowed=false`, `export_allowed=false`, and
  `official_score_claim=false`;
- no score-result-like fields;
- issue row coverage and required fields;
- no real-document-body-like fields;
- no secret-like fields;
- false forbidden-action flags.

Clean status:

- `PASS_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC`

Blocked status:

- `NO-GO_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC`

## Commands

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_final_review_issue_list
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_final_review_issue_list.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_final_review_issue_list.py --json
```

These commands are static only. They do not start services, visit endpoints, run
launchers, read held config content, read real business document bodies, read
secret bodies, export files, write formal results, refresh remotes, or connect
to a real Qingtian system.

## Failure Diagnostics

- `synthetic_fixture_missing`: restore the synthetic Phase 2E fixture.
- `synthetic_fixture_invalid_json`: repair fixture JSON syntax only.
- `required_sections_present`: restore the required object groups.
- `required_section_types_valid`: repair list/object shape before issue
  generation.
- `required_nested_fields_present`: add missing issue fields.
- `synthetic_fixture_declared`: keep `sanitized_demo=true` and
  `real_business_material=false`.
- `phase2a_contract_pass`: repair Phase 2A contract fields in the same fixture.
- `phase2b_matrix_pass`: repair Phase 2B matrix fields in the same fixture.
- `phase2c_binding_pass`: repair Phase 2C binding fields in the same fixture.
- `phase2d_checklist_pass`: repair Phase 2D checklist fields in the same
  fixture.
- `issue_items_present`: keep at least one final review issue item.
- `issue_ids_unique`: remove duplicate or empty issue ids.
- `issue_levels_cover_pass_warning_blocking`: keep pass, warning, and blocking
  issue classes represented.
- `severity_values_valid`: use only `info`, `low`, `medium`, `high`, or
  `blocking`.
- `source_phases_valid`: use only `P2A`, `P2B`, `P2C`, `P2D`, or
  `cross_phase`.
- `linked_scoring_items_known`: link only to Phase 2B matrix scoring item ids.
- `linked_engineering_objects_known`: link only to fixture engineering object
  ids.
- `linked_risks_known`: link only to Phase 2C risk ids.
- `linked_checklists_known`: link only to Phase 2D checklist ids.
- `issue_reason_present`: add a non-empty issue reason.
- `diagnostic_evidence_present`: add non-empty diagnostic evidence.
- `recommended_action_present`: add a non-empty reviewer action.
- `review_statuses_valid`: use the static review status enum.
- `blocking_levels_valid`: use `pass`, `warning`, or `blocking`.
- `formal_writeback_allowed_false`: keep every issue preview-only.
- `export_allowed_false`: keep every issue non-exporting.
- `official_score_claim_false`: keep every issue from claiming a score result.
- `no_official_score_like_fields`: remove score-result-like fields.
- `no_real_doc_body_like_fields`: remove body/raw/original/verbatim source
  fields.
- `no_secret_like_fields`: remove credential-like fields or values.
- `forbidden_action_flags_false`: keep all forbidden-action flags false.

## Phase 2F Relationship

Phase 2F may build an output pre-index only after Phase 2E passes, is committed
locally, and a separate controller gate authorizes the next phase. Phase 2E does
not authorize runtime, endpoint, launcher, held config content review, real
document reads, real Qingtian connection, export, formal writeback, push, fetch,
or merge.

Suggested next gate after Phase 2E local commit:

`PHASE2F_OUTPUT_PRE_INDEX_PLAN_OR_WRITE_GATE`

## Static Handoff Update

When a later controller explicitly authorizes Phase 2F, the Phase 2E issue ids
and static boundary flags may be referenced by the Phase 2F output pre-index.
This handoff does not alter Phase 2E's verified conclusion: Phase 2E remains a
preview-only final review issue list and still does not authorize runtime,
endpoint, launcher, held config content review, real document reads, real
Qingtian connection, export, formal writeback, push, fetch, or merge.
