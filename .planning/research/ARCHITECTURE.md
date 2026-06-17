# Architecture Research

**Domain:** CI/CD Build/Release Pipeline + XBEN Automated Benchmarking Integration
**Researched:** 2026-06-17
**Confidence:** HIGH

## System Overview

The existing Strix architecture is a modular monolith with clear layer boundaries. The new build/release pipeline and XBEN evaluation system extend this architecture through two new subsystems placed at the project root level (external to the `strix/` Python package). These subsystems integrate with the existing codebase at specific, well-defined integration points.

```
                    PROJECT ROOT (strix_interal/)
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  ┌──────────────────┐    ┌──────────────────────┐                     │
│  │  scripts/build/   │    │  xben-benchmarks/     │                    │
│  │  (build pipeline) │    │  XBEN/                │                    │
│  │                   │    │  (evaluation runner)  │                    │
│  └───────┬───────────┘    └──────────┬────────────┘                   │
│          │                           │                                │
│          │ reads version from        │ invokes strix via              │
│          │ pyproject.toml            │ subprocess (CLI mode)          │
│          │                           │                                │
│  ┌───────▼───────────────────────────▼────────────────────┐           │
│  │                    strix/  (unchanged)                  │           │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │           │
│  │  │interface/│  │  core/   │  │ runtime/ │             │           │
│  │  │ main.py  │  │ runner.py│  │ docker_  │             │           │
│  │  │          │  │          │  │ client.py│             │           │
│  │  └──────────┘  └──────────┘  └──────────┘             │           │
│  └───────────────────────────────────────────────────────┘           │
│                                                                       │
│  ┌───────────────────────────────────────────────────────┐           │
│  │                 containers/ (extended)                 │           │
│  │  Dockerfile  docker-entrypoint.sh  docker-compose.yml │           │
│  └───────────────────────────────────────────────────────┘           │
│                                                                       │
│  ┌───────────────────────────────────────────────────────┐           │
│  │              .github/workflows/ (extended)             │           │
│  │  build-release.yml (extended)  xben-eval.yml (NEW)    │           │
│  └───────────────────────────────────────────────────────┘           │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Build/Release Pipeline (`scripts/build/`)

| Component | Responsibility | Existing Connection |
|-----------|----------------|---------------------|
| `scripts/build/build-binary.sh` | Compile strix binary via PyInstaller for current platform | Reads `pyproject.toml` for version; uses `strix.spec`; replaces inline build from `scripts/build.sh` |
| `scripts/build/build-sandbox.sh` | Build the Docker sandbox image from `containers/Dockerfile` | Tags image with version from `pyproject.toml`; replaces `scripts/docker.sh` |
| `scripts/build/release.sh` | Orchestrate both builds + tag + push to GitHub Releases and GHCR | Coordinates all three delivery artifacts: binary, sandbox image, git tag |
| `scripts/build/version.sh` | Extract and validate version from `pyproject.toml` | Single source of truth -- all other scripts source this |
| `scripts/build/docker-compose.yml` | Docker Compose deployment definition for end users | References sandbox image tag from build; NEW file |

### XBEN Evaluation Runner (`xben-benchmarks/XBEN/`)

| Component | Responsibility | Existing Connection |
|-----------|----------------|---------------------|
| `xben-benchmarks/XBEN/runner.py` | Core benchmark execution engine (refactored from `run_infer_cli.py`) | Calls strix CLI via `subprocess.run()`; manages Docker Compose lifecycle per challenge |
| `xben-benchmarks/XBEN/aggregator.py` | Aggregate per-challenge results into summary report | Reads `result.json` files from runs directory; outputs summary JSON + markdown |
| `xben-benchmarks/XBEN/scheduler.py` | Filter/sort/limit challenge selection by difficulty, tags, count | Reads `benchmark.json` from each challenge directory |
| `xben-benchmarks/XBEN/cli.py` | CLI argument parsing and entry point | Exposes `--benchmarks`, `--limit`, `--level`, `--tags`, `--output` flags |

## Recommended Project Structure

### New Files (to be created)

```
strix_interal/
├── scripts/
│   └── build/                          # NEW: build pipeline directory
│       ├── version.sh                  # NEW: single version source
│       ├── build-binary.sh             # NEW: PyInstaller binary build
│       ├── build-sandbox.sh            # NEW: Docker sandbox image build
│       ├── release.sh                  # NEW: full release orchestrator
│       └── docker-compose.yml          # NEW: deployment compose file
│
├── xben-benchmarks/XBEN/               # EXISTING: restructured
│   ├── pyproject.toml                  # MODIFIED: update deps, add console_scripts
│   ├── runner.py                       # NEW: core execution engine (extracted from run_infer_cli.py)
│   ├── aggregator.py                   # NEW: result aggregation and summary report
│   ├── scheduler.py                    # NEW: challenge selection/filtering
│   ├── cli.py                          # NEW: CLI entry point
│   └── run_infer.py                    # EXISTING: kept as SDK-based variant (optional)
│
├── .github/workflows/
│   ├── build-release.yml               # MODIFIED: extend with sandbox build/push
│   └── xben-eval.yml                   # NEW: XBEN CI evaluation workflow
│
├── containers/
│   ├── Dockerfile                      # EXISTING: unchanged
│   ├── docker-entrypoint.sh            # EXISTING: unchanged
│   └── docker-compose.yml              # MOVED from scripts/build/ for CI use
│
├── Makefile                            # MODIFIED: add build, release, xben targets
├── run-xben-setup.bat                  # EXISTING: Windows setup helper (unchanged)
└── Dockerfile.build                    # EXISTING: CI-only build container (unchanged)
```

### Files NOT Created

- **No `.planning/build/` or `.planning/xben/`** -- these are project infrastructure, not planning artifacts
- **No files inside `strix/` package** -- build and evaluation are external to the Python package
- **No `ci/` directory** -- existing `.github/workflows/` is the established CI location

### Structure Rationale

- **`scripts/build/` separate from `scripts/`:** The existing `scripts/` contains `install.sh` (end-user install script distributed via GitHub Releases) and `build.sh`/`docker.sh` (current build helpers). The new `scripts/build/` groups all build/release pipeline scripts together, keeping them distinct from the end-user-facing install script. The old `build.sh` and `docker.sh` are superseded and can be removed or kept as backward-compatible wrappers.
- **`xben-benchmarks/XBEN/` restructured into modules:** The current monolithic `run_infer_cli.py` (210 lines) mixes CLI parsing, Docker lifecycle, subprocess execution, flag checking, result persistence, and summary reporting. Splitting into `runner.py`, `aggregator.py`, `scheduler.py`, and `cli.py` mirrors the modular structure of the main `strix/` package.
- **`docker-compose.yml` moved to `containers/`:** The deployment compose file lives with the Dockerfile it references, making the relationship explicit. CI can still reference it from this location.
- **Build pipeline external to `strix/` package:** Build infrastructure is not part of the runtime. PyInstaller already reads `strix.spec` from the project root. Keeping build scripts external avoids packaging them in the wheel and maintains clean separation of concerns.

## Architectural Patterns

### Pattern 1: Single Source of Truth for Version

**What:** All build artifacts (binary filename, Docker image tag, git tag) derive version from `pyproject.toml`. A single `version.sh` script extracts it, and all other build scripts source it.

**When to use:** Any project with multiple delivery artifacts that must carry the same version.

**Trade-offs:** Simple and prevents drift, but means `pyproject.toml` must be bumped before release. A CI validation step ensures the git tag matches.

**Implementation:**
```bash
# scripts/build/version.sh
VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
VERSION_TAG="v${VERSION}"
```

**Integration with existing code:** This replaces the inline version extraction in `scripts/build.sh` (line 45), `scripts/install.sh` (line 78-84), and `.github/workflows/build-release.yml` (line 41) with a single sourced script. All three current locations duplicate the same `grep | sed` pattern.

### Pattern 2: Subprocess Invocation for Evaluation

**What:** The XBEN runner invokes strix as a subprocess (`strix --target ... --non-interactive --scan-mode deep`) rather than importing it as a Python library. This mirrors how `run_infer_cli.py` already works.

**When to use:** When the tool under test is a CLI that manages its own process lifecycle (Docker sandbox creation, agent loops, report writing). Subprocess invocation provides process isolation -- a strix crash does not take down the evaluation runner.

**Trade-offs:** Slower startup (subprocess overhead) and less rich programmatic access to internal state. But the strix `run_strix_scan()` API (`strix/core/runner.py`) is available as an escape hatch for SDK-based evaluation (as done in `run_infer.py`).

**Integration with existing code:** The `run_infer_cli.py` already uses `subprocess.run()` to invoke strix. The new `runner.py` refines this pattern with better error handling, timeout management, and run directory discovery (using the "before/after" directory comparison technique already present at lines 74-87 of `run_infer_cli.py`).

### Pattern 3: Docker Compose Ephemeral Environments

**What:** Each benchmark challenge runs in a completely isolated Docker Compose stack: build images, start services with health checks, run strix, tear down with `docker compose down -v`. No state persists between challenges.

**When to use:** When benchmarks involve stateful services (databases, web apps) and runs must be fully reproducible without cross-contamination.

**Trade-offs:** Slower per-challenge execution (build + start overhead). Mitigated by Docker layer caching and the existing `docker compose build` step in `run_infer_cli.py`.

**Key details:**
- `docker compose -p <project-name> down --remove-orphans -v` in a `finally` block ensures cleanup even on failure
- Dynamic port allocation via `find_free_port()` prevents port conflicts between parallel CI jobs or local services
- Rewritten compose files (`.docker-compose.xben.yml`) are temporary and deleted after teardown
- Project names derived from benchmark IDs (lowercased) to allow concurrent execution of different challenges

### Pattern 4: GitHub Actions Matrix for Challenge Batching

**What:** The XBEN CI workflow uses a dynamically generated matrix to batch 104 challenges across parallel runners. A setup job computes the batch list, and each matrix job runs a subset.

**When to use:** When the total number of benchmark items exceeds reasonable serial execution time (104 challenges × variable duration = potentially days).

**Implementation:**
```yaml
jobs:
  setup-matrix:
    outputs:
      batches: ${{ steps.batch.outputs.matrix }}
    steps:
      - id: batch
        run: |
          # Split 104 challenges into batches of ~8
          echo "matrix=$(python scripts/build/make-batches.py --batch-size 8)" >> $GITHUB_OUTPUT

  evaluate:
    needs: setup-matrix
    strategy:
      fail-fast: false
      max-parallel: 6
      matrix:
        batch: ${{ fromJson(needs.setup-matrix.outputs.batches) }}
    steps:
      - run: xben run --benchmarks ${{ matrix.batch }}
```

**Trade-offs:** Complexity of batching logic and artifact aggregation. But `max-parallel: 6` with `fail-fast: false` provides a good balance of speed vs. GitHub Actions runner usage for a free-tier or team plan.

## Data Flow

### Build/Release Pipeline

```
Developer runs: scripts/build/release.sh
    │
    ├── 1. source scripts/build/version.sh
    │       └── Reads pyproject.toml → VERSION="1.0.5", VERSION_TAG="v1.0.5"
    │
    ├── 2. scripts/build/build-binary.sh
    │       └── uv run pyinstaller strix.spec --noconfirm
    │       └── Output: dist/strix (or dist/strix.exe)
    │       └── Packages: dist/release/strix-1.0.5-linux-x86_64.tar.gz
    │
    ├── 3. scripts/build/build-sandbox.sh
    │       └── docker build -f containers/Dockerfile -t strix-sandbox:1.0.5 .
    │       └── docker tag strix-sandbox:1.0.5 ghcr.io/usestrix/strix-sandbox:1.0.5
    │       └── docker push ghcr.io/usestrix/strix-sandbox:1.0.5
    │
    ├── 4. git tag v1.0.5 && git push origin v1.0.5
    │       └── Triggers .github/workflows/build-release.yml (existing)
    │
    └── 5. Validation check
            └── git tag == pyproject.toml version (with v prefix stripped)
            └── Docker image tag == pyproject.toml version
```

### XBEN Evaluation (Local CLI)

```
User runs: xben run --level 2 --limit 10
    │
    ├── 1. scheduler.py: filter_and_select()
    │       └── Reads validation-benchmarks/benchmarks/*/benchmark.json
    │       └── Filters by level=2, sorts, limits to 10
    │       └── Returns: [(Path, metadata), ...]
    │
    ├── 2. For each challenge (serial loop):
    │       │
    │       ├── 2a. runner.py: run_challenge()
    │       │       ├── read_flag_from_env(bench_path) → expected_flag
    │       │       ├── rewrite_compose(compose_path) → (rewritten_compose, host_port)
    │       │       │       └── Dynamic port mapping, platform=linux/amd64
    │       │       ├── docker_compose(bench_path, "build")
    │       │       ├── docker_compose(bench_path, "up")
    │       │       │       └── With healthcheck wait
    │       │       ├── wait_for_target(url)  # up to 30s
    │       │       │
    │       │       ├── run_strix_subprocess(url, instruction)
    │       │       │       └── subprocess.run(["strix", "--target", url,
    │       │       │                            "--non-interactive", "--scan-mode", "deep"])
    │       │       │       └── Before/after directory diff to find strix_runs/<name>/
    │       │       │       └── Returns: {ok, duration, output_dir, exit_code}
    │       │       │
    │       │       ├── check_flag(output_dir, expected_flag) → bool
    │       │       └── save: runs/<timestamp>/<benchmark_id>/result.json
    │       │               └── Also copies strix output to runs/.../outputs/
    │       │
    │       └── 2b. runner.py: cleanup (FINALLY block)
    │               ├── docker compose down --remove-orphans -v
    │               └── Remove temporary .docker-compose.xben.yml
    │
    └── 3. aggregator.py: aggregate_results()
            ├── Reads all runs/<timestamp>/*/result.json
            ├── Computes: solved/unsolved/errored counts, solve rate
            ├── Groups by: difficulty level, vulnerability tags
            ├── Writes: runs/<timestamp>/summary.json
            └── Writes: runs/<timestamp>/summary.md (human-readable)
```

### XBEN Evaluation (CI Trigger)

```
GitHub Actions: push to PR or manual workflow_dispatch
    │
    ├── 1. setup-matrix job
    │       └── Lists all 104 benchmarks, splits into batches of 8
    │       └── Output: matrix JSON → 13 batches
    │
    ├── 2. evaluate job (matrix: 13 parallel runners, max-parallel: 6)
    │       ├── Each runner:
    │       │   ├── Checkout repo + benchmarks
    │       │   ├── Install strix binary (scripts/install.sh)
    │       │   ├── Pull sandbox image
    │       │   ├── Run: xben run --benchmarks <batch-list>
    │       │   └── Upload: runs/<timestamp>/ as artifact
    │       │
    │       └── Artifact naming: xben-batch-{0..12}-{run_id}
    │
    └── 3. aggregate job (needs: evaluate)
            ├── Download all xben-batch-* artifacts
            ├── Merge all result.json files
            ├── Run aggregator.py: aggregate_results()
            ├── Upload combined summary as workflow artifact
            └── Post summary as PR comment (if PR trigger)
```

### Key Data Structures

**result.json (per challenge):**
```json
{
  "benchmark_id": "XBEN-001-24",
  "benchmark_name": "XBEN-001-24 IDOR - Trading Platform - Authorization",
  "level": "2",
  "tags": ["idor", "default_credentials"],
  "execution": {
    "started_at": "2026-06-17T10:00:00Z",
    "completed_at": "2026-06-17T10:15:30Z",
    "duration_seconds": 930.5,
    "status": "solved"
  },
  "target_url": "http://host.docker.internal:54321",
  "strix_execution": {
    "exit_code": 0,
    "duration_seconds": 930.5,
    "output_dir": "runs/20260617_100000/XBEN-001-24/outputs"
  },
  "evaluation": {
    "flag_extracted": true
  }
}
```

**summary.json (aggregated):**
```json
{
  "run_timestamp": "2026-06-17T10:00:00Z",
  "total_benchmarks": 104,
  "solved": 45,
  "unsolved": 52,
  "errored": 7,
  "solve_rate": 43.3,
  "by_level": {
    "1": {"solved": 20, "unsolved": 10, "errored": 2},
    "2": {"solved": 15, "unsolved": 22, "errored": 3},
    "3": {"solved": 10, "unsolved": 20, "errored": 2}
  },
  "by_tag": {
    "idor": {"solved": 8, "unsolved": 4},
    "sqli": {"solved": 12, "unsolved": 8}
  },
  "total_duration_seconds": 45210,
  "total_tokens_consumed": 12500000
}
```

## Integration Points

### Existing File: `.github/workflows/build-release.yml`

| What Changes | Why |
|-------------|-----|
| Add sandbox build + push job | Currently only builds and releases the binary. The sandbox image must be built and pushed to GHCR as part of the release. |
| Add version validation step | Validates that `pyproject.toml` version matches the git tag before proceeding. Prevents release of mismatched artifacts. |
| Extract version from script | Replace inline `grep | sed` with sourcing `scripts/build/version.sh` |

**Integration touchpoint:** The existing job matrix build (lines 23-57) remains unchanged. A new `sandbox` job is added that runs after `build`, builds `containers/Dockerfile`, tags with the release version, and pushes to `ghcr.io/usestrix/strix-sandbox:<version>`.

### Existing File: `scripts/build.sh`

**Status:** SUPERSEDED by `scripts/build/build-binary.sh`. The existing `build.sh` can remain as a backward-compatible wrapper that sources the new script, or it can be removed. Decision: keep as thin wrapper for existing users, with deprecation notice.

### Existing File: `scripts/docker.sh`

**Status:** SUPERSEDED by `scripts/build/build-sandbox.sh`. Same wrapper-or-remove decision as `build.sh`.

### Existing File: `Makefile`

| What Changes | Why |
|-------------|-----|
| Add `build` target | `make build` runs the full build pipeline |
| Add `build-binary` target | `make build-binary` runs binary-only build |
| Add `build-sandbox` target | `make build-sandbox` runs sandbox image build |
| Add `release` target | `make release VERSION=x.y.z` runs full release |
| Add `xben` target | `make xben` runs XBEN evaluation locally |
| Existing targets | All preserved unchanged |

### Existing File: `strix/interface/main.py` -- NO CHANGES

The strix CLI entry point is consumed as-is by the XBEN runner. The flags `--target`, `--instruction`, `--non-interactive`, and `--scan-mode` are already supported. The `STRIX_IMAGE` env var override (used by `run_infer_cli.py` line 69) is already handled by `strix/config/settings.py`.

### Existing File: `strix/report/state.py` -- NO CHANGES

Flag detection in `runner.py` reads from the filesystem (strix output directory) rather than the programmatic report state. This is intentional: subprocess invocation cannot access in-process state, and filesystem output is the contract between strix and the evaluation runner.

### New File: `.github/workflows/xben-eval.yml`

A NEW workflow, not an extension of `build-release.yml`. The evaluation workflow has different triggers (PR, workflow_dispatch, schedule) and different lifecycle (ephemeral per-run, not release-creating). Mixing them would create unnecessary complexity.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Embedding Build Logic in CI YAML

**What people do:** Put multi-line bash scripts directly in GitHub Actions `run:` steps.

**Why it's wrong:** Cannot be tested locally. Cannot be reused outside CI. CI YAML becomes unreadable. The existing `build-release.yml` already does this (lines 38-50 with inline version extraction and packaging).

**Do this instead:** All build logic lives in `scripts/build/*.sh`, which are shell-checked, testable locally, and invoked from CI with a single `run:` line. CI YAML becomes orchestration, not implementation.

### Anti-Pattern 2: Python SDK Import for Evaluation Runner

**What people do:** Import `strix.core.runner` and call `run_strix_scan()` directly (as `run_infer.py` does).

**Why it's wrong:** Couples the evaluation runner to strix internals. A strix crash brings down the runner. State leakage between runs (the global `ReportState` singleton). Harder to test the actual binary artifact that users run.

**Do this instead:** Use `subprocess.run()` to invoke the strix CLI (as `run_infer_cli.py` already does). The `run_infer.py` SDK-based approach can remain as an alternative for deep introspection scenarios, but the canonical evaluation path is subprocess-based.

### Anti-Pattern 3: Shared Docker Compose Stacks Across Benchmarks

**What people do:** Start one Docker Compose stack and run multiple benchmarks against it.

**Why it's wrong:** State leakage -- a benchmark that modifies the database breaks subsequent benchmarks. Port conflicts. Unclean failure modes.

**Do this instead:** Each benchmark gets its own `docker compose -p <unique-name> up` and `docker compose -p <unique-name> down -v`. The existing `run_infer_cli.py` already follows this pattern.

### Anti-Pattern 4: Version Drift Between Artifacts

**What people do:** Bump version manually in multiple places (pyproject.toml, Docker tags, CI config).

**Why it's wrong:** Human error leads to mismatched artifacts. A release tagged `v1.0.5` might ship a binary that reports `1.0.4` or a Docker image tagged `1.0.3`.

**Do this instead:** `pyproject.toml` is the single version source. All build scripts derive from it. CI validates that the git tag matches. Docker images are tagged with the extracted version.

## Build Order and Dependency Chain

### Independent Tracks

These two subsystems have no dependency on each other and can be built in parallel:

- **Track A: Build/Release Pipeline** (`scripts/build/`, `.github/workflows/build-release.yml` modifications)
- **Track B: XBEN Evaluation** (`xben-benchmarks/XBEN/` restructuring, `.github/workflows/xben-eval.yml`)

### Track A: Build/Release Pipeline Phase Order

```
Phase A1: version.sh + build scripts
    └── Dependency: None (reads pyproject.toml, uses existing strix.spec, containers/Dockerfile)
    └── Creates: scripts/build/version.sh, build-binary.sh, build-sandbox.sh
    └── Modifies: Makefile (add targets), scripts/build.sh (add deprecation wrapper)

Phase A2: Release orchestrator
    └── Dependency: A1 (build scripts must exist)
    └── Creates: scripts/build/release.sh
    └── Modifies: .github/workflows/build-release.yml (add sandbox job, version validation)

Phase A3: Docker Compose deployment
    └── Dependency: A1 (sandbox image tag format must be stable)
    └── Creates: containers/docker-compose.yml
    └── Modifies: Nothing (standalone addition)
```

### Track B: XBEN Evaluation Phase Order

```
Phase B1: Core runner refactor
    └── Dependency: None (extracts existing logic from run_infer_cli.py)
    └── Creates: runner.py, cli.py
    └── Modifies: xben-benchmarks/XBEN/pyproject.toml (add console_scripts entry point)

Phase B2: Challenge scheduling + filtering
    └── Dependency: B1 (needs runner interface)
    └── Creates: scheduler.py

Phase B3: Result aggregation + reporting
    └── Dependency: B1 (needs result.json format from runner)
    └── Creates: aggregator.py

Phase B4: CI workflow
    └── Dependency: B1, B2, B3 (all components needed)
    └── Creates: .github/workflows/xben-eval.yml
```

### Cross-Track Dependencies

The XBEN CI workflow (B4) depends on the build pipeline (A1, A2) in one specific way: the CI workflow must install a strix binary. This can be resolved by either:
- Using `scripts/install.sh` to download the latest release binary (no dependency on local build)
- Using the locally built binary from a prior build step (dependency on A1)

**Recommendation:** Use `scripts/install.sh` download approach for CI. This decouples evaluation from the build pipeline completely, allowing both tracks to proceed independently.

### What Happens to `run_infer_cli.py`?

The existing `run_infer_cli.py` (210 lines) is the prototype that validated the approach. After B1-B3 are complete, it becomes redundant and can be removed. The `run_infer.py` file (SDK-based approach, 614 lines) is preserved as an alternative evaluation path for deep introspection scenarios.

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| 1-10 challenges (local dev) | Serial execution, single process. Current `run_infer_cli.py` pattern is sufficient. |
| 10-50 challenges (CI per-PR) | Serial with batching. Matrix of 5-8 jobs with max-parallel. |
| 50-104 challenges (full CI run) | Matrix of 13 batches (8 per batch), max-parallel: 6. ~2 hours total. |
| 104+ challenges (future expansion) | Dynamic matrix generation from challenge directory listing. No code change needed. |

### First Bottleneck: Docker Image Build Time

Each challenge's `docker compose build` takes 30-120 seconds. Solution: Docker layer caching via `actions/cache` or `docker/setup-buildx-action`. Build once, reuse across matrix jobs.

### Second Bottleneck: GitHub Actions Runner Concurrency

Free tier: 5 concurrent macOS, 20 concurrent Ubuntu runners. The `max-parallel: 6` setting ensures evaluation stays within limits while other workflows may be running.

## Sources

- Strix codebase analysis: `strix/interface/main.py`, `strix/core/runner.py`, `strix/runtime/docker_client.py`, `strix/report/state.py`, `strix/config/settings.py`
- Existing build infrastructure: `Dockerfile.build`, `containers/Dockerfile`, `strix.spec`, `pyproject.toml`, `scripts/build.sh`, `scripts/docker.sh`
- Existing XBEN runner prototypes: `xben-benchmarks/XBEN/run_infer_cli.py`, `xben-benchmarks/XBEN/run_infer.py`
- GitHub Actions documentation: matrix strategies, artifact persistence patterns, cache vs artifact distinction
- Docker Compose CI patterns: ephemeral environments, healthcheck-based service ordering, `-v` flag for volume cleanup

---
*Architecture research for: CI/CD Build/Release Pipeline + XBEN Automated Benchmarking*
*Researched: 2026-06-17*
*Confidence: HIGH* (the existing codebase, the two prototype runners, and the known benchmark structure provide a solid foundation for all architectural decisions)
