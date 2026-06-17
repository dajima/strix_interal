# Directory Structure

**Last mapped:** 2026-06-16
**Commit:** 11e5d1c

## Top Level

`
strix_interal/
├── strix/            ← Main Python package (79 .py files)
├── containers/       ← Docker sandbox image definitions
├── benchmarks/       ← Performance benchmarks
├── scripts/          ← Utility / deployment scripts
├── docs/             ← Documentation (not part of the Python package)
├── .github/          ← CI workflows (build-release.yml)
├── .planning/        ← GSD planning artifacts
├── pyproject.toml    ← Project metadata + tool config
├── Makefile          ← Dev commands
├── strix.spec        ← PyInstaller spec
└── README.md
`

## strix/ Package Structure

`
strix/
├── __init__.py
├── agents/                   ← Agent construction
│   ├── factory.py            # build_strix_agent(), make_child_factory()
│   ├── prompt.py             # System prompt rendering
│   └── prompts/              # Prompt templates / fragments
├── config/                   ← Application settings
│   ├── __init__.py           # load_settings(), persist_current()
│   ├── settings.py           # pydantic-settings BaseSettings
│   └── models.py             # StrixProvider, SDK model config, retry policy
├── core/                     ← Orchestration + execution
│   ├── runner.py             # run_strix_scan() — main scan orchestrator
│   ├── execution.py          # Agent loop execution, child spawning
│   ├── agents.py             # AgentCoordinator
│   ├── hooks.py              # ReportUsageHooks
│   ├── inputs.py             # Task building, scope context, model settings
│   ├── paths.py              # Runtime output directory paths
│   └── sessions.py           # SQLite session management
├── interface/                ← CLI + TUI
│   ├── main.py               # Entry point, arg parsing, orchestration
│   ├── cli.py                # Non-interactive CLI mode
│   ├── utils.py              # Target resolution, Docker checks, git clone
│   ├── assets/               # Static assets (ascii art, etc.)
│   └── tui/                  # Textual-based interactive TUI
│       ├── app.py            # Textual App subclass
│       └── renderers/        # Custom TUI renderers
├── report/                   ← Vulnerability reporting
│   ├── state.py              # ReportState (global singleton)
│   ├── writer.py             # JSON artifact persistence
│   └── usage.py              # Usage tracking
├── runtime/                  ← Sandbox execution
│   ├── __init__.py           # session_manager export
│   ├── session_manager.py    # Sandbox lifecycle management
│   ├── backends.py           # Pluggable backend registry
│   ├── docker_client.py      # Custom Docker sandbox client
│   └── caido_bootstrap.py    # Caido proxy container init
├── skills/                   ← Agent skill definitions
│   ├── cloud/
│   ├── coordination/
│   ├── custom/
│   ├── frameworks/           # e.g., Django, Flask, React
│   ├── protocols/            # e.g., OAuth, JWT, WebSocket
│   ├── reconnaissance/
│   ├── scan_modes/
│   ├── technologies/
│   ├── tooling/
│   └── vulnerabilities/      # e.g., XSS, SQLi, SSRF, IDOR
├── telemetry/                ← Analytics + logging
│   ├── posthog.py
│   ├── scarf.py
│   └── logging.py
├── tools/                    ← AI agent tools (15 packages)
│   ├── agents_graph/         # Multi-agent coordination: create_agent, send_message, etc.
│   ├── agent_browser/        # Agent-specific browser (empty — uses filesystem only)
│   ├── apply_patch/          # Apply code patches (empty)
│   ├── finish/               # finish_scan + lifecycle completion
│   ├── load_skill/           # Dynamic skill loading
│   ├── notes/                # Agent note-taking (CRUD)
│   ├── proxy/                # Caido proxy interaction
│   ├── reporting/            # create_vulnerability_report
│   ├── shell/                # Shell execution (empty — uses SDK Shell capability)
│   ├── thinking/             # Structured thinking tool
│   ├── todo/                 # Agent task tracking (CRUD)
│   ├── view_image/           # Image viewing (empty)
│   └── web_search/           # Perplexity web search
└── utils/                    ← Shared utilities
`

## Key File Locations

| What | Where |
|---|---|
| Entry point (CLI + TUI dispatch) | strix/interface/main.py:main() |
| Arg parsing | strix/interface/main.py:parse_arguments() |
| Scan orchestrator | strix/core/runner.py:run_strix_scan() |
| Agent construction | strix/agents/factory.py:build_strix_agent() |
| System prompt | strix/agents/prompt.py |
| Settings / env vars | strix/config/settings.py |
| LLM provider routing | strix/config/models.py:StrixProvider |
| Docker sandbox client | strix/runtime/docker_client.py |
| Vulnerability report state | strix/report/state.py |
| Tool definitions (root) | strix/tools/*/tool.py (or 	ools.py) |
| Run output directory | strix_runs/<run_name>/ (runtime-managed) |
| Config file | ~/.strix/cli-config.json |

## Test & Script Locations

| What | Where |
|---|---|
| CI workflow | .github/workflows/build-release.yml |
| Benchmark scripts | enchmarks/ |
| Utility scripts | scripts/ |
| Dev commands | Makefile |
| PyInstaller spec | strix.spec |
