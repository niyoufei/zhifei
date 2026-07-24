# OpenClaw / Zhifei Doc Phase 2A Business Input Contract

## Purpose

Phase 2A defines the static business input contract for the Phase 2 business
engine. It adds a synthetic-only fixture and a no-runtime validator that can be
used before any scoring response matrix, risk binding, Qingtian AI review check,
final review issue list, or output-center pre-index work.

This gate does not read real tender files, drawings, bills of quantities, customer
materials, secrets, or `local-launcher-v1/mock-config.json` content. It does not
start runtime, visit endpoints, run launchers, export documents, write formal
results, push, fetch, pull, or merge.

## Business Input Objects

The Phase 2A contract uses these object groups:

- `project_metadata`: project id, synthetic project name, project type, location,
  and synthetic demo flags.
- `tender_metadata`: tender reference metadata, version, evaluation method, and
  summarized technical or format requirements.
- `scoring_item_metadata`: scoring item id, name, max score, requirement summary,
  evidence need, and related engineering object ids.
- `engineering_object_metadata`: synthetic road, drainage, bridge, structure, or
  other engineering object metadata.
- `risk_clue_metadata`: risk id, risk type, risk hint, related engineering object
  ids, and expected response mode.
- `output_intent_metadata`: intended static outputs, with export and formal
  writeback flags fixed false.
- `audit_boundary_metadata`: snapshot id, schema version, hash mode, human review
  requirement, and next-gate hint.
- `qingtian_ai_review_metadata`: evaluation-friendly and evidence-anchor fields
  used later by Qingtian AI review checks.
- `safety_boundary`: false flags for runtime, endpoint, launcher, held config body,
  real business document body, secret body, remote sync, export, and formal writeback.

## Synthetic Fixture

The first synthetic fixture is:

- `projects/_demo_phase2_business_input/project.json`

It represents a synthetic Hefei municipal road project with mock tender metadata,
scoring items, engineering objects, risk clues, Qingtian AI review-friendly fields,
and no real business material. The fixture is safe for deterministic static tests
and must not be replaced with real tender, drawing, BOQ, or customer content.

## Static Validator

The validator is:

- `backend/zhifei_autoplan/phase2_business_input_contract.py`
- `scripts/phase2_business_input_contract.py`

It checks:

- required top-level sections;
- required nested fields;
- section field types;
- synthetic fixture declaration;
- no real-document-body-like fields;
- no secret-like fields;
- false forbidden-action flags;
- Qingtian AI review metadata presence.

Clean status:

- `PASS_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC`

Blocked status:

- `NO-GO_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC`

## Commands

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_business_input_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_business_input_contract.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_business_input_contract.py --json
```

These commands are static only. They do not start services, visit endpoints, run
launchers, read held config content, read real business document bodies, read
secret bodies, or refresh remotes.

## Failure Diagnostics

- `synthetic_fixture_missing`: restore the synthetic Phase 2A fixture.
- `synthetic_fixture_invalid_json`: repair fixture JSON syntax only.
- `required_sections_present`: restore the required object groups.
- `required_section_types_valid`: repair list/object shape before Phase 2B.
- `required_nested_fields_present`: add missing metadata fields.
- `synthetic_fixture_declared`: keep `sanitized_demo=true` and `real_business_material=false`.
- `no_real_doc_body_like_fields`: remove body/raw/original/verbatim source fields.
- `no_secret_like_fields`: remove credential-like fields or values.
- `forbidden_action_flags_false`: keep all forbidden-action flags false.
- `qingtian_fields_present`: restore Qingtian AI review metadata fields.

## Phase 2B Relationship

Phase 2B builds the scoring item extraction and response matrix on top of this
static contract. The Phase 2B contract and validator live in:

- `docs/openclaw-zhifei-doc-phase2b-scoring-response-matrix.md`
- `projects/_demo_phase2_scoring_response_matrix/project.json`
- `backend/zhifei_autoplan/phase2_scoring_response_matrix.py`
- `scripts/phase2_scoring_response_matrix.py`

Phase 2B must remain synthetic-only until a later gate authorizes broader data
use. It must not infer permission for runtime, endpoint, launcher, held config
content review, real document reads, export, formal writeback, push, fetch, or
merge.

Suggested next gate after Phase 2A local commit:

`PHASE2B_SCORING_RESPONSE_MATRIX_PLAN_OR_WRITE_GATE`
