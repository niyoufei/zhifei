# ZDoc Domestic Top-Tier Model Fleet Latest Lookup Insufficient Source Closure - MODEL-FLEET-GOVERNANCE-004

## 1. Node

`MODEL-FLEET-GOVERNANCE-004-LATEST-LOOKUP-INSUFFICIENT-SOURCE-CLOSURE`

This node is a docs-only review and closure record for the insufficient-source and naming-difference items left by:

`MODEL-FLEET-GOVERNANCE-003-LATEST-VERSION-LOOKUP-EXECUTION`

This node only reviews the prior docs records. It does not perform online lookup, does not run Ollama, does not execute any Ollama command, does not upgrade, pull, delete, replace, run, or test any model, does not modify any `latest` pointer, does not download model files, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not use real project material or real business data, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Starting State

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `b718ad2b3957ddb820c479057c5f268c345126be`
- Starting remote tag record: `v0.1.563-zdoc-model-fleet-latest-version-lookup-execution`
- Initial `git status --short`: clean

The starting remote tag record is treated as the controller-provided record from this node instruction.

This node did not live-query the remote tag.

This node did not execute `git ls-remote`.

## 3. Prescribed Docs Read

The following prescribed docs files were readable and were read:

1. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-execution-record-model-fleet-governance-003.md`
2. `docs/zdoc-domestic-top-tier-model-fleet-latest-version-lookup-authorization-gate-model-fleet-governance-002.md`
3. `docs/zdoc-local-domestic-top-tier-model-fleet-and-construction-image-generation-governance-gate-model-fleet-governance-001.md`
4. `docs/zdoc-preview-only-validation-result-review-and-kg-safety-gate-kg-runtime-170.md`
5. `docs/zdoc-preview-only-technical-validation-execution-record-kg-runtime-169.md`
6. `docs/zdoc-preview-only-technical-validation-authorization-gate-kg-runtime-168.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 4. Required Facts From MODEL-FLEET-GOVERNANCE-003

1. `MODEL-FLEET-GOVERNANCE-003` has completed and passed boundary review for this closure node.
2. `MODEL-FLEET-GOVERNANCE-003` performed read-only online latest-version lookup.
3. `MODEL-FLEET-GOVERNANCE-003` did not run Ollama.
4. `MODEL-FLEET-GOVERNANCE-003` did not upgrade, pull, delete, or replace any model.
5. `MODEL-FLEET-GOVERNANCE-003` did not generate images and did not call image models.
6. `MODEL-FLEET-GOVERNANCE-003` current decision was:

   `LATEST-VERSION LOOKUP PARTIALLY COMPLETED / INSUFFICIENT SOURCES REQUIRE FOLLOW-UP`

7. This node performs only docs-only insufficient-source closure.
8. This node does not perform online follow-up lookup.
9. This node does not upgrade any model.
10. This node does not connect or call any image / multimodal model.

## 5. Source Basis

This node uses only the contents of the prescribed docs files.

For latest-version findings, this node treats the official / trusted source list recorded in `MODEL-FLEET-GOVERNANCE-003` as prior-doc evidence only. This node did not access those websites, model cards, repositories, Hugging Face pages, GitHub pages, Ollama model-library pages, or model files.

## 6. Text Model Review Matrix

| Model family / candidate | Known local model or candidate | `MODEL-FLEET-GOVERNANCE-003` latest lookup result | Source type | Source enough for upgrade decision | Source insufficient | Naming mismatch | Tag / version-policy difference | Can enter later priority gate | Only later follow-up lookup | Image / multimodal candidate only | Separate authorization needed | Controller status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `qwen3.6` / `qwen3.6:35b` | Prior-doc local `qwen3.6:35b` | `Qwen/Qwen3.6-35B-A3B`; Ollama official library recorded `qwen3.6:35b` as `latest` in MG003 | Prior-doc record of Qwen official HF model card plus Ollama official library | Enough only for candidate prioritization / retain-review; not enough for execution upgrade without separate authorization and local digest check | No for family candidate; local digest not rechecked | Yes, official full name differs from Ollama-style local tag | Official name `Qwen3.6-35B-A3B`; local tag `qwen3.6:35b`; local digest not rechecked | Yes | No, except if later local digest confirmation is authorized | No | Yes | `READY FOR PRIORITY GATE / source sufficient for candidate prioritization` |
| `qwen3` 30B / 235B candidates | Prior-doc local `qwen3:30b` and family candidates | `Qwen/Qwen3-30B-A3B-Instruct-2507`; `Qwen/Qwen3-235B-A22B-Instruct-2507`; Ollama Qwen3 library recorded updated 30B / 235B models | Prior-doc record of Qwen official HF model cards plus Ollama official library | Enough only for candidate prioritization; not enough for upgrade execution | Partial: exact local `qwen3:30b` digest / installed version not confirmed | Yes | Official 2507 naming includes `A3B-Instruct-2507`; local tag lacks the 2507 suffix | Yes | Yes, for exact local digest / version closure if needed | No | Yes | `NAME OR TAG MISMATCH NEEDS CLOSURE / local tag differs from official naming` |
| `qwen3` small local tags | Prior-doc local `qwen3:14b`, `qwen3:8b`, `qwen3:0.6b` | MG003 confirmed broader family candidates; exact latest status for `qwen3:14b` and `qwen3:0.6b` was not confirmed; `qwen3:8b` was marked latest in Ollama library but local digest was not rechecked | Prior-doc record of Ollama official library and Qwen family lookup | Not enough for upgrade execution; insufficient for exact small-tag latest closure for `14b` and `0.6b` | Yes, especially `qwen3:14b` and `qwen3:0.6b`; local digest check remains absent for all local small tags | Yes for broader family naming | Local short tags do not identify exact official release / digest state | No for `14b` and `0.6b`; conditional for `8b` only after local confirmation | Yes | No | Yes | `NEEDS FOLLOW-UP LOOKUP / source insufficient or version unclear` |
| `qwen3-next` | Prior-doc local `qwen3-next:80b-a3b-instruct-q8_0` | `Qwen/Qwen3-Next-80B-A3B-Instruct`; Ollama official library primary tag `qwen3-next:80b` | Prior-doc record of Qwen official HF model card plus Ollama official library | Enough for family candidate prioritization; not enough to treat local quantized tag as exact latest | Yes, for exact local quantized tag | Yes | Official source names `Qwen3-Next-80B-A3B-Instruct` / `qwen3-next:80b`; local tag adds `a3b-instruct-q8_0` | Conditional after naming / tag closure | Yes | No | Yes | `NAME OR TAG MISMATCH NEEDS CLOSURE / local tag differs from official naming` |
| `qwen3-coder` | Prior-doc local `qwen3-coder:30b` | `Qwen/Qwen3-Coder-480B-A35B-Instruct`; `Qwen/Qwen3-Coder-Next`; Ollama official library also recorded `qwen3-coder:30b`, `qwen3-coder:480b`, and `qwen3-coder-next` candidates | Prior-doc record of Qwen official HF model cards plus Ollama official library | Enough for candidate prioritization; not enough for upgrade execution | No for identifying stronger candidates; local 30B digest not rechecked | Yes | Local `30b` is not the strongest family candidate; official candidate names use 480B / Coder-Next naming | Yes | No for priority sorting; yes only if exact local 30B digest closure is later required | No | Yes | `READY FOR PRIORITY GATE / source sufficient for candidate prioritization` |
| `deepseek-r1` family candidates | Prior-doc local `deepseek-r1:32b`; candidates `DeepSeek-R1-0528` and `DeepSeek-R1-0528-Qwen3-8B` | `deepseek-ai/DeepSeek-R1-0528`; `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`; Ollama official library recorded R1-0528 for 8B distilled and full 671B variants | Prior-doc record of DeepSeek official HF model card plus Ollama official library | Enough for candidate prioritization; not enough for upgrade execution | No for identifying newer / stronger candidates; yes for exact local 32B latest closure | Yes | Local `deepseek-r1:32b` maps to older distilled Qwen 32B style naming; official current candidate names include `0528` | Yes | Yes, for exact local 32B status if needed | No | Yes | `READY FOR PRIORITY GATE / source sufficient for candidate prioritization` |
| `deepseek-r1:32b` exact local tag | Prior-doc local `deepseek-r1:32b` | MG003 found newer / stronger R1-0528 candidates but did not confirm local 32B exact latest status | Prior-doc record only | Not enough for direct upgrade execution or exact local latest declaration | Yes | Yes | Local tag lacks `0528` and maps to older distill naming | No | Yes | No | Yes | `NEEDS FOLLOW-UP LOOKUP / source insufficient or version unclear` |

## 7. Image / Multimodal Candidate Review Matrix

| Model family / candidate | Known local model or candidate | `MODEL-FLEET-GOVERNANCE-003` latest lookup result | Source type | Source enough for upgrade decision | Source insufficient | Naming mismatch | Tag / version-policy difference | Can enter later priority gate | Only later follow-up lookup | Image / multimodal candidate only | Separate authorization needed | Controller status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen Image | `Qwen/Qwen-Image-2512`; not installed | MG003 recorded local / private deployment evidence from official model-card usage and weights; candidate for construction scene / node / procedure image generation | Prior-doc record of Qwen official HF model card | Not enough for deployment, connection, or image execution | Not insufficient for candidate retention; insufficient for deployment decision | No local tag comparison available | Not a local tag; model-card candidate only | No text-model priority gate; may enter image selection gate | No, unless later source refresh is authorized | Yes | Yes | `IMAGE OR MULTIMODAL CANDIDATE ONLY / selection gate required` |
| Qwen3-VL | `Qwen/Qwen3-VL-235B-A22B-Instruct`; not installed | MG003 recorded image-text-to-text / multimodal understanding candidate; not image generation capability | Prior-doc record of Qwen official HF model card | Not enough for deployment, connection, or multimodal execution | Not insufficient for candidate retention; insufficient for deployment decision | No local tag comparison available | Not a local tag; model-card candidate only | No text-model priority gate; may enter image / multimodal selection gate | No, unless later source refresh is authorized | Yes | Yes | `IMAGE OR MULTIMODAL CANDIDATE ONLY / selection gate required` |
| HunyuanImage | `tencent/HunyuanImage-3.0` and related Instruct / Distil checkpoints; not installed | MG003 recorded local usage, model weights, Instruct, Distil, and vLLM support items; candidate for construction image generation / editing | Prior-doc record of Tencent official HF model card | Not enough for deployment, connection, or image execution | Not insufficient for candidate retention; licensing / deployment / safety review remains required | No local tag comparison available | Not a local tag; candidate family includes related checkpoint variants | No text-model priority gate; may enter image selection gate | No, unless later source refresh is authorized | Yes | Yes | `IMAGE OR MULTIMODAL CANDIDATE ONLY / selection gate required` |
| Kolors | `Kwai-Kolors/Kolors`; not installed | MG003 recorded Diffusers / local project usage and Chinese / English prompt support; noted commercial registration / safety-use cautions | Prior-doc record of Kwai-Kolors official HF model card | Not enough for deployment, connection, or image execution | Not insufficient for candidate retention; legal / governance review remains required | No local tag comparison available | Not a local tag; candidate appears older than Qwen-Image-2512 / HunyuanImage-3.0 in MG003 | No text-model priority gate; may enter image selection gate | No, unless later source refresh is authorized | Yes | Yes | `IMAGE OR MULTIMODAL CANDIDATE ONLY / selection gate required` |
| Other MG003-recorded image / multimodal candidates | No additional separately named candidate beyond the HunyuanImage related Instruct / Distil checkpoints recorded inside the HunyuanImage row | MG003 did not record another separately named image / multimodal candidate for this closure table | Prescribed docs only | No | Hold unless later itemized | Not applicable | Not applicable | No | Yes, only if later a candidate is itemized and authorized | Yes, if later itemized | Yes | `HOLD / not enough evidence for next action` |

## 8. Source-Insufficient Items Closed For This Node

The following items remain source-insufficient or version-unclear after docs-only review:

1. Exact current local model digests for all prior-doc local tags, because this node and MG003 did not run Ollama.
2. `qwen3:14b`, because exact official latest-version confirmation was not recorded in MG003.
3. `qwen3:0.6b`, because exact official latest-version confirmation was not recorded in MG003.
4. `qwen3:30b`, because official 2507 naming exists but the local digest / installed version was not rechecked.
5. `qwen3-next:80b-a3b-instruct-q8_0`, because the exact local quantized tag differs from official source naming.
6. `deepseek-r1:32b`, because newer / stronger R1-0528 candidates were identified, but the exact local 32B tag was not latest-confirmed.
7. Cross-vendor ranking of domestic image / multimodal candidates, because MG003 did not treat any single official source as authoritative for ranking all vendors.

This node closes the insufficient-source review by classifying the items above. It does not resolve them through new lookup.

## 9. Naming And Version-Policy Differences

1. Qwen official model names use full names such as `Qwen3.6-35B-A3B`, while prior docs use Ollama-style tags such as `qwen3.6:35b`.
2. Qwen3 official 2507 model names include `A3B-Instruct-2507`, while prior docs record local short tags such as `qwen3:30b`.
3. Qwen3-Next official source uses `Qwen3-Next-80B-A3B-Instruct`, while prior docs record `qwen3-next:80b-a3b-instruct-q8_0`.
4. Qwen3-Coder official candidate names include `Qwen3-Coder-480B-A35B-Instruct` and `Qwen3-Coder-Next`, while prior docs record local `qwen3-coder:30b`.
5. DeepSeek official candidate names include `DeepSeek-R1-0528` and `DeepSeek-R1-0528-Qwen3-8B`, while prior docs record local `deepseek-r1:32b`.
6. Ollama `latest` tags are registry tags and must not be treated as local installation state without a separately authorized local inventory / digest check.

## 10. Candidate Priority Gate Items

The following text-model items may enter a later docs-only upgrade candidate priority gate, with no upgrade authorized here:

1. `qwen3.6:35b` / `Qwen/Qwen3.6-35B-A3B` as a retain / no-upgrade-priority review item.
2. `Qwen/Qwen3-30B-A3B-Instruct-2507`.
3. `Qwen/Qwen3-235B-A22B-Instruct-2507`.
4. `Qwen/Qwen3-Coder-480B-A35B-Instruct`.
5. `Qwen/Qwen3-Coder-Next`.
6. `deepseek-ai/DeepSeek-R1-0528`.
7. `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`.

`qwen3-next` may enter the same priority gate only with an explicit naming / tag mismatch note because local `qwen3-next:80b-a3b-instruct-q8_0` differs from the official family and Ollama-library names recorded by MG003.

## 11. Follow-Up Lookup Items

The following items require later separate authorization before any follow-up lookup:

1. Exact latest status of `qwen3:14b`.
2. Exact latest status of `qwen3:0.6b`.
3. Exact local digest / installed version behind `qwen3:30b`.
4. Exact local digest / installed version behind `qwen3:8b`.
5. Exact local digest / installed version and naming closure for `qwen3-next:80b-a3b-instruct-q8_0`.
6. Exact latest status and naming closure for `deepseek-r1:32b`.
7. Any new or additional domestic top-tier text model family not already itemized in MG003.
8. Any refreshed cross-vendor ranking or newly itemized image / multimodal model candidate.

## 12. Image / Multimodal Selection Gate Items

The following candidates may only be retained as image / multimodal candidates and require a later selection gate before any deployment, connection, download, trial, or image execution:

1. `Qwen/Qwen-Image-2512`.
2. `Qwen/Qwen3-VL-235B-A22B-Instruct`.
3. `tencent/HunyuanImage-3.0` and related Instruct / Distil checkpoints recorded in MG003.
4. `Kwai-Kolors/Kolors`.

`Qwen/Qwen3-VL-235B-A22B-Instruct` is retained as a multimodal understanding / image-text candidate only and is not treated as an image generation capability.

## 13. Subsequent Path Judgment

Recommended later docs-only paths after human review:

1. Because several text-model candidates have enough prior-doc source evidence for candidate sorting:

   `MODEL-FLEET-GOVERNANCE-005-UPGRADE-CANDIDATE-PRIORITY-GATE`

2. Because some exact local tags and small Qwen3 tags remain source-insufficient or version-unclear:

   `MODEL-FLEET-GOVERNANCE-005-FOLLOW-UP-LATEST-LOOKUP-AUTHORIZATION-GATE`

3. Because image / multimodal candidates have only candidate-level information:

   `IMAGE-GOVERNANCE-001-CONSTRUCTION-IMAGE-MODEL-SELECTION-GATE`

This node does not enter any next node.

## 14. Current Decision

Current decision:

`LATEST LOOKUP REVIEWED / CANDIDATE PRIORITY GATE REQUIRED / NO UPGRADE AUTHORIZED`

`LATEST LOOKUP REVIEWED / FOLLOW-UP LOOKUP REQUIRED / NO UPGRADE AUTHORIZED`

`LATEST LOOKUP REVIEWED / IMAGE MODEL SELECTION GATE REQUIRED / NO IMAGE EXECUTION AUTHORIZED`

Explicit NO-GO:

`NO-GO FOR MODEL UPGRADE / NO-GO FOR IMAGE GENERATION EXECUTION / NO-GO FOR REAL USE / NO-GO FOR TRIAL`

This decision does not authorize model upgrade.

This decision does not authorize model pull.

This decision does not authorize model deletion.

This decision does not authorize model replacement.

This decision does not authorize `latest` pointer modification.

This decision does not authorize model download.

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

## 15. Prohibited Actions Record

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
- Treated this node as model upgraded: no
- Treated this node as model upgrade / pull / delete / replacement authorization: no
- Treated image / multimodal candidates as image generation capability already available: no
- Treated this node as formal trial readiness: no
- Performed directory scan again: no
- Modified adapter / route / helper / `main.py`: no
- Modified frontend / tests / config / JSON: no
- Connected RAG / registry / CI: no
- Added `.pyc` / `__pycache__`: no

## 16. Final Status

- `MODEL-FLEET-GOVERNANCE-004-LATEST-LOOKUP-INSUFFICIENT-SOURCE-CLOSURE` completed as a docs-only insufficient-source and naming-difference closure record.
- Only the prescribed prior docs files were read.
- The prescribed text model families were reviewed.
- The prescribed image / multimodal candidates were reviewed.
- Source-insufficient items were recorded.
- Naming mismatch and version-policy differences were recorded.
- Text candidates eligible for a later priority gate were recorded.
- Follow-up lookup items requiring later separate authorization were recorded.
- Image / multimodal candidates requiring a later selection gate were recorded.
- Current decision: `LATEST LOOKUP REVIEWED / CANDIDATE PRIORITY GATE REQUIRED / NO UPGRADE AUTHORIZED`; `LATEST LOOKUP REVIEWED / FOLLOW-UP LOOKUP REQUIRED / NO UPGRADE AUTHORIZED`; `LATEST LOOKUP REVIEWED / IMAGE MODEL SELECTION GATE REQUIRED / NO IMAGE EXECUTION AUTHORIZED`
- Explicit NO-GO: `NO-GO FOR MODEL UPGRADE / NO-GO FOR IMAGE GENERATION EXECUTION / NO-GO FOR REAL USE / NO-GO FOR TRIAL`
- Suggested next docs-only nodes were recorded.
- The next node was not entered.

MODEL-FLEET-GOVERNANCE-004 stops here and waits for human review.
