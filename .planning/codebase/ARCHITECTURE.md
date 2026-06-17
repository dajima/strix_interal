# Codebase Architecture

**Last mapped:** 2026-06-16
**Commit:** 11e5d1c

## Architectural Pattern

**Modular monolith** with clear package boundaries. Each package (strix/<domain>/) owns its layer. The architecture follows a pipeline pattern: CLI/TUI entry → config resolution → Docker sandbox setup → agent orchestration → tool execution → vulnerability reporting.

No DI framework. Dependency wiring is manual: strix/core/runner.py orchestrates everything, passing settings, sandbox clients, and configuration down to agents and tools explicitly.

## Layer Map

`
┌─────────────────────────────────────────────┐
│  strix/interface/   ← CLI args + TUI render  │
│  (main.py, cli.py, tui/)                     │
├─────────────────────────────────────────────┤
│  strix/core/        ← Orchestration layer    │
│  (runner.py, execution.py, sessions.py)      │
├─────────────────────────────────────────────┤
│  strix/agents/      ← Agent factory + prompts│
│  (factory.py, prompt/, prompts/)             │
├────────────────┬─────────────────────────────┤
│  strix/runtime/ │  strix/tools/              │
│  Docker sandbox │  AI agent toolset          │
│  lifecycle      │  (15 tool packages)        │
├────────────────┴─────────────────────────────┤
│  strix/config/    strix/report/              │
│  pydantic-settings vulnerability reports    │
├─────────────────────────────────────────────┤
│  strix/skills/     strix/telemetry/          │
│  (custom prompt    PostHog + Scarf          │
│   injection)                                 │
└─────────────────────────────────────────────┘
`

## Entry Points

| Entry | File | Purpose |
|---|---|---|
| strix CLI | strix/interface/main.py:main() | Registered as console script in pyproject.toml |
| CLI mode | strix/interface/cli.py | Non-interactive scan execution |
| TUI mode | strix/interface/tui/ | Interactive terminal UI (Textual framework) |
| un_strix_scan() | strix/core/runner.py | Programmatic entry for internal/embedded use |

## Data Flow

1. **CLI parsing** (main.py): arguments → validate env vars (STRIX_LLM, LLM_API_KEY) → check Docker → pull image → warm up LLM → generate run name
2. **Target resolution** (interface/utils.py): target string → type inference (URL, repo, local code, domain, IP) → workspace setup → diff scope (for git repos)
3. **Sandbox setup** (untime/): Docker client → create session with StrixDockerSandboxClient → apply manifest → start → inject Caido proxy
4. **Agent creation** (gents/factory.py): build SandboxAgent with tools + skills + system prompt → file system + shell capabilities
5. **Execution** (core/execution.py): run agent loop with max turns → stream events → handle child agent spawning / messaging
6. **Reporting** (eport/state.py, eport/writer.py): collect vulnerability reports → write JSON artifacts to strix_runs/<run_name>/

## Multi-Agent Topology

Strix supports hierarchical agent teams:
- **Root agent** (tool: create_agent) — spawns child agents for parallel investigation
- **Child agents** (tool: gent_finish) — focused sub-tasks, communicate via send_message_to_agent / wait_for_message
- **Agent graph** (tool: iew_agent_graph) — runtime visualization of agent topology
- Coordination via strix/tools/agents_graph/tools.py and strix/core/agents.py (AgentCoordinator)

## Key Abstractions

### Settings (strix/config/settings.py)
pydantic-settings BaseSettings with env var aliases. Nested settings: LlmSettings, RuntimeSettings, TelemetrySettings, IntegrationSettings.

### Sandbox Backend (strix/runtime/backends.py)
Pluggable backend registry. Default: Docker. Supports custom backends via egister_backend(). Config via STRIX_RUNTIME_BACKEND.

### Agent Factory (strix/agents/factory.py)
uild_strix_agent() — constructs SandboxAgent with:
- System prompt (rendered from strix/agents/prompt/)
- Tool set (26 tools for root, 25 for child)
- Sandbox capabilities (Filesystem, Shell)
- Lifecycle behavior (finish on inish_scan or gent_finish success)

### Tool Adapters (strix/agents/factory.py subroutines)
_custom_tool_as_function_tool() — wraps SDK CustomTool instances as FunctionTool for chat-completions model compatibility.
_wrap_exec_command() — catches ValidationError and InvalidManifestPathError for graceful error messages.

### Report State (strix/report/state.py)
Singleton ReportState tracking: vulnerability reports, usage stats, run record, completion status. LiteLLM cost tracking callback registered globally.

### Runtime Session (strix/runtime/session_manager.py)
create_or_reuse() — manages sandbox session lifecycle. Tracks agent-to-session mapping for multi-agent scenarios via AgentCoordinator.

## Dependency Direction

`
interface → config → (core, runtime, agents, report, telemetry, tools)
core → (agents, runtime, report, telemetry, config)
agents → (tools, skills, config)
tools → (runtime, report, config)
`

No circular imports. Lazy imports used in strix/runtime/backends.py (docker imported lazily), strix/report/usage.py, and various tools to avoid bootstrap dependencies.

## Pattern Usage

- **Singleton state:** ReportState accessed via get_global_report_state()
- **Factory pattern:** make_child_factory() creates agent builders with captured params
- **Strategy pattern:** SandboxBackend callable allows backend swapping
- **Closure-based configuration:** _make_shell_configurator() captures chat_completions flag
- **Lazy imports:** Heavy dependencies (docker, litellm internals) imported inside function bodies
