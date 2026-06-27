# Canonical Static Asset Boundary

## 1. Boundary Status

`local_launcher/v1/` is the current LOCAL-LAUNCHER canonical static asset candidate boundary.

This boundary is not runtime authorization.

This boundary is not endpoint authorization.

This boundary is not localhost authorization.

This boundary is not Ollama or model inference authorization.

This boundary is not service startup authorization.

This boundary only records the static asset scope for later governance nodes.

## 2. In-Scope Static Assets

- `README.md`
- `launcher-state.json`
- Static display files in this directory.
- Static configuration snapshots in this directory.
- Static boundary and guidance files in this directory.

In-scope status does not mean writable status. Future writes still require an independent gate with an exact file allowlist.

## 3. Out-of-Scope Assets

- `../../local-launcher-v1/`
- `../../scripts/`
- `../../文档生成系统.app/`
- `../../施组专家系统.app/`
- `.runtime/`
- endpoint
- `localhost` / `127.0.0.1`
- Ollama
- model inference
- backend service
- frontend service
- startup scripts
- desktop launchers
- logs, PID files, output, job, export, real project data, secrets, tokens, and credentials

## 4. Forbidden Actions

- Start services.
- Access `localhost` / `127.0.0.1`.
- Probe ports.
- Make HTTP requests.
- Run `.app` launchers.
- Run `run_web_ui.sh`.
- Run `start_web_ui_background.sh`.
- Execute model calls.
- Run Ollama.
- Modify runtime, endpoint, Ollama, or model inference configuration.
- Read or write `.runtime/`, PID, log, output, job, or export bodies.
- Run tests, builds, installs, migrations, formatters, or generated-output commands without a separate explicit gate.

## 5. Future Gate Requirement

Any later modification to `README.md` or `launcher-state.json` must be authorized by an independent gate with an exact file allowlist, acceptance criteria, rollback requirements, and no-runtime policy.

Any later change that attempts to lift a runtime, service, endpoint, localhost, port, Ollama, or model inference prohibition must be authorized by a separate runtime, service, or endpoint gate.

Until such a gate exists and explicitly authorizes the action, all runtime, endpoint, localhost, Ollama, model inference, service startup, script execution, and `.app` launcher actions remain forbidden.
