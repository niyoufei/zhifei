# ZDoc Single-Model Upgrade Qwen3.6 35B Pull Pre-List Blocked Audit - KG-RUNTIME-163-PULL-BLOCKED-AUDIT

## 1. Scope

KG-RUNTIME-163-PULL-BLOCKED-AUDIT is a docs-only blocked audit for the attempted KG-RUNTIME-163-PULL-EXECUTION path.

This node records only the failure fact from the prior pull execution attempt:

`KG-RUNTIME-163-PULL-EXECUTION` was attempted but did not complete.

This node is not a pull execution node, not a model upgrade node, not a stability verification node, and not a real-use or trial-use node.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama serve`.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute `ollama run`.
- Does not execute `ollama rm`.
- Does not execute any other Ollama command.
- Does not pull, upgrade, delete, or replace any model.
- Does not download model files.
- Does not modify the `latest` pointer.
- Does not run the ZDoc service.
- Does not access endpoints.
- Does not read real KG.
- Does not read real KG file body content.
- Does not parse real KG JSON.
- Does not trigger generation, export, or write-back.
- Does not write `output`, `job`, or `export`.
- Does not add a pull execution record file.
- Does not enter KG-RUNTIME-164.
- Does not enter stability verification.
- Does not enter real use or trial use.

## 2. Baseline

The prior KG-RUNTIME-163-PULL-EXECUTION attempt started from:

- Starting HEAD: `d7c2d5fa94ee6802b674b6af1e56b386c4e60e87`
- Starting tag: `v0.1.549-zdoc-single-model-upgrade-qwen3-6-35b-pull-authorization-gate`
- Candidate: `qwen3.6:35b`
- Authorized execution intent: command-limited pull execution for `qwen3.6:35b`

The prior KG-RUNTIME-163-PULL-EXECUTION attempt ended with HEAD still at:

`d7c2d5fa94ee6802b674b6af1e56b386c4e60e87`

No commit, push, or tag was created by the original PULL-EXECUTION node.

## 3. Pull Pre-List Failure Fact

The prior KG-RUNTIME-163-PULL-EXECUTION attempt tried to run the pull-precondition inventory command:

```bash
ollama list
```

The pull-precondition inventory command failed before pull execution.

The complete recorded failure output is:

```text
Error: Head "http://127.0.0.1:11434/": dial tcp 127.0.0.1:11434: connect: operation not permitted
```

Blocked nature:

`PULL PRE-LIST BLOCKED / localhost Ollama endpoint access not permitted`

Because the pull-precondition `ollama list` failed:

- `ollama pull qwen3.6:35b` was not executed.
- The post-pull `ollama list` was not executed.
- Pull execution was not completed.
- Model upgrade did not start.
- The local installed status of `qwen3.6:35b` is not confirmed by this failed attempt.

## 4. Missing Pull Execution Record

No pull execution record file was added by the original KG-RUNTIME-163-PULL-EXECUTION node.

The original KG-RUNTIME-163-PULL-EXECUTION node did not create:

- A completed pull execution docs artifact.
- A commit.
- A push.
- A tag.

Therefore this blocked audit must not be interpreted as a successful pull execution record.

## 5. Current Upgrade State

Current model upgrade state:

`PULL EXECUTION FAILED OR INCOMPLETE / blocked before stability validation`

Current state details:

- `KG-RUNTIME-163-PULL-EXECUTION` was attempted but did not complete.
- Pull-precondition `ollama list` failed.
- `ollama pull qwen3.6:35b` was not executed.
- Post-pull `ollama list` was not executed.
- No model was pulled by this attempt.
- No model was upgraded by this attempt.
- No model was deleted, replaced, or modified by this attempt.
- The `latest` pointer was not modified by this attempt.
- `qwen3.6:35b` installation status remains unconfirmed.
- Model upgrade has not started.

This node records the blocked state only. It must not be treated as pull execution having occurred.

## 6. Preserved Prohibitions

After this blocked audit, the following remain prohibited:

- Do not run Ollama.
- Do not execute `ollama serve`.
- Do not execute `ollama list`.
- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute `ollama run`.
- Do not execute `ollama rm`.
- Do not execute any other Ollama command.
- Do not pull any model.
- Do not delete, replace, or overwrite any model.
- Do not modify the `latest` pointer.
- Do not run the ZDoc service.
- Do not access endpoints.
- Do not read real KG.
- Do not read real KG file body content.
- Do not parse real KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not modify adapter, route, helper, or `main.py` files.
- Do not modify frontend, tests, config, or JSON files.
- Do not connect RAG, registry, or CI.
- Do not enter KG-RUNTIME-164.
- Do not enter stability verification.
- Do not enter real use or trial use.

## 7. Next-Step Boundary

The next step must not directly enter KG-RUNTIME-164.

The next step must not enter stability verification.

The next step must not enter real use or trial use.

The recommended next node is:

`KG-RUNTIME-163-PULL-RETRY-AUTHORIZATION-GATE: qwen3.6:35b pull retry path authorization gate docs-only`

The recommended next node may only form a retry-path authorization gate.

The recommended next node must not directly execute:

- `ollama list`
- `ollama pull qwen3.6:35b`
- Any other Ollama command

## 8. Current Decision

`Current decision: PULL PRE-LIST BLOCKED / localhost Ollama endpoint access not permitted`

Decision basis:

1. KG-RUNTIME-163-PULL-EXECUTION was attempted but did not complete.
2. The pull-precondition `ollama list` failed.
3. The complete recorded failure output is preserved in this document.
4. `ollama pull qwen3.6:35b` was not executed.
5. The post-pull `ollama list` was not executed.
6. No completed pull execution record file was created by the original PULL-EXECUTION node.
7. No commit, push, or tag was created by the original PULL-EXECUTION node.
8. `qwen3.6:35b` installation status is unconfirmed.
9. Model upgrade has not started.
10. Stability validation must not begin.

This is not a GO for KG-RUNTIME-164, stability verification, trial use, or real use.

## 9. Final Status

- KG-RUNTIME-163-PULL-BLOCKED-AUDIT completed as a docs-only blocked audit.
- KG-RUNTIME-163-PULL-EXECUTION was attempted but did not complete.
- Starting HEAD for the failed attempt was `d7c2d5fa94ee6802b674b6af1e56b386c4e60e87`.
- Starting tag for the failed attempt was `v0.1.549-zdoc-single-model-upgrade-qwen3-6-35b-pull-authorization-gate`.
- Ending HEAD for the failed attempt remained `d7c2d5fa94ee6802b674b6af1e56b386c4e60e87`.
- Pull-precondition `ollama list` was attempted in the failed PULL-EXECUTION node.
- Pull-precondition `ollama list` failed.
- Failure output was recorded completely.
- Blocked nature: `PULL PRE-LIST BLOCKED / localhost Ollama endpoint access not permitted`.
- `ollama pull qwen3.6:35b` was not executed.
- Post-pull `ollama list` was not executed.
- No pull execution record file was added by the original PULL-EXECUTION node.
- No commit, push, or tag was created by the original PULL-EXECUTION node.
- This node records only the blocked audit.
- This node does not prove that pull execution occurred.
- `qwen3.6:35b` installation status is unconfirmed.
- Current model upgrade state: `PULL EXECUTION FAILED OR INCOMPLETE / blocked before stability validation`.
- Model upgrade has not started.
- KG-RUNTIME-164 was not entered.
- Stability verification was not entered.
- Trial / real use was not entered.
- Next recommended node: `KG-RUNTIME-163-PULL-RETRY-AUTHORIZATION-GATE: qwen3.6:35b pull retry path authorization gate docs-only`.

KG-RUNTIME-163-PULL-BLOCKED-AUDIT stops here and does not enter the next node, KG-RUNTIME-164, stability verification, trial use, or real use.
