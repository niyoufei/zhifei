# ZDoc Preview-Only Route Frontend Integration Plan Fake Schema Stage Review

## 1. Scope

This document archives the Step 187 fake schema tests for the preview-only route frontend integration plan.

Step 188 is docs-only. It does not modify code, tests, frontend files, existing docs, backend routes, configuration, deployment scripts, or runtime files. It does not run pytest, start backend or frontend services, run Ollama, access ports, trigger `/generate`, trigger `/export_docx`, trigger `/review/apply`, call ZBid, write `output/job/export`, enter real ZDoc/ZBid integration, or enter the 50-person deployment design.

## 2. File Added In Step 187

Step 187 added one tests-only fake schema file:

- `backend/tests/test_preview_only_route_frontend_integration_plan_schema.py`

Step 187 did not modify:

- Production code
- Frontend code
- Existing tests
- Existing docs
- Backend formal generation chain
- DOCX export chain
- Review/apply chain
- ZBid writeback chain
- `output/job/export`
- Configuration or deployment scripts

## 3. Step 187 Test Evidence

Step 187 ran and passed the required checks:

- Single-file fake schema test:
  - `python -m pytest backend/tests/test_preview_only_route_frontend_integration_plan_schema.py -vv`
  - Result: 11 passed

- Frontend integration plan + route plan + route tests:
  - `python -m pytest backend/tests/test_preview_only_route_frontend_integration_plan_schema.py backend/tests/test_local_trial_preview_only_route_implementation_plan_schema.py backend/tests/test_local_trial_preview_only_route.py -vv`
  - Result: 29 passed

- Import-isolation combination:
  - `python -m pytest backend/tests/test_preview_only_route_frontend_integration_plan_schema.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - Result: 14 passed

- `git diff --check`
  - Result: passed

## 4. Coverage Summary

Step 187 fixed the Step 186 frontend integration plan as deterministic fake schema coverage.

The tests explicitly covered the required frontend integration plan sections:

- `current_baseline`
- `frontend_integration_goal`
- `frontend_state_display_design`
- `forbidden_behaviors`
- `future_code_scope`
- `acceptance_criteria`
- `next_steps`

The tests also confirmed that the fake schema remains deterministic and side-effect free.

## 5. Baseline Coverage Confirmed

Step 187 fixed the current baseline:

- `/local-trial/preview-only` has been implemented.
- The route runtime smoke has passed.
- `preview_packet` is readable.
- `validator_result` is readable.
- `blocked_reasons` is readable.
- The five formal chain flags remain false.
- The frontend no-write UI has been repaired.
- The frontend no-write UI has passed screenshot-level visual smoke.

The tests also keep the current gap explicit:

- The frontend does not yet call `/local-trial/preview-only`.
- Real ZDoc/ZBid integration has not been entered.
- Formal generation, DOCX export, review/apply, ZBid writeback, and output writes remain closed.

## 6. Frontend Integration Plan Contract Locked

Step 187 fixed the future frontend integration goal:

- The frontend must only call `/local-trial/preview-only`.
- The frontend must only display preview-only metadata.
- The frontend must display `preview_packet`.
- The frontend must display `validator_result`.
- The frontend must display `blocked_reasons`.
- The frontend must display `preview-only`.
- The frontend must display `no-write`.
- The frontend must display that advisory content is not evidence.
- The frontend must display that preview content is not formal正文.
- The frontend must not trigger formal generation.
- The frontend must not trigger DOCX export.
- The frontend must not trigger review/apply.
- The frontend must not trigger ZBid writeback.

## 7. State Display Boundary Locked

Step 187 fixed the frontend state display requirements:

- Preview-only state must be visible.
- No-write state must be visible.
- Validator states must be visible:
  - `accepted_preview_only`
  - `blocked`
  - `requires_human_review`
- `blocked_reasons` must be visible and readable.
- Evidence boundary copy must be visible.
- Scoring refs and tender refs must be read-only.
- The five formal chain flags must display as false.

The tests preserve the distinction between preview metadata and formal output.

## 8. Forbidden Behaviors Locked

Step 187 fixed the following forbidden frontend behaviors:

- Do not call `/generate`.
- Do not call `/export_docx`.
- Do not call `/review/apply`.
- Do not call ZBid API / DB / writeback.
- Do not trigger formal writeback.
- Do not write `output/job/export`.
- Do not generate DOCX.
- Do not treat advisory as evidence.
- Do not treat preview as formal正文.
- Do not treat `accepted_preview_only` as writeback permission.

## 9. Formal Flags Confirmed False

The fake schema tests fixed all five formal chain flags as false:

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

These flags are expected to remain false in the future frontend integration until a separate, explicit authorization changes the project stage.

## 10. No-Write And Import-Isolation Boundary

Step 187 tests confirmed no execution side effects in the fake schema plan:

- Backend not started
- Frontend not started
- Ollama not run
- Local port not accessed
- Network not called
- `output/job/export` not written
- DOCX not generated
- ZBid not called
- `/generate` not triggered
- `/export_docx` not triggered
- `/review/apply` not triggered
- Real ZDoc/ZBid integration not entered
- 50-person deployment design not entered

The import-isolation test also prevents the fake schema test file from importing the main chain or service modules, including:

- `orchestrator`
- `llm_client`
- `provider`
- `generation`
- `export`
- `review`
- `actions_bridge`
- `zbid`
- `FastAPI`
- `requests`
- `httpx`
- `Ollama`
- `docx` / `python-docx`

## 11. Unimplemented Items

The following items remain unimplemented:

- Frontend has not yet been updated to call `/local-trial/preview-only`.
- Frontend-to-route integration smoke has not been executed.
- Real ZDoc/ZBid integration has not been entered.
- Formal generation has not been opened.
- DOCX export has not been opened.
- Review/apply has not been opened.
- ZBid writeback has not been opened.
- Formal writeback has not been opened.
- `output/job/export` writes have not been opened.

## 12. Risk And Limitation Assessment

No high risk is introduced by Step 187 because the work was tests-only and fake schema only.

Remaining risk:

- The frontend integration is still only designed and schema-tested.
- The actual frontend code path has not been implemented.
- The actual browser/UI behavior for calling `/local-trial/preview-only` has not been verified.

This review should not be interpreted as permission to modify frontend code or to run a frontend integration smoke. Those actions require a separate user authorization step.

## 13. Recommended Next Step

Recommended next step:

ZDoc Step 189: preview-only route frontend integration code implementation authorization request.

Step 189 should be docs-only / authorization-request-only. It should draft the authorization request for future frontend code implementation and must not directly modify frontend code, start services, access ports, run Ollama, trigger formal routes, write `output/job/export`, enter real ZDoc/ZBid integration, or enter the 50-person deployment design.

## 14. Safety Conclusion

Step 187 completed fake schema tests for the Step 186 preview-only route frontend integration plan. The tests locked the structure, frontend display requirements, preview-only/no-write boundary, evidence boundary, forbidden behaviors, formal flags false, no-write side effects, and import isolation.

The system still has not implemented frontend calling `/local-trial/preview-only`, has not performed frontend integration smoke, has not entered real ZDoc/ZBid integration, and has not opened formal generation, DOCX export, review/apply, ZBid writeback, formal writeback, or `output/job/export` writes.
