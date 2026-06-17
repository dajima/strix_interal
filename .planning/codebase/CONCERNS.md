# Concerns & Technical Debt

**Last mapped:** 2026-06-16
**Commit:** 11e5d1c

## Critical: No Automated Tests

**Severity: High**

The codebase has zero unit tests, zero integration tests, and zero CI test workflow. All quality assurance relies on static analysis (mypy, ruff, pyright, bandit) plus manual QA. This is the most significant gap.

**Why it matters now:**
- Any refactoring or feature addition carries regression risk
- The agent factory (uild_strix_agent()) has complex tool-wrapping logic with no test coverage
- LLM provider routing (StrixProvider) has no test coverage — a regression could silently break model connectivity for all non-OpenAI providers
- The sandbox lifecycle (session create/delete) has no test coverage

## SDK Pinning & Fragile Subclass

**Severity: Medium**

strix/runtime/docker_client.py contains a verbatim copy of the upstream SDK's _create_container method body (pinned to openai-agents==0.14.6). The file explicitly warns:

> "Pinned to openai-agents==0.14.6. Bumping the SDK requires re-merging the parent body. Track upstream for an injection hook."

Any SDK version bump requires a manual merge-and-review of ~50 lines of upstream code to ensure Strix's customizations (NET_ADMIN/NET_RAW caps, host-gateway, entrypoint preservation) don't regress.

## Missing CI Quality Gates

**Severity: Medium**

Only one GitHub Actions workflow exists (uild-release.yml). Missing:
- **No PR check workflow** — no automated build, lint, or type check on PRs
- **No automated test workflow** (since there are no tests)
- **No dependency vulnerability scanning**
- **No binary build verification** — the PyInstaller build only runs on release

## Docker Dependency Coupling

**Severity: Low-Medium**

- check_docker_installed() in main.py hard-fails if Docker isn't installed (sys.exit(1))
- The docker Python package is a non-optional dependency (not behind an extra)
- Only one backend (docker) is registered; egister_backend() API exists but no alternatives are shipped

If Strix needs to run without Docker (e.g., in restricted CI environments), the current architecture requires non-trivial refactoring.

## Global Mutable State

**Severity: Low**

strix/report/state.py uses a module-level global _global_report_state for the singleton ReportState. While intentional (one scan runs at a time), this would cause issues if:
- Multiple scans run concurrently in the same process
- Tests are added that need isolated report state per test

## Broad Exception Silencing

**Severity: Low**

Multiple locations use bare except Exception: pass with # noqa: BLE001 — intentional but worth auditing:
- _mirror_api_key_to_provider_env() — swallows litellm.validate_environment errors
- StrixDockerSandboxClient.delete() — silently ignores docker.errors.NotFound and APIError
- Various CLI/TUI locations — catch-all for terminal rendering resilience

## Large Functions

**Severity: Low (maintainability)**

Several functions exceed typical size guidelines:
- strix/interface/main.py:main() — orchestrates full scan lifecycle (~200 lines)
- strix/agents/factory.py:build_strix_agent() — complex tool assembly
- strix/interface/tui/app.py — Textual App with extensive renderer logic

These are acknowledged by ruff overrides (PLR0912, PLR0915) in per-file-ignores.

## Unused/Empty Tool Directories

**Severity: Trivial**

Several tool directories exist with no Python files:
- strix/tools/agent_browser/ — empty
- strix/tools/apply_patch/ — empty
- strix/tools/shell/ — empty (SDK Shell capability used instead)
- strix/tools/view_image/ — empty

These may be placeholders for future tool implementations or vestigial. They add no value but create confusion.

## Security: No Secret Scanning in CI

**Severity: Low**

No GitHub secret scanning, no git-secrets, no .gitleaks.toml. API keys could accidentally be committed — relies solely on developer discipline and .gitignore.

## Dependency Management

**Severity: Low (informational)**

- uv is the only supported package manager — good but less universal than pip
- Some ruff rules are disabled (S101, S301, S104) — intentional but documented only in config, not rationale
- pyproject.toml still has legacy [tool.black] and [tool.isort] sections — these are vestigial (ruff handles both)
