# TdxClaw Evaluation

Date: 2026-07-08

This note records whether TdxClaw should be installed or integrated into Locust Plan at the current recovery stage.

## Decision

Do not install TdxClaw for now.

Reasons:

- The current project goal is to restore and stabilize Locust Plan, not to replace its data or trading workflow.
- TdxClaw is primarily a desktop AI investment research client. Its documented value is inside its own app, not a stable project-level API that Locust Plan can call directly today.
- It requires Tongdaxin token/model and data-service keys for full use. We do not have those keys configured in this project.
- The official notes warn that heartbeat behavior can consume model tokens or points if left running.
- Locust Plan already has AKShare-based A-share data access, local cockpit UI, DeepSeek, Doubao, and Futu checks. Installing another desktop client would add operational complexity before there is a clear integration path.

## Skills Worth Learning From

The following ideas are useful for future Locust Plan upgrades:

- Research task agents: split market review, position review, announcement/research-report digest, and post-trade review into separate assistant roles.
- Skill hub design: expose small, named analysis skills such as capital-flow scan, sector hotspot scan, portfolio stress test, failed-trade replay, and Fibonacci anchor review.
- Scheduled tasks: add recurring checks for holdings, abnormal volume, sector heat, and risk alerts.
- Tongdaxin terminal bridge: only consider this later if we need to operate a running Tongdaxin desktop terminal, such as sending selected stocks into a custom board or running Tongdaxin formulas.
- Data-service optional adapter: keep AKShare as the default A-share source. Add Tongdaxin data only as an optional connector after a data-service key is available.

## Possible Future Locust Plan Modules

- `tdx_data_connector.py`: optional Tongdaxin data-service connector, disabled unless `TDX_DATA_KEY` exists.
- `research_agents/`: role-specific prompts and workflows for holdings, market heat, announcements, and replay.
- `scheduled_jobs.py`: local scheduled research checks with manual on/off controls.
- `tdx_terminal_bridge.py`: experimental desktop-terminal bridge, only after explicit approval.

## Installer Handling

No TdxClaw installer was found on the desktop scan. If an installer is later found and we still choose not to install, remove only the clearly identified TdxClaw installer file, not unrelated trading or finance files.
