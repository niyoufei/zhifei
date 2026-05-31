# ZDoc Model Fleet Upgrade Candidate Priority And Next-Action Gate - MODEL-FLEET-GOVERNANCE-005

## 1. Node

`MODEL-FLEET-GOVERNANCE-005-UPGRADE-CANDIDATE-PRIORITY-GATE`

This node forms a docs-only model-fleet upgrade candidate priority and next-action authorization gate based on:

`MODEL-FLEET-GOVERNANCE-004-LATEST-LOOKUP-INSUFFICIENT-SOURCE-CLOSURE`

This node does not perform online lookup, does not run Ollama, does not execute any Ollama command, does not upgrade, pull, delete, or replace any model, does not modify any `latest` pointer, does not download model files, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not use real project material or real business data, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Starting State

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `e683f4aa5f8111832687d2d2018eedffad87c2f2`
- Starting remote tag record: `v0.1.564-zdoc-model-fleet-latest-lookup-insufficient-source-closure`
- Initial `git status --short`: clean

The starting remote tag record is treated as the controller-provided record from this node instruction.

This node did not live-query the remote tag.

This node did not execute `git ls-remote`.

## 3. Prescribed Docs Read

The following prescribed docs files were readable and were read:

1. `docs/zdoc-domestic-top-tier-model-fleet-latest-lookup-insufficient-source-closure-model-fleet-governance-004.md`
2. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-execution-record-model-fleet-governance-003.md`
3. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-authorization-gate-model-fleet-governance-002.md`
4. `docs/zdoc-local-domestic-top-tier-model-fleet-and-construction-image-generation-governance-gate-model-fleet-governance-001.md`
5. `docs/zdoc-preview-only-validation-result-review-and-kg-safety-gate-kg-runtime-170.md`
6. `docs/zdoc-preview-only-technical-validation-execution-record-kg-runtime-169.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 4. Current Facts

1. `MODEL-FLEET-GOVERNANCE-004` has completed and is treated under the human-review-passed wording for this node.
2. `MODEL-FLEET-GOVERNANCE-004` completed insufficient-source closure and naming-difference review.
3. Current model upgrade remains unauthorized.
4. Current image model integration remains unauthorized.
5. Current image generation remains unauthorized.
6. Current real use / trial remains unauthorized.
7. Current status remains:

   `NO-GO FOR MODEL UPGRADE`

   `NO-GO FOR IMAGE GENERATION EXECUTION`

   `NO-GO FOR REAL USE`

   `NO-GO FOR TRIAL`

This node records priority and authorization-gate recommendations only.

## 5. Text Model Upgrade Candidate Priority

The following priority order is a recommendation for later authorization-gate formation only. It does not authorize upgrade, pull, replacement, deletion, local validation, or `latest` pointer modification.

| Priority | Candidate family | ZDoc copy output quality impact | Construction organization / technical-bid impact | Code or system-development impact | Local compute impact | Stability validation cost | Source or naming issue | Follow-up lookup needed | Suitable for near-term upgrade authorization gate |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | `qwen3.6` / `qwen3` | Highest direct impact on main ZDoc prose quality, long-form construction text, and technical-bid drafting. | Highest direct impact because this family is the main text-generation baseline for construction organization design and technical-bid content. | Medium; useful for general reasoning and structured drafting, not the primary coding-specialized family. | Medium to high depending on candidate size; `qwen3.6:35b` and `qwen3:30b` are more feasible than very large 235B candidates. | Medium for already known local-scale candidates; high for larger candidates. | `qwen3.6:35b` has sufficient prior-doc evidence for candidate retention; `qwen3:30b` has official naming / local-tag mismatch; `qwen3:14b` and `qwen3:0.6b` remain source-insufficient. | Yes for exact local digest / installed-version closure where needed, especially `qwen3:30b`, `qwen3:14b`, `qwen3:8b`, and `qwen3:0.6b`. | Yes for evidence-backed candidate sorting, with no execution authorization. |
| 2 | `deepseek-r1` | High impact on reasoning-heavy drafting, review logic, and complex technical-bid argumentation. | High impact for construction scheme reasoning, risk analysis, and technical response quality. | Medium; useful for reasoning assistance but not the primary coding-specialized family. | Medium to very high depending on whether later candidates are distilled or full-size. | Medium to high because local `deepseek-r1:32b` differs from newer / stronger R1-0528 candidate naming. | Newer / stronger R1-0528 candidates were identified in prior docs, but exact local `deepseek-r1:32b` latest status remains unclear. | Yes for exact local `deepseek-r1:32b` status and naming closure before execution. | Yes for candidate prioritization; execution must wait for separate authorization and any required lookup closure. |
| 3 | `qwen3-coder` | Medium direct impact on ZDoc prose; stronger impact on code-adjacent prompt tooling, templates, and automation support. | Medium indirect impact by improving system support for technical-bid production workflows. | Highest impact for code ability and system-development assistance. | Medium to very high; local `30b` is feasible relative to 480B-class candidates, while larger candidates may be costly. | Medium for local-scale coder candidates; high for larger or new family candidates. | Stronger candidates such as `Qwen3-Coder-480B-A35B-Instruct` and `Qwen3-Coder-Next` were identified in prior docs; local `qwen3-coder:30b` is not treated as the whole-family latest. | No for priority sorting; yes only if exact local `30b` digest / version closure is later required. | Yes after main text-model priority is handled, especially for system-development support. |
| 4 | `qwen3-next` | Medium to high possible text-quality impact, but less directly clear than the main `qwen3.6` / `qwen3` branch under current prior-doc evidence. | Medium to high possible impact for long-context construction content, subject to local stability and naming closure. | Medium. | High because prior-doc local tag is an 80B quantized variant with large local footprint. | High because naming / tag mismatch and large-model stability cost remain material. | Local `qwen3-next:80b-a3b-instruct-q8_0` differs from official family / Ollama-library naming recorded in prior docs. | Yes for exact local quantized tag and naming closure before high-priority execution consideration. | Conditional; should not be treated as a high-priority execution object before lookup / naming closure. |

Priority rule applied:

1. First protect main text quality for ZDoc copy output and construction organization / technical-bid drafting.
2. Then protect code and system-development assistance quality.
3. Then advance image / multimodal model selection.
4. Source-insufficient items enter follow-up lookup authorization before execution priority.
5. Evidence-backed candidates may enter later upgrade authorization gates first.
6. Any branch still requires explicit user authorization before action.

## 6. Source-Insufficient / Follow-Up Lookup Branch

The following items require later separate authorization before any follow-up read-only online latest lookup or local inventory / digest closure:

1. Exact latest status of `qwen3:14b`.
2. Exact latest status of `qwen3:0.6b`.
3. Exact local digest / installed version behind `qwen3:30b`.
4. Exact local digest / installed version behind `qwen3:8b`.
5. Exact local digest / installed version and naming closure for `qwen3-next:80b-a3b-instruct-q8_0`.
6. Exact latest status and naming closure for `deepseek-r1:32b`.
7. Any new or additional domestic top-tier text model family not already itemized in the prior docs.
8. Any refreshed cross-vendor ranking or newly itemized image / multimodal model candidate.

Follow-up lookup rules:

1. Follow-up lookup requires later separate user authorization.
2. Follow-up lookup is not model upgrade authorization.
3. Finding a new version does not authorize `pull`.
4. Finding a new version does not authorize model deletion, replacement, or `latest` pointer modification.
5. Before insufficient-source items are closed, they must not be treated as high-priority upgrade execution objects.
6. This node performs no online lookup.

## 7. Image / Multimodal Model Selection Gate Branch

The following image / multimodal candidates may enter a later selection-gate node only:

`IMAGE-GOVERNANCE-001-CONSTRUCTION-IMAGE-MODEL-SELECTION-GATE`

Candidate families retained for that later selection gate:

1. Qwen Image.
2. Qwen3-VL.
3. HunyuanImage.
4. Kolors.

Image / multimodal branch rules:

1. This node does not integrate any image model.
2. This node does not generate images.
3. Image / multimodal candidates do not mean image generation capability is already available.
4. Qwen3-VL is retained as a multimodal understanding / image-text candidate and is not treated as image generation capability.
5. Before image model integration, the system must complete safety and civilized construction negative-list rules, prompt templates, image-text consistency checks, human review, and pre-trial acceptance gates.
6. Image capability must follow this order:

   `selection gate -> integration authorization -> stability validation -> image-text consistency check -> human review -> pre-trial acceptance`

7. No image / multimodal branch may skip user authorization.

## 8. Recommended Next Paths

### Recommended path A: text model upgrade priority authorization gate

`MODEL-FLEET-GOVERNANCE-006-TEXT-MODEL-UPGRADE-AUTHORIZATION-GATE`

Purpose: form a per-model upgrade authorization gate for the highest-priority text model candidate.

This node does not enter that path.

### Recommended path B: follow-up latest lookup authorization gate

`MODEL-FLEET-GOVERNANCE-006-FOLLOW-UP-LATEST-LOOKUP-AUTHORIZATION-GATE`

Purpose: form a supplemental read-only online lookup authorization gate for source-insufficient or naming-unclear model families.

This node does not enter that path.

### Recommended path C: construction image model selection gate

`IMAGE-GOVERNANCE-001-CONSTRUCTION-IMAGE-MODEL-SELECTION-GATE`

Purpose: form a selection gate for image / multimodal model candidates without integration or image generation.

This node does not enter that path.

## 9. Later Authorization Prompt Requirement

For any later action listed below, the prompt must prominently state:

**是否需要用户授权：需要。**

Actions requiring separate authorization:

1. Supplemental online latest lookup.
2. Any model upgrade.
3. Any `ollama pull`.
4. Any model deletion or replacement.
5. Any `latest` pointer modification.
6. Image / multimodal model integration.
7. Image generation capability validation.
8. Real KG reading or parsing.
9. ZDoc service execution.
10. Endpoint access.
11. Real use / trial.

## 10. Current Decision

Current decision:

`MODEL FLEET PRIORITY GATE FORMED / NO MODEL UPGRADE AUTHORIZED / NO IMAGE EXECUTION AUTHORIZED`

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

This decision does not authorize image / multimodal model deployment.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG reading or parsing.

This decision does not authorize generation, export, or write-back.

This decision does not authorize real use.

This decision does not authorize trial.

This decision does not authorize 1-2 person controlled trial.

This decision does not authorize 2-5 person limited concurrent trial.

## 11. Prohibited Actions Record

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
- Treated this node as image generation capability already available: no
- Treated this node as formal trial readiness: no
- Performed directory scan again: no
- Modified adapter / route / helper / `main.py`: no
- Modified frontend / tests / config / JSON: no
- Connected RAG / registry / CI: no
- Added `.pyc` / `__pycache__`: no

## 12. Final Status

- `MODEL-FLEET-GOVERNANCE-005-UPGRADE-CANDIDATE-PRIORITY-GATE` completed as a docs-only priority and next-action authorization gate.
- `MODEL-FLEET-GOVERNANCE-004` was reviewed as the basis for this node.
- The prescribed docs files were read.
- Current facts and NO-GO lines were recorded.
- Text model upgrade candidate priorities were recorded.
- Source-insufficient / follow-up lookup branch was recorded.
- Image / multimodal model selection gate branch was recorded.
- Later authorization prompt requirements were recorded.
- Current decision: `MODEL FLEET PRIORITY GATE FORMED / NO MODEL UPGRADE AUTHORIZED / NO IMAGE EXECUTION AUTHORIZED`
- Explicit NO-GO: `NO-GO FOR MODEL UPGRADE / NO-GO FOR IMAGE GENERATION EXECUTION / NO-GO FOR REAL USE / NO-GO FOR TRIAL`
- Suggested next nodes were recorded.
- The next node was not entered.

MODEL-FLEET-GOVERNANCE-005 stops here and waits for human review.
