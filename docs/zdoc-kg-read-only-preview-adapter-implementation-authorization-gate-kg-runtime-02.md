# ZDoc KG Read-Only Preview Adapter Implementation Authorization Gate KG-RUNTIME-02

## 1. Execution Summary

KG-RUNTIME-02 is a docs-only authorization gate for a possible future read-only
preview adapter. This step does not create an adapter, does not write code, does
not register a manifest, does not enable a knowledge pack, and does not connect
any runtime path.

The current conclusion is: ZDoc may continue to evaluate a future read-only
preview adapter only if the next step is separately authorized by ChatGPT. The
future adapter, if authorized, must remain default-off, manually triggered,
read-only, non-evidence, non-scoring, non-RAG, non-prompt-registry, and
non-system-instruction-registry.

KG-RUNTIME-03 is not authorized by this document.

## 2. Baseline And Inputs

Repository:

`/Users/youfeini/Desktop/文档生成系统`

Start baseline:

`e7ba53940e9432e13c056f4b2c6b83ada1340806`

Start tag:

`v0.1.382-zdoc-kg-read-only-preview-integration-design`

Primary input document:

`docs/zdoc-kg-read-only-preview-integration-design-kg-runtime-01.md`

Referenced static KG artifacts:

| Artifact | Path | Required status |
| --- | --- | --- |
| KG-31 disabled manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | Disabled, not registered, not runtime-loadable |
| KG-33 disabled registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | Disabled, not registered, not registry-loadable |
| KG-41 validator draft | `docs/kg-controlled-validators/zdoc_kg_disabled_entity_pair_static_validator_draft.py` | Static draft only, not executed |
| KG-RUNTIME-01 design | `docs/zdoc-kg-read-only-preview-integration-design-kg-runtime-01.md` | Design only, no adapter |

## 3. KG-RUNTIME-01 Conclusion Inheritance

KG-RUNTIME-01 established the read-only preview target shape:

- The KG preview is a human-triggered inspection surface, not a generation
  input.
- KG-31 and KG-33 remain disabled entity drafts in a docs non-runtime directory.
- The preview must not write back to document正文.
- The preview must not become evidence.
- The preview must not become a scoring basis.
- The preview must not enter `/generate`.
- The preview must not trigger `/export_docx`, `/review/apply`, or ZBid writeback.
- The preview must not write `output/job/export`.
- The preview must not connect to RAG, prompt registry, or system instruction
  registry.
- The KG-41 validator draft remains non-executable and outside tests or CI.

KG-RUNTIME-02 accepts those conclusions without expanding authority.

## 4. Authorization Disposition

This step does not authorize implementation.

It only records that a future implementation step may be considered if ChatGPT
separately authorizes KG-RUNTIME-03 with explicit file scope, explicit rollback
requirements, and explicit no-runtime constraints.

Until such authorization exists:

- No adapter may be created.
- No runtime file may be created.
- No registry may be created.
- No existing JSON may be modified.
- No validator draft may be modified or executed.
- No ZDoc service may be started.
- No endpoint may be called.
- No local model may be upgraded, pulled, deleted, or replaced.

## 5. Future Adapter Boundary If Separately Authorized

If KG-RUNTIME-03 is separately authorized, the adapter may only be scoped as a
read-only preview adapter.

Required properties:

- `default_off`: the adapter must be off unless a human explicitly requests a
  preview action.
- `manual_trigger_only`: no automatic invocation from generation, export,
  review, scoring, or writeback flows.
- `read_only`: the adapter may read only approved static metadata or disabled
  entity fields.
- `no_body_writeback`: the adapter must not write, replace, append, or patch
  document正文.
- `no_evidence`: the adapter output must not be cited as evidence.
- `no_scoring`: the adapter output must not influence scoring.
- `no_generation_chain`: the adapter must not enter `/generate` or any main
  generation chain.
- `no_registry_activation`: the adapter must not register or enable KG-31,
  KG-33, or any knowledge pack.
- `no_rag_connection`: the adapter must not connect to RAG.
- `no_prompt_registry_connection`: the adapter must not connect to prompt
  registry.
- `no_system_instruction_connection`: the adapter must not connect to system
  instruction registry.
- `no_output_write`: the adapter must not write `output/job/export`.

## 6. Non-Negotiable Runtime Prohibitions

The following remain prohibited for KG-RUNTIME-02 and are not authorized for
KG-RUNTIME-03 unless ChatGPT issues a separate instruction that explicitly
changes the boundary:

- Running ZDoc service.
- Running ZBid service.
- Running Ollama.
- Opening or probing ports.
- Calling any endpoint.
- Triggering `/generate`.
- Triggering `/export_docx`.
- Triggering `/review/apply`.
- Triggering ZBid writeback.
- Generating DOCX.
- Writing `output/job/export`.
- Registering a manifest.
- Creating a real registry.
- Enabling or loading any knowledge pack.
- Connecting to RAG, prompt registry, or system instruction registry.
- Running the KG-41 validator draft.
- Running `py_compile` on the KG-41 validator draft.
- Adding the validator draft to tests or CI.
- Upgrading, pulling, deleting, or replacing any local model.

## 7. KG-31 And KG-33 State Confirmation

The KG-31 disabled manifest entity and KG-33 disabled registry entity remain
static docs artifacts only.

Required locked state:

| Field or rule | Required value |
| --- | --- |
| `enabled` | `false` |
| `registration_status` | `not_registered` |
| runtime loadability | `false` |
| registry loadability | `false` where applicable |
| RAG loadability | `false` |
| prompt registry loadability | `false` |
| system instruction loadability | `false` |
| evidence permission | `false` |
| scoring permission | `false` |
| source files copied | `false` |
| raw system instruction embedded | `false` |

The future read-only preview adapter must not change these states.

## 8. KG-41 Validator Draft State Confirmation

The KG-41 validator draft remains a static design artifact in a docs
non-runtime directory.

Locked constraints:

- It must not be run.
- It must not be compiled with `py_compile`.
- It must not be imported by tests.
- It must not be added to CI.
- It must not be converted into a runtime validator.
- It must not automatically read files.
- It must not write files.
- It must not call services, ports, Ollama, or endpoints.
- It must not be connected to ZDoc runtime.

KG-RUNTIME-02 does not change this status.

## 9. KG-RUNTIME-03 Minimum Scope If Authorized

KG-RUNTIME-03 may proceed only after ChatGPT separately authorizes it.

Recommended minimum implementation scope:

| Area | Minimum allowable scope if separately authorized | Still prohibited |
| --- | --- | --- |
| Adapter shape | A small read-only preview adapter candidate with explicit default-off behavior | Any automatic runtime loading |
| Inputs | Static disabled entity metadata only, preferably KG-31 and KG-33 fields | Raw `AI知识图谱大全` file copying |
| Trigger | Manual preview-only trigger | Trigger from `/generate`, export, review, scoring, or ZBid |
| Output | Human-readable preview summary only | Evidence, scoring basis,正文 writeback, DOCX, job output |
| Registry | No registry registration | Real registry creation or activation |
| RAG | No RAG access | Retrieval enablement or corpus ingestion |
| Prompt registry | No prompt registry access | Prompt pack registration or activation |
| System instruction registry | No system instruction access | System instruction loading or promotion |
| Validator | No validator execution by default | Running KG-41, `py_compile`, tests, or CI |

Recommended forbidden modification scope for KG-RUNTIME-03:

- No changes to KG-08 manifest candidate JSON.
- No changes to KG-15 registry candidate JSON.
- No changes to KG-31 manifest entity JSON.
- No changes to KG-33 registry entity JSON.
- No changes to KG-41 validator draft.
- No changes to existing docs unless explicitly authorized.
- No changes to tests, frontend, backend, or config unless KG-RUNTIME-03
  explicitly lists those files.
- No changes outside `/Users/youfeini/Desktop/文档生成系统`.
- No file operations against `/Users/youfeini/Desktop/AI知识图谱大全` beyond
  read-only inspection if separately authorized.

## 10. KG-RUNTIME-03 Input Conditions

KG-RUNTIME-03 should not start unless all conditions below are met:

- ChatGPT explicitly authorizes KG-RUNTIME-03.
- The authorized file list is known before edits begin.
- The start HEAD and tag are recorded.
- The worktree is checked before edits.
- KG-31 and KG-33 are confirmed still disabled and not registered.
- KG-41 is confirmed unchanged and not executed.
- The future adapter boundary is confirmed as default-off and read-only.
- The rollback approach is defined before implementation.

## 11. KG-RUNTIME-03 Output Conditions

If KG-RUNTIME-03 is authorized later, acceptable output should remain narrow.

Preferred output pattern:

- One minimal adapter candidate or one minimal design-to-code scaffold, only if
  explicitly authorized.
- One review document describing why the adapter is still preview-only.
- No registration file.
- No runtime config enablement.
- No output artifacts.
- No generated DOCX.
- No model changes.

Any broader output must be rejected unless separately authorized by ChatGPT.

## 12. Rollback Requirements

If a future KG-RUNTIME-03 adapter candidate is created, rollback must be simple:

- Remove or disable the adapter candidate without touching KG-31 or KG-33.
- Preserve KG-08, KG-15, KG-31, KG-33, and KG-41 unchanged.
- Confirm no registry state was created.
- Confirm no runtime config was changed.
- Confirm no output/job/export files were written.
- Confirm no model files were pulled, replaced, or deleted.
- Confirm no service was started and no endpoint was called.

The adapter must not create durable runtime state that requires database,
registry, or model cleanup.

## 13. Acceptance Criteria For Any Future Adapter

A future adapter cannot pass acceptance unless all of the following are true:

- It is default-off.
- It is manually triggered.
- It reads only allowed static disabled entity metadata.
- It does not copy source knowledge files.
- It does not expose raw system instruction or prompt text.
- It does not write document正文.
- It does not enter `/generate`.
- It does not call `/export_docx`.
- It does not call `/review/apply`.
- It does not write back to ZBid.
- It does not create evidence.
- It does not affect scoring.
- It does not connect to RAG.
- It does not connect to prompt registry.
- It does not connect to system instruction registry.
- It does not write `output/job/export`.
- It does not run KG-41 validator draft.
- It does not trigger model upgrade or model pull.

## 14. Current Stage Closure

KG-RUNTIME-02 closes as a docs-only implementation authorization gate.

Current status:

- AI knowledge graph remains outside ZDoc runtime.
- KG read-only preview remains design-only.
- No adapter has been created.
- No code has been modified.
- No JSON has been modified.
- No validator has been run or compiled.
- No service, Ollama, port, or endpoint has been touched.
- No local model has been upgraded, pulled, deleted, or replaced.
- KG-RUNTIME-03 is not entered.

Further progress requires a separate ChatGPT authorization with a new task ID,
new start baseline, explicit allowed files, and explicit no-runtime acceptance
criteria.
