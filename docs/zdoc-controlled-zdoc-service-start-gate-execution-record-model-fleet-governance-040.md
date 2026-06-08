# MODEL-FLEET-GOVERNANCE-040: Controlled ZDoc Service Start Gate Execution Record

## 1. Baseline

- Task node: `MODEL-FLEET-GOVERNANCE-040-CONTROLLED-ZDOC-SERVICE-START-GATE`
- Node type: controlled ZDoc service start gate
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `ea47779807d546c71ea9f88994abd3d270f7aa10`
- Start tag at HEAD: `v0.1.600-zdoc-controlled-endpoint-validation-preflight-gate`
- Previous node: `MODEL-FLEET-GOVERNANCE-039-CONTROLLED-PREVIEW-ONLY-ENDPOINT-VALIDATION-PREFLIGHT-AND-SERVICE-START-GATE`
- Previous node status: reviewed and accepted as the current baseline

This node starts the ZDoc FastAPI service only for later controlled preview-only / no-write endpoint validation preparation.

This node does not access any endpoint, execute `curl`, send any HTTP request, read real KG, run Ollama, trigger formal generation, trigger export, trigger write-back, write `output`, `job`, or `export`, enter real use, or enter trial.

## 2. Authorized Inputs Reviewed

Required files read:

1. `docs/zdoc-controlled-preview-only-endpoint-validation-preflight-and-service-start-gate-model-fleet-governance-039.md`
2. `docs/zdoc-controlled-preview-only-endpoint-authorization-gate-model-fleet-governance-038.md`
3. `backend/tests/test_local_trial_preview_only_route.py`
4. `backend/app/routers/local_trial_preview_only.py`

Additional startup-related files read because the startup command was not confirmed in the first four files:

1. `backend/app/main.py`
2. `backend/app/__init__.py`
3. `README.md`

The following allowed startup-related files were checked for existence and were not present:

1. `pyproject.toml`
2. `backend/pyproject.toml`
3. `Makefile`

No full-repository `rg` was executed.

No unknown `.json` body was read.

No `知识图谱/**`, `AI知识图谱大全/**`, `output/**`, `job/**`, or `export/**` path was read.

## 3. Startup Command Source

The service startup command was confirmed from `README.md`, under the manual backend service startup section:

```bash
export PYTHONPATH="$PWD:$PYTHONPATH"
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The README also lists a later `curl` verification step, but that step was not executed because endpoint access, `curl`, and HTTP requests are prohibited in this node.

`backend/app/main.py` confirms the FastAPI app object:

```text
app = FastAPI()
```

and includes `local_trial_preview_only_router`. Reading this file did not require endpoint access, real KG access, Ollama execution, generation, export, write-back, or trial.

## 4. Pre-Start State

- `git status --short`: clean
- `git rev-parse HEAD`: `ea47779807d546c71ea9f88994abd3d270f7aa10`
- `git log -1 --oneline`: `ea47779 docs: add controlled endpoint validation preflight gate`
- `git tag --points-at HEAD`: `v0.1.600-zdoc-controlled-endpoint-validation-preflight-gate`
- Existing listener on `127.0.0.1:8000`: none found
- Existing `uvicorn backend.app.main:app` process: none found

## 5. Service Start Execution

The authorized application command was started with a detached local process wrapper so the service could remain running and the log could be written outside the repository:

```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Runtime wrapper used for detached execution:

```text
screen -dmS zdoc_mfg040 sh -c 'exec env PYTHONPATH="$PWD:$PYTHONPATH" python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 >> /tmp/zdoc-service-start-model-fleet-governance-040.log 2>&1'
```

Service log path:

```text
/tmp/zdoc-service-start-model-fleet-governance-040.log
```

Initial detached background attempt returned PID `74884` but did not leave a running service, listener, or log output. A macOS `screen -Logfile` attempt failed before service start because the local `screen` version does not support that option. The final detached `screen` command above started the service successfully.

## 6. Post-Start Service State

- Service running: yes
- Service PID: `76906`
- Parent process chain: `SCREEN` PID `76882`, login shell PID `76883`, Python/Uvicorn PID `76906`
- Host: `127.0.0.1`
- Port: `8000`
- Listener: `TCP 127.0.0.1:8000 (LISTEN)`
- Bound to `0.0.0.0`: no
- Bound to external address: no
- Service still running after status check: yes

Observed process command:

```text
/Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Observed listener:

```text
Python 76906 youfeini TCP 127.0.0.1:8000 (LISTEN)
```

## 7. Log Summary

Log tail from `/tmp/zdoc-service-start-model-fleet-governance-040.log`:

```text
INFO:     Started server process [76906]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

The startup log shows only normal Uvicorn startup and application startup completion.

The startup log does not show endpoint access, `curl`, HTTP request handling, KG reads, Ollama calls, generation, export, write-back, ZBid write-back, output writes, job writes, export writes, or trial entry.

## 8. Prohibited Actions Confirmation

- Endpoint accessed: no
- `curl` executed: no
- HTTP request sent: no
- Real KG read: no
- Unknown `.json` body read: no
- `知识图谱/**` read: no
- `AI知识图谱大全/**` read: no
- `output/**` read: no
- `job/**` read: no
- `export/**` read: no
- Ollama run: no
- Any Ollama command executed: no
- Formal generation triggered: no
- Export triggered: no
- Write-back triggered: no
- `output` written: no
- `job` written: no
- `export` written: no
- Frontend started: no
- Extra worker started: no
- Scheduler started: no
- Generation worker started: no
- Export worker started: no
- Write-back worker started: no
- ZBid write-back chain started: no
- Database migration executed: no
- Seed executed: no
- Dependency install executed: no
- Test executed: no
- Real use entered: no
- Trial entered: no
- Image generation executed: no
- Image model called: no

## 9. Repository State After Start

- `git status --short` after service start, before this document was added: clean
- Repository changes made by this node: only this execution record document
- Non-target repository changes observed: no
- Service startup produced non-target repository changes: no

## 10. Next Gate Readiness

The service startup command was confirmed from authorized startup-related content.

The ZDoc service is running on localhost only.

No endpoint was accessed in this node.

No trial is authorized in this node.

The next node may proceed only if it separately authorizes controlled preview-only endpoint validation and continues to prohibit real KG, unknown `.json` bodies, formal generation, export, write-back, `output` writes, `job` writes, `export` writes, real use, and trial.

## 11. Current Decision

`CONTROLLED ZDOC SERVICE START COMPLETED / SERVICE RUNNING LOCALHOST ONLY / ENDPOINT NOT ACCESSED / NO TRIAL AUTHORIZED`
