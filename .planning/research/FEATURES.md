# Feature Research

**Domain:** CI/CD Build/Release Pipeline + XBEN Automated Security Benchmarking
**Researched:** 2026-06-17
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = pipeline feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single-command build of strix binary | CI/CD must be reproducible; no one wants a 10-step manual build process | MEDIUM | Already have `Dockerfile.build` and working `strix.spec`. Need: encapsulate `docker build -f Dockerfile.build` + `docker run --rm -v ... cp` into a script/Makefile target |
| Docker sandbox image build + push | strix runtime requires `strix-sandbox:dev` or equivalent; release must ship this pre-built to avoid 7GB local builds | MEDIUM | Already have `containers/Dockerfile`. Need: script to `docker build -t strix-sandbox:VERSION containers/` + `docker push ghcr.io/usestrix/strix-sandbox:VERSION` |
| Platform-specific binaries (Linux/Win/macOS) | Users on each OS expect a native binary, not "install Python first" | MEDIUM | Existing `build-release.yml` already handles 4 targets (macos-arm64, macos-x86_64, linux-x86_64, windows-x86_64) via PyInstaller matrix. Needs to be exposed as a one-click trigger |
| GitHub Release with artifacts attached | Standard OSS distribution pattern; users find binaries via GitHub Releases, not raw git | LOW | Existing `softprops/action-gh-release@v2` already works. Just need to augment artifact list |
| Checksums for release artifacts | Security-conscious users verify downloads; missing checksums erodes trust | LOW | Add `sha256sum` step to release workflow for each artifact |
| Docker Compose deployment file | Users running strix in "production" (CTF practice, security labs) expect a single `docker compose up` | MEDIUM | Must declare strix binary + sandbox image + environment variables in one compose file |
| XBEN runner CLI with `--help` | Discoverability is table stakes for CLI tools | LOW | Already have `run_infer_cli.py` with argparse. Needs minor polish |
| XBEN results saved to disk as JSON | Users need machine-readable results for dashboards, reports, CI integration | LOW | Already have `result.json` per-challenge. Need aggregate summary JSON |
| Pass/fail reporting per challenge | The whole point of a benchmark is knowing what passed and what failed | LOW | Already in existing runner. Needs structured summary |
| Docker container cleanup after each challenge | Memory/disk exhaustion from 104 challenge containers would kill the host | MEDIUM | `docker compose down -v` already executed in `finally` block. Needs double-safety: cleanup trap on SIGTERM/SIGINT |

### Differentiators (Competitive Advantage)

Features that set this pipeline apart. Not required, but valuable for the security tooling ecosystem.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| One-click release via `workflow_dispatch` | Eliminates "which command do I run?" friction; release manager picks version and platform from a dropdown | MEDIUM | GitHub Actions `workflow_dispatch` with `choice` inputs for version tag and platform subset. Triggers the existing build matrix |
| Challenge subset selection (by difficulty, by ID, by count) | 104 challenges x ~12 min = ~21 hours. Must be able to run meaningful subsets for PR checks and targeted regression testing | MEDIUM | Already have `--limit` and `--benchmarks`. Need to add `--level` filter, `--tags` filter (by vuln type), and `--sample N` (random subset) |
| Difficulty-tiered pass rate reporting | Shows whether agent capability degrades with challenge difficulty -- actionable for model selection and prompt tuning | LOW | Parse `benchmark.json` level field, group results by level (1/2/3), compute solve rate per tier |
| Vulnerability-type breakdown in report | Shows which vuln classes strix excels at vs. struggles with -- guides development priorities | LOW | Parse `benchmark.json` tags field, group results by tag (idor, sqli, xss, etc.), compute solve rate per tag |
| Token usage and cost tracking per challenge | LLM API costs are the dominant operational expense; need visibility into cost-per-challenge to evaluate model/provider tradeoffs | MEDIUM | `run_infer.py` already collects `resource_usage` (input_tokens, output_tokens, cost) via Tracer. CLI runner does not -- need to expose this data in exit output |
| Agent trajectory logging | Debugging why a challenge failed requires seeing what the agent tried; opaque failures make benchmarks useless for improvement | HIGH | Requires capturing strix run logs to the results directory. Already have `strix_runs/<run>/` output; need to ensure strix log files are included in copied outputs |
| Parallel challenge execution with resource governance | 104 challenges x serial = 21+ hours. Parallelism is the only way to get results in a practical timespan | HIGH | Multiple `docker compose up` stacks run concurrently. Need: max-parallel flag, port allocation coordination (free port per runner avoids collisions), Docker network isolation |
| GitHub Actions CI smoke-test subset on PR | Catch agent regressions before they merge; automated quality gate | MEDIUM | Run a curated 5-10 challenge subset (mix of easy + medium, diverse vuln types) in < 30 minutes on GitHub Actions |
| `docker-compose.yml` for one-command strix deployment | "Run this penetration testing AI agent on your own infrastructure" is a strong differentiator vs. SaaS-only competitors | MEDIUM | Single `docker-compose.yml` that: pulls strix binary (or mounts it), pulls sandbox image, sets env vars, configures Docker socket access |
| Auto-generated release notes from git history | Professional OSS presentation; saves release manager 20 minutes of manual changelog writing | LOW | `softprops/action-gh-release` already has `generate_release_notes: true`. Augment with categorized changes (features, fixes, breaking) |
| Timeout-safe partial results | 104 challenges at 1h timeout each = upto 104h. If process is killed/CI times out, should not lose results from completed challenges | MEDIUM | Save `result.json` immediately after each challenge completes (already done). Add checkpoint file so re-run picks up where it left off |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time dashboard during XBEN run | "I want to watch progress live" | Adds WebSocket server, front-end, and state sync complexity for a 21-hour batch job. Builds infrastructure that distracts from the core pipeline | Terminal progress bar with periodic summary (every 10 challenges). HTML report generated at end. CI users watch Actions log anyway |
| Inline LLM provider switching during benchmark | "Let me compare models mid-run" | LLM state is tied to agent session; switching provider mid-challenge invalidates the benchmark (different capabilities). Cross-contaminates results | Run separate XBEN evaluations with different `STRIX_LLM` values. Compare aggregate reports after both complete |
| Web UI for triggering builds/releases | "I want a button in a web page" | Duplicates GitHub's built-in `workflow_dispatch` UI in Actions tab. Adds maintenance burden for a React app that 3 people will ever use | Use GitHub Actions `workflow_dispatch` dropdown (already built into GitHub). Document `gh workflow run` for CLI users |
| Auto-publishing to PyPI/npm/Homebrew on every release | "Wider distribution = more users" | Each packaging format has its own maintenance burden, compatibility matrix, and security review. Premature distribution fragmentation | Ship via GitHub Releases first (single source of truth). Add packaging formats when user demand is demonstrated, not speculatively |
| "Run all 104 challenges on PR" in CI | "Maximum quality gate" | 104 challenges x ~12 min avg = ~21 hours, well beyond GitHub's 6h limit. Even with self-hosted runners, the LLM API cost per PR ($200-500+) is prohibitive. Slows development velocity to zero | Curated smoke-test subset (10 challenges, < 30 min, ~$10-20 API cost). Full suite as nightly scheduled run or manual `workflow_dispatch` only |
| Dynamic challenge container orchestration (K8s) | "More scalable than docker compose" | Strix already requires Docker socket access. Adding K8s means managing clusters, kubectl configs, ingress, and persistent volumes -- for what is essentially 104 standalone `docker compose` operations that run sequentially or with bounded parallelism | Plain `docker compose` per challenge. The parallelism limit is LLM API rate limits and cost, not container orchestration scale. For >4 parallel agents, add `--max-parallel` flag using Python's `concurrent.futures` |

## Feature Dependencies

```
One-click build & release (workflow_dispatch)
    ├──requires──> Single-command binary build (Makefile/script)
    │                   └──requires──> Dockerfile.build (already exists)
    │                   └──requires──> strix.spec (already exists)
    ├──requires──> Docker sandbox image build + push
    │                   └──requires──> containers/Dockerfile (already exists)
    │                   └──requires──> ghcr.io push credentials (already exists)
    └──requires──> Docker Compose deployment file

XBEN automated evaluation runner
    ├──requires──> Challenge subset selection
    ├──enhances──> Parallel execution (makes subset selection more useful)
    ├──enhances──> Token usage tracking (separate concern, same data path)
    └──enhances──> Timeout-safe partial results (robustness layer)

CI integration (PR check)
    ├──requires──> Challenge subset selection (smoke-test subset)
    ├──requires──> Pass/fail reporting (exit code determines check status)
    └──requires──> Docker container cleanup (CI runner has limited disk)

GitHub Release
    ├──requires──> Single-command binary build (to produce artifacts)
    └──enhances──> Auto-generated release notes (cosmetic, not blocking)

Agent trajectory logging
    └──requires──> strix output directory discovery (already solved in run_infer_cli.py)
```

### Dependency Notes

- **One-click release requires single-command binary build:** The `workflow_dispatch` trigger must orchestrate the existing `Dockerfile.build` + `containers/Dockerfile` build sequence. It does not replace them -- it wraps them in a single invocation point.
- **CI integration requires challenge subset selection:** Without `--level` and `--limit`, CI would attempt all 104 challenges and time out. Subset selection is a hard prerequisite.
- **Parallel execution enhances subset selection:** Once subsets exist, parallelism makes them practical. Serial execution of 10 challenges = 2 hours; parallel (4-way) = 30 minutes.
- **Agent trajectory logging is a separate data path from result.json:** result.json captures pass/fail/timing. Trajectory logging captures the agent's reasoning trace, which lives in strix_runs/<run>/ and is currently already copied via `shutil.copytree`. The feature is about ensuring coverage (logs, not just vulnerability reports) is included.

## MVP Definition

### Launch With (v1 -- This Milestone)

Minimum viable product -- what's needed to make the pipeline useful.

- [ ] **Single-command binary build** -- A `Makefile` or script (`scripts/build.sh`) that builds strix binary inside Docker and extracts it. Essential because the current process requires knowing the right `docker build` + `docker run` incantation.
- [ ] **Docker Compose deployment file** -- A `docker-compose.yml` that declares the strix service (sandbox image, env vars, docker socket mount). Essential because strix has no deployment story today -- users reverse-engineer it from source.
- [ ] **One-click release via workflow_dispatch** -- GitHub Actions workflow with `workflow_dispatch` inputs (version tag as `string`, platform selection as `choice`). Essential because the current release process requires pushing a git tag AND knowing the workflow exists.
- [ ] **Challenge subset selection (by difficulty + count)** -- `--level` filter and `--limit` already partially exist. `--tags` filter by vulnerability type. Essential for practical use -- nobody runs 104 challenges every time.
- [ ] **Pass/fail reporting with difficulty breakdown** -- Aggregate results grouped by difficulty level. Essential because the raw per-challenge JSON doesn't answer "how well does strix do on hard challenges?"
- [ ] **Docker container cleanup (robust)** -- `finally` block cleanup + signal handler for SIGTERM/SIGINT. Essential because orphaned Docker containers from 104 challenges crash the host.
- [ ] **GitHub Release artifact augmentation** -- Add checksums, add `docker-compose.yml` to release artifacts, ensure binary naming convention is consistent. Essential for trust and deployability.

### Add After Validation (v1.x)

Features to add once core pipeline is proven.

- [ ] **Parallel challenge execution** -- `--max-parallel N` using `concurrent.futures.ProcessPoolExecutor` (each worker runs `run_one` in a subprocess). Trigger: when serial benchmark times exceed practical limits for the team.
- [ ] **Token usage and cost tracking** -- Expose `resource_usage` from strix's LiteLLM cost tracker into `result.json`. Trigger: when cost visibility becomes important for model selection decisions.
- [ ] **CI smoke-test on PR** -- Curated 10-challenge subset in GitHub Actions workflow triggered on `pull_request`. Trigger: when the team has enough benchmark data to select representative challenges.
- [ ] **Timeout-safe checkpoint/resume** -- Write a checkpoint file after each challenge; `--resume` flag skips already-completed challenges. Trigger: when full-suite runs are interrupted frequently enough to justify the complexity.
- [ ] **Auto-generated release notes** -- Categorize git history into features/fixes/breaking for release body. Trigger: when release frequency increases to weekly.

### Future Consideration (v2+)

Features to defer.

- [ ] **Agent trajectory HTML viewer** -- Visualize agent decision tree from logs. Defer because: requires building a separate UI component; JSON logs are sufficient for debugging today.
- [ ] **Regression detection across runs** -- Compare current run results against baseline, flag challenges that regressed from "solved" to "unsolved". Defer because: requires stable baseline data that doesn't exist yet.
- [ ] **Multi-model comparison report** -- Run same challenge set against different LLM providers, produce side-by-side comparison. Defer because: requires multiple full benchmark runs; cost-prohibitive until baseline established.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Single-command binary build | HIGH | MEDIUM | P1 |
| Docker Compose deployment file | HIGH | MEDIUM | P1 |
| One-click release (workflow_dispatch) | HIGH | MEDIUM | P1 |
| Challenge subset selection (level + tags + limit) | HIGH | MEDIUM | P1 |
| Pass/fail report with difficulty breakdown | HIGH | LOW | P1 |
| Docker container cleanup (robust) | HIGH | MEDIUM | P1 |
| GitHub Release checksums + compose | MEDIUM | LOW | P1 |
| Parallel challenge execution | HIGH | HIGH | P2 |
| Token usage per challenge | MEDIUM | MEDIUM | P2 |
| CI smoke-test on PR | MEDIUM | MEDIUM | P2 |
| Checkpoint/resume | MEDIUM | MEDIUM | P2 |
| Agent trajectory logging | MEDIUM | HIGH | P2 |
| Auto-generated release notes | LOW | LOW | P2 |
| Vuln-type breakdown report | MEDIUM | LOW | P2 |

**Priority key:**
- P1: Must have for launch (this milestone)
- P2: Should have, add when possible (v1.x)

## Competitor Feature Analysis

| Feature | XBOW XBEN (original runner) | Gato-X / AIRTBench | Our Approach |
|---------|----------------------------|-------------------|--------------|
| Benchmark runner | Python SDK-based, async, clones from GitHub per run | N/A (these are attack tools, not benchmark runners) | CLI-based subprocess runner -- decoupled from strix internals, tests the actual binary |
| Challenge subset selection | `--benchmarks` filter only | N/A | difficulty + tags + limit + random sample |
| Results format | `result.json` per challenge | Vulnerability/enumeration output | `result.json` per challenge + aggregate summary JSON |
| LLM cost tracking | Via Tracer (internal SDK) | N/A | Via strix LiteLLM cost callback (external to runner) |
| Parallel execution | Serial only | Scans 35K repos in parallel via thread pools | `ProcessPoolExecutor` with Docker resource governance |
| Deployment story | Clones repo, runs in development mode | pip install | docker compose up (production deployment) |

## Sources

- Existing codebase analysis: `run_infer_cli.py` (CLI runner v2), `run_infer.py` (SDK runner v1), `build-release.yml` (existing GHA workflow), `Dockerfile.build` (build container), `containers/Dockerfile` (sandbox image), `strix.spec` (PyInstaller config), `.planning/XBEN-SETUP-SUMMARY.md` (build/debug history)
- PyInstaller cross-platform CI best practices -- platform-specific matrix builds on GitHub Actions, spec file conditionals, clean venv for reproducible builds
- Docker Compose multi-platform deployment best practices -- base + override file pattern, `.env` for platform differences, single `docker compose up` invocation
- GitHub Actions 6-hour job limit -- requires challenge subset selection for CI; self-hosted runners for full suite; checkpoint/resume for interrupted runs
- Docker-in-Docker pitfalls -- never `docker system prune` in shared environments; scoped cleanup by project name; port collision avoidance via `find_free_port`; network pool exhaustion prevention
- LLM API cost patterns -- tool-heavy agents add 1500-3000 tokens/schema overhead per request; rate limiting as real-world constraint; batch evaluation 10-1000x cheaper than per-item scoring
- GitHub Actions `workflow_dispatch` best practices -- use `choice` inputs over `string` where possible; provide defaults; validate inputs explicitly; use protected environments for sensitive operations
- `softprops/action-gh-release@v2` -- `generate_release_notes: true` for auto-generated notes; `files:` glob for artifact attachment; `prerelease:` boolean for tag vs. manual distinction

---
*Feature research for: Strix CI/CD pipeline & XBEN automated benchmarking*
*Researched: 2026-06-17*
