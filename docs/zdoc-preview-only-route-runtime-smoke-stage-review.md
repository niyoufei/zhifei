# ZDoc Preview-Only Route Runtime Smoke Stage Review

## 1. Scope

This document archives the Step 184 preview-only route runtime smoke result.

Step 185 is docs-only. It does not rerun runtime smoke, start backend or frontend services, run Ollama, access local ports, trigger `/generate`, trigger `/export_docx`, trigger `/review/apply`, call ZBid, generate DOCX, write `output/job/export`, or enter the 50-person deployment design.

## 2. Step 184 Execution Summary

Step 184 was executed under explicit user authorization to start the backend and access only:

- `GET /health`
- `GET /local-llm/preview-safe`
- `POST /local-trial/preview-only`

Runtime facts recorded in Step 184:

- Backend address: `127.0.0.1:18760`
- Backend PID: `85443`
- Backend stop result: stopped
- Port result after stop: `127.0.0.1:18760` had no listener
- Git status before smoke: empty
- Git status after smoke: empty
- Start HEAD: `f835ad31c3139b82d8e2525d5074616f9c517f57`
- End HEAD: `f835ad31c3139b82d8e2525d5074616f9c517f57`
- HEAD changed: no
- HEAD tag: `v0.1.238-zdoc-preview-only-route-runtime-smoke-authorization-request`

No files were modified by Step 184.

## 3. Endpoint Results

Step 184 endpoint results:

- `GET /health`: HTTP 200, `ok=true`
- `GET /local-llm/preview-safe`: HTTP 405, `Method Not Allowed`
- `POST /local-trial/preview-only`: HTTP 200

The `GET /local-llm/preview-safe` result is a method mismatch observation. Step 184 did not switch to another method because the authorization text requested GET for that endpoint, and the smoke did not expand beyond the authorized route surface.

## 4. Preview-Only Route Result

`POST /local-trial/preview-only` returned the expected preview-only, no-write runtime response.

Confirmed response fields:

- `preview_only=true`
- `no_write=true`
- `preview_packet` readable
- `validator_result` readable
- `blocked_reasons` readable

Confirmed `blocked_reasons`:

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

The route result confirms that the local trial preview-only route can return a preview packet, validator result, and explicit blocked reasons through the running backend service.

## 5. Safety Flags

Formal chain flags remained false:

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

Side-effect flags remained false:

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `affects_zbid_writeback=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`

These fields preserve the preview-only and no-write boundary for the route smoke.

## 6. Strict Non-Occurrence Confirmation

Step 184 did not perform or trigger the following:

- Did not run Ollama
- Did not run `ollama serve`
- Did not start frontend
- Did not access `127.0.0.1:11434`
- Did not trigger `/generate`
- Did not trigger `/export_docx`
- Did not trigger `/review/apply`
- Did not trigger ZBid writeback
- Did not call ZBid API / DB / writeback
- Did not generate DOCX
- Did not write `output/job/export`
- Did not modify code
- Did not modify tests
- Did not modify docs
- Did not modify configuration
- Did not modify deployment scripts
- Did not execute `git add`
- Did not execute `git commit`
- Did not execute `git tag`
- Did not execute `git push`
- Did not execute `git clean`
- Did not enter the 50-person deployment design

## 7. Output Job Export Result

Step 184 output isolation result:

- `output/job/export` pre-snapshot: empty
- `output/job/export` post-snapshot: empty
- Pre/post diff: no difference

No DOCX, JSON, Markdown, job, output, or export artifact was created under `output/job/export`.

## 8. Risk And Limitation Assessment

No high risk was found in Step 184.

Observed limitation:

- `GET /local-llm/preview-safe` returned HTTP 405, `Method Not Allowed`.
- This means the endpoint is not currently available through GET.
- Step 184 did not retry with another method because doing so would have expanded beyond the exact endpoint method listed in the authorization.

Confirmed positive result:

- `/local-trial/preview-only` passed runtime smoke through the running backend service.
- The route returned `preview_only=true`, `no_write=true`, readable metadata, readable validator output, readable blocked reasons, and all formal chain flags false.

Remaining limitation:

- Frontend has not yet been wired to call `/local-trial/preview-only`.
- No frontend-to-route integration smoke has been executed.
- No real ZDoc/ZBid integration was performed.
- Formal generation, DOCX export, review/apply, ZBid writeback, and formal writeback remain unopened.

## 9. Recommended Next Step

Recommended next step:

ZDoc Step 186: preview-only route frontend integration plan design, docs-only.

Step 186 should only design the future frontend integration plan for the preview-only route. It should not directly modify frontend code, start services, access ports, run Ollama, perform real ZDoc/ZBid integration, write `output/job/export`, or enter the 50-person deployment design.

## 10. Safety Conclusion

Step 184 confirms that the backend runtime route `POST /local-trial/preview-only` is accessible and returns a no-write preview-only response. It also confirms that `output/job/export` remained unchanged and all formal chain flags stayed false.

This stage review does not represent frontend integration, real ZDoc/ZBid联调, formal generation, DOCX export, review/apply, ZBid writeback, formal writeback, or 50-person deployment readiness.
