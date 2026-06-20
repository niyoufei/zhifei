# OpenClaw / Zhifei Doc Phase 2D Qingtian-Friendly Checklist

## Purpose

Phase 2D builds a deterministic static checklist for Qingtian-friendly review
readiness. It checks whether synthetic technical proposal metadata has parseable
keywords, scoring-item coverage, engineering-object bindings, evidence anchors,
risk-control traceability, and diagnosable failure reasons.

This checklist is static and preview-only. It is not a real evaluation result,
does not produce a scoring result, and does not connect to any real Qingtian
system. It does not read real tender files, drawings, bills of quantities,
customer materials, secrets, or `local-launcher-v1/mock-config.json` content. It
does not start runtime, visit endpoints, run launchers, export documents, write
formal results, push, fetch, pull, or merge.

## Checklist Fields

Each checklist row contains:

- `checklist_id`: stable checklist item id.
- `checklist_title`: synthetic checklist title.
- `checklist_category`: readiness category.
- `linked_scoring_item_ids`: scoring item ids found in the Phase 2B matrix.
- `linked_engineering_object_ids`: engineering object ids found in the fixture.
- `linked_risk_ids`: optional Phase 2C risk binding ids.
- `qingtian_keywords`: Qingtian-friendly keywords.
- `qingtian_parse_tags`: Qingtian-friendly parse tags.
- `evidence_requirements`: static evidence metadata anchors.
- `traceability_requirements`: Phase 2B / Phase 2C trace ids.
- `diagnosable_failure_reason`: static reason to report if the checklist fails.
- `severity`: static checklist severity.
- `affects_score`: always false in this preview-only gate.
- `official_score_claim`: always false in this preview-only gate.
- `checklist_status`: `ready_static` or `no_go_static`.
- `audit_traceability_id`: deterministic Phase 2D trace id.

## Synthetic Fixture

The Phase 2D synthetic fixture is:

- `projects/_demo_phase2_qingtian_friendly_checklist/project.json`

It extends the Phase 2C synthetic risk binding fixture with checklist metadata.
The fixture uses mock metadata only and must not be replaced with real tender,
drawing, BOQ, or customer content.

## Static Engine

The engine and CLI are:

- `backend/zhifei_autoplan/phase2_qingtian_friendly_checklist.py`
- `scripts/phase2_qingtian_friendly_checklist.py`

The engine checks:

- required top-level sections and section types;
- required checklist fields;
- synthetic fixture declaration;
- Phase 2B matrix pass status from the same synthetic fixture;
- Phase 2C binding pass status from the same synthetic fixture;
- non-empty checklist items;
- unique checklist ids;
- checklist coverage for every Phase 2B scoring item;
- non-empty Qingtian keywords and parse tags;
- linked scoring item ids present in the Phase 2B matrix;
- linked engineering object ids present in the fixture;
- linked risk ids present in the Phase 2C binding when supplied;
- non-empty evidence and traceability requirements;
- `affects_score=false` and `official_score_claim=false`;
- no score-result-like fields;
- checklist row coverage and required fields;
- no real-document-body-like fields;
- no secret-like fields;
- false forbidden-action flags.

Clean status:

- `PASS_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC`

Blocked status:

- `NO-GO_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC`

## Commands

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_qingtian_friendly_checklist
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_qingtian_friendly_checklist.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_qingtian_friendly_checklist.py --json
```

These commands are static only. They do not start services, visit endpoints, run
launchers, read held config content, read real business document bodies, read
secret bodies, refresh remotes, or connect to a real Qingtian system.

## Failure Diagnostics

- `synthetic_fixture_missing`: restore the synthetic Phase 2D fixture.
- `synthetic_fixture_invalid_json`: repair fixture JSON syntax only.
- `required_sections_present`: restore the required object groups.
- `required_section_types_valid`: repair list/object shape before checklist generation.
- `required_nested_fields_present`: add missing checklist fields.
- `synthetic_fixture_declared`: keep `sanitized_demo=true` and `real_business_material=false`.
- `phase2b_matrix_pass`: repair Phase 2B matrix fields in the same synthetic fixture.
- `phase2c_binding_pass`: repair Phase 2C binding fields in the same synthetic fixture.
- `checklist_items_present`: keep at least one checklist item.
- `checklist_ids_unique`: remove duplicate or empty checklist ids.
- `checklist_covers_scoring_items`: cover every Phase 2B scoring item.
- `qingtian_keywords_present`: add non-empty Qingtian-friendly keywords.
- `qingtian_parse_tags_present`: add non-empty Qingtian-friendly parse tags.
- `linked_scoring_items_known`: link only to Phase 2B matrix scoring item ids.
- `linked_engineering_objects_known`: link only to fixture engineering object ids.
- `linked_risks_known`: link only to Phase 2C risk ids when risk ids are supplied.
- `evidence_requirements_present`: add non-empty evidence anchors.
- `traceability_requirements_present`: add non-empty traceability anchors.
- `affects_score_false`: keep checklist items preview-only with `affects_score=false`.
- `official_score_claim_false`: keep checklist items from claiming a formal score result.
- `no_official_score_like_fields`: remove score-result-like fields.
- `no_real_doc_body_like_fields`: remove body/raw/original/verbatim source fields.
- `no_secret_like_fields`: remove credential-like fields or values.
- `forbidden_action_flags_false`: keep all forbidden-action flags false.

## Phase 2E Relationship

Phase 2E may build a final review issue list only after Phase 2D passes and a
separate controller gate authorizes the next phase. Phase 2D does not authorize
runtime, endpoint, launcher, held config content review, real document reads,
real Qingtian connection, export, formal writeback, push, fetch, or merge.

Suggested next gate after Phase 2D local commit:

`PHASE2E_FINAL_REVIEW_ISSUE_LIST_PLAN_OR_WRITE_GATE`
