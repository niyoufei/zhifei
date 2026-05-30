# ZDoc Single-Model Upgrade Controller-Mediated Official-Source Evidence Intake — KG-RUNTIME-161

## 1. Scope

KG-RUNTIME-161 is a docs-only controller-mediated official-source evidence intake node for the ZDoc single-model upgrade chain.

This node records only the official-source evidence provided by the ChatGPT controller after read-only network verification. Codex does not independently recheck the official sources.

This node explicitly records that:

- The user authorized the controller to handle official-source evidence.
- The evidence was provided after the controller completed read-only official-source verification.
- Codex does not perform network re-verification.
- Codex does not re-execute network HEAD, GET, or download tests.
- Codex does not execute download size live reconfirmation.
- Codex does not run Ollama.
- Codex does not execute `ollama list`.
- Codex does not execute `ollama pull qwen3.6:35b`.
- Codex does not execute any Ollama model command.
- Codex does not upgrade, pull, delete, or replace models.
- Codex does not download model files.
- Codex does not run the ZDoc service.
- Codex does not access endpoints.
- Codex does not read or parse real KG.
- Codex does not trigger generation, export, or write-back.
- Codex does not enter real use or trial use.

KG-RUNTIME-161 is not an upgrade authorization node, not an upgrade execution node, not an Ollama command node, and not a real-use or trial-use node.

## 2. Baseline

KG-RUNTIME-160 recorded the following baseline for this node:

- HEAD: `0b64654df94980c6260d52041af12a3359b636a7`
- tag: `v0.1.543-zdoc-single-model-upgrade-remaining-insufficiency-resolution-gate`
- Target docs file: `docs/zdoc-single-model-upgrade-remaining-preflight-insufficiency-resolution-authorization-gate-kg-runtime-160.md`
- Current gate decision: `NO-GO / pending remaining insufficiency resolution authorization`
- Recommended path: `Path A / user-mediated official-source evidence intake`
- Candidate: `qwen3.6:35b`

KG-RUNTIME-161 starts from that NO-GO gate and closes only the controller-provided evidence intake item. It does not authorize upgrade execution.

## 3. Controller Authorization Note

The user explicitly stated that they can authorize the controller to handle official-source evidence.

KG-RUNTIME-161 therefore adopts controller-mediated evidence intake:

- Codex receives only the evidence provided by the controller.
- Codex does not perform network re-verification.
- Codex does not run Ollama.
- Codex does not download models.
- Codex does not upgrade models.
- Codex does not execute `ollama pull qwen3.6:35b`.
- Codex does not execute any Ollama model command.

## 4. Official-Source Evidence Intake

### Evidence 1: Ollama official model page

- Official source name: Ollama official model library.
- Official source URL or page title: `qwen3.6:35b`.
- Page accessible: yes.
- Target candidate or corresponding model-family candidate found: yes.
- Model name displayed by page: `qwen3.6:35b`.
- Download size or file size displayed by page: `24GB`.
- Evidence acquisition time: 2026-05-31.
- Page text excerpt or explanation:
  - Model record: `07d35212591f · 24GB`.
  - Parameters: `36B`.
  - Quantization: `Q4_K_M`.
  - Page example model name: `qwen3.6:35b`.
- Evidence nature: controller read-only official-source verification result.
- Ollama executed: `NO`.
- Model downloaded: `NO`.
- `ollama pull qwen3.6:35b` executed: `NO`.

### Evidence 2: Ollama official tags page

- Official source name: Ollama official model library tags page.
- Official source URL or page title: `Tags · qwen3.6`.
- Page accessible: yes.
- Target candidate or corresponding model-family candidate found: yes.
- Model names displayed by page:
  - `qwen3.6:35b`
  - `qwen3.6:35b-a3b`
  - `qwen3.6:35b-a3b-q4_K_M`
- Download size or file size displayed by page:
  - `qwen3.6:35b`: `24GB`
  - `qwen3.6:35b-a3b`: `24GB`
  - `qwen3.6:35b-a3b-q4_K_M`: `24GB`
- Evidence acquisition time: 2026-05-31.
- Page text excerpt or explanation:
  - Context window: `256K`.
  - Input: `Text, Image`.
  - Digest: `07d35212591f`.
- Evidence nature: controller read-only official-source verification result.
- Ollama executed: `NO`.
- Model downloaded: `NO`.
- `ollama pull qwen3.6:35b` executed: `NO`.

### Evidence 3: Hugging Face Qwen official organization model page

- Official source name: Hugging Face / Qwen official organization.
- Official source URL or page title: `Qwen/Qwen3.6-35B-A3B`.
- Page accessible: yes.
- Target candidate or corresponding upstream model found: yes, corresponding upstream model `Qwen3.6-35B-A3B` was found.
- Model name displayed by page: `Qwen3.6-35B-A3B`.
- Download size or file size displayed by page: not used as the Ollama download-size source; this page is used for upstream model identity and parameters.
- Evidence acquisition time: 2026-05-31.
- Page text excerpt or explanation:
  - Type: Causal Language Model with Vision Encoder.
  - Number of Parameters: 35B total and 3B activated.
  - Context Length: 262,144 natively and extensible up to 1,010,000 tokens.
- Evidence nature: controller read-only official-source verification result.
- Ollama executed: `NO`.
- Model downloaded: `NO`.
- `ollama pull qwen3.6:35b` executed: `NO`.

## 5. Candidate Mapping Assessment

- The only candidate in this stage remains `qwen3.6:35b`.
- The Ollama official model page directly displays `qwen3.6:35b`.
- The Ollama tags page displays both `qwen3.6:35b` and `qwen3.6:35b-a3b` as `24GB`.
- The Hugging Face Qwen official organization page displays the corresponding upstream model identity as `Qwen3.6-35B-A3B`.
- Therefore, `qwen3.6:35b` can be used as the Ollama-side candidate tag, and `Qwen3.6-35B-A3B` can be used as the upstream official model identity reference.

## 6. Evidence Completeness Assessment

`Evidence completeness result: CLOSED / official-source evidence received from controller`

Reasons:

- Official-source accessibility evidence has been provided.
- Ollama-side candidate existence evidence has been provided.
- Ollama-side `24GB` size evidence has been provided.
- Upstream Qwen official organization model identity reference has been provided.
- It has been confirmed that Ollama was not run.
- It has been confirmed that no model was downloaded.
- It has been confirmed that `ollama pull qwen3.6:35b` was not executed.

## 7. Remaining Insufficiency Status

### 7.1 Network connectivity

- Status: `CLOSED / official-source evidence received from controller`
- Explanation: Codex-side network verification is not repeated in this node. The controller's read-only official-source verification result is accepted as the evidence intake basis.

### 7.2 `qwen3.6:35b` download size live reconfirmation

- Status: `CLOSED / 24GB official-source evidence received from controller`
- Explanation: The Ollama official model page and the Ollama tags page both display `24GB`.

## 8. Current Decision

`Current decision: EVIDENCE CLOSED / upgrade execution still not authorized`

Decision meaning:

- KG-RUNTIME-161 completes evidence intake closure only.
- Upgrade execution remains not authorized.
- `ollama pull qwen3.6:35b` remains not authorized.
- No Ollama command is authorized.
- No direct model upgrade stage may be entered.
- Trial / real use may not be entered.
- The single-model candidate remains `qwen3.6:35b`.

## 9. Next Recommended Node

Next recommended node:

`KG-RUNTIME-162: single-model upgrade execution authorization gate after evidence closure docs-only`

KG-RUNTIME-162 target:

1. Based on KG-RUNTIME-161 evidence closure, form the upgrade execution authorization gate.
2. Still not directly execute upgrade.
3. Still not run Ollama.
4. Still not execute `ollama pull qwen3.6:35b`.
5. Still not execute any Ollama model command.
6. Still not upgrade, pull, delete, or replace any model.
7. Only form the next explicit user-authorization wording.

KG-RUNTIME-162 must not be written as an upgrade execution node.

KG-RUNTIME-161 stops here and does not enter KG-RUNTIME-162.

## 10. Explicit Prohibitions Preserved

The following prohibitions remain preserved after KG-RUNTIME-161:

- Do not run Ollama.
- Do not execute `ollama list`.
- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- Do not execute any Ollama model command.
- Do not upgrade, pull, delete, or replace models.
- Do not download model files.
- Do not run the ZDoc service.
- Do not access endpoints.
- Do not read real KG.
- Do not parse real KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not enter real use or trial use.

## 11. Final Status

- KG-RUNTIME-161 completed as docs-only controller-mediated official-source evidence intake.
- Official-source evidence received from controller.
- Evidence completeness result: `CLOSED / official-source evidence received from controller`
- Network connectivity evidence closed.
- `qwen3.6:35b` download size evidence closed at `24GB`.
- Current decision: `EVIDENCE CLOSED / upgrade execution still not authorized`
- Upgrade remains not authorized.
- `ollama pull qwen3.6:35b` remains not authorized.
- No Ollama command is authorized.
- Model upgrade has not been executed.
- Trial / real use has not started.
- Candidate remains `qwen3.6:35b`.
- Next recommended node: `KG-RUNTIME-162: single-model upgrade execution authorization gate after evidence closure docs-only`

KG-RUNTIME-161 stops here and does not enter KG-RUNTIME-162.
