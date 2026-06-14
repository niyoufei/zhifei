# LOCAL-LAUNCHER-001 ZDoc Local App Requirements And Safety Gate

## 1. Node

- Node: `LOCAL-LAUNCHER-001-ZDOC-LOCAL-APP-REQUIREMENTS-AND-SAFETY-GATE`
- Node type: docs-only / requirements-and-safety-gate.
- Scope: define the local App / local launcher positioning, technical route, safety boundaries, and later implementation gate.
- This node does not implement code, create scripts, create an App, start services, access endpoints, run Ollama, read real data, trigger generation/export/write-back, or enter trial.

## 2. Start State

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `6b52ac253de491118c5466ad21448089ee9f6502`
- Start tag at HEAD: `v0.1.696-local-launcher-zdoc-local-app-v1-ollama-server-recovery-execution-authorization-gate`
- Worktree preflight: `git status --short` was clean.
- Target docs file preflight: `docs/zdoc-local-launcher-v1-requirements-and-safety-gate-local-launcher-001.md` did not exist.
- Target tag preflight: `v0.1.625-local-launcher-zdoc-local-app-requirements-and-safety-gate` did not exist locally or remotely.
- Historical note: this node is being re-executed on the current repository HEAD without reset, checkout, or history rewrite.

## 3. Local App / Local Launcher Positioning

The local App / local launcher is a future local control surface for operating the ZDoc local workflow on the user's Mac. Its role is to make approved local actions visible, deliberate, and bounded.

The launcher is not the ZDoc generation engine, not a KG reader, not an Ollama model runner, and not a trial or production usage surface. It is an operator-facing wrapper that may later expose approved start, stop, status, log, port, and configuration controls only after a separate implementation gate authorizes code work.

The launcher must default to auditability over convenience. Every future action must be explicit, visible, and tied to a user-approved gate.

## 4. Technical Route

The intended route is a local-only desktop or local web control surface that can call narrowly authorized local commands through a constrained backend adapter.

The route must preserve these principles:

- UI first presents state and allowed actions; it must not auto-run services.
- Command execution, if later authorized, must be mediated by a small allowlisted command layer.
- Runtime controls must be separated from generation, export, write-back, KG access, project-data access, and model inference.
- Any future implementation must use existing repository conventions and must be authorized by a later code implementation gate.
- The first implementation milestone must be preview/safe controls only, not real trial or production use.

No technology stack is selected or implemented by this node. A later gate must decide whether the surface is implemented as a local web UI, desktop wrapper, menu-bar helper, or another local-only form.

## 5. Allowed Function Boundary

A future authorized launcher may expose only explicitly approved controls such as:

- Show local service status summaries.
- Show configured port and process status summaries.
- Show selected non-sensitive log summaries.
- Start, stop, or restart local services only when a later recovery/execution gate explicitly authorizes those actions.
- Display safe configuration values and local environment readiness checks.
- Show operator-facing warnings before any action that can change runtime state.
- Produce structured status reports for ChatGPT review.

Allowed functions must remain local to the user's Mac and must be reversible or inspectable where possible.

## 6. Forbidden Function Boundary

The launcher must not:

- Run ZDoc generation, export, or write-back.
- Read real KG content.
- Read real project materials.
- Read real bidding documents.
- Read `.env`, secrets, tokens, credentials, private keys, cookies, or account material.
- Read registration, metadata, proof, manifest, or sample instances unless a later gate explicitly authorizes a narrow review.
- Read output/job/export bodies.
- Read full log bodies.
- Read `/tmp` stdout/stderr capture bodies except where a later gate authorizes a bounded non-sensitive excerpt.
- Run Ollama model inference.
- Send prompts to any model.
- Download, delete, create, or run models.
- Access endpoints or issue HTTP requests.
- Enter trial, real use, or 50-person formal use.
- Modify backend/frontend/config/dependency surfaces unless a later code implementation gate authorizes the exact files.
- Auto-enter `LOCAL-LAUNCHER-002`.

## 7. Start Boundary

The launcher must not start ZDoc, Ollama, or any local service by default.

Any future start action requires:

- A named gate authorizing the exact service.
- A clean preflight state.
- A visible user confirmation.
- A capture plan for non-sensitive stdout/stderr.
- A bounded post-start status check.
- A mandatory stop-and-report step before the next node.

## 8. Stop Boundary

The launcher must not stop or kill processes automatically.

Any future stop action requires:

- A named gate authorizing the exact process or service.
- Confirmation that the target process belongs to the intended local workflow.
- A non-sensitive before/after status summary.
- No use of broad kill patterns.

## 9. Status Check Boundary

Status checks must be read-only and must prefer non-sensitive summaries:

- Current process presence.
- Port listen state.
- Homebrew service summary.
- launchctl summary.
- Local file existence where explicitly authorized.

Status checks must not become endpoint probes, model prompts, real data reads, or log body reads without a later explicit gate.

## 10. Log Boundary

Logs are treated as potentially sensitive.

The launcher may only show:

- Whether an approved log or capture file exists.
- File path, size, and timestamp metadata where authorized.
- A bounded excerpt only if a later gate explicitly authorizes the exact file and line limit.
- A non-sensitive summary that avoids credentials, environment variables, personal data, project content, prompts, and model output.

## 11. Port Boundary

Port handling must stay observational unless later authorized:

- It may show whether a specific approved port is listening.
- It may show process name and PID summaries for approved ports.
- It must not call the port endpoint.
- It must not issue `curl`, browser requests, HTTP requests, or health probes unless a later endpoint gate authorizes them.

## 12. Configuration Boundary

Configuration handling must be safe by default:

- The launcher may show a list of required configuration categories.
- It may show whether a required config file exists only when authorized.
- It must not display secret values.
- It must not edit configuration unless a later code/config gate authorizes the exact file and fields.
- It must not create or mutate `.env`, credentials, tokens, or model configuration.

## 13. Relationship Boundaries

### ZDoc

The launcher may become a local operator surface around ZDoc lifecycle controls only after later authorization. It is not itself ZDoc generation, export, or write-back.

### KG

The launcher must not read real KG. It may only record that KG access is out of scope until a later explicit data-access gate.

### Ollama

The launcher may later display Ollama readiness or service state only through approved diagnostics. It must not run `ollama serve`, `ollama list`, `ollama run`, `ollama pull`, `ollama create`, or `ollama rm` unless a later node explicitly authorizes the exact action. Model inference and prompt input remain forbidden here.

### ZBid

The launcher must not read real bidding documents or ZBid project materials. Any future ZBid-facing function requires a separate authorization gate and must distinguish UI control from real document access.

## 14. Later Code Implementation Gate

No code implementation is authorized by this node.

A later implementation gate must define:

- Exact files allowed to be created or modified.
- Whether the launcher is local web, desktop wrapper, menu-bar helper, or another form.
- Allowed dependencies, if any.
- Allowed commands and adapters.
- UI scope and safety copy.
- Test scope.
- Verification scope.
- Explicit prohibition on generation/export/write-back, real KG reads, endpoint access, and trial unless separately authorized.

Without that later gate, no launcher code, scripts, App package, dependency changes, or runtime controls may be created.

## 15. Entry Conditions For `LOCAL-LAUNCHER-002`

`LOCAL-LAUNCHER-002` may not start automatically.

Entry requires all of the following:

- ChatGPT total-controller review approves this 001 docs artifact.
- The 001 commit exists and is pushed.
- The 001 tag exists and is pushed.
- Worktree is clean.
- The user explicitly authorizes the next node.
- The next node states its own allowed and forbidden scope.

## 16. Execution Negatives

During this node:

- Code modified: no.
- Script created: no.
- App created: no.
- Service run: no.
- Endpoint accessed: no.
- Ollama run: no.
- Any Ollama command executed: no.
- Model inference executed: no.
- Prompt input to model: no.
- Real KG read: no.
- Real project data read: no.
- Real bidding documents read: no.
- `.env` / secrets / tokens / credentials read: no.
- Registration / metadata / proof / manifest / sample instances read: no.
- Output/job/export body read: no.
- Log body read: no.
- Generation/export/write-back triggered: no.
- Output/job/export written: no.
- Trial entered: no.
- Real use or 50-person formal use entered: no.
- `LOCAL-LAUNCHER-002` entered: no.

## 17. Current Decision

`LOCAL-LAUNCHER-001 ZDOC LOCAL APP REQUIREMENTS AND SAFETY GATE COMPLETED / REQUIREMENTS AND SAFETY BOUNDARY DOCUMENTED / LOCAL APP POSITIONING DOCUMENTED / TECHNICAL ROUTE DOCUMENTED / ALLOWED AND FORBIDDEN FUNCTION BOUNDARIES DOCUMENTED / START STOP STATUS LOG PORT CONFIG BOUNDARIES DOCUMENTED / CODE IMPLEMENTATION GATE DOCUMENTED / NO CODE IMPLEMENTED / NO SCRIPT CREATED / NO APP CREATED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED / STOPPED BEFORE LOCAL-LAUNCHER-002`

## 18. Stop

Stop after this node and report for ChatGPT total-controller review. Do not enter `LOCAL-LAUNCHER-002`.
