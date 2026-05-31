# MODEL-FLEET-GOVERNANCE-009: Single-Model Upgrade Authorization Gate

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `3eec729f0e1de42ffa5d8fdb7ad3dc57309fe1e5`
- Starting tag at HEAD: none
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-008`
- Previous decision:

  `FOLLOW-UP LATEST LOOKUP COMPLETED / SINGLE-MODEL UPGRADE AUTHORIZATION GATE REQUIRED / NO MODEL UPGRADE AUTHORIZED`

This node is a docs-only single-model upgrade authorization gate.

This node does not run Ollama, does not execute any Ollama command, does not perform online lookup, does not upgrade, pull, delete, replace, run, or test any model, does not modify any `latest` pointer, does not download model files, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-follow-up-latest-version-lookup-execution-record-model-fleet-governance-008.md`
2. `docs/zdoc-follow-up-latest-version-lookup-authorization-gate-model-fleet-governance-007.md`
3. `docs/zdoc-text-model-upgrade-authorization-gate-model-fleet-governance-006.md`
4. `docs/zdoc-model-fleet-upgrade-candidate-priority-and-next-action-gate-model-fleet-governance-005.md`
5. `docs/zdoc-domestic-top-tier-model-fleet-latest-lookup-insufficient-source-closure-model-fleet-governance-004.md`
6. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-execution-record-model-fleet-governance-003.md`

No other model source was queried.

No new candidate was added beyond the prior-doc evidence.

## 3. Candidate Review

Based on the prior docs, the single-model upgrade authorization gate can be formed around the same-family Qwen text candidates only.

| Candidate | Prior-doc support | ZDoc suitability judgment | Gate judgment |
|---|---|---|---|
| `qwen3.6:35b` / `Qwen/Qwen3.6-35B-A3B` | `MODEL-FLEET-GOVERNANCE-003`, `004`, `006`, and `008` record it as the current evidence-backed local baseline from prior docs and official / trusted source comparison. | Current baseline for ZDoc text output. Prior docs do not identify a need to re-pull or replace it in this node. | Retain as baseline; no upgrade action authorized. |
| `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507` | `MODEL-FLEET-GOVERNANCE-008` records it as the most relevant same-family Qwen3 text candidate for near-term ZDoc prose and long-document comparison, with naming / tag mismatch requiring explicit target authorization. | Candidate most directly relevant to ZDoc copy output, construction organization design, technical-bid drafting, and long-document structured output under prior-doc evidence. It is not locally execution-proven by this node. | Primary candidate for a later explicit single-model upgrade execution authorization node. |
| `qwen3.6:27b` / `Qwen/Qwen3.6-27B` | `MODEL-FLEET-GOVERNANCE-008` records it as a Qwen3.6 same-family comparison candidate with lower Ollama footprint than `qwen3.6:35b`. | Useful only as a later human-authorized comparison target. Prior docs do not prove it is strictly better than `qwen3.6:35b` for ZDoc copy output. | Secondary comparison candidate; no upgrade action authorized. |
| `qwen3:235b` / `Qwen/Qwen3-235B-A22B-Instruct-2507` | `MODEL-FLEET-GOVERNANCE-003`, `004`, and `008` record it as a strong Qwen3 text candidate. | Strong official text candidate, but not treated as a near-term local deployment target under prior-doc governance due very large footprint and no local authorization. | Hold; no near-term upgrade execution gate selected. |
| `qwen3:14b`, `qwen3:8b`, `qwen3:0.6b` | Prior docs record them as local Qwen3 tags, with exact latest or local digest closure gaps for at least part of this set. | Not identified as better than the current `qwen3.6:35b` baseline for ZDoc long-form quality. | Observe; no upgrade action authorized. |

Candidate conclusion:

1. `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507` is the only primary same-family candidate suitable for forming the next explicit single-model upgrade execution authorization gate.
2. `qwen3.6:27b` / `Qwen/Qwen3.6-27B` is retained only as a secondary comparison candidate.
3. The current installed baseline remains prior-doc `qwen3.6:35b`.
4. Prior docs support that `qwen3:30b` may be better suited for ZDoc prose, construction organization design, technical-bid drafting, and long-document structured output review than the current baseline, but no execution, local inventory check, pull, validation, or real-use test was performed here.
5. No candidate is authorized for upgrade by this node.

## 4. Authorization Boundary

This node is only an authorization gate.

This node is not upgrade authorization.

This node is not pull authorization.

This node is not authorization to run Ollama.

This node is not authorization to run `ollama list`.

This node is not authorization to run `ollama pull`.

This node is not authorization to modify any `latest` pointer.

This node is not authorization to run the ZDoc service.

This node is not authorization to access endpoints.

This node is not authorization to read or parse real KG.

This node is not authorization to trigger generation / export / write-back.

This node is not authorization to write `output`, `job`, or `export`.

This node is not authorization to generate images or call image generation tools.

This node is not authorization to enter real use, trial, 1-2 person controlled trial, or 2-5 person limited concurrent trial.

## 5. Future User Authorization Template

The following template is only a future authorization template.

It is not authorization granted by this node.

It must not be treated as already authorized.

Future authorization template:

```text
I explicitly authorize MODEL-FLEET-GOVERNANCE-010-SINGLE-MODEL-UPGRADE-EXECUTION-AUTHORIZATION for one model only.

Required itemized authorization:

1. Concrete model allowed for execution:
   - Official model name: <required>
   - Ollama registry tag: <required>
2. Is `ollama list` allowed before execution: yes / no
3. Is `ollama pull <model>` allowed: yes / no
4. Is pull-before and pull-after inventory recording allowed: yes / no
5. Is `ollama rm` prohibited: yes / no
6. Is replacing any other model prohibited: yes / no
7. Is modifying any `latest` pointer prohibited: yes / no
8. Is running the ZDoc service prohibited: yes / no
9. Is accessing endpoints prohibited: yes / no
10. Is reading real KG prohibited: yes / no
11. Is triggering generation / export / write-back prohibited: yes / no
12. Must the node stop after completion and wait for human review: yes / no
```

Minimum recommended target if the user later authorizes execution:

- Official model name: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- Ollama registry tag: `qwen3:30b`

The target above is a future authorization candidate only.

It is not authorized for pull, upgrade, validation, real use, or trial by this node.

## 6. Current Decision

Current decision:

`SINGLE-MODEL UPGRADE AUTHORIZATION GATE FORMED / NO MODEL UPGRADE AUTHORIZED`

This decision forms the authorization wording needed before a later explicit execution-authorization node.

This decision does not authorize model upgrade.

This decision does not authorize model pull.

This decision does not authorize model deletion.

This decision does not authorize model replacement.

This decision does not authorize `latest` pointer modification.

This decision does not authorize model download.

## 7. NO-GO Statements

`NO-GO FOR MODEL UPGRADE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR KG READ / PARSE`

## 8. Next Recommended Node

Recommended next node after human review:

`MODEL-FLEET-GOVERNANCE-010-SINGLE-MODEL-UPGRADE-EXECUTION-AUTHORIZATION`

That next node still requires explicit itemized user authorization.

Before that explicit authorization is granted:

1. Do not run Ollama.
2. Do not execute `ollama pull`.
3. Do not upgrade any model.
4. Do not modify any `latest` pointer.
5. Do not run the ZDoc service.
6. Do not access endpoints.
7. Do not read or parse real KG.
8. Do not trigger generation / export / write-back.
9. Do not enter real use or trial.

This node does not enter `MODEL-FLEET-GOVERNANCE-010`.

MODEL-FLEET-GOVERNANCE-009 stops here and waits for human review.
