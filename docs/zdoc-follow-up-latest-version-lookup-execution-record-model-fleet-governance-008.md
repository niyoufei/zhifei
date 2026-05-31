# ZDoc Follow-Up Latest-Version Lookup Execution Record - MODEL-FLEET-GOVERNANCE-008

## 1. Node

`MODEL-FLEET-GOVERNANCE-008-FOLLOW-UP-LATEST-LOOKUP-EXECUTION`

This node records a docs-only, read-only follow-up latest-version lookup after explicit user authorization.

This node does not run Ollama, does not execute any Ollama command, does not upgrade, pull, delete, replace, run, or test any model, does not modify any `latest` pointer, does not download model files, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. User Authorization Summary

The user explicitly authorized `MODEL-FLEET-GOVERNANCE-008` to execute follow-up latest-version lookup.

The authorization scope was limited to:

1. Read-only online verification of official latest-version wording for `qwen3.6` / `qwen3`.
2. Read-only online verification of naming differences between `qwen3.6:35b` and official / Ollama / Hugging Face naming.
3. Read-only online verification of whether a same-family candidate is more suitable for ZDoc copy output, construction organization design, technical-bid preparation, and long-document structured output.
4. Supplemental read-only verification for `deepseek-r1`, `qwen3-next`, and `qwen3-coder` only where relevant to text-model priority judgment.
5. Docs-only recording of the lookup results.

This authorization does not authorize model upgrade, model pull, model deletion, model replacement, `latest` pointer modification, model-file download, image generation, image-model invocation, ZDoc service execution, endpoint access, real KG reading, real KG parsing, generation, export, write-back, real use, controlled trial, or limited concurrent trial.

## 3. Starting State

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `bba175378bc1b6f1be9bd00b78159000dd55db29`
- Starting remote tag record: `v0.1.567-zdoc-follow-up-latest-version-lookup-authorization-gate`
- Initial `git status --short`: clean

The starting remote tag record is treated as the controller-provided record from the execution instruction.

This node did not live-query the remote tag.

This node did not execute `git ls-remote`.

## 4. Prescribed Docs Read

The following prescribed docs files were readable and were read before lookup:

1. `docs/zdoc-follow-up-latest-version-lookup-authorization-gate-model-fleet-governance-007.md`
2. `docs/zdoc-text-model-upgrade-authorization-gate-model-fleet-governance-006.md`
3. `docs/zdoc-model-fleet-upgrade-candidate-priority-and-next-action-gate-model-fleet-governance-005.md`
4. `docs/zdoc-domestic-top-tier-model-fleet-latest-lookup-insufficient-source-closure-model-fleet-governance-004.md`
5. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-execution-record-model-fleet-governance-003.md`
6. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-authorization-gate-model-fleet-governance-002.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 5. Actual Read-Only Online Lookup Scope

The actual follow-up lookup was limited to:

1. `qwen3.6` / `qwen3` official latest-version wording.
2. `qwen3.6:35b` official / Ollama / Hugging Face naming differences.
3. Same-family Qwen candidates relevant to ZDoc copy output, construction organization design, technical-bid preparation, and long-document structured output.
4. Supplemental `deepseek-r1` latest-version wording.
5. Supplemental `qwen3-next` latest-version wording.
6. Supplemental `qwen3-coder` latest-version wording.

No unrelated model family was included as an upgrade basis.

## 6. Official / Trusted Sources Actually Accessed

Only official / trusted sources were used for conclusions:

1. Qwen official release pages:
   - `https://qwen.ai/blog?id=qwen3.6-35b-a3b`
   - `https://qwen.ai/blog?id=qwen3.6-27b`
   - `https://qwenlm.github.io/blog/qwen3/`
2. Qwen official Hugging Face organization model cards:
   - `https://huggingface.co/Qwen/Qwen3.6-35B-A3B`
   - `https://huggingface.co/Qwen/Qwen3.6-27B`
   - `https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507`
   - `https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507`
   - `https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct`
   - `https://huggingface.co/Qwen/Qwen3-Coder-Next`
3. Ollama official model library pages:
   - `https://ollama.com/library/qwen3.6`
   - `https://ollama.com/library/qwen3.6:35b`
   - `https://ollama.com/library/qwen3.6:27b`
   - `https://ollama.com/library/qwen3`
   - `https://ollama.com/library/qwen3:30b`
   - `https://ollama.com/library/qwen3:14b`
   - `https://ollama.com/library/qwen3:8b`
   - `https://ollama.com/library/qwen3:0.6b`
   - `https://ollama.com/library/qwen3-next`
   - `https://ollama.com/library/qwen3-coder`
   - `https://ollama.com/library/qwen3-coder-next`
   - `https://ollama.com/library/deepseek-r1`
4. DeepSeek official release / organization sources:
   - `https://api-docs.deepseek.com/news/news250528`
   - `https://huggingface.co/deepseek-ai/DeepSeek-R1-0528`

No non-official source was used as upgrade evidence.

No model files were downloaded from any source.

## 7. `qwen3.6` / `qwen3` Latest-Version Wording

### 7.1 `qwen3.6`

Official / trusted source result:

1. Qwen official sources identify `Qwen3.6-35B-A3B` as a Qwen3.6 open-weight model with 35B total parameters and 3B activated parameters.
2. Qwen official sources also identify `Qwen3.6-27B` as a 27B dense Qwen3.6 model.
3. Ollama official library records `qwen3.6:latest` and `qwen3.6:35b` pointing to the 35B-A3B variant.
4. Ollama official library also records `qwen3.6:27b` as a separately available tag.

Status:

`qwen3.6:35b` remains an evidence-backed current local baseline from the online source side, but this node did not re-check local digest or installed state because Ollama execution was prohibited.

### 7.2 `qwen3`

Official / trusted source result:

1. Qwen official sources identify `Qwen3-30B-A3B-Instruct-2507` as a 30B / 3B activated Qwen3 Instruct candidate with improved alignment, instruction following, and long-context handling.
2. Qwen official sources identify `Qwen3-235B-A22B-Instruct-2507` as a larger 235B / 22B activated candidate.
3. Ollama official library records `qwen3:latest` and `qwen3:30b` pointing to the 30B-A3B candidate.
4. Ollama official library records `qwen3:14b`, `qwen3:8b`, and `qwen3:0.6b` as separate tags.

Status:

`Qwen3-30B-A3B-Instruct-2507` / Ollama `qwen3:30b` is the most relevant same-family Qwen3 text candidate for near-term ZDoc prose and long-document comparison under this lookup. The larger 235B candidate is not treated as a near-term local deployment target under this node.

## 8. `qwen3.6:35b` Naming Differences

| Layer | Observed name or tag | Difference judgment |
|---|---|---|
| Qwen official release / model-card naming | `Qwen3.6-35B-A3B` | Full official family / size / MoE naming. |
| Hugging Face official organization model name | `Qwen/Qwen3.6-35B-A3B` | Full official repository name. |
| Ollama official model-library tag | `qwen3.6:35b`; `qwen3.6:latest` | Lowercase registry tag; omits `A3B`; `latest` is an Ollama registry tag, not local installed-state proof. |
| Prior-doc local tag | `qwen3.6:35b` | Matches the Ollama tag spelling, but local digest was not rechecked in this node. |

Controller status:

`NAME OR TAG MISMATCH RECORDED / upgrade authorization requires explicit target`

Any later authorization must explicitly name the target as an Ollama tag, official Hugging Face model name, or both. This node does not authorize changing or re-pointing `latest`.

## 9. Same-Family Candidate Suitability For ZDoc Text Output

The follow-up lookup identifies the following same-family candidates:

| Candidate | Source basis | ZDoc suitability judgment | Controller status |
|---|---|---|---|
| `qwen3.6:35b` / `Qwen/Qwen3.6-35B-A3B` | Qwen official release / model card plus Ollama official library | Keep as evidence-backed current baseline. No upgrade action is recommended by this node for this already-recorded local baseline. | `OBSERVE / keep installed model and monitor` |
| `qwen3.6:27b` / `Qwen/Qwen3.6-27B` | Qwen official release / model card plus Ollama official library | Same-family alternative with lower downloaded size than the 35B-A3B Ollama tag. Useful as a possible later comparison target, but not proven by this node to be strictly better for ZDoc copy output than `qwen3.6:35b`. | `READY FOR SINGLE-MODEL UPGRADE AUTHORIZATION / source sufficient` |
| `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507` | Qwen official model card plus Ollama official library | Most relevant same-family text candidate for ZDoc prose, construction organization design, technical-bid drafting, and long-document structured output because official wording emphasizes updated Instruct alignment, text generation, instruction following, and long-context handling. | `NAME OR TAG MISMATCH RECORDED / upgrade authorization requires explicit target` |
| `qwen3:235b` / `Qwen/Qwen3-235B-A22B-Instruct-2507` | Qwen official model card plus Ollama official library | Strong official text candidate, but not treated as a near-term local deployment candidate under this node due very large footprint and no local authorization. | `HOLD / no upgrade action recommended` |
| `qwen3:14b`, `qwen3:8b`, `qwen3:0.6b` | Ollama official model library plus Qwen family sources | Smaller legacy / lightweight tags are not identified as better than the current `qwen3.6:35b` baseline for ZDoc long-form quality. | `OBSERVE / keep installed model and monitor` |

Conclusion:

There is a same-family candidate worth a later explicit single-model authorization gate: `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507`.

There is also a same-family comparison candidate: `qwen3.6:27b` / `Qwen/Qwen3.6-27B`.

This node does not authorize pulling, replacing, deleting, validating, or using either candidate.

## 10. `deepseek-r1` Supplemental Result

Official / trusted source result:

1. DeepSeek official release notes and DeepSeek official Hugging Face organization identify `DeepSeek-R1-0528` as the current refreshed R1 candidate.
2. DeepSeek official sources also identify `DeepSeek-R1-0528-Qwen3-8B` as a distilled candidate.
3. Ollama official library exposes `deepseek-r1` tags, including 0528-related tags for 8B and 671B-scale variants.
4. Prior docs record the local model only as `deepseek-r1:32b`; this node did not run Ollama and did not re-check local digest or installed state.

Status:

`NAME OR TAG MISMATCH RECORDED / upgrade authorization requires explicit target`

`deepseek-r1` remains a reasoning-model candidate, not the main near-term ZDoc prose output candidate from this follow-up lookup.

## 11. `qwen3-next` Supplemental Result

Official / trusted source result:

1. Qwen official model card identifies `Qwen/Qwen3-Next-80B-A3B-Instruct`.
2. Ollama official library records the primary registry tag as `qwen3-next:80b`.
3. Prior docs record the local tag as `qwen3-next:80b-a3b-instruct-q8_0`, which is more specific than the official / Ollama primary naming.
4. This node did not run Ollama and did not re-check local digest or installed state.

Status:

`NAME OR TAG MISMATCH RECORDED / upgrade authorization requires explicit target`

`qwen3-next` remains an observe / naming-closure candidate. It is not selected as the primary near-term ZDoc prose upgrade object by this node.

## 12. `qwen3-coder` Supplemental Result

Official / trusted source result:

1. Qwen official model card identifies `Qwen/Qwen3-Coder-Next` as an 80B / 3B activated coding-focused model.
2. Ollama official library exposes `qwen3-coder:30b`, `qwen3-coder:480b`, and `qwen3-coder-next` candidates.
3. Prior docs record the local model only as `qwen3-coder:30b`; this node did not run Ollama and did not re-check local digest or installed state.

Status:

`HOLD / no upgrade action recommended`

`qwen3-coder` remains relevant to code and system-development assistance, but it is not more suitable than the Qwen text candidates for ZDoc prose output, construction organization design, technical-bid drafting, or long-document structured output.

## 13. Current Known Local Models Versus Follow-Up Lookup

This node did not run Ollama and did not re-check local model inventory. The local model list below is inherited only from prior docs:

| Prior-doc local model | Follow-up source comparison | Difference judgment |
|---|---|---|
| `qwen3.6:35b` | Qwen official `Qwen3.6-35B-A3B`; Ollama `qwen3.6:35b` / `qwen3.6:latest` | Online source identity aligns with the prior local tag. Local digest not rechecked. |
| `qwen3-next:80b-a3b-instruct-q8_0` | Qwen official `Qwen3-Next-80B-A3B-Instruct`; Ollama `qwen3-next:80b` | Naming / tag mismatch remains. Local digest not rechecked. |
| `qwen3-coder:30b` | Qwen official Coder-Next and Ollama `qwen3-coder` / `qwen3-coder-next` candidates | Stronger coding-family candidates exist, but this is not a ZDoc prose priority. Local digest not rechecked. |
| `deepseek-r1:32b` | DeepSeek official `DeepSeek-R1-0528`; Ollama 0528-related `deepseek-r1` candidates | Local tag does not identify the 0528 candidate. Local digest not rechecked. |
| `qwen3:30b` | Qwen official `Qwen3-30B-A3B-Instruct-2507`; Ollama `qwen3:30b` | Same-family text candidate suitable for a later explicit target gate. Local digest not rechecked. |
| `qwen3:14b` | Ollama `qwen3:14b` tag exists; no better exact 14B same-family target selected by this node | Keep / observe. Local digest not rechecked. |
| `qwen3:8b` | Ollama `qwen3:8b` tag exists; no better exact 8B same-family target selected by this node | Keep / observe. Local digest not rechecked. |
| `qwen3:0.6b` | Ollama `qwen3:0.6b` tag exists; no better exact 0.6B same-family target selected by this node | Keep / observe. Local digest not rechecked. |

## 14. Remaining Source-Insufficient Items

The online latest lookup source basis is sufficient to identify the relevant same-family Qwen candidates and supplemental DeepSeek / Qwen3-Next / Qwen3-Coder candidates.

The following items remain insufficient for execution because this node was prohibited from running Ollama:

1. Exact current local digest / installed-state confirmation for every prior-doc local model tag.
2. Exact current local state behind `qwen3.6:35b`.
3. Exact current local state behind `qwen3:30b`.
4. Exact current local state behind `qwen3-next:80b-a3b-instruct-q8_0`.
5. Exact current local state behind `deepseek-r1:32b`.

These source-insufficient items do not block forming a later single-model authorization gate, but they do block any upgrade execution in this node.

## 15. Naming / Version-Policy Differences

Naming or version-policy differences still exist:

1. Official Qwen model names use full model names such as `Qwen3.6-35B-A3B` and `Qwen3-30B-A3B-Instruct-2507`.
2. Ollama registry tags use short lowercase names such as `qwen3.6:35b` and `qwen3:30b`.
3. Hugging Face official model names include organization prefixes such as `Qwen/Qwen3.6-35B-A3B`.
4. Ollama `latest` is a registry tag and must not be treated as proof of local installed state.
5. Prior-doc local tags do not prove current local digest because this node did not run Ollama.

Controller status:

`NAME OR TAG MISMATCH RECORDED / upgrade authorization requires explicit target`

## 16. Single-Model Upgrade Authorization Gate Candidate

This follow-up lookup forms the basis for a later single-model authorization gate, but does not authorize upgrade.

Candidate suitable for later explicit authorization:

1. Primary text candidate:
   - Official model name: `Qwen/Qwen3-30B-A3B-Instruct-2507`
   - Ollama registry tag: `qwen3:30b`
   - Reason: same-family Qwen text model with official source support for updated Instruct alignment, text generation, instruction following, and long-context handling.
2. Secondary comparison candidate:
   - Official model name: `Qwen/Qwen3.6-27B`
   - Ollama registry tag: `qwen3.6:27b`
   - Reason: Qwen3.6 same-family candidate with lower Ollama footprint than `qwen3.6:35b`, suitable only for later human-authorized comparison.

No model upgrade is authorized.

No `ollama pull` is authorized.

No model replacement is authorized.

No deletion is authorized.

No `latest` pointer modification is authorized.

## 17. Upgrade Governance Principles

1. This node is only follow-up latest lookup.
2. Latest lookup is not model upgrade authorization.
3. Finding a new version does not authorize `ollama pull`.
4. Finding a stronger candidate does not authorize replacement of any existing model.
5. Single-model upgrade must separately form explicit user authorization.
6. Single-model upgrade authorization must explicitly state target model name, target tag, download size or size-unknown status, disk precheck, whether `ollama list` is allowed, and whether `ollama pull` is allowed.
7. Single-model upgrade must be followed by stability validation.
8. Single-model upgrade must be followed by preview-only review.
9. Before stability validation and preview-only review are complete, the model must not enter real use or trial.
10. Old models must not be automatically deleted.
11. Any `latest` pointer must not be automatically modified.

## 18. Current Decision

Current decision:

`FOLLOW-UP LATEST LOOKUP COMPLETED / SINGLE-MODEL UPGRADE AUTHORIZATION GATE REQUIRED / NO MODEL UPGRADE AUTHORIZED`

Reason:

The lookup is sufficient to identify same-family Qwen candidates for later explicit target-gate review, especially `qwen3:30b` / `Qwen/Qwen3-30B-A3B-Instruct-2507`, while preserving the current `qwen3.6:35b` baseline and recording naming / tag mismatch.

Explicit NO-GO:

`NO-GO FOR MODEL UPGRADE / NO-GO FOR IMAGE GENERATION EXECUTION / NO-GO FOR REAL USE / NO-GO FOR TRIAL`

This decision does not authorize model upgrade.

This decision does not authorize model pull.

This decision does not authorize model deletion.

This decision does not authorize model replacement.

This decision does not authorize `latest` pointer modification.

This decision does not authorize model download.

This decision does not authorize image model integration.

This decision does not authorize image generation.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG reading or parsing.

This decision does not authorize generation, export, or write-back.

This decision does not authorize real use.

This decision does not authorize trial.

This decision does not authorize 1-2 person controlled trial.

This decision does not authorize 2-5 person limited concurrent trial.

## 19. Next Node Suggestion

Suggested next node after human review:

`MODEL-FLEET-GOVERNANCE-009-SINGLE-MODEL-UPGRADE-AUTHORIZATION-GATE`

The later node must explicitly identify the single target model object and must separately authorize any local inventory check, disk precheck, pull, stability validation, and preview-only review.

This node does not enter any next node.

Alternative later paths remain:

1. `MODEL-FLEET-GOVERNANCE-009-REMAINING-LOOKUP-INSUFFICIENT-SOURCE-CLOSURE` if the human reviewer decides that local digest closure must be separated before target-gate formation.
2. `MODEL-FLEET-GOVERNANCE-009-MODEL-HOLD-AND-OBSERVE-GATE` if the human reviewer decides not to pursue any model action.
3. `KG-RUNTIME-171-KG-SAFETY-AUTHORIZATION-GATE` if the human reviewer decides to return to the KG safety mainline.
4. `IMAGE-GOVERNANCE-001-CONSTRUCTION-IMAGE-MODEL-SELECTION-GATE` if the human reviewer decides to enter image governance.

This node enters none of those paths.

## 20. Prohibited Actions Record

- Ran Ollama: no
- Executed `ollama list`: no
- Executed `ollama pull`: no
- Executed `ollama run`: no
- Executed `ollama rm`: no
- Executed `ollama serve`: no
- Executed any Ollama command: no
- Upgraded any model: no
- Pulled any model: no
- Deleted any model: no
- Replaced any model: no
- Modified `latest` pointer: no
- Downloaded model files: no
- Ran ZDoc service: no
- Accessed endpoint: no
- Read real KG file body content: no
- Parsed real KG JSON: no
- Triggered generation: no
- Triggered export: no
- Triggered write-back: no
- Wrote `output`: no
- Wrote `job`: no
- Wrote `export`: no
- Used real project material: no
- Used real business data: no
- Generated images: no
- Called image generation tool or image model: no
- Entered real use or trial: no
- Entered 1-2 person controlled trial: no
- Entered 2-5 person limited concurrent trial: no
- Treated this node as model upgraded: no
- Treated this node as allowing `ollama pull`: no
- Treated this node as allowing deletion, replacement, or `latest` pointer modification: no
- Treated this node as image generation capability already available: no
- Treated this node as formal trial readiness: no
- Performed directory scan again: no
- Modified adapter / route / helper / `main.py`: no
- Modified frontend / tests / config / JSON: no
- Connected RAG / registry / CI: no
- Added `.pyc` / `__pycache__`: no

## 21. Final Status

- `MODEL-FLEET-GOVERNANCE-008-FOLLOW-UP-LATEST-LOOKUP-EXECUTION` completed as a docs-only follow-up latest-version lookup execution record.
- The prescribed prior docs files were read.
- Read-only online follow-up lookup was performed.
- Only the authorized model families were checked.
- Only official / trusted sources were used for conclusions.
- `qwen3.6` / `qwen3` latest-version wording was recorded.
- `qwen3.6:35b` official / Ollama / Hugging Face naming differences were recorded.
- Same-family Qwen text candidates for ZDoc copy output were recorded.
- `deepseek-r1` supplemental result was recorded.
- `qwen3-next` supplemental result was recorded.
- `qwen3-coder` supplemental result was recorded.
- Current known local models versus follow-up lookup results were recorded.
- Remaining local digest / installed-state insufficiency was recorded.
- Naming / version-policy differences were recorded.
- Single-model authorization gate candidate was recorded.
- Current decision: `FOLLOW-UP LATEST LOOKUP COMPLETED / SINGLE-MODEL UPGRADE AUTHORIZATION GATE REQUIRED / NO MODEL UPGRADE AUTHORIZED`
- Explicit NO-GO: `NO-GO FOR MODEL UPGRADE / NO-GO FOR IMAGE GENERATION EXECUTION / NO-GO FOR REAL USE / NO-GO FOR TRIAL`
- Suggested next node: `MODEL-FLEET-GOVERNANCE-009-SINGLE-MODEL-UPGRADE-AUTHORIZATION-GATE`
- The next node was not entered.

MODEL-FLEET-GOVERNANCE-008 stops here and waits for human review.
