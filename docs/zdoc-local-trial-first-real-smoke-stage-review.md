# ZDoc Local Trial First Real Smoke Stage Review

## 1. Scope

This document is the docs-only stage review for Step 159, the first real local smoke test execution.

It records the execution result, authorization boundary, runtime observations, process shutdown result, output isolation result, risks, and remaining conditions before the next trial.

This Step 160 review is docs-only:

- It does not rerun the smoke test.
- It does not start the backend service.
- It does not start the frontend service.
- It does not run Ollama.
- It does not access any local port.
- It does not call ZBid.
- It does not write `output/job/export`.
- It does not enter 50-user formal deployment design.

## 2. User authorization baseline

Step 159 was executed only after the user explicitly authorized the first real local smoke test.

Authorization summary:

> "我授权执行 Step 159 首次真实 local smoke test，授权范围仅限 Step 158 授权请求文档中列明事项；不得触发 /generate、/export_docx、/review/apply、ZBid 写回、正式写回，不得写 output/job/export，不得进入 50 人正式部署设计。"

Authorization boundaries:

- The authorization applied only to Step 159.
- The authorization does not extend to Step 160.
- The authorization does not grant automatic authorization for later steps.
- Any future real runtime execution still requires explicit user authorization.

## 3. Git and environment result

Step 159 recorded the following baseline and final state:

- Current directory: `/Users/youfeini/Desktop/文档生成系统`
- Current branch: `main`
- Start HEAD: `b3f1f9054a160cffa9d6c05830f76f158d63bec7`
- End HEAD: `b3f1f9054a160cffa9d6c05830f76f158d63bec7`
- `git status --short`: empty
- Tag pointing at HEAD: `v0.1.217-zdoc-first-real-smoke-authorization-request`
- Python: `3.13.3`
- Node: `v22.22.2`
- pnpm: `10.33.2`
- `.env`: absent; no sensitive configuration was printed.

Step 159 did not modify any files, did not commit, did not tag, and did not push.

## 4. Output isolation result

Step 159 recorded these before and after file counts:

- `output/job/export`: `0 -> 0`
- `backend/data/autoplan/jobs`: `87 -> 87`
- `build`: `1389 -> 1389`

Confirmed boundaries:

- No write occurred under `output/job/export`.
- No DOCX, JSON, or Markdown formal artifact appeared.
- No new job/export state file appeared.
- No cleanup, deletion, or `git clean` was executed.

## 5. Backend smoke result

Step 159 started the backend only for the authorized health and preview-safe checks.

Runtime result:

- Backend address: `127.0.0.1:18760`
- Backend PID: `9081`
- `/health`: returned OK.
- `/local-llm/preview-safe`: returned:
  - `preview_only=true`
  - `no_write=true`
  - `calls_generate_route=false`
  - `calls_export_docx_route=false`
  - `calls_review_apply_route=false`
  - `affects_zbid_writeback=false`
  - `writes_output=false`
  - `writes_job=false`
  - `writes_export=false`

Shutdown result:

- Backend PID `9081` was stopped.
- `127.0.0.1:18760` had no listener after shutdown.

Backend boundaries:

- `/generate` was not accessed.
- `/export_docx` was not accessed.
- `/review/apply` was not accessed.
- No ZBid writeback interface was accessed.
- Backend startup was limited to health and preview-safe no-write checks.

## 6. Frontend smoke result

Step 159 started the frontend only for the authorized page accessibility check.

Runtime result:

- Frontend address: `127.0.0.1:18761`
- `/`: redirected to `/index`.
- `/index`: returned `200`.
- Only GET accessibility checks were performed.
- No button was clicked.
- No business action was triggered.

Shutdown result:

- Frontend service was stopped.
- `127.0.0.1:18761` had no listener after shutdown.

Frontend boundaries:

- DOCX export was not triggered.
- ZBid writeback was not triggered.
- `review/apply` was not triggered.
- Formal writeback was not triggered.
- Interactive button-click behavior was not verified in Step 159.

## 7. Ollama optional check result

Step 159 performed only the authorized optional Ollama availability checks.

Observed result:

- Ollama CLI exists at `/opt/homebrew/bin/ollama`.
- `ollama list` reported that the Ollama service was not running.
- `127.0.0.1:11434/api/tags` was not reachable.
- `ollama serve` was not run.
- No model was downloaded.
- No model was pulled.
- No model generation was called.

Boundary interpretation:

- Step 159 verified that when Ollama is unavailable, the smoke did not auto-start Ollama, did not download models, and did not write back.
- Step 159 did not verify a usable local model chain.
- `thinking_only_fallback` must not be treated as formal body-generation capability.
- Model output must not be treated as evidence.

## 8. Fake preview packet / validator result

Step 159 executed the local fake preview packet and validator check.

Observed result:

- Fake preview packet / validator local check passed.
- Packet result: `accepted_preview_only`.
- Validator result: `accept_preview_only`.
- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

Boundary interpretation:

- `accepted_preview_only` does not mean writeback permission.
- `accepted_preview_only` does not mean evidence.
- No real ZBid API was called.
- No ZBid DB was accessed.
- No ZBid writeback occurred.

## 9. Strict non-occurrence confirmation

Step 159 confirmed that the following did not occur:

- No `/generate` trigger.
- No `/export_docx` trigger.
- No DOCX generation.
- No `/review/apply` trigger.
- No ZBid writeback.
- No ZBid API / DB / writeback call.
- No formal writeback.
- No formal writeback dry-run.
- No `output/job/export` write.
- No production code modification.
- No tests modification.
- No docs modification.
- No configuration modification.
- No deployment script modification.
- No `git add`, `git commit`, `git tag`, or `git push`.
- No action outside the Step 159 smoke authorization scope.
- No local deployment execution.
- No 50-user formal deployment design.

## 10. Process shutdown result

Step 159 stopped all services started during the smoke:

- Backend PID `9081` was stopped.
- Frontend service was stopped.
- `127.0.0.1:18760` had no listener.
- `127.0.0.1:18761` had no listener.
- No unknown residual process was reported.

Scope note:

- Step 159 confirmed only that the authorized smoke ports were no longer listening.
- Step 159 did not run destructive batch `kill` commands.
- Step 159 did not expand process inspection beyond the authorized smoke scope.

## 11. Risk and limitation assessment

Step 159 left the following limitations:

1. Ollama was not running, so a usable local model chain was not verified.
2. The frontend check only verified GET page accessibility; interactive button clicks were not tested.
3. Forbidden endpoints were not accessed; formal-chain blocking evidence comes from preview-safe response fields and the fact that forbidden routes were not triggered.
4. A real ZDoc/ZBid preview-only route was not verified.
5. Real evidence anchors were not verified.
6. Real scoring clause refs were not verified.
7. Real local-model section review was not verified.
8. Real DOCX / ZBid / review/apply UI disabled states were not verified through interaction.
9. This smoke does not prove that local deployment is complete.
10. This smoke does not prove 50-user team deployment capability.

## 12. Pass criteria evaluation

Step 159 satisfied the first local no-write smoke criteria:

- Git preflight passed.
- Environment versions were readable.
- `output/job/export` had no difference.
- Backend started and `/health` returned OK.
- Preview-safe no-write fields were readable.
- Frontend started and the page was accessible.
- Ollama unavailable state did not auto-start, download, or write back.
- Fake preview packet / validator could be checked locally.
- Formal-chain flags remained false.
- Started service processes were stopped.
- 50-user deployment design was not entered.

## 13. Remaining blockers before next real trial

Before the next real trial, the following items still need explicit authorization or design:

- Whether to allow starting `ollama serve`.
- Whether to allow access to Ollama model generation endpoints.
- Whether to allow real preview-only API requests.
- Whether to allow interactive frontend button-state checks.
- Whether to allow testing forbidden endpoints for blocked responses.
- Whether to prepare a small local trial data set.
- Whether to generate a separate smoke report file.
- Whether to enter ZDoc/ZBid preview-only route design or implementation.

## 14. Recommended next step

Recommended next step:

ZDoc Step 161: second smoke authorization request for Ollama optional and UI block checks, docs-only / authorization-request-only.

Step 161 should only draft the second-round smoke authorization request. It must not start services, run Ollama, access ports, or execute a smoke test. Only after explicit user authorization may a second real smoke be executed.

## 15. Safety conclusion

Step 159 completed the first real local smoke test within the authorized scope. No `output/job/export` write, formal-chain trigger, ZBid call, or started-process residue was observed.

The current system passed the first no-write / preview-safe / service-start-stop smoke, but it has not yet completed Ollama usable-chain verification, real ZDoc/ZBid preview-only route verification, interactive UI blocking verification, or small-team trial validation.

This document does not mean that local deployment is complete. It does not mean that ZDoc/ZBid has been actually integrated. It does not mean that the local model chain is usable. It does not mean that DOCX export, ZBid writeback, `review/apply`, or formal writeback has been implemented.
