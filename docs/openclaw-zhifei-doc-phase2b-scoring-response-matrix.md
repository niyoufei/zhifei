# OpenClaw / Zhifei Doc Phase 2B Scoring Response Matrix

## Purpose

Phase 2B builds a deterministic static scoring response matrix from synthetic
Phase 2 business input metadata. It maps each scoring item to a response
strategy, linked engineering objects, required evidence anchors, Qingtian AI
review-friendly keywords and parse tags, missing-item diagnostics, and an audit
status.

This gate remains synthetic-only. It does not read real tender files, drawings,
bills of quantities, customer materials, secrets, or
`local-launcher-v1/mock-config.json` content. It does not start runtime, visit
endpoints, run launchers, export documents, write formal results, push, fetch,
pull, or merge.

## Matrix Fields

Each matrix row contains:

- `scoring_item_id`: stable scoring item id from synthetic scoring metadata.
- `scoring_title`: synthetic scoring item title.
- `scoring_category`: response category used for grouping later review work.
- `max_score`: numeric score weight, greater than zero.
- `response_strategy`: non-empty static response plan.
- `linked_engineering_objects`: sorted engineering object ids found in the fixture.
- `required_evidence`: sorted evidence metadata anchors.
- `qingtian_keywords`: Qingtian AI review-friendly keywords.
- `qingtian_parse_tags`: Qingtian parse tags for later static review checks.
- `missing_items`: missing or invalid fields detected for that row.
- `audit_status`: `ready_static` or `no_go_static`.
- `traceability_id`: deterministic Phase 2B trace id.

## Synthetic Fixture

The Phase 2B synthetic fixture is:

- `projects/_demo_phase2_scoring_response_matrix/project.json`

It extends the Phase 2A synthetic business input shape with scoring category,
response strategy, Qingtian keywords, and Qingtian parse tags. The fixture uses
mock metadata only and must not be replaced with real tender, drawing, BOQ, or
customer content.

## Static Engine

The engine and CLI are:

- `backend/zhifei_autoplan/phase2_scoring_response_matrix.py`
- `scripts/phase2_scoring_response_matrix.py`

The engine checks:

- required top-level sections and section types;
- required scoring and engineering object fields;
- non-empty scoring items;
- unique scoring item ids;
- numeric positive max scores;
- non-empty response strategies;
- non-empty required evidence;
- linked engineering object ids present in the fixture;
- Qingtian matrix fields present;
- matrix row coverage for all scoring items;
- matrix rows include all contract fields;
- no real-document-body-like fields;
- no secret-like fields;
- false forbidden-action flags.

Clean status:

- `PASS_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC`

Blocked status:

- `NO-GO_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC`

## Commands

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_scoring_response_matrix
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_scoring_response_matrix.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_scoring_response_matrix.py --json
```

These commands are static only. They do not start services, visit endpoints, run
launchers, read held config content, read real business document bodies, read
secret bodies, or refresh remotes.

## Failure Diagnostics

- `synthetic_fixture_missing`: restore the synthetic Phase 2B fixture.
- `synthetic_fixture_invalid_json`: repair fixture JSON syntax only.
- `required_sections_present`: restore the required object groups.
- `required_section_types_valid`: repair list/object shape before matrix generation.
- `required_nested_fields_present`: add missing scoring or engineering metadata fields.
- `synthetic_fixture_declared`: keep `sanitized_demo=true` and `real_business_material=false`.
- `scoring_items_present`: keep at least one synthetic scoring item.
- `scoring_item_ids_unique`: remove duplicate or empty scoring item ids.
- `max_scores_valid`: keep max scores numeric and greater than zero.
- `response_strategies_present`: add non-empty response strategies.
- `required_evidence_present`: add non-empty evidence metadata anchors.
- `linked_engineering_objects_known`: link only to fixture engineering object ids.
- `qingtian_matrix_fields_present`: add category, keywords, and parse tags.
- `matrix_rows_cover_scoring_items`: repair row generation or scoring item ids.
- `matrix_rows_have_required_fields`: restore the Phase 2B matrix field contract.
- `no_real_doc_body_like_fields`: remove body/raw/original/verbatim source fields.
- `no_secret_like_fields`: remove credential-like fields or values.
- `forbidden_action_flags_false`: keep all forbidden-action flags false.

## Phase 2C Relationship

Phase 2C may bind risk objects to matrix rows only after Phase 2B passes and a
separate controller gate authorizes the next phase. Phase 2B does not authorize
runtime, endpoint, launcher, held config content review, real document reads,
export, formal writeback, push, fetch, or merge.

Suggested next gate after Phase 2B local commit:

`PHASE2C_RISK_OBJECT_BINDING_PLAN_OR_WRITE_GATE`
