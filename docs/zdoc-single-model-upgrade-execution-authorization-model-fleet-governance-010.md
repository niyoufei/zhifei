# MODEL-FLEET-GOVERNANCE-010: Single-Model Upgrade Execution Authorization

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `6fa9ae2510b1bd401208c132f6a60ef0ab3d6714`
- Starting tag at HEAD: none
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-009`
- Previous decision:

  `SINGLE-MODEL UPGRADE AUTHORIZATION GATE FORMED / NO MODEL UPGRADE AUTHORIZED`

This node is a docs-only single-model upgrade execution authorization record.

This node does not run Ollama, does not execute any Ollama command, does not upgrade, pull, delete, replace, run, or test any model, does not modify any `latest` pointer, does not download model files, does not perform online lookup, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-upgrade-authorization-gate-model-fleet-governance-009.md`
2. `docs/zdoc-follow-up-latest-version-lookup-execution-record-model-fleet-governance-008.md`
3. `docs/zdoc-follow-up-latest-version-lookup-authorization-gate-model-fleet-governance-007.md`
4. `docs/zdoc-text-model-upgrade-authorization-gate-model-fleet-governance-006.md`
5. `docs/zdoc-model-fleet-upgrade-candidate-priority-and-next-action-gate-model-fleet-governance-005.md`
6. `docs/zdoc-domestic-top-tier-model-fleet-latest-lookup-insufficient-source-closure-model-fleet-governance-004.md`

No model source was queried.

No new candidate was added beyond prior-doc support.

No real KG file body content was read.

No real KG JSON was parsed.

## 3. Controller Authorization Record

The user has confirmed that ChatGPT is authorized as the controller for the localized deployment system.

ChatGPT is responsible for controller judgment, boundary review, node handoff, authorization prompts, Codex instruction drafting, and execution report review.

Codex is the execution side.

Codex must not replace ChatGPT's controller judgment.

The user has authorized continuing to the next step.

This controller authorization must not be interpreted as permission for Codex to directly run high-impact commands outside explicit boundaries.

Actions involving Ollama, model upgrade, ZDoc service execution, endpoint access, real KG, generation / export / write-back, or real use / trial still require explicit ChatGPT controller instructions that define the allowed scope, prohibited scope, stop condition, and report requirements.

## 4. Candidate for Command-Limited Upgrade Execution

Based on the prior docs, the future command-limited single-model upgrade execution candidate is:

- Official model name: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- Ollama registry tag: `qwen3:30b`
- Candidate family: `qwen3.6` / `qwen3`
- Candidate status: primary same-family Qwen text candidate for a later explicit command-limited execution node

Reason:

1. `MODEL-FLEET-GOVERNANCE-008` records `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507` as the most relevant same-family Qwen3 text candidate for near-term ZDoc prose and long-document comparison.
2. `MODEL-FLEET-GOVERNANCE-009` records `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507` as the only primary same-family candidate suitable for the next explicit single-model upgrade execution authorization gate.
3. The candidate remains within the `qwen3.6` / `qwen3` family already supported by prior docs.
4. No unsupported new candidate is added by this node.

Current baseline retained from prior docs:

- Prior-doc baseline: `qwen3.6:35b` / `Qwen/Qwen3.6-35B-A3B`
- Baseline status: retained as evidence-backed current local baseline from prior docs
- Current node action: no local confirmation, no inventory check, no digest check, no pull, no upgrade, no validation, no real use, and no trial

Secondary comparison candidate retained only for later human-authorized comparison:

- Official model name: `Qwen/Qwen3.6-27B`
- Ollama registry tag: `qwen3.6:27b`
- Status: secondary comparison candidate only, not the command-limited execution target of this node

This node does not confirm the current local model state.

This node does not update any local model.

This node does not execute any model upgrade.

## 5. Future Command-Limited Execution Boundary

The next execution node may consider only the following command or action candidates, and only if explicitly authorized by ChatGPT controller instructions for that future node:

1. `git status --short`
2. `git rev-parse HEAD`
3. Read prescribed docs files
4. Quick disk-space confirmation before upgrade
5. `ollama list` before-upgrade inventory record
6. `ollama pull <authorized-model>` single-model pull or upgrade
7. `ollama list` after-upgrade inventory record
8. Generate a docs-only execution record file
9. `git diff --check`
10. `git diff --cached --check`
11. commit / push / remote tag

`<authorized-model>` may only come from a single-model candidate supported by prior docs.

The current prior-doc primary candidate is `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507`.

The future node must not expand this boundary into multi-model upgrade.

The future node must not treat this document as authorization for any model action unless the ChatGPT controller instruction for that future node explicitly grants the exact command scope.

## 6. Future Prohibited Execution Boundary

The future execution node remains prohibited from:

1. `ollama run`
2. `ollama rm`
3. `ollama serve`
4. Deleting or replacing other models
5. Modifying any `latest` pointer
6. Running the ZDoc service
7. Accessing endpoints
8. Reading or parsing real KG
9. Triggering generation / export / write-back
10. Writing `output`, `job`, or `export`
11. Generating images
12. Calling image generation tools or image models
13. Entering real use or trial

The future node must not enter 1-2 person controlled trial.

The future node must not enter 2-5 person limited concurrent trial.

## 7. Required Stop Condition

After the next execution node completes its explicitly authorized command-limited work, it must stop and wait for human review.

The next execution node must not automatically enter stability validation.

The next execution node must not automatically run the ZDoc service.

The next execution node must not automatically enter KG safety access.

The next execution node must not automatically enter real trial or real use.

## 8. Current Decision

Current decision:

`SINGLE-MODEL UPGRADE EXECUTION AUTHORIZATION RECORDED / COMMAND-LIMITED EXECUTION NODE REQUIRED / NO MODEL UPGRADE EXECUTED`

This decision records the boundary required before a later command-limited single-model upgrade execution node.

This decision does not authorize model upgrade in this node.

This decision does not authorize Ollama execution in this node.

This decision does not authorize image generation.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG reading or parsing.

This decision does not authorize generation, export, or write-back.

This decision does not authorize real use or trial.

## 9. NO-GO Statements

`NO-GO FOR MODEL UPGRADE IN THIS NODE`

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR KG READ / PARSE`

## 10. Next Recommended Node

Recommended next node after human review:

`MODEL-FLEET-GOVERNANCE-011-SINGLE-MODEL-UPGRADE-COMMAND-LIMITED-EXECUTION`

That next node may execute single-model upgrade commands only within the scope explicitly authorized by ChatGPT controller instructions.

That next node must not expand into multi-model upgrade.

That next node must not enter stability validation.

That next node must not enter ZDoc service execution.

That next node must not enter KG safety access.

That next node must not enter real use or trial.

This node does not enter `MODEL-FLEET-GOVERNANCE-011`.

MODEL-FLEET-GOVERNANCE-010 stops here and waits for human review.
