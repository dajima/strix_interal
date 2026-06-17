# Codebase Tech Stack

**Last mapped:** 2026-06-16
**Commit:** 11e5d1c

## Languages & Runtime

- **Python >= 3.12** — pure Python, no Rust/C extensions
- **uv** — package manager and dependency resolver (uv.lock present)
- **hatchling** — build backend (PEP 517)

## Core Frameworks

| Dependency | Version | Purpose |
|---|---|---|
| openai-agents | 0.14.6 (with [litellm] extra) | AI agent orchestration SDK — SandboxAgent, tooling, multi-agent topology |
| pydantic | >=2.11.3 | Runtime validation, serialization |
| pydantic-settings | >=2.13.0 | Environment variable-backed settings (BaseSettings) |

## CLI / Interface

| Dependency | Version | Purpose |
|---|---|---|
| ich | latest | Formatting CLI output (panels, colors, progress spinners) |
| 	extual | >=6.0.0 | TUI framework for interactive terminal UI |
| rgparse | stdlib | CLI argument parsing in strix/interface/main.py |
| syncio | stdlib | Async execution loop tied to Textual (syncio.run) |

## Runtime / Sandbox

| Dependency | Version | Purpose |
|---|---|---|
| docker | >=7.1.0 | Docker Python SDK — container lifecycle, image pull |
| Docker daemon | host | Required runtime dependency (CLI checks shutil.which("docker")) |
| ghcr.io/usestrix/strix-sandbox:1.0.0 | 1.0.0 | Sandbox container image (default, overridable via STRIX_IMAGE) |

## External Integrations

| Dependency | Version | Purpose |
|---|---|---|
| equests | >=2.32.0 | HTTP client for web scanning / API calls |
| cvss | >=3.2 | CVSS vulnerability scoring |
| caido-sdk-client | >=0.2.0 | Caido proxy integration for traffic interception |
| LiteLLM | transitive | Multi-provider LLM routing — prefixes like nthropic/, deepseek/ transparently route through litellm |

## LLM Architecture

The StrixProvider (strix/config/models.py) extends the SDK's MultiProvider:
- Bare model names (no /) route to OpenAI by default
- provider/model prefixes route through LiteLLM automatically
- ollama/ prefix maps to ollama_chat/ via litellm
- Configurable via STRIX_LLM, LLM_API_KEY, LLM_API_BASE env vars
- Model retry: 5 retries, exponential backoff (2s → 90s), covers rate limits + network errors

## Dev Tooling

| Tool | Config | Purpose |
|---|---|---|
| **ruff** | pyproject.toml | Linter + formatter (line-length 100, comprehensive rule set) |
| **mypy** | pyproject.toml | Strict type checking |
| **pyright** | pyproject.toml | Alternative strict type checker |
| **bandit** | pyproject.toml | Security linting (medium severity) |
| **pre-commit** | local hooks | Git pre-commit automation |

## Key Configuration Files

| File | Purpose |
|---|---|
| pyproject.toml | Project metadata, all tool config, dependencies |
| uv.lock | Locked dependency resolution |
| Makefile | Development commands (format, lint, type-check, security) |
| .github/workflows/build-release.yml | CI: build + release workflow |
| strix.spec | PyInstaller spec for standalone binary builds |
| Dockerfile (in containers/) | Sandbox container image definitions |
