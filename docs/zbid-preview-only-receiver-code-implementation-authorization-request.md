# ZBid Preview-Only Receiver Code Implementation Authorization Request

## 1. Purpose

This document drafts the authorization request for a future ZBid preview-only receiver code implementation step.

This document is authorization-request-only. It does not authorize code changes, ZBid repository access, service startup, port access, endpoint calls, runtime smoke, real ZDoc/ZBid integration, or any writeback behavior.

The proposed next implementation step must not begin until the user explicitly authorizes it.

## 2. Authorization Request Source

This request is based on:

- Step 206: ZBid candidate repository read-only readiness verification.
- Step 207: ZBid preview-only receiver repository readiness verification stage review.

Step 206 only verified repository readiness. Step 207 only archived that readiness verification. Neither step authorized ZBid code changes.

## 3. Confirmed Candidate ZBid Repository Baseline

The candidate ZBid repository information confirmed by Step 206 and archived by Step 207 is:

- Candidate path: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Candidate branch: `local-llm-integration-clean`
- Candidate HEAD: `e9f8e772b9ea71429803b07d01854f689ac956ca`
- `git status --short`: empty
- Worktree clean: yes

These values are the baseline proposed for a future authorized implementation step. Before any code modification, the future step must re-check the path, branch, HEAD, and clean state.

## 4. Proposed Future Code Implementation Scope

The future ZBid preview-only receiver implementation should be limited to the smallest preview-only receiver/helper surface.

Preferred allowed file scope:

- Add `app/engine/zdoc_zbid_preview_receiver.py`
- Add `tests/test_zdoc_zbid_preview_receiver.py`

The receiver should only implement a preview-only helper or adapter boundary. It must not modify scoring, evidence, persistence, DOCX export, main routing, or writeback behavior.

The future step must not modify `app/main.py`. If a later step needs to expose an API route, that route exposure must be separately authorized and must remain default-off, preview-only, and no-write.

## 5. Receiver Allowed Data Scope

The ZBid preview-only receiver may only carry or validate metadata-only preview data:

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- no-write / no-formal-chain flags

The receiver must not treat advisory, preview, shadow candidate, patch, diff, rollback, dry-run, or model-generated text as evidence.

## 6. Required No-Write / No-Formal-Chain Flags

The receiver output or envelope must include the following flags, and they must remain false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

If the receiver detects missing required preview metadata, unsafe evidence semantics, or any attempted writeback state, it must return a preview-only/no-write blocked or invalid result. It must not fall back to any formal chain.

## 7. ZBid-Side Boundary

The ZBid side must remain:

- preview-only
- no-write
- no-evidence
- metadata-only

The ZBid side must not:

- write back to ZBid formal business data
- write back to ZDoc
- treat advisory as evidence
- treat preview as formal content
- treat shadow candidate, patch, diff, rollback, or dry-run output as evidence
- call or expose any formal writeback path

## 8. Files And Chains That Must Be Avoided

The future implementation must avoid these risk-sensitive files unless a later step grants explicit file-level authorization:

- `app/engine/evidence.py`
- `app/engine/evidence_units.py`
- `app/engine/scorer.py`
- `app/engine/v2_scorer.py`
- `app/engine/docx_exporter.py`
- `app/storage.py`
- `app/main.py`

The future implementation must avoid these chains:

- `score_text` / `score_text_v2` scoring chain
- `export_report_to_docx` DOCX export chain
- `save_*` persistence chain
- writeback paths
- storage write paths
- scoring basis write paths
- qingtian results write paths

## 9. Explicitly Not Authorized By This Request

This authorization request does not authorize:

- ZBid repository modification
- ZDoc repository code modification
- service startup
- port access
- endpoint calls
- pytest execution
- Ollama execution
- `/local-trial/preview-only` calls
- any ZBid endpoint calls
- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- DOCX generation
- `output/job/export` writes
- real ZDoc/ZBid integration
- 50-person deployment design

## 10. Proposed Next Step

The proposed next step is:

ZDoc Step 209: ZBid preview-only receiver code implementation.

Step 209 must require a separate explicit user authorization before execution. It must not default to service startup, port access, endpoint calls, runtime smoke, ZBid writeback, or any formal-chain behavior.

## 11. Suggested Step 209 User Authorization Wording

The user may authorize Step 209 with wording equivalent to:

> I authorize Step 209: ZBid preview-only receiver code implementation. The authorized ZBid repository path is `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`; the authorized branch is `local-llm-integration-clean`; the required starting HEAD is `e9f8e772b9ea71429803b07d01854f689ac956ca`; the worktree must be clean before starting. The allowed file scope is limited to adding `app/engine/zdoc_zbid_preview_receiver.py` and `tests/test_zdoc_zbid_preview_receiver.py`. The implementation must remain preview-only, no-write, and no-evidence; it must not start services, access ports, call endpoints, trigger `/generate`, `/export_docx`, `/review/apply`, ZBid writeback, DOCX generation, or write `output/job/export`.

If the future Step 209 preflight finds a different path, branch, HEAD, or non-clean worktree, it must stop and report the mismatch.

## 12. Safety Conclusion

This document only drafts a future code implementation authorization request. It does not authorize Step 209 by itself.

Any future ZBid receiver implementation must remain limited to preview-only metadata handling, with no writeback, no evidence promotion, no formal scoring, no DOCX export, no persistence, no service startup, no port access, and no runtime smoke unless separately authorized.
