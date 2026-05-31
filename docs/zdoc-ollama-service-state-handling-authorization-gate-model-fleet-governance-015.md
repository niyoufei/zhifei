# MODEL-FLEET-GOVERNANCE-015: Ollama Service-State Handling Authorization Gate

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `cbec9d60b298b2c121f7a0e0fa805643a34bc168`
- Starting tag at HEAD: not queried because this node's allowed scope did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-014`
- Previous decision:

  `RETRY FAILURE AUDIT COMPLETED / OLLAMA SERVICE-STATE HANDLING REQUIRED / NO MODEL UPGRADE EXECUTED`

This node is a docs-only Ollama service-state handling authorization gate.

This node does not run Ollama, does not execute `ollama serve`, does not execute `ollama list`, does not execute `ollama pull qwen3:30b`, does not upgrade, pull, delete, replace, run, or test any model, does not modify any `latest` pointer, does not download model files, does not perform online model-version lookup, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-upgrade-retry-failure-audit-model-fleet-governance-014.md`
2. `docs/zdoc-single-model-upgrade-command-limited-full-access-retry-record-model-fleet-governance-013.md`
3. `docs/zdoc-single-model-upgrade-blocked-audit-model-fleet-governance-012.md`
4. `docs/zdoc-single-model-upgrade-command-limited-execution-record-model-fleet-governance-011.md`
5. `docs/zdoc-single-model-upgrade-execution-authorization-model-fleet-governance-010.md`
6. `docs/zdoc-single-model-upgrade-authorization-gate-model-fleet-governance-009.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 3. Current Blocker

Current blocker:

`Error: could not connect to ollama server, run 'ollama serve' to start it`

This blocker indicates that the local Ollama server is not running or is not connectable.

The current blocker is not `connect: operation not permitted`.

Full access has removed or bypassed the earlier permission-class blocker recorded in `MODEL-FLEET-GOVERNANCE-011`.

`ollama pull qwen3:30b` has not yet executed.

Whether `qwen3:30b` exists remains unconfirmed.

## 4. Service-State Handling Options

Path A:

The user manually starts the Ollama app or Ollama service, then reports "已启动 Ollama" or provides the user's local `ollama list` output.

Path B:

Codex executes minimal service startup or service-state confirmation commands only under explicit controlled authorization.

Recommended path: Path A.

This node does not execute Path A or Path B.

This node only forms the authorization gate for later Ollama service-state handling.

## 5. Recommended Path A Procedure

The recommended user-side procedure is:

1. Start the Ollama app, or start the Ollama server using the user's normal local method.
2. Manually execute `ollama list`.
3. Confirm that `could not connect to ollama server` no longer appears.
4. Paste the complete `ollama list` output back to ChatGPT.

User-side manual execution is not Codex execution.

The user's manual `ollama list` output is only service-state and model-inventory evidence.

The user's manual `ollama list` output does not authorize `ollama pull`.

## 6. Path B Authorization Boundary

If Path B is selected later, a separate controlled node must be formed first.

Path B command candidates may only include:

1. Service-state confirmation commands.
2. Minimal service startup commands.
3. `ollama list` service-availability confirmation.

Path B must not directly expand into `ollama pull qwen3:30b`.

Path B must not execute `ollama run`.

Path B must not execute `ollama rm`.

Path B must not delete models.

Path B must not replace models.

Path B must not modify any `latest` pointer.

## 7. Future Retry Path After Service Ready

After service availability is confirmed, a later node may enter:

`MODEL-FLEET-GOVERNANCE-016-SINGLE-MODEL-UPGRADE-COMMAND-LIMITED-RETRY-AFTER-SERVICE-READY`

The only authorized model for that later retry must still be:

`qwen3:30b`

That later retry may still allow only:

1. `ollama list`
2. `ollama pull qwen3:30b`
3. Pull-after `ollama list`
4. Docs-only execution record
5. Git checks, commit, push, and tag

That later retry must not expand into multi-model upgrade.

That later retry must not delete or replace other models.

That later retry must not modify any `latest` pointer.

## 8. Current Decision

`OLLAMA SERVICE-STATE HANDLING GATE FORMED / PATH A RECOMMENDED / NO OLLAMA EXECUTION IN THIS NODE`

This decision records only the service-state handling authorization gate.

This decision does not authorize Ollama execution in this node.

This decision does not authorize model upgrade in this node.

## 9. NO-GO Statements

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR OLLAMA SERVE IN THIS NODE`

`NO-GO FOR OLLAMA LIST IN THIS NODE`

`NO-GO FOR OLLAMA PULL IN THIS NODE`

`NO-GO FOR MODEL UPGRADE IN THIS NODE`

`NO-GO FOR OLLAMA RUN`

`NO-GO FOR OLLAMA RM`

`NO-GO FOR MULTI-MODEL UPGRADE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR GENERATION / EXPORT / WRITE-BACK`

## 10. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-016-SINGLE-MODEL-UPGRADE-COMMAND-LIMITED-RETRY-AFTER-SERVICE-READY`

That node may execute only after Path A is complete.

Path A completion condition:

The user manually starts Ollama and provides usable `ollama list` output.

This node does not automatically execute `ollama pull qwen3:30b`.

The next node must not automatically execute `ollama pull qwen3:30b` without explicit node authorization.

The next node must not automatically enter stability validation, ZDoc service execution, KG safety access, real use, trial, or ZDoc preview / trial / production flow.

MODEL-FLEET-GOVERNANCE-015 stops here and waits for human review.
