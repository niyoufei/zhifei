# OpenClaw / Zhifei Doc Phase 2C Risk Object Binding

## Purpose

Phase 2C builds deterministic static bindings from synthetic risk clues to
engineering objects, Phase 2B scoring matrix rows, response controls, evidence
requirements, Qingtian tags, and audit traceability. It uses the synthetic
business input shape from Phase 2A and the Phase 2B matrix contract as static
inputs.

This gate remains synthetic-only. It does not read real tender files, drawings,
bills of quantities, customer materials, secrets, or
`local-launcher-v1/mock-config.json` content. It does not start runtime, visit
endpoints, run launchers, export documents, write formal results, push, fetch,
pull, or merge.

## Binding Fields

Each binding row contains:

- `risk_id`: stable risk binding id.
- `risk_title`: synthetic risk title.
- `risk_category`: risk grouping used for later checklist review.
- `risk_level`: one of `low`, `medium`, `high`, or `critical`.
- `risk_clue_id`: source risk clue id.
- `linked_engineering_object_ids`: sorted engineering object ids found in the fixture.
- `linked_scoring_item_ids`: sorted scoring item ids found in the Phase 2B matrix.
- `response_control_points`: sorted response-control metadata anchors.
- `required_evidence`: sorted evidence metadata anchors.
- `qingtian_tags`: sorted Qingtian-friendly tags.
- `audit_traceability_id`: deterministic Phase 2C trace id.
- `binding_status`: `ready_static` or `no_go_static`.
- `diagnostics`: missing or invalid binding fields.

## Synthetic Fixture

The Phase 2C synthetic fixture is:

- `projects/_demo_phase2_risk_object_binding/project.json`

It extends the Phase 2B synthetic matrix fixture with risk level, risk title,
linked scoring item ids, response control points, required evidence, Qingtian
tags, and binding-ready risk metadata. The fixture uses mock metadata only and
must not be replaced with real tender, drawing, BOQ, or customer content.

## Static Engine

The engine and CLI are:

- `backend/zhifei_autoplan/phase2_risk_object_binding.py`
- `scripts/phase2_risk_object_binding.py`

The engine checks:

- required top-level sections and section types;
- required risk binding fields;
- synthetic fixture declaration;
- Phase 2B matrix pass status from the same synthetic fixture;
- non-empty risk clues;
- unique risk ids;
- risk level enum values;
- linked engineering object ids present in the fixture;
- linked scoring item ids present in the Phase 2B matrix;
- non-empty response control points;
- non-empty required evidence;
- non-empty Qingtian tags;
- binding row coverage for all risk clues;
- binding rows include all contract fields;
- no real-document-body-like fields;
- no secret-like fields;
- false forbidden-action flags.

Clean status:

- `PASS_PHASE2C_RISK_OBJECT_BINDING_STATIC`

Blocked status:

- `NO-GO_PHASE2C_RISK_OBJECT_BINDING_STATIC`

## Commands

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_risk_object_binding
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_risk_object_binding.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_risk_object_binding.py --json
```

These commands are static only. They do not start services, visit endpoints, run
launchers, read held config content, read real business document bodies, read
secret bodies, or refresh remotes.

## Failure Diagnostics

- `synthetic_fixture_missing`: restore the synthetic Phase 2C fixture.
- `synthetic_fixture_invalid_json`: repair fixture JSON syntax only.
- `required_sections_present`: restore the required object groups.
- `required_section_types_valid`: repair list/object shape before binding generation.
- `required_nested_fields_present`: add missing risk binding fields.
- `synthetic_fixture_declared`: keep `sanitized_demo=true` and `real_business_material=false`.
- `phase2b_matrix_pass`: repair Phase 2B matrix fields in the same synthetic fixture.
- `risk_clues_present`: keep at least one synthetic risk clue.
- `risk_ids_unique`: remove duplicate or empty risk ids.
- `risk_levels_valid`: use only `low`, `medium`, `high`, or `critical`.
- `linked_engineering_objects_known`: link only to fixture engineering object ids.
- `linked_scoring_items_known`: link only to Phase 2B matrix scoring item ids.
- `response_control_points_present`: add non-empty response controls.
- `required_evidence_present`: add non-empty evidence metadata anchors.
- `qingtian_tags_present`: add non-empty Qingtian-friendly tags.
- `binding_rows_cover_risk_clues`: repair row generation or risk ids.
- `binding_rows_have_required_fields`: restore the Phase 2C binding field contract.
- `no_real_doc_body_like_fields`: remove body/raw/original/verbatim source fields.
- `no_secret_like_fields`: remove credential-like fields or values.
- `forbidden_action_flags_false`: keep all forbidden-action flags false.

## Phase 2D Relationship

Phase 2D may build a static, preview-only Qingtian-friendly checklist only after
Phase 2C passes and a separate controller gate authorizes the next phase. The
Phase 2D contract and validator live in:

- `docs/openclaw-zhifei-doc-phase2d-qingtian-friendly-checklist.md`
- `projects/_demo_phase2_qingtian_friendly_checklist/project.json`
- `backend/zhifei_autoplan/phase2_qingtian_friendly_checklist.py`
- `scripts/phase2_qingtian_friendly_checklist.py`

Phase 2D must not be treated as a real evaluation result. Phase 2C does not
authorize runtime, endpoint, launcher, held config content review, real document
reads, real Qingtian connection, export, formal writeback, push, fetch, or
merge.

Suggested next gate after Phase 2C local commit:

`PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_PLAN_OR_WRITE_GATE`
