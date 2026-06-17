# Coding Conventions

**Last mapped:** 2026-06-16
**Commit:** 11e5d1c

## Python Version & Features

- **Target:** Python 3.12+
- **rom __future__ import annotations** used throughout for PEP 604 union syntax
- **Type hints:** Full type annotations on all public interfaces
- **No 	yping.Optional:** Uses str | None style (PEP 604)

## Code Style

- **Formatter:** ruff (was black previously, pyproject.toml still has [tool.black])
- **Linter:** ruff with comprehensive rule set (50+ rule families)
- **Line length:** 100 chars (not default 88)
- **Quote style:** Double quotes (")
- **Import sorting:** isort via ruff, known-first-party = ["strix"]
- **Trailing commas:** Enabled (multi-line collections use trailing comma)

## Naming

| Convention | Example |
|---|---|
| Modules | snake_case.py |
| Classes | PascalCase (e.g., StrixProvider, ReportState, LlmSettings) |
| Functions | snake_case (e.g., uild_strix_agent(), configure_sdk_model_defaults()) |
| Constants | UPPER_SNAKE_CASE (e.g., HOST_GATEWAY_HOSTNAME, DEFAULT_MAX_TURNS) |
| Private helpers | _leading_underscore (e.g., _custom_tool_as_function_tool()) |
| Test files | N/A — no test files exist |
| Banned | Hungarian notation, type prefixes, I-prefix interfaces |

## Error Handling

- **Custom tool errors:** Wrapped as model-visible results (tools return error strings instead of raising)
- **Validation:** pydantic ValidationError caught and formatted for tool results
- **CLI usage errors:** sys.exit(1) with Rich-panel error messages
- **Broad except clauses:** Explicit # noqa: BLE001 annotations on intentional bare exceptions
- **Lazy import errors:** Docker import failures caught to allow non-Docker backend deployments

## Common Ruff Ignore Patterns

| Rule | Reason |
|---|---|
| BLE001 | Bare except — intentional in CLI/tool error handling |
| PLC0415 | Top-level import — lazy imports in function bodies for dependency isolation |
| TC002/TC003 | Type-check imports — SDK requires eager imports for runtime type resolution |
| PLR0912/PLR0915 | Too many branches/statements — CLI/TUI orchestration functions |
| SLF001 | Private member access — SDK subclassing requires it |
| S101 | assert usage — allowed |
| EM101/EM102 | String/f-string exceptions — minor |
| FBT001/FBT002 | Boolean args — tolerated |

## Async Patterns

- **syncio throughout:** CLI and TUI both use syncio.run()
- **Windows:** syncio.WindowsSelectorEventLoopPolicy() set for Windows compatibility
- **Container lifecycle:** sync with always available but Strix manages lifetimes explicitly via client.delete()
- **Concurrent execution:** Agent tree, syncio.gather for parallel tool execution

## Documentation

- **Docstrings:** Google-style, present on most public functions
- **Type annotations serve as documentation** (no redundant type-hint-in-docstring)
- **Module docstrings:** Single-line summary, present on most modules

## Dependencies

- **Package manager:** uv (not pip or poetry)
- **Build system:** hatchling
- **Lock file:** uv.lock committed to repo

## Git

- **Branch:** main
- **Pre-commit hooks:** ruff, mypy, pyright, bandit (via .pre-commit-config.yaml)
- **No branch protection visible** — only build-release CI workflow, no PR check workflow
