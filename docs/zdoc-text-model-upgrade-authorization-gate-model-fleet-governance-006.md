# ZDoc Text Model Upgrade Authorization Gate - MODEL-FLEET-GOVERNANCE-006

## 1. Node

`MODEL-FLEET-GOVERNANCE-006-TEXT-MODEL-UPGRADE-AUTHORIZATION-GATE`

This node forms a docs-only highest-priority text model upgrade authorization gate based on:

`MODEL-FLEET-GOVERNANCE-005-UPGRADE-CANDIDATE-PRIORITY-GATE`

This node does not run Ollama, does not execute any Ollama command, does not query latest model versions online, does not access any model official site / model repository / GitHub / Hugging Face / Ollama model library, does not upgrade, pull, delete, or replace any model, does not modify any `latest` pointer, does not download model files, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Starting State

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `dbc2d64d884ffa41e8240b61430b12804cdd21d9`
- Starting remote tag record: `v0.1.565-zdoc-model-fleet-upgrade-candidate-priority-gate`
- Initial `git status --short`: clean

The starting remote tag record is treated as the controller-provided record from this node instruction.

This node did not live-query the remote tag.

This node did not execute `git ls-remote`.

## 3. Prescribed Docs Read

The following prescribed docs files were readable and were read:

1. `docs/zdoc-model-fleet-upgrade-candidate-priority-and-next-action-gate-model-fleet-governance-005.md`
2. `docs/zdoc-domestic-top-tier-model-fleet-latest-lookup-insufficient-source-closure-model-fleet-governance-004.md`
3. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-execution-record-model-fleet-governance-003.md`
4. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-authorization-gate-model-fleet-governance-002.md`
5. `docs/zdoc-local-domestic-top-tier-model-fleet-and-construction-image-generation-governance-gate-model-fleet-governance-001.md`
6. `docs/zdoc-preview-only-validation-result-review-and-kg-safety-gate-kg-runtime-170.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 4. Current Facts

1. `MODEL-FLEET-GOVERNANCE-005` has completed and is treated under the human-review-passed wording for this node.
2. The current model-fleet priority gate has been formed.
3. No text model upgrade is currently authorized.
4. No `ollama pull` has been executed by this node.
5. No model has been deleted, replaced, or overwritten by this node.
6. No `latest` pointer has been modified by this node.
7. No online follow-up lookup has been performed by this node.
8. This node has not entered image model selection gate.
9. Image generation has not been authorized.
10. This node has not entered real use or trial.
11. Current status remains:

   `NO-GO FOR MODEL UPGRADE`

   `NO-GO FOR IMAGE GENERATION EXECUTION`

   `NO-GO FOR REAL USE`

   `NO-GO FOR TRIAL`

## 5. Highest-Priority Text Model Candidate

Based on `MODEL-FLEET-GOVERNANCE-005`, the highest-priority text model candidate is:

- Candidate family name: `qwen3.6` / `qwen3`
- Existing local models recorded in prior docs:
  1. `qwen3.6:35b`
  2. `qwen3:30b`
  3. `qwen3:14b`
  4. `qwen3:8b`
  5. `qwen3:0.6b`
- Latest lookup result summary from prior docs:
  1. `qwen3.6:35b` was recorded as current / latest-confirmed by official-source lookup evidence in `MODEL-FLEET-GOVERNANCE-003`, but local digest was not rechecked because Ollama execution was prohibited.
  2. `Qwen/Qwen3-30B-A3B-Instruct-2507` and `Qwen/Qwen3-235B-A22B-Instruct-2507` were recorded as Qwen3 2507 candidates.
  3. `qwen3:8b` was recorded as latest in the Ollama official library in prior docs, but local digest was not rechecked.
  4. Exact latest status for `qwen3:14b` and `qwen3:0.6b` was not confirmed from the checked official sources in prior docs.
- Source insufficiency:
  1. Source is sufficient only for retaining `qwen3.6:35b` as an evidence-backed candidate / current local baseline.
  2. Source remains insufficient for exact local digest / installed-version closure of `qwen3:30b` and `qwen3:8b`.
  3. Source remains insufficient for exact latest status of `qwen3:14b` and `qwen3:0.6b`.
- Naming or tag differences:
  1. Qwen official model names use full names such as `Qwen3.6-35B-A3B`, while local tags use Ollama-style tags such as `qwen3.6:35b`.
  2. Qwen3 2507 official names include `A3B-Instruct-2507`, while local short tags such as `qwen3:30b` do not identify the exact official release / digest state.
  3. Ollama `latest` tags are registry tags and must not be treated as local installation state without a separately authorized local inventory / digest check.
- Suitability for per-model upgrade authorization:
  1. `qwen3.6:35b` is suitable for retention / no-upgrade-priority review, but this node does not authorize re-pull, replacement, digest confirmation, or validation.
  2. The `qwen3` local tags are not suitable for immediate upgrade execution authorization because exact local digest / installed-version closure, target candidate selection, and naming / tag closure remain unresolved.
  3. The highest-priority family should enter supplemental lookup authorization before any actual upgrade execution authorization.

Required branch:

`MODEL-FLEET-GOVERNANCE-007-FOLLOW-UP-LATEST-LOOKUP-AUTHORIZATION-GATE`

This branch is required before any `qwen3` family upgrade execution if the target object is not a fully closed, single local model object.

## 6. Upgrade Authorization Preconditions

Before any later actual text model upgrade may execute, the following minimum conditions must be satisfied:

1. A single model object must be explicitly identified.
2. The current local installed version must be explicitly identified.
3. The target candidate version must be explicitly identified.
4. Download size or size-unknown status must be explicitly identified.
5. Disk-space precheck requirements must be explicitly identified.
6. Whether `ollama list` is allowed must be explicitly authorized.
7. Whether `ollama pull <model>` is allowed must be explicitly authorized.
8. Whether retaining the old model is allowed or required must be explicitly identified.
9. Deleting or replacing non-target models must remain prohibited.
10. Modifying any `latest` pointer must remain prohibited unless separately authorized.
11. Post-upgrade stability validation requirements must be explicitly identified.
12. Post-upgrade preview-only review requirements must be explicitly identified.

## 7. User Authorization Requirement And Template

If a later node enters actual model upgrade execution, explicit user authorization is required.

**是否需要用户授权：需要。**

Future authorization template:

“我明确授权 MODEL-FLEET-GOVERNANCE-007 执行 `<目标模型>` 单模型升级。授权范围仅限：确认 git 状态、读取前序 docs、执行升级前 `ollama list`、执行 `ollama pull <目标模型>`、执行升级后 `ollama list`、生成 docs-only 升级记录、commit、push、创建远端 tag。禁止 `ollama run`、禁止 `ollama rm`、禁止 `ollama serve`、禁止删除或替换其他模型、禁止修改 latest 指向、禁止运行 ZDoc 服务、禁止访问 endpoint、禁止读取或解析真实 KG、禁止触发 generation/export/write-back、禁止生成图片、禁止进入真实使用/试用阶段。”

The template above is not authorization granted by this node.

This node does not authorize `MODEL-FLEET-GOVERNANCE-007` upgrade execution.

This node does not authorize `ollama pull`.

## 8. Subsequent Path Judgment

### Path A: single-model upgrade execution authorization

If a highest-priority text model candidate later has sufficient evidence and the user explicitly authorizes every required action, the suggested node is:

`MODEL-FLEET-GOVERNANCE-007-SINGLE-TEXT-MODEL-UPGRADE-EXECUTION: single text model upgrade after explicit user authorization`

This path may execute only after itemized explicit user authorization.

This node does not enter Path A.

### Path B: supplemental latest lookup authorization

Because the highest-priority `qwen3.6` / `qwen3` family still contains local digest, installed-version, source-insufficient, naming, and tag-closure gaps for the upgrade-relevant local `qwen3` tags, the recommended next node is:

`MODEL-FLEET-GOVERNANCE-007-FOLLOW-UP-LATEST-LOOKUP-AUTHORIZATION-GATE`

This path may only form supplemental lookup authorization and must not perform upgrade execution unless a later node separately authorizes it.

### Path C: image model selection gate

Image / multimodal candidates remain an independent branch:

`IMAGE-GOVERNANCE-001-CONSTRUCTION-IMAGE-MODEL-SELECTION-GATE`

This node does not enter image model integration and does not generate images.

## 9. Current Decision

Current decision:

`TEXT MODEL UPGRADE AUTHORIZATION BLOCKED / FOLLOW-UP LOOKUP REQUIRED`

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

## 10. Prohibited Actions Record

- Ran Ollama: no
- Executed any Ollama command: no
- Queried latest model versions online: no
- Accessed any model official site / model repository / GitHub / Hugging Face / Ollama model library: no
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
- Treated this node as model upgrade authorized: no
- Treated this node as allowing `ollama pull`: no
- Treated this node as image generation capability already available: no
- Treated this node as formal trial readiness: no
- Performed directory scan again: no
- Modified adapter / route / helper / `main.py`: no
- Modified frontend / tests / config / JSON: no
- Connected RAG / registry / CI: no
- Added `.pyc` / `__pycache__`: no

## 11. Final Status

- `MODEL-FLEET-GOVERNANCE-006-TEXT-MODEL-UPGRADE-AUTHORIZATION-GATE` completed as a docs-only text model upgrade authorization gate.
- `MODEL-FLEET-GOVERNANCE-005` was reviewed as the basis for this node.
- The prescribed docs files were read.
- Current facts and NO-GO lines were recorded.
- Highest-priority text model candidate was recorded.
- Upgrade authorization preconditions were recorded.
- Future user authorization template was recorded and is not treated as already authorized.
- Current decision: `TEXT MODEL UPGRADE AUTHORIZATION BLOCKED / FOLLOW-UP LOOKUP REQUIRED`
- Explicit NO-GO: `NO-GO FOR MODEL UPGRADE / NO-GO FOR IMAGE GENERATION EXECUTION / NO-GO FOR REAL USE / NO-GO FOR TRIAL`
- Recommended next node: `MODEL-FLEET-GOVERNANCE-007-FOLLOW-UP-LATEST-LOOKUP-AUTHORIZATION-GATE`
- The next node was not entered.

MODEL-FLEET-GOVERNANCE-006 stops here and waits for human review.
