# Stack Research: CI/CD Build Pipeline & XBEN Benchmarking Additions

**Domain:** CI/CD build pipeline and automated security benchmark evaluation
**Researched:** 2026-06-17
**Confidence:** HIGH

## Recommended Stack

### Core Technologies — Build & Release

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **GitHub CLI (gh)** | latest (v2.x) | Release creation and asset upload from scripts and CI | Official GitHub tool, cross-platform (Windows/macOS/Linux via Git Bash on Windows), supports `gh release create` with inline asset upload and `--generate-notes`. Already partially used via `softprops/action-gh-release@v2` in existing workflow. Direct `gh` CLI allows one-click local release scripts outside CI. |
| **Docker Compose v2** | v2.40+ (bundled with Docker Desktop / `docker-compose-plugin`) | Multi-container orchestration for deployment | Replaces deprecated `docker-compose` (v1, EOL July 2023). Uses `docker compose` (space, not hyphen). Compose Specification v5.0.0 ("Mont Blanc") is the current spec. Built-in to Docker Desktop on Windows/Linux. Supports `include:` for modular composition, health checks with `depends_on condition: service_healthy`, and `deploy.resources` for limits. |
| **PyInstaller** | 6.x (already in use) | Single-file binary packaging | Already configured in `strix.spec`. No change needed — used by pipeline to produce Windows `.exe` and Linux binary artifacts. |
| **GitHub Actions** | N/A (SaaS) | CI/CD orchestration | Already has `build-release.yml`. This milestone adds new workflow files under `.github/workflows/` for PR checks and XBEN evaluation triggering. |

### Core Technologies — XBEN Evaluation Pipeline

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python 3.12 stdlib `concurrent.futures`** | stdlib | Parallel challenge execution (ThreadPoolExecutor) | XBEN challenges are I/O-bound (waiting for Docker Compose builds and strix scan completion). ThreadPoolExecutor is correct here — ProcessPoolExecutor would add unnecessary process-spawn overhead for subprocess management tasks. `max_workers=4` recommended to avoid Docker daemon contention. Use `with` statement for automatic `shutdown()`. |
| **Python 3.12 stdlib `asyncio`** | stdlib | Async execution within individual strix runs | Already used throughout Strix. The existing `run_infer.py` uses `asyncio.run()`. The evaluation runner can keep this pattern — each worker thread runs its own asyncio event loop for the scan it manages. |
| **ruamel.yaml** | >=0.19.1 | Round-trip-safe docker-compose.yml rewriting | Preserves comments, key ordering, blank lines, and scalar styles when programmatically modifying docker-compose files. PyYAML (already in use, v6.0) strips all comments and reorders keys — it corrupts docker-compose files on rewrite. `ruamel.yaml` is the standard for any YAML file that humans also edit. Install: `pip install ruamel.yaml`. |
| **psutil** | >=7.2.2 | Resource monitoring for long-running evaluation jobs | Cross-platform CPU/memory/disk monitoring. Used to track resource consumption during benchmark runs (container memory, disk usage per run). Lighter-weight than full Prometheus stack. Docker-aware — use `psutil.Process(pid).memory_info()` for per-process tracking. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Jinja2** | >=3.1 (already transitive via strix agents) | Markdown report templating | Generate evaluation summary reports (pass/fail rates by difficulty, tag categories, execution timeline). Already a transitive dependency — no new install needed, just import and use template files. |
| **json-schema-for-humans** | >=1.5.1 | JSON schema documentation generation from result schema | If the XBEN evaluation results need a formal JSON schema for downstream consumers, this generates readable markdown from it. Optional — only needed if results are consumed by external systems that need schema docs. |
| **shutil** | stdlib | Directory/file operations | Copying strix outputs, cleaning up temporary directories. Already used in existing `run_infer_cli.py` — no new dependency. |
| **subprocess** | stdlib | Shell command execution | Running `docker compose`, `strix` binary, `gh` CLI. Already used — no new dependency. |
| **datetime (timezone-aware)** | stdlib | Timestamp generation for run logs | Already used with `datetime.now(timezone.utc)` pattern — correct. No new dependency. |
| **pathlib** | stdlib | Cross-platform path handling | Already used. Use `/` operator for path joining — works on both Windows and Linux. |
| **json** | stdlib | Result serialization | Already used for `result.json`. No new dependency. |

### Development & Testing Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| **pytest** | >=8.3 | Test framework for pipeline validation | Not a new dependency — already in `excludes` in `strix.spec`. Install as dev dependency. This milestone adds the FIRST automated tests to the project. |
| **pytest-asyncio** | >=1.4.0 | Async test support (strix scan execution tests) | Required for testing async `run_strix()` paths. v1.4.0 (May 2026) is latest stable. Use `pytestmark = pytest.mark.asyncio` on test modules. |
| **pytest-mock** | >=3.15.1 | Mocking `subprocess.run`, `docker` SDK, file I/O | Mock docker compose calls and subprocess invocations in pipeline tests. Use `mocker.patch("subprocess.run")` returning `CompletedProcess`. |
| **pytest-cov** | >=7.1.0 | Code coverage measurement | Track test coverage for pipeline code. v7.1.0 (March 2026) is latest. Configure in `pyproject.toml` with `--cov=strix --cov-report=term-missing`. |
| **pytest-timeout** | >=2.3 | Test timeout enforcement | Prevent hanging tests in CI (especially for any integration tests). Set `--timeout=300` for CI runs. |

## Installation

```bash
# Core additions for build/release pipeline
pip install ruamel.yaml>=0.19.1
pip install psutil>=7.2.2

# Dev dependencies — testing framework (FIRST automated tests in project)
pip install pytest>=8.3
pip install pytest-asyncio>=1.4.0
pip install pytest-mock>=3.15.1
pip install pytest-cov>=7.1.0
pip install pytest-timeout>=2.3

# Optional — result schema documentation
pip install json-schema-for-humans>=1.5.1
```

**Note on package manager:** Continue using `uv` for dependency management. Add dev dependencies to `pyproject.toml` under `[tool.uv]` dev-dependencies section, or as a separate `[project.optional-dependencies]` group named `dev` or `test`.

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **ruamel.yaml** | PyYAML (already in project, v6.0) | PyYAML strips comments, reorders keys, and uses YAML 1.1 which misinterprets `on`/`off`/`yes`/`no` as booleans. Any docker-compose rewrite via PyYAML corrupts the file for human editing. ruamel.yaml is the standard for round-trip YAML editing. |
| **ThreadPoolExecutor** | ProcessPoolExecutor | XBEN evaluation is I/O-bound (Docker builds, subprocess waits). ProcessPoolExecutor adds process-spawn overhead and IPC complexity for tasks that just wait on external processes. ThreadPoolExecutor is simpler and correct for this workload. |
| **pytest-asyncio** | Writing manual async test harnesses | pytest-asyncio integrates with pytest fixtures and provides `event_loop` fixture management, proper cleanup, and CI-friendly output. Don't reinvent this. |
| **Jinja2 (already transitive)** | f-strings for report generation | Jinja2 separates template structure from data — critical for report templates that evolve independently. f-strings in Python code would require code changes for any report format change. |
| **psutil** | Running `top`/`ps` via subprocess | Parsing CLI output is fragile across platforms (Linux vs Windows). psutil is a single cross-platform API — no parsing, no platform branches. |
| **softprops/action-gh-release@v3** | Using `gh release create` in CI directly | The action handles draft→upload→publish lifecycle, asset globbing, and error handling better than raw `gh` commands in CI. Use the action for CI, direct `gh` CLI for local one-click scripts. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **docker-compose (v1, with hyphen)** | Deprecated since July 2023. Not available on modern Docker Desktop. | `docker compose` (v2, space) |
| **docker-compose Python SDK** | The `docker-compose` Python package was the v1 implementation. It is unmaintained and incompatible with Compose v2. | Call `docker compose` via subprocess, or use `docker` Python SDK (already in stack) for individual container operations. |
| **asyncio subprocess for docker compose** | `asyncio.create_subprocess_exec` for `docker compose up` adds complexity without benefit — compose commands are blocking by nature (waiting for containers). | Use `subprocess.run` in thread pool workers. Let ThreadPoolExecutor handle parallelism. |
| **Celery / Redis / RabbitMQ** | Over-engineered for a pipeline that runs in CI or as a single CLI command. XBEN evaluation is a batch job, not a distributed task system. | ThreadPoolExecutor within a single Python process. |
| **Prometheus / Grafana** | Infrastructure-heavy for collecting metrics from 104 benchmark runs. Add ops overhead. | psutil for process-level metrics + JSON result files + Jinja2 markdown reports. |
| **Docker Python SDK for benchmark orchestration** | The `docker` Python SDK (already installed) is great for single-container operations but does not handle Docker Compose files. | subprocess + `docker compose` commands for compose files. Use `docker` SDK only for image pulling/inspection. |
| **Click / Typer** | The existing XBEN CLI runner already uses argparse. Adding a new CLI framework creates inconsistency. | Extend the existing argparse-based CLI in the XBEN runner. |
| **pre-commit (for pipeline scripts)** | Already configured. No new hooks needed for shell scripts. | Keep existing pre-commit setup as-is. |

## Stack Patterns by Variant

**If running XBEN evaluation locally (CLI trigger):**
- Use `concurrent.futures.ThreadPoolExecutor(max_workers=4)` — limits Docker daemon pressure
- Wrap entire run in `try/finally` to ensure `docker compose down` for all benchmarks
- Use `ruamel.yaml` for compose rewriting, `argparse` for CLI, `psutil` for resource logging

**If running XBEN evaluation in CI (GitHub Actions trigger):**
- Same ThreadPoolExecutor — GitHub Actions runners have 2-4 cores
- Set `max_workers` via environment variable (`XBEN_WORKERS`) with default `4`
- Upload run artifacts via `actions/upload-artifact@v4` with `retention-days: 7`
- Use `pytest` with `-x --timeout=300` for fast failure in CI
- Set `STRIX_TIMEOUT` lower in CI (1800s vs 21600s) to avoid runner timeout

**If building and releasing (one-click script):**
- Use `gh release create` with `--draft` for local scripts (review before publish)
- Use `softprops/action-gh-release@v3` for CI automation
- Build matrix: Linux (PyInstaller bin) + Windows (PyInstaller exe) + Docker sandbox image
- Platform-specific packaging: `.tar.gz` for Linux, `.zip` for Windows

**If Docker Desktop containerd issue encountered:**
- The known containerd compatibility issue means `DOCKER_BUILDKIT=0` is set in the existing runner
- Keep this workaround but document it in the docker-compose deployment instructions
- Monitor for Docker Desktop updates that fix the issue — remove workaround when possible

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| ruamel.yaml >=0.19.1 | Python >=3.9 | Works on 3.12+. Pure Python, no compiled extensions. |
| pytest-asyncio >=1.4.0 | pytest >=8.0, Python >=3.9 | v1.x line is the current stable track. v0.x (0.26.0) is legacy. |
| pytest-mock >=3.15.1 | pytest >=6.2.5, Python >=3.9 | Standard `mocker` fixture. |
| pytest-cov >=7.1.0 | pytest >=4.6, coverage >=7.5 | Uses `coverage.py` under the hood. |
| psutil >=7.2.2 | Python >=3.6 | Cross-platform. Some features (sensors, individual process I/O) require platform-specific permissions. |
| Jinja2 >=3.1 | Python >=3.7 | Already transitive via `openai-agents[litellm]`. No version conflict risk. |

## Existing Stack Integration Points

### Already present — do NOT re-add:
| Tool | Location | Notes |
|------|----------|-------|
| **PyInstaller** | `strix.spec`, `Dockerfile.build` | Binary packaging — pipeline uses this, no change |
| **Docker Python SDK** | `pyproject.toml` (`docker>=7.1.0`) | Container lifecycle — not for compose orchestration |
| **LiteLLM** | Transitive via `openai-agents[litellm]` | LLM routing — XBEN evaluation uses Strix's existing config |
| **openai-agents SDK** | Pinned to `0.14.6` | Agent framework — evaluation runner invokes strix binary or SDK directly |
| **GitHub Actions** | `.github/workflows/build-release.yml` | Existing CI — this milestone adds new workflow files |
| **PyYAML** | `pyproject.toml` (`pyyaml>=6.0`) | Kept for reading YAML (loading is fine). Use `ruamel.yaml` ONLY when writing back docker-compose files. |
| **argparse** | stdlib, used in `run_infer_cli.py` | CLI parsing — extend, don't replace |
| **Rich** | `pyproject.toml` | Terminal output formatting — already used in `run_infer.py` |
| **Textual** | `pyproject.toml` | TUI — not needed for evaluation pipeline |

### New integration points:

```
CI Matrix Build (New Workflow) → PyInstaller → gh release create
                                   Docker Build → ghcr.io + GitHub Release
Docker Compose (New compose.yaml) → strix binary + sandbox image
XBEN Runner (Enhanced run_infer_cli.py) → ThreadPoolExecutor → strix binary
                                           ruamel.yaml → compose rewrite
                                           psutil → resource metrics
                                           Jinja2 → summary report
pytest Suite (New) → pytest-asyncio → strix core tests
                     pytest-mock → subprocess/docker mocks
```

## Sources

- GitHub CLI official docs — `gh release create` and `gh release upload` commands, cross-platform usage patterns. Confidence: HIGH.
- Docker Compose Specification v5.0.0 ("Mont Blanc") — `compose.yaml` structure, `include`, `depends_on condition: service_healthy`. Confidence: HIGH.
- ruamel.yaml PyPI page and documentation — round-trip YAML preservation, Python 3.12 compatibility. Confidence: HIGH.
- pytest-asyncio v1.4.0 PyPI page — latest stable with Python 3.12 support, `event_loop` fixture management. Confidence: HIGH.
- pytest-mock v3.15.1 PyPI page — `mocker` fixture, `subprocess.run` mocking patterns. Confidence: HIGH.
- pytest-cov v7.1.0 PyPI page — coverage measurement integration. Confidence: HIGH.
- psutil v7.2.2 PyPI page and documentation — cross-platform process/system monitoring, Docker container considerations. Confidence: HIGH.
- Python `concurrent.futures` official docs — ThreadPoolExecutor for I/O-bound workloads, `max_workers` tuning. Confidence: HIGH.
- softprops/action-gh-release v3 GitHub Marketplace — draft→upload→publish workflow pattern. Confidence: HIGH.
- json-schema-for-humans v1.5.1 PyPI page — JSON schema to markdown documentation generation. Confidence: HIGH.
- Existing codebase analysis: `Dockerfile.build`, `containers/Dockerfile`, `strix.spec`, `.github/workflows/build-release.yml`, `xben-benchmarks/XBEN/run_infer_cli.py`, `xben-benchmarks/XBEN/run_infer.py`. Confidence: HIGH.

---
*Stack research for: CI/CD build pipeline and XBEN automated benchmarking stack additions*
*Researched: 2026-06-17*
