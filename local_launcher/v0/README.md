# ZDoc Local Launcher V0 Safety Shell

This directory contains the V0 safety shell skeleton for the ZDoc local launcher.

V0 is a static safety shell only. It does not start, stop, probe, read, write, generate, export, or call any runtime component.

## Boundary

- V0 does not start ZDoc services.
- V0 does not access endpoints.
- V0 does not run Ollama or any model command.
- V0 does not enter trial, preview-only trial, real use, or production use.
- V0 does not trigger generation, export, or write-back.
- V0 does not read real KG content.
- V0 does not read real project materials.
- V0 does not read output, job, or export content.
- V0 does not include an executable launcher script.
- V0 does not create a packaged App.

## Files

- `index.html`: static local safety-shell page with status placeholders.
- `styles.css`: static local styles only.
- `launcher-state.json`: static placeholder state with all runtime permissions disabled.

## Controls

All action buttons are disabled by default. The disabled controls are visible only to show future V1/V2 boundary categories.

V0 cannot start ZDoc, stop ZDoc, open preview, run Ollama, generate documents, export documents, write back to ZBid, read KG, load project files, or open output/job/export content.

## Future Boundary

V1 may connect controlled startup only after a separate named authorization gate defines exact commands, ownership, ports, logs, stop behavior, rollback behavior, and verification limits.

Until that separate authorization exists, this V0 safety shell remains static, inert, and placeholder-only.

After LOCAL-LAUNCHER-003 is completed, the result must wait for ChatGPT master-control review. The workflow must stop and must not enter the next node automatically.
