# ZDoc Single-Model Upgrade Latest-Version Recheck Authorization Gate - KG-RUNTIME-151

## 1. Runtime Scope

KG-RUNTIME-151 is a docs-only latest-version recheck authorization gate for the ZDoc single-model upgrade chain.

This stage only records whether a future controlled latest-version read-only recheck may be requested for the single-model candidate carried forward from KG-RUNTIME-150.

This stage explicitly:

- Does not execute an upgrade.
- Does not run Ollama.
- Does not execute any model command.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not query the internet for latest-version information.
- Does not enter upgrade preflight.
- Does not enter real use, formal trial use, or controlled trial use.
- Does not enter KG-RUNTIME-152.

KG-RUNTIME-151 is not latest-version lookup authorization, not upgrade authorization, and not an execution node.

## 2. Baseline

KG-RUNTIME-150 ended with the following recorded state:

- End HEAD: `c3b6f81673912d3ee2ad724386e6c908a0958642`
- Remote tag: `v0.1.533-zdoc-single-model-upgrade-approval-response-intake`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-explicit-approval-response-intake-kg-runtime-150.md`
- Approval response intake result: `incomplete / pending explicit user approval`
- Current GO / NO-GO status: `NO-GO / pending explicit user approval`
- Worktree state after KG-RUNTIME-150: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-151 preflight observed:

- Start HEAD: `c3b6f81673912d3ee2ad724386e6c908a0958642`
- Baseline remote tag carried from KG-RUNTIME-150: `v0.1.533-zdoc-single-model-upgrade-approval-response-intake`
- Worktree before this docs-only change: clean

## 3. Source Boundary

KG-RUNTIME-151 is based only on the following authorized project documents:

1. KG-RUNTIME-150 explicit approval response intake document:
   `docs/zdoc-single-model-upgrade-execution-explicit-approval-response-intake-kg-runtime-150.md`
2. KG-RUNTIME-149 explicit approval wait-state document:
   `docs/zdoc-single-model-upgrade-execution-explicit-approval-wait-state-kg-runtime-149.md`
3. KG-RUNTIME-148 authorization decision checkpoint document:
   `docs/zdoc-single-model-upgrade-execution-authorization-decision-checkpoint-kg-runtime-148.md`

This stage:

- Does not add internet lookup.
- Does not re-collect the local model inventory.
- Does not expand model families.
- Does not adjust candidate priority.
- Does not introduce any external new basis.
- Does not treat general acceptance of the control route as actual command authorization.
- Does not treat this latest-version recheck authorization gate as internet lookup authorization.
- Does not treat this latest-version recheck authorization gate as model upgrade authorization.

## 4. Candidate Confirmation

The only single-model candidate for this latest-version recheck authorization gate is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Current state: future latest-version recheck authorization gate candidate only
- Upgrade executed by KG-RUNTIME-151: no
- Internet lookup allowed in KG-RUNTIME-151: no
- Upgrade allowed in KG-RUNTIME-151: no
- Upgrade allowed in an automatic later node: no
- Requirement for any later execution path: complete explicit user authorization, controlled latest-version read-only recheck, and a separate upgrade preflight must occur first

No other model candidate is confirmed by KG-RUNTIME-151. No model family is expanded by this stage.

## 5. Latest-Version Recheck Need

A later latest-version recheck is needed before any actual upgrade path can be considered because:

- KG-RUNTIME-139 previously performed a controlled latest-version lookup.
- Model version information may have changed after KG-RUNTIME-139.
- Before any real upgrade, the project must confirm whether `qwen3.6:35b` is still the current recommended candidate.
- KG-RUNTIME-151 only establishes the authorization gate for that future recheck.
- KG-RUNTIME-151 does not perform internet lookup.
- Any conclusion about the current latest model must be based on a later controlled read-only recheck result, not on KG-RUNTIME-151.

## 6. Proposed Latest-Version Recheck Scope

The following scope may be requested for a future user-authorized read-only recheck, but KG-RUNTIME-151 does not execute it:

1. `qwen3.6:35b`
2. The `qwen3` model family
3. The same model-family context already involved in KG-RUNTIME-139, if needed

The future recheck must not expand to unrelated model families. It must not query models unrelated to the local single-model candidate.

## 7. Proposed Trusted Sources for Future Recheck

The following read-only sources may be requested for a future user-authorized recheck, but KG-RUNTIME-151 does not access them:

1. The corresponding Ollama official model library page.
2. Qwen official release channels.
3. The Qwen official organization page on Hugging Face.
4. Official or trusted sources already recorded by KG-RUNTIME-139.

KG-RUNTIME-151 records these only as a future authorization boundary. It does not visit or query these sources.

## 8. Latest-Version Recheck Authorization Items

Before any later node may perform a latest-version read-only recheck, the user must explicitly authorize all required items, including:

1. Whether read-only internet recheck is allowed.
2. Whether visiting the Ollama official model library is allowed.
3. Whether visiting Qwen official release channels is allowed.
4. Whether visiting the Qwen official organization page on Hugging Face is allowed.
5. Whether the recheck object is strictly limited to `qwen3.6:35b` / the `qwen3` model family.
6. Whether querying other model families remains prohibited.
7. Whether running Ollama remains prohibited.
8. Whether executing any model command remains prohibited.
9. Whether pulling, upgrading, deleting, or replacing models remains prohibited.
10. Whether the recheck result is only a later preflight basis.
11. Whether direct upgrade after the recheck remains prohibited.
12. Whether a later separate review and authorization is still required.

Missing, implied, partial, or template-only approval remains insufficient.

## 9. Latest-Version Recheck Gate Result

Latest-version recheck gate result:

`NOT AUTHORIZED / pending explicit user approval`

Current GO / NO-GO status:

`NO-GO / pending explicit user approval`

Reasoning:

- Current user authorization for latest-version read-only internet recheck has not been received.
- Current model upgrade authorization has not been received.
- KG-RUNTIME-151 cannot query the internet for latest model information.
- KG-RUNTIME-151 cannot execute `ollama pull qwen3.6:35b`.
- KG-RUNTIME-151 cannot enter actual upgrade execution.

This result blocks internet latest-version lookup, all Ollama commands, model upgrade, upgrade preflight as an already-started phase, real use, formal trial use, controlled trial use, and KG-RUNTIME-152 execution.

## 10. Future Recheck Command / Query Boundary

KG-RUNTIME-151 does not execute any internet query or model command.

For a later node, if and only if the user explicitly authorizes it, the boundary may be limited to read-only web recheck. Even then:

- KG-RUNTIME-151 does not perform any internet lookup.
- KG-RUNTIME-151 does not execute any model command.
- A future authorized node may only perform read-only web recheck.
- `ollama list` must not be run.
- `ollama pull qwen3.6:35b` must not be run.
- No Ollama command may be run.
- No model may be automatically downloaded or replaced.

No command candidate is approved by KG-RUNTIME-151.

## 11. Required User Approval Text for KG-RUNTIME-152

If the user later wants KG-RUNTIME-152 to perform latest-version read-only recheck, the user must provide explicit approval text equivalent to:

- 我允许 KG-RUNTIME-152 进行只读联网复核。
- 复核对象仅限 `qwen3.6:35b` / `qwen3` 模型族。
- 允许访问 Ollama 官方模型库。
- 允许访问 Qwen 官方发布渠道。
- 允许访问 Hugging Face 上 Qwen 官方组织页面。
- 禁止扩展查询其他模型族。
- 禁止运行 Ollama。
- 禁止执行 `ollama list`。
- 禁止执行 `ollama pull qwen3.6:35b`。
- 禁止执行任何模型命令。
- 禁止升级、拉取、删除或替换模型。
- 复核结果仅作为后续升级前预检依据。
- 复核完成后仍需回报和审核，不得直接升级。

This template is only the required future approval format. It is not KG-RUNTIME-151 authorization, does not approve internet lookup in KG-RUNTIME-151, does not approve any model command, and does not permit any model upgrade.

## 12. Decision for Next Runtime

Recommended next stage:

`KG-RUNTIME-152: single-model upgrade controlled latest-version recheck docs-only`

KG-RUNTIME-152 may be entered only if the user explicitly approves the latest-version read-only recheck scope, sources, and prohibited boundaries.

KG-RUNTIME-152 must still:

- Not run Ollama.
- Not execute `ollama pull qwen3.6:35b`.
- Not upgrade, pull, delete, or replace any model.
- Only perform read-only internet recheck and result documentation.
- Stop after reporting the result for review.
- Not directly upgrade after the recheck.

After any future latest-version recheck, a separate upgrade preflight node is still required before any upgrade command may be considered.

## 13. Hard NO-GO Conditions

A current or future latest-version recheck or upgrade preparation node must remain `NO-GO / pending explicit user approval` if any of the following conditions apply:

- The user has not explicitly authorized internet recheck.
- The user authorization content is incomplete.
- The recheck scope is unclear.
- The recheck object is not `qwen3.6:35b` / the `qwen3` model family.
- The task needs to expand to other model families but that expansion has not been authorized.
- The task needs to run Ollama.
- The task needs to execute `ollama list`.
- The task needs to execute `ollama pull qwen3.6:35b`.
- The task needs to execute any model command.
- The task needs to upgrade, pull, delete, or replace any model.
- A service is found running and service runtime was not authorized.
- There is endpoint access risk.
- There is real KG file body read risk.
- There is real KG JSON parse risk.
- There is generation, export, or writeback risk.

NO-GO means stop the stage, report the reason, and wait for user review. It does not mean retry, broaden scope, run services, access endpoints, or continue into real use or trial use.

## 14. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Preview-only validation before model upgrade remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 15. Final Compliance Statement

- This stage only adds one docs file.
- This stage did not run Ollama.
- This stage did not execute `ollama list`.
- This stage did not execute any Ollama command.
- This stage did not execute `ollama pull qwen3.6:35b`.
- This stage did not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- This stage did not upgrade, pull, delete, or replace any model.
- This stage did not query the internet for latest-version information.
- This stage did not perform internet expansion lookup.
- This stage did not run the ZDoc service.
- This stage did not access any endpoint.
- This stage did not read real KG.
- This stage did not parse real KG JSON.
- This stage did not execute another directory scan.
- This stage did not trigger generation, export, or writeback.
- This stage did not write `output`, `job`, or `export`.
- This stage did not modify code.
- This stage did not modify adapter, route, helper, or `main.py`.
- This stage did not modify frontend, tests, config, or JSON.
- This stage did not connect RAG, registry, or CI.
- This stage did not add `.pyc` or `__pycache__`.
- This stage did not enter real use.
- This stage did not enter formal trial use.
- This stage did not enter controlled trial use.
- Model upgrade has not been executed.
- KG-RUNTIME-152 has not been entered.
