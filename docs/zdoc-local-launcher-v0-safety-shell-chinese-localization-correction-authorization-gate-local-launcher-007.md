# ZDoc Local Launcher V0 Safety Shell Chinese Localization Correction Authorization Gate - LOCAL-LAUNCHER-007

## 1. Node Identification

- Node: `LOCAL-LAUNCHER-007-ZDOC-LOCAL-APP-V0-SAFETY-SHELL-CHINESE-LOCALIZATION-CORRECTION-AUTHORIZATION-GATE`
- Current branch: `main`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only Chinese localization correction authorization gate
- Scope: record user manual verification issue and define the future Chinese localization correction boundary only

LOCAL-LAUNCHER-007 is docs-only.

LOCAL-LAUNCHER-007 does not modify V0 artifacts.

## 2. Baseline

- HEAD: `def3889ac8247c98c830c05007eb25ad8a5a1bbe`
- Tag: `v0.1.642-local-launcher-zdoc-local-app-v0-safety-shell-manual-verification-result-record-gate`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only Chinese localization correction authorization gate
- Starting branch confirmation: `main`
- Starting worktree status: clean

The required baseline matched before this document was created.

## 3. Purpose

This node records the user manual verification issue and defines the authorization boundary for a future Chinese localization correction.

`LOCAL-LAUNCHER-007 records the user manual verification issue and authorizes only the documentation of a future Chinese localization correction boundary. It does not modify, run, open, start, stop, access, or repair any runtime component.`

This node does not execute the correction. It does not edit `index.html`, `README.md`, `launcher-state.json`, `styles.css`, backend, frontend, config, dependency, output, job, or export files.

## 4. User Manual Verification Issue

`User manually reviewed V0 and reported that the page is currently in English and needs to be changed to Chinese.`

Issue classification:

1. Issue type: UI language localization issue.
2. Affected user experience: ordinary users may not immediately understand the V0 safety-shell status.
3. Affected Chinese-user usability: Chinese users face unnecessary comprehension cost.
4. Affected productization experience: V0 should be Chinese-first before later readiness review.
5. Safety impact: no service run, endpoint access, Ollama run, generation/export/write-back, trial, real KG read, real project read, or output/job/export write risk was reported.
6. Current handling: enter correction authorization boundary documentation, not V1.

Allowed evidence command output confirmed English UI strings in `local_launcher/v0/index.html`, `local_launcher/v0/README.md`, and `local_launcher/v0/launcher-state.json`, including `Safety`, `Boundary`, `Status`, `Placeholder`, `Disabled`, `Repository`, `Branch`, `Endpoint`, `Ollama`, `Generation`, `Export`, `Write-back`, `Start`, `Stop`, `Open`, `Read`, and `Load`.

## 5. Correction Objective

The future Chinese localization correction objective is:

1. Change the page title to Chinese.
2. Change safety boundary wording to Chinese.
3. Change status placeholder areas to Chinese.
4. Change all button labels to Chinese.
5. Change disabled explanations to Chinese.
6. Make README Chinese-first.
7. Keep machine-readable field names in `launcher-state.json`; localize explanatory values if present and safe.
8. Preserve `V0 Safety Shell` or `V0 安全外壳` as a technical identifier.
9. Add no runtime ability.
10. Preserve all `disabled` and `false` safety states.

The correction objective is language localization only. It is not a feature, runtime, service, endpoint, trial, model, generation, export, write-back, KG, project-data, or V1 startup authorization.

## 6. Allowed Future Correction Scope For LOCAL-LAUNCHER-008

If LOCAL-LAUNCHER-008 is separately authorized, it may modify only:

```text
local_launcher/v0/index.html
local_launcher/v0/README.md
local_launcher/v0/launcher-state.json
docs/zdoc-local-launcher-v0-safety-shell-chinese-localization-correction-implementation-gate-local-launcher-008.md
```

Additional future-scope rules:

1. `styles.css` is not allowed by default.
2. `styles.css` may be modified only if Chinese display clearly requires minor layout adjustment and LOCAL-LAUNCHER-008 explicitly authorizes it.
3. Backend files must not be modified.
4. Frontend files must not be modified.
5. Config files must not be modified.
6. Dependency files must not be modified.
7. Scripts must not be added.
8. App packaging must not be created.
9. Services must not be run.
10. The page must not be opened by Codex.
11. Endpoints must not be accessed.
12. Ollama must not be run.

## 7. Prohibited Future Correction Scope

Even if LOCAL-LAUNCHER-008 is later authorized, the following remain prohibited by default:

1. Start service.
2. Stop service.
3. Open the HTML page.
4. Access endpoint.
5. Execute `curl`.
6. Run Ollama.
7. Run npm/yarn/pnpm/pip.
8. Run tests.
9. Trigger generation/export/write-back.
10. Write output/job/export.
11. Read real KG.
12. Read real project material.
13. Read registration/metadata/proof/manifest/sample instances.
14. Modify backend.
15. Modify frontend.
16. Modify dependencies.
17. Enter trial.
18. Enter real use.
19. Enter V1.

LOCAL-LAUNCHER-008, if authorized, must stay limited to static text localization and the target 008 documentation artifact.

## 8. Chinese Localization Acceptance Criteria

The Chinese localization correction is acceptable only if all criteria below are satisfied:

1. Ordinary users can clearly understand that the page is a `V0 安全外壳`.
2. The primary page title is Chinese.
3. Safety boundary wording is Chinese.
4. Status item labels are Chinese.
5. Status values are Chinese or bilingual without reducing clarity.
6. All button labels are Chinese.
7. All buttons remain disabled.
8. No endpoint URL appears.
9. No network request appears.
10. No real KG content appears.
11. No real project material appears.
12. No sensitive real path appears.
13. JSON permissions remain all `false`.
14. README still clearly states no service start, no endpoint access, no Ollama, no generation, no export, and no write-back.
15. A later manual re-verification is still required after localization.

The correction must preserve all V0 safety-shell restrictions.

## 9. Productization Judgment

Controller judgment:

1. V0 has passed static safety audit.
2. V0 has formed the static safety shell.
3. User manual viewing found a language mismatch issue.
4. Chinese localization is required before later V1 readiness consideration.
5. V1 is not recommended before localization correction is complete.
6. After localization correction, static audit and manual re-verification are still required.
7. Localization correction must not open any runtime permission.

This node authorizes only correction-boundary documentation. It does not authorize implementation, runtime behavior, service startup, endpoint access, Ollama, trial, generation, export, write-back, real KG read, real project read, output/job/export write, or V1.

## 10. Decision

`LOCAL-LAUNCHER-007 ZDOC LOCAL APP V0 SAFETY SHELL CHINESE LOCALIZATION CORRECTION AUTHORIZATION GATE COMPLETED / USER ISSUE RECORDED / CHINESE LOCALIZATION CORRECTION REQUIRED / DOCS-ONLY / NO FILES MODIFIED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 11. Next Node Boundary

LOCAL-LAUNCHER-007 must stop after this document is created, checked, committed, tagged, pushed, and reported.

LOCAL-LAUNCHER-007 must not enter `LOCAL-LAUNCHER-008`.

LOCAL-LAUNCHER-007 must not repair files.

LOCAL-LAUNCHER-007 must not modify V0 artifacts.

LOCAL-LAUNCHER-007 must not run service.

LOCAL-LAUNCHER-007 must not open the page.

After ChatGPT master-control review of this node, a later separately authorized instruction may decide whether to enter:

`LOCAL-LAUNCHER-008-ZDOC-LOCAL-APP-V0-SAFETY-SHELL-CHINESE-LOCALIZATION-CORRECTION-IMPLEMENTATION-GATE`

LOCAL-LAUNCHER-007 does not enter that node.
