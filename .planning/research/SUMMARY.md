# Project Research Summary

**Project:** CI/CD Build Pipeline and XBEN Automated Security Benchmarking for Strix
**Domain:** AI-driven security testing tool -- build/release pipeline and automated benchmark evaluation
**Researched:** 2026-06-17
**Confidence:** HIGH

## Executive Summary

This initiative adds two related but independent subsystems to the existing Strix codebase: a build/release pipeline that produces versioned, platform-native binaries and Docker sandbox images via a one-click process, and an XBEN evaluation runner that executes 104 security benchmark challenges to measure Strix''s capability and detect regressions.

The research recommends building these as two parallel tracks with minimal cross-dependency. The build pipeline wraps existing Dockerfile.build, strix.spec, and containers/Dockerfile into version-coherent shell scripts with a pyproject.toml-driven single source of truth for version numbers. The XBEN runner is a refactoring of the existing run_infer_cli.py prototype into a modular Python CLI (runner.py, aggregator.py, scheduler.py, cli.py) that invokes strix via subprocess (decoupled from internals), manages isolated Docker Compose environments per challenge, and produces structured JSON summary reports with difficulty-tiered and vulnerability-type breakdowns.

The dominant risks are security, operational cost, and evaluation integrity. Docker socket exposure on CI runners (Pitfall 1) must be addressed with rootless Docker and ephemeral runners before any CI automation. LLM API cost explosion (Pitfall 3) demands smoke-test subsets, per-run cost caps, and budget enforcement. Flag leakage between challenge runs (Pitfall 8) requires --volumes on every docker compose down and unique project naming. Version drift across independently-built artifacts (Pitfall 6) is prevented by pyproject.toml as the single version source. Three phases are recommended: Pipeline Foundation (build scripts, cleanup infrastructure, version management, baseline recording), XBEN Runner Hardening (sharding, cost controls, flag verification, parallel execution), and Cross-Platform Hardening (Windows build matrix, platform-specific PyInstaller configuration).

## Key Findings

### Recommended Stack

The existing stack (Python 3.12, PyInstaller 6.x, Docker SDK, LiteLLM, GitHub Actions) requires minimal additions. The core additions are ruamel.yaml (>=0.19.1) for round-trip-safe docker-compose.yml rewriting (PyYAML corrupts comments and key ordering), psutil (>=7.2.2) for cross-platform resource monitoring, and a pytest test suite (pytest >=8.3, pytest-asyncio >=1.4.0, pytest-mock >=3.15.1, pytest-cov >=7.1.0, pytest-timeout >=2.3) for the project''s first automated tests. All concurrency uses concurrent.futures.ThreadPoolExecutor -- XBEN evaluation is I/O-bound (Docker builds, subprocess waits), so ProcessPoolExecutor is unnecessary overhead. Jinja2 (already a transitive dependency via openai-agents[litellm]) is used for markdown report templating. The build pipeline uses gh CLI for local one-click scripts and softprops/action-gh-release@v3 for CI automation.

Critical exclusions: no Celery/Redis/RabbitMQ (over-engineered for batch jobs), no Prometheus/Grafana (infrastructure-heavy, psutil + JSON reports suffice), no live dashboard (adds WebSocket complexity for a 21+ hour batch job), no Kubernetes (Docker Compose per challenge is correct at this scale), and no docker-compose v1 (deprecated).

**Core technologies:**
- **ruamel.yaml >=0.19.1:** Round-trip-safe docker-compose.yml rewriting -- preserves comments, key ordering, and scalar styles that PyYAML destroys
- **psutil >=7.2.2:** Cross-platform CPU/memory/disk monitoring for long-running evaluation jobs -- lighter than Prometheus, Docker-aware
- **pytest suite (8.3+, with asyncio, mock, cov, timeout plugins):** First automated tests in the project -- validates pipeline scripts and XBEN runner
- **ThreadPoolExecutor (stdlib):** Parallel challenge execution for I/O-bound workloads -- max_workers=4 to avoid Docker daemon contention
- **gh CLI (v2.x) + softprops/action-gh-release@v3:** Local one-click release scripts + CI release automation with draft->upload->publish lifecycle

### Expected Features

**Must have (table stakes) -- P1:**
- Single-command binary build (wraps Dockerfile.build + strix.spec into one script) -- users expect reproducible builds
- Docker Compose deployment file -- strix has no deployment story today, users reverse-engineer from source
- One-click release via workflow_dispatch -- eliminates "which command do I run?" friction
- Challenge subset selection by difficulty, tags, and count -- 104 challenges take 21+ hours, must be filterable
- Pass/fail reporting with difficulty-level breakdown -- raw per-challenge JSON does not answer "how well does strix do on hard challenges?"
- Robust Docker container cleanup (finally block + signal handler + pre-flight cleanup) -- orphaned containers from 104 challenges crash the host
- GitHub Release artifact augmentation (checksums, compose file, consistent naming) -- security-conscious users verify downloads

**Should have (competitive) -- P2:**
- Parallel challenge execution (--max-parallel N) -- 26+ hours serial is impractical
- Token usage and cost tracking per challenge -- LLM API costs are the dominant operational expense
- CI smoke-test subset on PR (5-10 challenges, <30 min) -- automated quality gate for regressions
- Timeout-safe checkpoint/resume -- interrupted runs at challenge 98 must not lose 97 completed results
- Agent trajectory logging -- opaque failures make benchmarks useless for improvement
- Auto-generated release notes from git history -- professional OSS presentation
- Vulnerability-type breakdown in reports -- shows which vuln classes strix excels at vs. struggles with

**Defer (v2+):**
- Agent trajectory HTML viewer -- JSON logs suffice for debugging, UI component is premature
- Regression detection across runs -- requires stable baseline data that does not exist yet
- Multi-model comparison report -- requires multiple full benchmark runs, cost-prohibitive until baseline established

### Architecture Approach

The build pipeline and XBEN evaluation runner are two independent subsystems placed at the project root level (external to the strix/ Python package). Track A (Build/Release) lives in scripts/build/ with orchestration through Makefile targets and workflow_dispatch. Track B (XBEN Evaluation) lives in xben-benchmarks/XBEN/ restructured from a monolithic 210-line run_infer_cli.py into four modules: runner.py (core execution), aggregator.py (results aggregation and report generation), scheduler.py (challenge filtering/sorting/selection), and cli.py (CLI entry point). Both subsystems integrate with the existing codebase at well-defined points: the build pipeline reads version from pyproject.toml and uses strix.spec and containers/Dockerfile; the XBEN runner invokes strix as a subprocess (decoupled from internals) and manages ephemeral Docker Compose environments per challenge. A new CI workflow xben-eval.yml is separate from the existing build-release.yml -- evaluation has different triggers and lifecycle, and mixing them creates unnecessary complexity.

**Major components:**
1. **Build/Release Pipeline (scripts/build/):** version.sh (single version source), build-binary.sh (PyInstaller), build-sandbox.sh (Docker image), release.sh (orchestrator), docker-compose.yml (deployment) -- all version-derived from pyproject.toml
2. **XBEN Evaluation Runner (xben-benchmarks/XBEN/):** runner.py (subprocess-based challenge execution with Docker Compose lifecycle), scheduler.py (filter by level/tags/limit), aggregator.py (result.json -> summary.json + summary.md), cli.py (argparse-based CLI)
3. **CI Workflows (.github/workflows/):** build-release.yml (extended with sandbox build/push, version validation), xben-eval.yml (new: matrix-based challenge sharding with aggregation)

### Critical Pitfalls

1. **Docker-in-Docker Socket Escape on Self-Hosted Runners** -- Mounting /var/run/docker.sock in CI gives every strix agent root-equivalent host access. Use rootless Docker daemon and ephemeral self-hosted runners destroyed after each job. Never trigger XBEN CI on pull_request from forks. Segregate XBEN evaluation to its own runner group with zero access to deployment credentials.

2. **Cleanup Failure Cascading Into Resource Starvation** -- If docker compose down never executes (process killed, OOM, Docker daemon hang), hundreds of orphaned containers, networks, and volumes accumulate. Add pre-flight cleanup at the START of every CI job, label all Docker resources with xben-run=$GITHUB_RUN_ID, use if: always() on post-job cleanup steps, and expand the Docker network pool from 31 to 255 networks.

3. **LLM API Cost Explosion During Full Evaluation** -- 104 challenges at frontier model pricing can cost $300-2,000 per run. Use smoke-test subsets (5-10 challenges) for CI, full suite only via workflow_dispatch or weekly cron. Implement a hard per-run cost cap. Use cost-effective models (DeepSeek via LiteLLM) for evaluation. Reduce max_turns to 100 for CI evaluation mode.

4. **GitHub Actions 6-Hour Job Limit Meets 26-Hour Evaluation** -- 104 challenges x 15 min = 26+ hours, far exceeding GitHub''s 6-hour limit. Use matrix sharding (split into 5 shards of ~21 challenges each, each completing in <5 hours) with a final aggregation job. Smoke-test subset (<30 min) for PR CI.

5. **Flag Leakage Between Challenge Runs** -- Missing --volumes on docker compose down lets flags from previous challenges persist in shared volumes. Always use docker compose down --volumes --remove-orphans. Use unique project names per challenge (xben-{benchmark_id}-{run_id}). Isolate strix output directories per challenge. Verify found flag matches the current challenge''s expected flag.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Pipeline Foundation
**Rationale:** The build/release pipeline and cleanup infrastructure must exist before any CI automation. Version management is architectural and must be correct from the first release. A reproducible baseline must exist before optimization begins. The SDK pin break prevention (CI check) must be in place before any dependency upgrades.
**Delivers:** scripts/build/version.sh, build-binary.sh, build-sandbox.sh, release.sh; extended build-release.yml with sandbox build/push and version validation; Makefile build/release targets; pre-flight and post-job Docker cleanup infrastructure; BASELINE.md with documented smoke-test results; CI check for SDK pin consistency; containers/docker-compose.yml deployment file.
**Addresses:** Single-command binary build, Docker Compose deployment file, one-click release, GitHub Release artifact augmentation, Docker container cleanup (robust).
**Avoids:** Pitfall 6 (version drift -- solved by single version source), Pitfall 7 (cache busting -- registry cache for sandbox image), Pitfall 9 (SDK pin break -- automated CI check), Pitfall 10 (no baseline -- BASELINE.md recording).
**Uses:** pyproject.toml version extraction, PyInstaller (strix.spec), Docker (containers/Dockerfile, Dockerfile.build), gh CLI, softprops/action-gh-release@v3, registry-based Docker layer caching.

### Phase 2: XBEN Runner Hardening
**Rationale:** The existing run_infer_cli.py prototype works but lacks cost controls, flag verification, sharding, and structured reporting. These must be in place before CI integration in Phase 4 to prevent cost explosion (Pitfall 3), flag leakage (Pitfall 8), and 6-hour timeout failures (Pitfall 4). The smoke-test subset must be defined and validated before PR CI is enabled.
**Delivers:** runner.py (refactored from run_infer_cli.py), scheduler.py (level/tags/limit/shard/sample filtering), aggregator.py (summary.json + summary.md with difficulty and vuln-type breakdowns), cli.py (argparse CLI with --help); smoke-test challenge subset definition; per-run cost cap enforcement; --volumes flag on all docker compose down calls; unique Docker Compose project names; flag uniqueness validation; --shard and --max-parallel arguments.
**Addresses:** Challenge subset selection, pass/fail reporting with difficulty breakdown, vulnerability-type breakdown, token usage tracking, parallel challenge execution (P2), timeout-safe checkpoint/resume (P2), agent trajectory logging (P2).
**Avoids:** Pitfall 3 (cost explosion -- smoke-test subset, cost cap), Pitfall 4 (6-hour limit -- sharding), Pitfall 8 (flag leakage -- volumes flag, project naming, flag verification), Pitfall 2 (cleanup supplements from Phase 1).
**Uses:** ruamel.yaml (compose rewriting), psutil (resource monitoring), Jinja2 (report templating), ThreadPoolExecutor (parallelism), pytest suite (runner tests), subprocess (strix invocation).

### Phase 3: Cross-Platform Hardening
**Rationale:** Windows binary support is a P2 differentiator and must be verified before the release pipeline is considered complete. This phase adds the Windows build matrix, platform-specific PyInstaller configuration, and smoke tests against compiled binaries on clean environments. It is deliberately Phase 3 (not part of Phase 1) because the build pipeline works on Linux first, and cross-platform is an extension -- not a rewrite.
**Delivers:** Windows runner in CI build matrix (windows-2022); platform-aware strix.spec (separate or conditional hiddenimports for Linux vs Windows); post-build smoke tests on clean VMs; warn-*.txt artifact archival and analysis; PyInstaller --onedir debug workflow.
**Addresses:** Platform-specific binaries (this makes the Windows binary story trustworthy).
**Avoids:** Pitfall 5 (PyInstaller cross-platform failures -- native OS build environments, platform-specific hiddenimports, clean-environment smoke tests).
**Uses:** GitHub Actions OS matrix, PyInstaller platform-aware configuration, existing strix.spec extended for Windows.

### Phase 4: CI Integration
**Rationale:** With the XBEN runner hardened (Phase 2), the CI workflow can safely integrate it as a PR quality gate. This phase creates xben-eval.yml with matrix sharding for full evaluation and smoke-test subset for PR checks. It is Phase 4 (not alongside Phase 2) because the runner must be trustworthy before CI automation begins -- running an untested evaluation pipeline in CI against LLMs with API keys creates both cost and security risks.
**Delivers:** xben-eval.yml workflow (PR trigger with smoke-test subset, workflow_dispatch trigger for full suite, scheduled cron for weekly full evaluation); matrix shard generation; artifact upload/aggregation; PR comment with results summary; budget enforcement in CI; self-hosted runner configuration with rootless Docker.
**Addresses:** CI smoke-test on PR, auto-generated release notes (cosmetic enhancement during this phase).
**Avoids:** Pitfall 1 (Docker socket escape -- rootless Docker, ephemeral runners, PR trigger restrictions), Pitfall 3 (cost explosion -- CI budget cap, smoke-test only on PR), Pitfall 4 (6-hour limit -- sharding for full suite, smoke-test <30 min).
**Uses:** GitHub Actions matrix strategies, artifact persistence, step-security/harden-runner@v2, dedicated evaluation API keys with spending limits.

### Phase Ordering Rationale

- **Phase 1 before Phase 2:** Cleanup infrastructure and version management are gating for any automation. You cannot safely run an evaluation pipeline that leaves orphaned Docker resources across 104 challenges without Phase 1''s pre-flight/post-job cleanup.
- **Phase 2 before Phase 4:** The XBEN runner must have sharding, flag verification, and cost controls before CI triggers are enabled. Running an unhardened runner in CI risks cost explosion, invalid results, and security compromise.
- **Phase 3 after Phase 1:** Cross-platform is an extension of the build pipeline, not a prerequisite for it. Linux build works first, then Windows is added.
- **Phase 4 is the capstone:** CI integration depends on all prior phases. It validates that the build pipeline produces working artifacts (Phase 1 + 3) and that the XBEN runner produces trustworthy results (Phase 2).
- **Tracks A and B are parallel-capable within Phase 1 and 2:** The build pipeline (Phase 1, Phase 3) and XBEN runner (Phase 2) can be developed concurrently by different team members. The cross-track dependency is resolved by CI using scripts/install.sh to download the release binary rather than requiring a local build.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** ruamel.yaml docker-compose rewrite edge cases (YAML anchors, environment variable substitution preservation), find_free_port() race condition under parallel execution, LLM cost estimation accuracy for different model/provider combinations
- **Phase 4:** GitHub Actions self-hosted runner rootless Docker setup on Windows, matrix job artifact merging correctness, PR comment character limits for large result tables

Phases with standard patterns (skip research-phase):
- **Phase 1:** Build scripts, version extraction, Docker layer caching -- well-documented, established patterns. PyInstaller configuration already understood from existing strix.spec.
- **Phase 3:** PyInstaller cross-platform build matrices -- standard GitHub Actions pattern. Platform-specific hidden imports are documented in PyInstaller official docs.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All additions are well-understood libraries (ruamel.yaml, psutil, pytest ecosystem) with Python 3.12 compatibility verified. Existing stack integration points identified from direct codebase analysis. |
| Features | HIGH | Feature list derived from prototype analysis (run_infer_cli.py, run_infer.py) and user expectations for CLI tools, CI pipelines, and security benchmarks. Competitor analysis cross-referenced. |
| Architecture | HIGH | Existing codebase structure, prototype runners, and known benchmark layout provide a solid foundation. Component boundaries and data flows are clear. The two-track parallel design follows the existing project layout without requiring changes to the strix/ package. |
| Pitfalls | HIGH | Cross-referenced web research (PyInstaller docs, CVE-2025-32955, Docker caching issues, GitHub Actions limits) with direct codebase observation (SDK pin comment, missing --volumes flag, cleanup gaps, cost tracking absence, version extraction duplication). Historical XBEN v0.4.0 results provide context for baseline concerns. |

**Overall confidence:** HIGH

### Gaps to Address

- **Self-hosted runner provisioning:** The research assumes availability of self-hosted runners with rootless Docker for XBEN CI evaluation. If these are not provisioned, the CI integration phase (Phase 4) is blocked. Handle during Phase 4 planning by confirming runner availability or falling back to smoke-test-only on GitHub-hosted runners.
- **LLM model selection for evaluation:** The research notes that cost-effective models (DeepSeek) should be used for CI evaluation, but the exact model, its solve-rate characteristics, and its compatibility with the smoke-test subset need empirical validation during Phase 2. The baseline recording (Phase 1) should use the same model as CI evaluation.
- **Smoke-test subset curation:** Which 5-10 challenges provide the best regression signal is unknown without empirical data. Phase 2 should run the full suite once (locally or via workflow_dispatch) to identify challenges with deterministic pass/fail behavior before defining the smoke-test subset.
- **Windows PyInstaller hidden imports:** The exact set of platform-specific hidden imports for Windows cannot be fully determined without a build attempt. Phase 3 should start with a pyi-makespec on a Windows runner and diff against the Linux strix.spec.
- **XBEN challenge security audit:** The research flags that challenge source code should be audited before CI execution. Whether this audit has been done or needs to be done during Phase 2 is not determined.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: strix/runtime/docker_client.py (SDK pinning), strix/interface/main.py (CLI flags), strix/config/settings.py (STRIX_IMAGE, LLM settings), strix/report/state.py (cost tracking), strix.spec (PyInstaller config), containers/Dockerfile (sandbox image), Dockerfile.build (build container)
- Existing XBEN prototypes: xben-benchmarks/XBEN/run_infer_cli.py (subprocess-based runner, 210 lines), xben-benchmarks/XBEN/run_infer.py (SDK-based runner, 614 lines)
- Existing CI: .github/workflows/build-release.yml (matrix build, release creation)
- Planning artifacts: .planning/BUILD-SESSION.md, .planning/XBEN-SETUP-SUMMARY.md, .planning/codebase/ARCHITECTURE.md, .planning/codebase/CONCERNS.md
- ruamel.yaml PyPI and documentation -- round-trip YAML editing, Python 3.12 compatibility
- pytest-asyncio, pytest-mock, pytest-cov PyPI pages -- version compatibility, fixture management
- psutil PyPI page and documentation -- cross-platform process monitoring
- Python concurrent.futures official docs -- ThreadPoolExecutor for I/O-bound workloads
- Docker Compose Specification v5.0.0 ("Mont Blanc") -- compose file structure, depends_on condition, include
- softprops/action-gh-release v3 GitHub Marketplace -- release automation patterns
- GitHub Actions documentation -- matrix strategies, artifact persistence, 6-hour job limit, workflow_dispatch inputs
- PyInstaller official documentation -- cross-platform build requirements, hidden imports, warn-*.txt diagnostics

### Secondary (MEDIUM confidence, cross-referenced)
- CVE-2025-32955 (April 2025) -- Docker group privilege escalation bypassing disable-sudo, affecting step-security/harden-runner
- Docker layer caching in CI -- GHA cache 10 GB limit, registry cache alternative, build-push-action v6 patterns
- GitHub Actions community discussion -- 6-hour hard limit on GitHub-hosted runners, workaround strategies
- AIRTBench paper -- LLM API rate limiting and cost scaling concerns for batch evaluation
- TeamPCP Cascade (March 2026) -- supply chain attack compromising CI/CD workflows, relevant for runner isolation decisions

### Tertiary (LOW confidence, needs validation)
- XBEN v0.4.0 solve rates (Level 1 100%, Level 2 96%, Level 3 75%) -- from .planning/XBEN-SETUP-SUMMARY.md Section 1.2. These were achieved with unknown model and configuration. Cannot be used as a performance target without reproduction. This is explicitly why Phase 1 includes baseline recording.

---
*Research completed: 2026-06-17*
*Ready for roadmap: yes*
