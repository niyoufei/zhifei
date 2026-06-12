# LOCAL-LAUNCHER-011 ZDOC Local App V1 Controlled Start Readiness Gate

## 1. Node Identification

- Node: `LOCAL-LAUNCHER-011-ZDOC-LOCAL-APP-V1-CONTROLLED-START-READINESS-GATE`
- Scope: docs-only V1 controlled start readiness gate.
- Target artifact: `docs/zdoc-local-launcher-v1-controlled-start-readiness-gate-local-launcher-011.md`
- Execution boundary: no implementation, no V0 artifact modification, no service run, no endpoint access, no Ollama, no trial, and no generation/export/write-back.

## 2. Baseline

- HEAD: `ed2cc3222a4e6c18a18a233db515b831831c0391`
- Tag: `v0.1.646-local-launcher-zdoc-local-app-v0-safety-shell-chinese-manual-reverification-pass-gate`
- Current branch line: `LOCAL-LAUNCHER`
- Current node nature: docs-only V1 controlled start readiness gate
- Starting branch confirmation: `main`
- Starting worktree status: clean

The required baseline matched before this document was created.

## 3. Purpose

LOCAL-LAUNCHER-011 defines only the readiness boundary for a possible future V1 controlled start. It does not implement, run, open, start, stop, access, or repair any runtime component.

This node exists only to define the prerequisites, risks, acceptance matrix, and future authorization path that must be satisfied before a later node may even consider implementing V1 controlled startup.

Binding purpose limits:

1. V1 readiness is not immediate service startup.
2. LOCAL-LAUNCHER-011 does not implement code.
3. LOCAL-LAUNCHER-011 does not modify V0 files.
4. LOCAL-LAUNCHER-011 does not start ZDoc service.
5. LOCAL-LAUNCHER-011 does not access endpoint.
6. LOCAL-LAUNCHER-011 does not run Ollama.
7. LOCAL-LAUNCHER-011 does not enter trial.
8. LOCAL-LAUNCHER-011 does not trigger generation/export/write-back.
9. LOCAL-LAUNCHER-011 does not read real KG.
10. LOCAL-LAUNCHER-011 does not read real project material.
11. LOCAL-LAUNCHER-011 stops after completion.

## 4. V0 Closure Inheritance

LOCAL-LAUNCHER-011 reviews and inherits the V0 closure chain without modifying it:

1. LOCAL-LAUNCHER-001 requirements and safety gate completed.
2. LOCAL-LAUNCHER-002 skeleton implementation authorization gate completed.
3. LOCAL-LAUNCHER-003 V0 safety shell skeleton created.
4. LOCAL-LAUNCHER-004 static artifact audit passed.
5. LOCAL-LAUNCHER-005 user handoff completed.
6. LOCAL-LAUNCHER-006 manual verification status recorded.
7. LOCAL-LAUNCHER-007 Chinese localization correction authorized.
8. LOCAL-LAUNCHER-008 Chinese localization implemented.
9. LOCAL-LAUNCHER-009 Chinese localization static audit passed.
10. LOCAL-LAUNCHER-010 user manual re-verification passed.
11. V0 Chinese safety shell accepted.

Inherited closure meaning:

1. V0 is a static Chinese safety shell.
2. V0 is accepted only as a static visual and documentation safety shell.
3. V0 does not authorize runtime behavior.
4. V0 does not authorize endpoint access.
5. V0 does not authorize Ollama.
6. V0 does not authorize trial.
7. V0 does not authorize generation, export, or write-back.
8. V0 does not authorize real KG or real project material reads.

## 5. V1 Controlled Start Definition

Future V1 controlled start, if separately authorized later, may be designed as a bounded startup and shutdown control layer for already-defined local ZDoc services.

Future V1 may target:

1. controlled startup of ZDoc backend;
2. controlled startup of ZDoc frontend;
3. service status checks;
4. log path display;
5. port status checks;
6. one-click stop;
7. visible service status;
8. visible abnormal-state prompts;
9. visible no-generation/no-export/no-write-back state;
10. startup and shutdown audit information.

Future V1 does not mean:

1. generation;
2. export;
3. write-back;
4. trial;
5. real KG read;
6. real project material read;
7. registration/metadata/proof/manifest/sample instance read;
8. model execution;
9. production use;
10. 50-user formal use.

LOCAL-LAUNCHER-011 defines these meanings only. It does not execute any V1 capability.

## 6. V1 Readiness Preconditions

V1 implementation authorization may be considered only if every precondition below is satisfied in a later separately authorized gate.

| No. | Precondition | Required evidence | Failure action |
| --- | --- | --- | --- |
| 1 | ChatGPT master-control reviews LOCAL-LAUNCHER-011 and approves it. | Review result explicitly names `LOCAL-LAUNCHER-011` as approved. | Stop; do not enter V1 authorization. |
| 2 | User explicitly authorizes a later V1 implementation authorization gate. | User instruction names the next V1 authorization node and exact scope. | Stop; wait for explicit authorization. |
| 3 | Repository is clean before later V1 work. | `git status --short` is empty in the later node. | Stop; report dirty state. |
| 4 | V0 artifacts have passed user manual re-verification. | LOCAL-LAUNCHER-010 acceptance is present and inherited. | Stop; return to V0 verification or correction path. |
| 5 | Backend startup command is separately authorized. | Later node lists exact command, working directory, environment, owner, and stop condition. | Stop before backend command. |
| 6 | Frontend startup command is separately authorized. | Later node lists exact command, working directory, environment, owner, and stop condition. | Stop before frontend command. |
| 7 | Service ports are separately authorized. | Later node lists exact intended ports and allowed port-check method. | Stop before port check or listener inspection. |
| 8 | Log read scope is separately authorized. | Later node lists exact log path whitelist, allowed fields, redaction rule, and no-content boundary. | Stop before log read. |
| 9 | Config read scope is separately authorized. | Later node lists exact config files, allowed fields, redaction rule, and write prohibition. | Stop before config read. |
| 10 | Endpoint health check is separately authorized. | Later node lists exact endpoint allowlist, method, expected response, and no-data boundary. | Stop before endpoint access. |
| 11 | Ollama remains prohibited by default. | Later node either preserves no-Ollama or separately authorizes a bounded model-runtime gate. | Stop before any Ollama command. |
| 12 | Generation/export/write-back remain prohibited by default. | Later node states no generation, no export, no write-back, no output/job/export write. | Stop before any write path. |
| 13 | Trial remains prohibited by default. | Later node states no preview-only, real use, small-scope trial, or 50-user use. | Stop before trial. |
| 14 | Real KG and real project materials remain prohibited by default. | Later node states no real KG, no real project, no tender, no business, and no privacy data reads. | Stop before protected data read. |

No single precondition may be inferred from this document. Every later action must be separately named and authorized.

## 7. V1 Allowed Future Capability Boundary

If a later node separately authorizes V1 implementation, that future authorization may define a limited capability boundary such as:

1. controlled backend startup;
2. controlled frontend startup;
3. process status viewing;
4. port listener status viewing;
5. whitelisted log path viewing;
6. controlled service stop;
7. service status display;
8. abnormal-state display;
9. no-generation/no-export/no-write-back state display;
10. startup/stop audit record display.

LOCAL-LAUNCHER-011 does not authorize any of the above actions.

All future capabilities require a separate node that defines exact files, exact commands, exact ports, exact logs, exact process ownership, exact stop behavior, exact rollback behavior, and exact verification boundaries.

## 8. V1 Prohibited Default Boundary

Even if the LOCAL-LAUNCHER line later enters V1, the following remain prohibited by default:

1. Ollama run.
2. Model call.
3. Real KG read.
4. Real project material read.
5. Registration/metadata/proof/manifest/sample instance read.
6. Generation.
7. Export.
8. Write-back.
9. ZBid write-back.
10. Trial.
11. Real use.
12. 50-user formal use.
13. Output/job/export write.
14. Unauthorized endpoint access.

Default prohibited means no substitute command, no fallback probe, no hidden background action, no browser action, no automatic check, and no continuation into runtime behavior without a later explicit authorization gate.

## 9. V1 Risk Register

| No. | Risk | Control | Verification | Stop condition |
| --- | --- | --- | --- | --- |
| 1 | Starting services may cause port conflict. | Later gate must define exact port ownership and conflict handling. | Authorized port evidence only. | Unknown or occupied port outside scope. |
| 2 | Service may not close correctly. | Later gate must define owned processes and stop command. | Authorized process status evidence only. | Stop path absent or process owner unclear. |
| 3 | Endpoint may be accessed accidentally. | Endpoint access remains banned until allowlist is explicit. | No endpoint command in 011; later endpoint allowlist required. | Any need for unlisted endpoint. |
| 4 | Logs may expose paths or sensitive information. | Later gate must whitelist log paths and redact protected content. | Allowed log metadata only. | Log body or sensitive content required. |
| 5 | Launcher may mislead users into thinking generation is available. | UI must keep generation/export/write-back visibly disabled. | Static UI or later UI review. | Any wording suggests write-path availability. |
| 6 | Button click may trigger unintended action. | Dangerous buttons must stay disabled until exact action is authorized. | Later implementation review. | Button has action without authorization. |
| 7 | Process residue may remain after startup. | Later gate must define cleanup and owned-process shutdown. | Authorized stop evidence. | Residual process outside ownership boundary. |
| 8 | Config path may be wrong or overexposed. | Later gate must define config whitelist and redaction. | Whitelisted config metadata only. | Need to read unlisted config or secret value. |
| 9 | Multiple clicks may create duplicate processes. | Later gate must define idempotent start lock and status check. | Controlled start state evidence. | Duplicate start cannot be prevented. |
| 10 | Future preview-only integration may blur boundaries. | Preview-only remains separate and prohibited until V2 authorization. | Later docs must name preview-only gate. | V1 attempts preview or trial. |
| 11 | Model Fleet governance may be confused with launcher governance. | LOCAL-LAUNCHER cannot authorize model execution or governance bypass. | Later docs must preserve mainline separation. | V1 attempts model/governance shortcut. |
| 12 | ZBid write-back boundary may be confused with service startup. | Write-back remains disabled and separately gated. | Later docs must state no ZBid write-back. | V1 attempts ZBid write-back. |

## 10. V1 UI Evolution Proposal

If a later V1 implementation authorization gate is approved, the UI may evolve from V0 safety shell toward a controlled-start console while preserving the safety surface:

1. Keep Chinese interface.
2. Keep safety boundary prompts.
3. Add service status area.
4. Add pre-start check area.
5. Add stop-service area.
6. Add log area.
7. Add port area.
8. Keep generation/export/write-back disabled prompts.
9. Keep Ollama disabled prompt.
10. Keep real KG and real project material disabled prompts.

This proposal is not implementation authorization. It is only a readiness design boundary for a future node.

## 11. Future Implementation Gate Recommendation

Recommended next node, only after ChatGPT master-control review and explicit user authorization:

`LOCAL-LAUNCHER-012-ZDOC-LOCAL-APP-V1-CONTROLLED-START-IMPLEMENTATION-AUTHORIZATION-GATE`

Required constraints for that future node:

1. LOCAL-LAUNCHER-012 should still be an authorization gate.
2. LOCAL-LAUNCHER-012 must not directly start service.
3. LOCAL-LAUNCHER-012 must not access endpoint.
4. LOCAL-LAUNCHER-012 must not run Ollama.
5. LOCAL-LAUNCHER-012 must not enter trial.
6. LOCAL-LAUNCHER-012 should define only V1 implementation code scope and runtime prerequisites.
7. Real service startup must require a separate runtime preflight or execution gate.

LOCAL-LAUNCHER-011 does not enter LOCAL-LAUNCHER-012.

## 12. Decision

`LOCAL-LAUNCHER-011 ZDOC LOCAL APP V1 CONTROLLED START READINESS GATE COMPLETED / DOCS-ONLY / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

This decision is based only on the allowed LOCAL-LAUNCHER prior documents and allowed V0 static files. It does not rely on backend/frontend source, runtime state, endpoint output, Ollama output, real KG, real project material, registration, metadata, proof, manifest, sample, output, job, or export bodies.

## 13. Next Node Boundary

LOCAL-LAUNCHER-011 stops after this document is created, checked, committed, tagged, pushed, and reported.

LOCAL-LAUNCHER-011 must not enter `LOCAL-LAUNCHER-012`.

LOCAL-LAUNCHER-011 must not run service.

LOCAL-LAUNCHER-011 must not open the page.

LOCAL-LAUNCHER-011 must not modify V0 artifacts.

LOCAL-LAUNCHER-011 must not access endpoints, execute `curl`, send HTTP requests, run Ollama, run tests, enter trial, trigger generation, trigger export, trigger write-back, read real KG, read real project materials, or write output/job/export.

Recommended next node only after ChatGPT master-control review and explicit later authorization:

`LOCAL-LAUNCHER-012-ZDOC-LOCAL-APP-V1-CONTROLLED-START-IMPLEMENTATION-AUTHORIZATION-GATE`

This recommendation is not authorization. Codex must stop and wait.
