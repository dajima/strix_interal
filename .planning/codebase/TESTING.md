# Testing

**Last mapped:** 2026-06-16
**Commit:** 11e5d1c

## Status

**No automated tests exist in this codebase.**

- No 	est_*.py files found anywhere
- No 	ests/ directory
- No test dependencies in pyproject.toml (no pytest, no coverage)
- No test target in Makefile

## Static Analysis (Test Substitute)

Strix relies heavily on **static analysis** as a substitute for unit tests:

| Tool | Purpose | Strictness |
|---|---|---|
| **mypy** | Type checking | strict = true |
| **pyright** | Alternative type checker | 	ypeCheckingMode = "strict" |
| **ruff** | Linting (50+ rule families) | Comprehensive |
| **bandit** | Security linting | Medium severity |

The Makefile dev cycle is: ormat → lint → type-check → security — no test step.

## Runtime Validation

Since there are no unit tests, correctness is validated through:
1. **Type checker coverage** — both mypy and pyright in strict mode catch many bugs
2. **Linter enforcement** — ruff catches common Python errors
3. **LLM warm-up** (warm_up_llm()) — validates LLM connectivity before scan starts
4. **Docker readiness checks** — validates Docker daemon connection + image presence
5. **Runtime assertions** — pydantic validates all config at startup

## Integration Testing

No integration test infrastructure. Verification relies on:
- Running Strix against real targets (manual QA)
- The inish_scan lifecycle tool reporting scan completion
- Vulnerability report output validation (manual review)

## CI

Only one GitHub Actions workflow: uild-release.yml (build + release).

**Missing:**
- PR check/test workflow
- Automated build verification
- Regression test suite
- Coverage reporting

## Test Framework Recommendations (if added)

The project would benefit from:
- **pytest** — standard Python test framework
- **pytest-asyncio** — async test support (project is async-heavy)
- **pytest-mock** — mocking (Docker, LLM APIs)
- **coverage** — code coverage reporting
- Test targets for Makefile (e.g., make test, make test-cov)
- CI test workflow (.github/workflows/test.yml)

## Key Areas Most in Need of Tests

1. **strix/agents/factory.py** — tool wrapping, agent construction, chat-completions adaptation
2. **strix/config/models.py** — StrixProvider._resolve_prefixed_model(), LiteLLM configuration
3. **strix/runtime/backends.py** — backend registry, fallback, error paths
4. **strix/core/execution.py** — agent loop, child spawning, resume logic
5. **strix/interface/utils.py** — target type inference, git cloning, diff scope
6. **strix/report/state.py** — vulnerability collection, cleanup, telemetry hooks
