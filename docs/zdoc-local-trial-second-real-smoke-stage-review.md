# ZDoc Local Trial Second Real Smoke Stage Review

## 1. Scope

This document is the docs-only stage review for Step 162, the second real local smoke test execution with `ollama serve` explicitly allowed by the user.

This Step 163 review only archives the Step 162 result. It does not rerun smoke checks, start services, run Ollama, access local ports, call ZBid, write `output/job/export`, enter local deployment execution, or enter 50-user formal deployment design.

## 2. Step 162 Authorization Summary

Step 162 was executed under explicit user authorization:

> 允许执行 Step 162 第二轮真实 local smoke test，授权范围仅限 Step 161 授权请求文档中列明事项；允许运行 ollama serve；不得触发 /generate、/export_docx、/review/apply、ZBid 写回、正式写回，不得写 output/job/export，不得下载或拉取模型，不得进入 50 人正式部署设计。

Authorization boundaries observed in Step 162:

- `ollama serve` was allowed and was started only for the local smoke.
- No model download or pull was allowed.
- No model generation was allowed.
- No formal route was allowed.
- No ZBid writeback or ZBid API / DB access was allowed.
- No `output/job/export` write was allowed.
- The authorization did not cover local deployment execution or 50-user deployment design.

## 3. Git and Environment Result

Step 162 recorded:

- Current directory: `/Users/youfeini/Desktop/文档生成系统`
- Current branch: `main`
- Start HEAD: `eb84f8595701a6218babe3a21fa9039b695dee32`
- End HEAD: `eb84f8595701a6218babe3a21fa9039b695dee32`
- `git status --short`: empty
- Tag pointing at HEAD: `v0.1.219-zdoc-second-smoke-authorization-request`
- Python: `3.13.3`
- Node: `v22.22.2`
- pnpm: `10.33.2`
- `.env`: absent; no sensitive configuration was printed.

Step 162 did not modify files, did not stage, did not commit, did not tag, and did not push.

## 4. Output and Runtime File Difference Result

Step 162 recorded these before and after counts:

- `output/job/export`: `0 -> 0`
- `backend/data/autoplan/jobs`: `87 -> 87`
- `build`: `1389 -> 1389`
- `frontend_web/users.db` stat: unchanged at `1761005121 12288`

Confirmed boundaries:

- No write occurred under `output/job/export`.
- No DOCX file was generated.
- No JSON or Markdown formal export artifact was generated.
- No new job/export state file appeared.
- No cleanup, deletion, or `git clean` was executed.

## 5. Backend Smoke Result

Step 162 started the backend only for the authorized health and preview-safe checks.

Runtime result:

- Backend address: `127.0.0.1:18762`
- Backend PID: `40968`
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
  - `calls_ollama=false`

Backend boundaries:

- `/generate` was not accessed.
- `/export_docx` was not accessed.
- `/review/apply` was not accessed.
- No ZBid writeback interface was accessed.
- No model generation was called through the backend.
- The backend check remained preview-safe and no-write.

## 6. Frontend Smoke Result

Step 162 started the frontend only for page accessibility and read-only UI state inspection.

Runtime result:

- Frontend address: `127.0.0.1:18763`
- Frontend PID: `41022`
- `/`: redirected to `/index`.
- `/index`: returned `200`.
- Only GET accessibility and HTML inspection checks were performed.
- No button was clicked.
- No form was submitted.
- No business action was triggered.

Read-only UI observations:

- Buttons found: `上传`, `上传`, `上传`, `生成 Word 文档`.
- Disabled input count: `4`.
- No `/export_docx` route text was found.
- No `/review/apply` route text was found.
- No ZBid text or entry was found.
- No `preview-only` / `预览` boundary text was found.
- No `blocked_reasons` text was found.
- No `evidence` / `证据` boundary text was found.

## 7. Ollama Serve Result

Step 162 started `ollama serve` under explicit authorization.

Runtime result:

- `ollama serve` listened on `127.0.0.1:11434`.
- Ollama PID: `40917`.
- `/api/tags` was reachable.
- `ollama list` was readable.
- Local model count: `7`.
- Models listed:
  - `qwen3-next:80b-a3b-instruct-q8_0`
  - `qwen3-coder:30b`
  - `deepseek-r1:32b`
  - `qwen3:30b`
  - `qwen3:14b`
  - `qwen3:8b`
  - `qwen3:0.6b`

Ollama boundaries:

- No model was downloaded.
- No model was pulled.
- No model generation was called.
- No model output was used as evidence.
- No model output was used as formal body content.

## 8. Fake Packet / Validator Result

Step 162 executed the local fake preview packet and validator check.

Observed result:

- Packet status: `accepted_preview_only / mapped_preview_only / preview_only`
- Validator status: `accepted_preview_only / accept_preview_only`
- `blocked_reasons`:
  - `preview_only_is_not_writeback_permission`
  - `preview_only_is_not_evidence`
  - `zbid_preview_scoring_is_not_evidence`

Formal-chain flags in both packet and validation result remained false:

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

Boundary interpretation:

- `accepted_preview_only` does not grant writeback permission.
- `accepted_preview_only` does not become evidence.
- ZBid preview scoring does not become evidence.
- No real ZBid API was called.
- No ZBid DB was accessed.
- No ZBid writeback occurred.

## 9. Strict Non-Occurrence Confirmation

Step 162 confirmed that the following did not occur:

- No model download.
- No model pull.
- No model-generated formal body content.
- No external model/API call.
- No `/generate` trigger.
- No `/export_docx` trigger.
- No DOCX generation.
- No `/review/apply` trigger.
- No ZBid writeback.
- No ZBid API / DB / writeback call.
- No formal writeback.
- No formal writeback dry-run.
- No `output/job/export` write.
- No source section modification.
- No formal document generation.
- No real shadow generation implementation.
- No real candidate patch generation.
- No formal body-generation chain.
- No ZDoc/ZBid actual integration writeback chain.
- No 50-user team deployment design.
- No production code modification.
- No tests modification.
- No docs modification during Step 162.
- No configuration modification.
- No deployment script modification.
- No `git add`, `git commit`, `git tag`, or `git push`.
- No `git clean`.
- No file deletion.
- No authorization expansion.

## 10. Process Shutdown Result

Step 162 stopped all services started during the smoke:

- Backend PID `40968` was stopped.
- Frontend PID `41022` was stopped.
- Ollama PID `40917` was stopped.
- `127.0.0.1:18762` had no listener after shutdown.
- `127.0.0.1:18763` had no listener after shutdown.
- `127.0.0.1:11434` had no listener after shutdown.

Scope note:

- Step 162 confirmed only the authorized smoke ports were no longer listening.
- Step 162 did not run destructive batch `kill` commands.
- Step 162 did not expand process inspection beyond the authorized smoke scope.

## 11. Formal Chain Flags Result

The formal-chain flags remained false throughout the Step 162 checks:

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

No Step 162 observation grants writeback, export, review/apply, ZBid writeback, or output-write permission.

## 12. Frontend UI Risk Items

Step 162 found an important frontend UI risk:

- The page contains a visible `生成 Word 文档` entry.
- The page did not display `preview-only` / `预览` boundary text.
- The page did not display `no-write` boundary text.
- The page did not display `blocked_reasons` boundary text.
- The page did not display `evidence` / `证据` boundary text.
- No `/export_docx`, `/review/apply`, or ZBid text or entry was found.
- The `生成 Word 文档` entry was not clicked or submitted.

Risk interpretation:

- The current frontend page is accessible, but it does not make the preview-only / no-write stage explicit.
- The visible `生成 Word 文档` entry may confuse a local-trial user into thinking formal Word generation is available.
- The absence of `blocked_reasons` and evidence-boundary copy means users may not see why writeback/export/review paths remain blocked.
- This is a UI contract risk, not evidence that a forbidden endpoint was triggered.

## 13. Pass Criteria Evaluation

Step 162 satisfied the second local smoke criteria within its authorization boundary:

- Git preflight passed.
- Environment versions were readable.
- `output/job/export` had no difference.
- `backend/data/autoplan/jobs` had no difference.
- `build` had no difference.
- `frontend_web/users.db` stat did not change.
- Backend started and `/health` returned OK.
- Preview-safe no-write fields were readable.
- Frontend started and `/index` was accessible.
- `ollama serve` started under authorization.
- Ollama tags and model list were readable.
- No model download or pull occurred.
- Fake preview packet / validator could be checked locally.
- Formal-chain flags remained false.
- Started backend, frontend, and Ollama processes were stopped.
- 50-user deployment design was not entered.

## 14. Remaining Risks and Limitations

Step 162 still leaves the following items unresolved:

- The frontend no-write / preview-only UI boundary is not explicit enough.
- The visible `生成 Word 文档` entry needs a no-write risk control design before any implementation.
- The UI did not show `blocked_reasons`.
- The UI did not show evidence-boundary copy.
- The UI did not show preview-only copy.
- The smoke did not click or submit the `生成 Word 文档` entry.
- The smoke did not trigger forbidden endpoints to verify blocked responses.
- The smoke did not validate a real ZDoc/ZBid preview-only route.
- The smoke did not validate real evidence anchors.
- The smoke did not validate real scoring clause refs.
- The smoke does not prove local deployment is complete.
- The smoke does not prove 50-user deployment capability.

## 15. Recommended Next Step

Recommended next step:

ZDoc Step 164: frontend no-write UI risk contract design, docs-only.

Purpose:

Design the frontend no-write / preview-only / `blocked_reasons` / evidence-boundary messaging and the `生成 Word 文档` entry risk control before changing code.

Step 164 should not directly modify frontend code. It should remain docs-only, define the UI contract, and keep formal writeback, DOCX export, review/apply, ZBid writeback, and 50-user deployment out of scope.

## 16. Safety Conclusion

Step 162 completed the second real local smoke test within the explicit authorization scope.

It confirmed that `ollama serve` can start and stop, tags and model list are readable, backend preview-safe remains no-write, frontend page is accessible, `output/job/export` remains unchanged, and formal-chain flags remain false.

The main finding is a frontend UI contract risk: the current page exposes a `生成 Word 文档` entry while not showing preview-only, no-write, `blocked_reasons`, or evidence-boundary messaging. This should be addressed first through a docs-only UI risk contract design before any code change.
