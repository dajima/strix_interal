# Pitfalls Research: CI/CD Build Pipeline + XBEN Automated Benchmarking

**Domain:** Adding build pipeline and automated security benchmark evaluation to an existing AI-driven security testing tool
**Researched:** 2026-06-17
**Confidence:** HIGH (cross-referenced web research + direct codebase observation from BUILD-SESSION.md, XBEN-SETUP-SUMMARY.md, CONCERNS.md + strix docker_client.py SDK pinning analysis)

---

## Critical Pitfalls

These cause rewrites, data loss, security compromise, or massive unexpected costs. Address in Phase 1 (Pipeline Foundation) before any CI automation.

### Pitfall 1: Docker-in-Docker Socket Escape on Self-Hosted Runners

**What goes wrong:**
Strix's sandbox architecture requires spawning Docker containers (strix-sandbox, Caido proxy) from within the XBEN evaluation runner. If the evaluation runs inside a GitHub Actions self-hosted runner container, the ONLY way to make `docker compose up` work inside CI is to mount the host Docker socket (`/var/run/docker.sock`). This gives every strix agent and every XBEN challenge container root-equivalent access to the CI host. A strix agent that executes `docker run -v /:/host` can read and exfiltrate every secret, token, SSH key, and cloud credential on the runner -- including the `GITHUB_TOKEN`, `GHCR_PAT`, and any LLM API keys in environment variables.

**Why it happens:**
The temptation is "just mount the socket, it's our own runner." But strix agents run arbitrary shell commands inside sandbox containers with NET_ADMIN and NET_RAW capabilities (`strix/runtime/docker_client.py` lines 107-108). A container breakout vulnerability in the 7.38 GB sandbox image (hundreds of packages, many with CVEs) becomes a host compromise. The Docker group on Linux is well-documented as equivalent to root -- CVE-2025-32955 (April 2025) specifically demonstrated that even with sudo disabled, Docker group membership allows full privilege escalation.

**How to avoid:**
1. Use **ephemeral self-hosted runners** destroyed after every job. Limits blast radius to hours, not permanent.
2. Use **rootless Docker daemon** on the runner host (`dockerd-rootless` via `docker:dind-rootless`). Socket access to a rootless daemon limits what a compromised container can do.
3. **NEVER trigger XBEN CI on `pull_request` from forks.** Only `push` to protected branches or `workflow_dispatch`.
4. Segregate XBEN evaluation to its own runner group with zero access to deployment credentials or registry push tokens -- those secrets go to a separate `build-release` workflow.
5. Apply `step-security/harden-runner@v2` on the runner and monitor egress traffic for exfiltration patterns.

**Warning signs:**
- `/var/run/docker.sock` mounted in CI config or runner startup scripts
- Self-hosted runner labels in workflow files with `pull_request` triggers
- `GITHUB_TOKEN` or `secrets.GHCR_PAT` in the same job that runs `docker compose`
- `groups runner` showing `docker` on the runner host
- Any reference to `--privileged` in runner container launch scripts

**Phase to address:** Phase 1 -- Pipeline Foundation. This is a security architecture decision that gates whether XBEN evaluation can safely run in CI at all.

---

### Pitfall 2: Cleanup Failure Cascading Into Resource Starvation

**What goes wrong:**
Each XBEN challenge execution: `docker compose up` (1-4 containers + network + volumes), strix scan (creates sandbox container + volumes), `docker compose down`. If ANY step fails -- strix SIGKILL, Python OOM, subprocess timeout, Docker daemon hang, GitHub Actions 6-hour timeout sending SIGKILL -- the `docker compose down` never executes. After 104 challenges, hundreds of orphaned containers, dozens of Docker networks (default pool: 31 networks on `/16`), and gigabytes of orphaned volumes accumulate. The next CI run fails with "could not find an available, non-overlapping IPv4 address pool among the defaults" or "no space left on device."

**Why it happens:**
Python's `try/finally` only works if the process stays alive. GitHub Actions sends SIGTERM (then SIGKILL after 7.5 seconds) on timeout. Docker daemon restarts, host reboots, and OOM kills all bypass Python's cleanup. The existing `run_infer_cli.py` has per-challenge cleanup but depends on the Python process surviving. Additionally, strix creates its own sandbox container via `strix/runtime/session_manager.py` -- if the evaluation runner dies, the sandbox and its volumes are orphaned.

**How to avoid:**
1. Add a **pre-flight cleanup** at the START of every CI job:
   ```bash
   docker ps -a --filter "label=xben-run" -q | xargs -r docker rm -f 2>/dev/null
   docker network ls --filter "label=xben-run" -q | xargs -r docker network rm 2>/dev/null
   docker container prune -f --filter "label=xben-run" 2>/dev/null
   ```
2. Label ALL docker compose resources with `--label xben-run=$GITHUB_RUN_ID`. This makes scoped cleanup trivial even from outside the Python process.
3. Add a **post-job cleanup step** that runs with `if: always()` (executes even on cancellation/failure).
4. Expand the Docker network pool on the runner:
   ```json
   { "default-address-pools": [ {"base": "172.17.0.0/12", "size": 24} ] }
   ```
   This goes from ~31 to ~255 available networks.
5. Use `docker compose down --volumes --remove-orphans --timeout 30` with explicit timeout -- never the default 10-second timeout.
6. Add a `STRIX_TIMEOUT_SECONDS` environment variable and set it lower in CI (600 seconds per challenge) to prevent hung scans from consuming the entire job window.

**Warning signs:**
- "could not find an available IPv4 address pool" mid-run
- `docker ps -a | wc -l` showing >100 exited containers on the runner
- `docker system df` showing >80% disk in "volumes" or "images"
- CI runner disk filling after 2-3 consecutive XBEN runs
- Unexplained "No space left on device" errors during Docker pull

**Phase to address:** Phase 1 -- Pipeline Foundation. Cleanup infrastructure is gating for any CI automation of multi-challenge runs.

---

### Pitfall 3: LLM API Cost Explosion During Full Evaluation

**What goes wrong:**
A full 104-challenge evaluation, at ~12-18 minutes per challenge with an agent loop of up to 300 turns, can execute tens of thousands of LLM API calls. With frontier model pricing ($3-15/M tokens input, $15-60/M tokens output for Claude/GPT-class models), a single full evaluation can cost $300-$2,000 in API fees. Running this on every PR or every push to main yields a four-figure monthly bill. If evaluation is accidentally left in a loop (e.g., a cron workflow with no budget cap), the bill hits five figures before anyone notices.

**Why it happens:**
The `run_infer_cli.py` has zero cost tracking or budget enforcement. Strix does track costs internally (via `strix/report/state.py` LiteLLM callbacks), but the evaluation runner doesn't consume or enforce these. Additionally, the full agent loop of 300 turns with a large context window means each challenge can burn through millions of tokens -- the agent sees its full conversation history plus tool outputs on every turn.

**How to avoid:**
1. **Create a smoke-test subset** of 5-10 challenges (one per difficulty level + vulnerability type) that runs on every CI trigger. Full 104 is `workflow_dispatch` or weekly cron ONLY.
2. **Implement a hard per-run cost cap** as a GitHub Actions secret (`XBEN_MAX_COST_PER_RUN`). The runner parses strix's cost metrics and aborts if exceeded.
3. **Use cost-effective models for evaluation**: DeepSeek or similar open-weight models via LiteLLM routing (already supported via `STRIX_LLM` provider prefix) cost 10-100x less than frontier models for comparable capability on structured CTF tasks.
4. **Reduce `max_turns` for CI**: The `--scan-mode deep` uses 300 turns. Create a `--scan-mode eval` mode with 100 turns max for benchmarking -- the point is to measure if strix CAN solve the challenge, not to give it unlimited budget.
5. **Track cumulative monthly spend** and hard-stop the workflow if a monthly budget threshold is breached.
6. **Warn, don't silently bill**: Print estimated cost at the start of each challenge based on model pricing and expected token usage.

**Warning signs:**
- No `max_turns` or `timeout` on per-challenge strix invocations in CI
- Hardcoded `--scan-mode deep` for evaluation (300 turns -- too many for benchmarking)
- No budget secret or cost check in the CI workflow
- LLM provider dashboard showing unexpected cost spikes on days CI runs
- "Let's just run all 104 to see how we do" without a cost estimate

**Phase to address:** Phase 2 -- XBEN Runner Hardening. Cost controls, smoke-test subset, and budget enforcement must exist before CI triggers are enabled.

---

### Pitfall 4: GitHub Actions 6-Hour Job Limit Meets 26-Hour Evaluation

**What goes wrong:**
104 challenges x 15 minutes (typical observed time) = 26 hours of wall-clock time. GitHub-hosted runners have a hard 6-hour job timeout. A single CI job attempting all 104 dies at the 6-hour mark with SIGTERM, leaving ~80 challenges un-run, dozens of orphaned Docker resources, and misleading partial results showing a solve rate of only the earliest (easiest) challenges.

**Why it happens:**
The naive approach is "one Python script, run all challenges, get results." The 6-hour limit isn't discovered until the first full run fails. The partial results are worse than useless -- they show a solve rate based only on challenges 1-24 (sorted by difficulty, so the easiest ones).

**How to avoid:**
Three strategies, ordered by preference:

**Strategy A: Shard across multiple CI jobs (best for GitHub-hosted runners).**
```yaml
strategy:
  matrix:
    shard: [0, 1, 2, 3, 4]
```
Split 104 challenges into 5 shards of ~21 each. Each shard runs as a separate job, each completing within ~5 hours (with 1-hour headroom). A final aggregation job merges results. Requires the XBEN runner to accept `--shard N --shard-count M` arguments.

**Strategy B: Self-hosted runners with checkpoint/restart.**
No 6-hour limit on self-hosted runners, but requires addressing Pitfall 1. Each challenge writes its result atomically to disk. If the runner crashes at challenge 37, restart picks up from 38. Requires a persistent result store that survives process death.

**Strategy C: Smoke-test subset in CI, full suite as scheduled trigger.**
PR CI runs 5-10 challenges (~2 hours). Full 104 evaluation is a `workflow_dispatch` manual trigger or weekly cron schedule. This is the pragmatic approach -- get fast feedback on every PR, comprehensive results on a schedule.

**Warning signs:**
- A single CI job calling `python run_infer_cli.py` with no sharding or `--limit`
- `timeout-minutes: 360` on the job (pushing the exact limit with zero headroom)
- Assuming "we'll just use self-hosted" without addressing Pitfall 1
- No result aggregation step in the workflow definition

**Phase to address:** Phase 2 -- XBEN Runner Hardening. Sharding, checkpoint, and subset selection must be implemented before CI integration.

---

### Pitfall 5: Cross-Platform PyInstaller Build Failures in CI

**What goes wrong:**
The current `Dockerfile.build` produces a Linux ELF binary. The existing `build-release.yml` only builds on Linux. When Windows binary support is added, the CI encounters: (1) hidden imports that work on Linux but NOT on Windows (ctypes DLLs, platform-specific subprocess behaviors), (2) the `strix.spec` file generated on Linux having platform-specific entries that fail on Windows, (3) the `containers/` directory being copied into the build but having no purpose on a Windows binary. The Windows build succeeds but the resulting `.exe` crashes at runtime with cryptic `ModuleNotFoundError` or `FileNotFoundError`.

**Why it happens:**
PyInstaller cannot cross-compile -- each target OS needs its own build environment. The `.spec` file generated by `pyi-makespec` includes platform-detected entries. Python packages like `docker`, `textual`, and `litellm` have different hidden imports on Windows (win32api, ms-sql drivers) vs Linux. The 150+ hidden imports in the current `strix.spec` were manually curated for Linux; Windows needs its own audit.

**How to avoid:**
1. **Build matrix with native OS runners**: `ubuntu-22.04` for Linux binary, `windows-2022` for Windows `.exe`. No WSL cross-build -- native Windows Python + PyInstaller.
2. **Generate `.spec` per platform** and diff them: `pyi-makespec --onefile strix/interface/main.py` on each OS, compare the hiddenimports lists.
3. **Test the binary in a clean environment** (fresh VM or Docker container without Python/dev tools): the most common PyInstaller failure mode is "works in dev, crashes in production" because the dev's Python environment masks missing imports.
4. **Add `--onedir` test build first**: `--onedir` mode (directory output) is easier to inspect -- you can `ls` the output and see exactly what was bundled. Use it for debugging before switching to `--onefile` for release.
5. **Check `build/*/warn-*.txt`** after every build. Archive these as CI artifacts. Any "WARNING: Hidden import X not found" that's NOT a known-safe false positive (e.g., `user32` on Linux) is a runtime crash waiting to happen.
6. **Exclude platform-specific dependencies**: `psutil` sensors on Windows need different handling than Linux. `pywin32` is Windows-only. The `strix.spec` `excludes` list needs to be platform-aware.
7. **Known strix-specific risk**: The `strix/runtime/docker_client.py` SDK pinning comment says "Bumping the SDK requires re-merging the parent body." If any PyInstaller-related change touches imports in this file or its parent SDK classes, the merged code must be verified on both platforms.

**Warning signs:**
- PyInstaller build warnings mentioning `user32`, `msvcrt`, `win32api` on a Linux build (or `fcntl`, `termios` on Windows)
- CI matrix building only one OS
- No post-build smoke test ("does the binary actually start on a clean machine?")
- `warn-*.txt` files being ignored (not archived as CI artifacts)

**Phase to address:** Phase 3 -- Cross-Platform Hardening. The build matrix and platform-specific spec file management are part of this phase.

---

### Pitfall 6: Version Drift Between pyproject.toml, Git Tags, Docker Tags, and Release Artifacts

**What goes wrong:**
A release is cut with `pyproject.toml` at version `1.0.5`, the Docker sandbox image tagged `strix-sandbox:1.0.5`, and the Git tag `v1.0.5`. But the PyInstaller binary inside the GitHub Release (built by a different CI workflow) was built from a different commit because someone pushed to main between the tag and the build trigger. The `strix --version` output in the binary shows `1.0.5`, but the embedded `containers/Dockerfile` is from commit `v1.0.6-dev`. The sandbox image that `strix` expects (`ghcr.io/usestrix/strix-sandbox:1.0.5`) doesn't match the one users pull. Result: runtime errors or unexpected behavior that's nearly impossible to reproduce.

**Why it happens:**
Multiple independently-versioned artifacts (Python package in `pyproject.toml`, Docker sandbox image, PyInstaller binary, Git tag) are produced by different tooling at different times. The existing `build-release.yml` workflow doesn't enforce atomicity -- the tag, the PyPI publish, the Docker push, and the GitHub Release asset upload are separate steps that can partially succeed or use stale inputs.

**How to avoid:**
1. **Single source of truth for version**: Read version from `pyproject.toml` (or `strix/__init__.py` `__version__`) in ALL build steps. Never hardcode versions in workflow files.
2. **Atomic release workflow**: The entire release process (tag, build binary, build sandbox image, push to PyPI, push to GHCR, create GitHub Release) should be one workflow with explicit dependencies. If any step fails, the release is not published.
3. **Embed the Git SHA in every artifact**: PyInstaller builds should include `--add-data` for a `VERSION` file containing `{version}+{git_sha}`. Docker images should have `org.opencontainers.image.revision` label with the SHA.
4. **Verify before publishing**: After building all artifacts, run a smoke test that verifies `strix --version` output matches the release version, and `docker inspect strix-sandbox:latest` shows the correct revision label.
5. **Don't use `latest` tag for anything automated**: Pin to explicit version tags (`strix-sandbox:1.0.5`, not `strix-sandbox:latest`). The `latest` tag drifts silently and makes debugging version-related bugs impossible.

**Warning signs:**
- Version string appears in more than one file (pyproject.toml AND a hardcoded string somewhere)
- `docker tag ... latest` without an explicit versioned tag
- Separate CI workflows for "build" and "release" that can trigger independently
- `git describe --tags` used in one step and `pyproject.toml` version in another
- GitHub Release created BEFORE all artifacts are confirmed built and pushed

**Phase to address:** Phase 1 -- Pipeline Foundation. Version management is architectural and must be correct from the first automated release.

---

### Pitfall 7: Docker Layer Cache Busting on Every CI Run

**What goes wrong:**
The CI build for the sandbox image (`containers/Dockerfile`, 225 lines, ~25 RUN layers, 7.38 GB final image) takes 45+ minutes per build. Without proper layer caching, every CI run does a full rebuild from scratch. With GitHub Actions' GHA cache (10 GB per-repo limit), the first build fills the cache, but subsequent builds find the cache EVICTED because the 7.38 GB image exceeds the 10 GB limit when combined with other cached layers. The build is slow forever.

**Why it happens:**
Docker layer caching in CI is subtle: GHA cache has a 10 GB cap shared across ALL caches in the repo. `docker/build-push-action` with `cache-to: type=gha,mode=max` exports ALL intermediate layers -- for a 7.38 GB image with 25 layers, this can be 15-20 GB of cache data. It gets evicted silently. Additionally, the `COPY . .` or `COPY containers/ .` step invalidates all subsequent layers on ANY file change, even changes to unrelated files. The current `Dockerfile.build` does `COPY strix/ strix/` and `COPY containers/ containers/` before `RUN pip install`, so ANY Python source change re-installs all dependencies.

**How to avoid:**
1. **Use registry cache (`type=registry`) instead of GHA cache (`type=gha`)** for the sandbox image. Push cache layers to GHCR (which has no 10 GB limit):
   ```yaml
   - uses: docker/build-push-action@v6
     with:
       cache-from: type=registry,ref=ghcr.io/usestrix/strix-sandbox:buildcache
       cache-to: type=registry,ref=ghcr.io/usestrix/strix-sandbox:buildcache,mode=max
   ```
2. **Separate the sandbox image build from the binary build.** The sandbox changes infrequently (tools are relatively stable). Rebuild it only when `containers/Dockerfile` changes, detected via path filtering:
   ```yaml
   on:
     push:
       paths:
         - 'containers/Dockerfile'
         - 'containers/docker-entrypoint.sh'
   ```
3. **Reorder Dockerfile layers** for maximum cache reuse: `COPY pyproject.toml` before `RUN pip install`, then `COPY strix/` after. This means dependency installation is cached even when source code changes.
4. **Use `mode=min`** not `mode=max` for GHA cache on the build image (smaller, fits in 10 GB). Registry cache for the sandbox image.
5. **Tag build cache images** with a predictable key that doesn't change every run (e.g., based on `containers/Dockerfile` hash, not `github.run_id`).

**Warning signs:**
- CI build always takes exactly as long as the first build (~45+ minutes for sandbox)
- GitHub Actions cache usage showing >9 GB used
- `cache-to: type=gha` for a >1 GB image
- `COPY . .` early in the Dockerfile followed by expensive install commands
- No path filtering on the CI trigger -- rebuilding the sandbox image on every `.py` file change

**Phase to address:** Phase 1 -- Pipeline Foundation. Caching strategy affects build time from the very first CI run.

---

### Pitfall 8: Flag Leakage Between Challenge Runs

**What goes wrong:**
XBEN challenge XBEN-012-24 (medium difficulty) has a `.env` file with `FLAG=flag{abc123}`. The evaluation runner starts the challenge, strix scan runs, and the flag is found. `docker compose down` is called. But the next challenge XBEN-013-24 happens to use the same Docker project name or writes to a shared Docker volume that wasn't cleaned up. The flag from XBEN-012-24 is still present in the volume. Strix finds it and reports XBEN-013-24 as "solved" without actually solving it. The solve rate metric is inflated.

**Why it happens:**
Docker Compose volumes are not automatically removed by `docker compose down` unless `--volumes` is explicitly passed. The existing `run_infer_cli.py` calls `docker compose down` without `--volumes`. Additionally, if two challenges use the same `container_name` (possible with default compose project naming), one may fail to start and leave its state behind. The strix output directory comparison (`before/after strix_runs/`) can also pick up stale output from a previous run if names collide.

**How to avoid:**
1. **Always use `docker compose down --volumes --remove-orphans`** -- the `--volumes` flag is critical and currently MISSING from `run_infer_cli.py`.
2. **Use unique Docker Compose project names** per challenge: `--project-name xben-{benchmark_id}-{run_id}` instead of the default (which is derived from the directory name).
3. **Isolate strix output directories**: Set `STRIX_RUNS_DIR` environment variable to a per-challenge temporary directory, and clean it up after flag extraction.
4. **Verify flag uniqueness**: After flag extraction, run a sanity check -- if challenge X found a flag, verify that the found flag string matches the challenge's own `.env` file. If it matches a DIFFERENT challenge's flag, flag the result as invalid.
5. **Wipe the Docker context between challenges**: After `docker compose down --volumes`, run `docker container prune -f` and `docker volume prune -f` scoped to the challenge's labels. Don't run un-scoped prune commands (they could kill other concurrent runs).

**Warning signs:**
- Missing `--volumes` flag on `docker compose down`
- Same Docker project name being reused across challenges
- Flag detection finding a flag in `strix_runs/` that doesn't match the current challenge's `.env`
- A challenge showing "SOLVED" with a flag that looks like a UUID from a different challenge
- Inflated solve rates on subsequent runs (comparing run 2 vs run 1 showing sudden jumps for easy challenges)

**Phase to address:** Phase 2 -- XBEN Runner Hardening. Flag verification and volume isolation are evaluation integrity requirements.

---

### Pitfall 9: SDK Upgrade Breaks the Docker Client Pin

**What goes wrong:**
A Dependabot PR bumps `openai-agents` from `0.14.6` to `0.15.0`. The CI build passes (the import still resolves). But at runtime, the `StrixDockerSandboxClient._create_container()` method -- which contains a verbatim copy of the upstream `DockerSandboxClient._create_container` body from v0.14.6 -- is now out of sync with the parent class at v0.15.0. The upstream changed an internal method signature, renamed `_build_docker_volume_mounts`, or refactored manifest handling. Strix still calls the OLD version copied into `docker_client.py`, which uses stale APIs. The sandbox container fails to create with an obscure AttributeError or Docker API error.

**Why it happens:**
The SDK pin is documented in `strix/runtime/docker_client.py` (comment block lines 19-21): "Pinned to openai-agents==0.14.6. Bumping the SDK requires re-merging the parent body." But this is a code comment, not an automated check. Dependabot, Renovate, or a developer doing `uv lock --upgrade-package openai-agents` will NOT read the comment. The pin in `pyproject.toml` (`openai-agents[litellm]==0.14.6`) prevents casual upgrades, but a deliberate SDK bump for security fixes or new features will break silently.

**How to avoid:**
1. **Add a CI check** that verifies the SDK version in `pyproject.toml` matches the version documented in `docker_client.py`'s pin comment. If they diverge, fail the CI build with a clear message: "SDK version changed from 0.14.6 to X.Y.Z -- you MUST re-merge `StrixDockerSandboxClient._create_container` with the new upstream body. See strix/runtime/docker_client.py lines 19-21."
   ```python
   # Check: extract version from docker_client.py comment, compare to installed openai-agents
   import re, subprocess
   with open("strix/runtime/docker_client.py") as f:
       match = re.search(r"Pinned to openai-agents==([\d.]+)", f.read())
       pinned = match.group(1) if match else None
   actual = subprocess.check_output(["python", "-c", "import openai.agents; print(openai.agents.__version__)"]).decode().strip()
   assert pinned == actual, f"SDK pin mismatch: docker_client.py pinned {pinned}, installed {actual}"
   ```
2. **Add a test that actually calls `_create_container`** (with a mock Docker daemon) and verifies the `create_kwargs` contain NET_ADMIN, NET_RAW, and host-gateway. This test catches the case where the parent class API changed.
3. **Upstream the fix**: Track whether the `openai-agents` SDK has added an injection hook for customizing `_create_container`. If they have, switch to the hook instead of subclass reimplementation.
4. **Lock the SDK aggressively**: In `pyproject.toml`, use `==0.14.6` not `>=0.14.6,<0.15.0`. Add a Dependabot ignore rule for this specific package with a comment referencing the pin.

**Warning signs:**
- Dependabot/Renovate PR bumping `openai-agents` version
- `uv lock --upgrade-package openai-agents` being run without reading `docker_client.py` comments
- Docker sandbox creation errors mentioning `_build_docker_volume_mounts`, `Manifest`, or `DockerSandboxClientOptions`
- CI build succeeds but sandbox container creation fails at runtime

**Phase to address:** Phase 1 -- Pipeline Foundation. The CI check and test should be part of the PR validation pipeline.

---

### Pitfall 10: Not Having a Baseline Before Starting Optimization

**What goes wrong:**
You build the CI pipeline, run XBEN evaluation, get a 45% solve rate, and have NO IDEA whether this is good or bad. You spend weeks optimizing prompts and tool configurations, reach 52%, and declare success. But the pre-pipeline manual run (from `XBEN-SETUP-SUMMARY.md`, which showed v0.4.0 results: Level 1 100%, Level 2 96%, Level 3 75%) was measured with a DIFFERENT model, DIFFERENT scan mode, or DIFFERENT version of the code. You've been optimizing against a phantom regression.

**Why it happens:**
The existing XBEN v0.4.0 results (100%/96%/75% by difficulty) are from a different version of strix with unknown configuration. They're not reproducible. Without a reproducible baseline from the CURRENT codebase, every future comparison is meaningless. The runner gets built, the pipeline works, but nobody can answer "did this PR improve or regress strix's capability?"

**How to avoid:**
1. **Record a baseline run FIRST** -- before any pipeline automation, run the smoke-test subset manually with documented configuration (exact model, STRIX_LLM value, scan mode, Docker image version, commit SHA). Save the results as `BASELINE.md` in the repo.
2. **Pin ALL variables in the baseline**: model, temperature, max_turns, Docker image digest (not tag), strix version, date. These must be documented to make the baseline reproducible.
3. **Run the baseline on the SAME model** that will be used in CI evaluation. If CI uses DeepSeek for cost reasons, the baseline must also be DeepSeek. Comparing DeepSeek results to v0.4.0's (presumably frontier model) results is apples-to-oranges.
4. **Treat baseline as a regression test**: Every CI run compares against the baseline. A surprise drop from 45% to 32% on the smoke-test subset is a blocked merge.
5. **Accept that the baseline may be LOW**. The v0.4.0 numbers are likely with a more capable/expensive model. A 45% solve rate on DeepSeek may be the correct baseline. The important thing is tracking CHANGE over time, not the absolute number.

**Warning signs:**
- Referencing v0.4.0 XBEN results as the performance target without a CI reproduction
- No `BASELINE.md` or equivalent in the repository
- CI evaluation workflow has no expected-minimum-solve-rate check
- "We'll establish a baseline after the pipeline is working" (this is backwards -- the pipeline validates against the baseline)

**Phase to address:** Phase 1 -- Pipeline Foundation (baseline recording) and Phase 2 -- XBEN Runner Hardening (regression detection against baseline).

---

## Technical Debt Patterns

Shortcuts that seem reasonable during pipeline development but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding `max_workers=4` without making it configurable | One fewer CLI argument | Cannot tune for different runner hardware (2-core laptop vs 64-core CI) | If `XBEN_MAX_WORKERS` env var is added within the same phase |
| Using `subprocess.run("strix", ...)` without capturing stderr to a log | Simpler runner code | Impossible to debug why a challenge failed -- no agent trajectory, no LLM call logs | Only for the smoke-test subset; full evaluation MUST capture stderr |
| Skipping `--volumes` on `docker compose down` "because it works without it" | One fewer flag to type | Flag leakage (Pitfall 8), disk exhaustion from 104+ dangling volumes | Never for multi-challenge runs |
| Using the same `strix_runs/` base directory for all challenges without cleanup | Simpler output management | Run N's outputs contaminate run N+1's flag detection (Pitfall 8) | Never -- this is the root cause of flag leakage |
| Running the XBEN runner directly on the CI host (not containerized) | No Docker-in-Docker complexity | Host accumulates Docker state, makes cleanup harder, runner environment changes between runs | Only for local dev; never for CI |
| Not implementing checkpoint/restart in the first version | Faster initial delivery | A crashed run at challenge 98 loses ALL results. Must re-run all 104. | If `--shard` mode is implemented instead (multiple shorter jobs) |
| Copying `containers/Dockerfile` into PyInstaller build even though it's not used at runtime | One fewer `excludes` entry to maintain | Bloats binary by embedding a 225-line Dockerfile that will never be used | Never -- exclude it explicitly |

---

## Integration Gotchas

Specific mistakes when connecting the build pipeline with XBEN evaluation.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-----------------|
| **PyInstaller + Docker SDK** | The `docker` Python package imports `requests`, `urllib3`, and `websocket`. If PyInstaller misses any of these hidden imports, the binary crashes on `docker.from_env()`. | Add `docker`, `requests`, `urllib3`, `websocket`, `docker.transport`, `docker.api` to `hiddenimports` in `strix.spec`. Verify by running the binary on a Docker-less machine (should exit cleanly with "Docker not found," not a ModuleNotFoundError). |
| **XBEN runner + strix binary** | The evaluation runner calls `strix` via `subprocess.run()`. If `strix` is installed as a Python package (`pip install -e .`), the subprocess inherits the development environment. The runner works in dev but fails in CI. | In CI, use the compiled binary (PyInstaller output) as the `STRIX_BIN`. In local dev, `STRIX_BIN` defaults to the `strix` console script. Test both paths. |
| **Docker compose + strix sandbox** | The XBEN challenge runs on `docker compose` networks. Strix sandbox tries to reach `host.docker.internal:PORT`. On Docker Desktop for Windows, there's a multi-layer proxy (Windows -> WSL2 VM -> Docker bridge). New port mappings have a 2-5 second propagation delay. | Keep the existing `wait_for_target()` polling (from `run_infer_cli.py`) but also add a pre-scan connectivity check from within the sandbox: `docker exec strix-sandbox curl -s host.docker.internal:PORT`. Retry with backoff. |
| **CI secrets + LLM API keys** | The XBEN evaluation needs `LLM_API_KEY` and `PERPLEXITY_API_KEY` as environment variables. Storing them as GitHub Actions secrets and passing them to every job step makes them accessible to every subprocess -- including compromised challenge containers. | Pass secrets ONLY to the XBEN runner step, not the Docker compose step. Use `env:` at the step level, not the job level. Consider using `STRIX_LLM` with a dedicated evaluation API key that has spending limits and restricted permissions. |
| **GitHub Release artifacts + PyPI package** | Publishing to PyPI AND GitHub Releases creates two competing "official" distribution channels. Users installing via `pip install strix-agent` get a DIFFERENT version than users downloading the binary from GitHub Releases. | Decide: is the PyPI package the canonical distribution, or is the binary? Document this. For now: PyPI for `pip` users, GitHub Release for binary users. Both must report the same version string and the same capabilities. |
| **Docker sandbox image + CI cache** | The sandbox image is 7.38 GB. Pushing it to multiple registries (GHCR, Docker Hub) as cache layers creates enormous egress costs on CI. | Push cache layers to a single registry (GHCR, already used). For the actual release image, push only the final layer, not all intermediate stages. |

---

## "Looks Done But Isn't" Checklist

Things that appear complete during pipeline development but are missing critical production-readiness pieces.

- [ ] **Binary build works on Linux:** But does it work on Windows? The `strix.spec` was manually curated for Linux. Windows needs `pywin32`, different `hiddenimports`, and `--add-data` paths with `;` separator (not `:`).
- [ ] **XBEN runner completes all 104 challenges:** But were all flags verified? A challenge reporting "solved" because strix found a flag from the PREVIOUS challenge (Pitfall 8) is worse than unsolved -- it gives false confidence.
- [ ] **Docker compose down is called after each challenge:** But does it include `--volumes`? Without `--volumes`, shared volumes from challenge to challenge silently accumulate state.
- [ ] **CI job has a `timeout-minutes`:** But is it set below the GitHub Actions 360-minute hard limit? The job needs headroom for cleanup steps. Set to 300 minutes (5 hours) with a 30-minute post-job cleanup step.
- [ ] **LLM API key is stored as a GitHub secret:** But is it scoped to a dedicated evaluation API key with spending limits? Using the production key in CI risks cost explosion (Pitfall 3).
- [ ] **The smoke-test subset is defined:** But does it cover all difficulty levels and vulnerability types? A smoke test of 5 Level-1 challenges misses the real regressions (which happen on Level 2 and 3).
- [ ] **Docker daemon is running on the CI host:** But is it rootless? Standard Docker daemon runs as root. A container escape in the strix sandbox (7.38 GB of attack surface) becomes a CI host compromise.
- [ ] **The runner has cleanup logic:** But does cleanup run `if: always()`? Without this, cleanup is skipped on cancellation, timeout, or failure -- exactly when it's most needed.
- [ ] **Release workflow publishes all artifacts:** But does it verify them first? Publishing a binary that crashes on startup is worse than not publishing -- it wastes users' time and trust.
- [ ] **Version string is consistent:** But does `strix --version` in the compiled binary match `pyproject.toml` version and the Git tag? Test this in CI before creating the GitHub Release.

---

## Performance Traps

Patterns that work at small scale but fail when running 104 challenges sequentially.

| Trap | Symptoms | Prevention | Break Threshold |
|------|----------|------------|-----------------|
| **Sequential challenge execution with no parallelism** | 104 challenges x 15 min = 26 hours wall-clock time | ThreadPoolExecutor with `max_workers=4` for parallel challenge execution | Breaks at ~5 challenges (75 min -- too slow for PR feedback) |
| **Docker image pull before every challenge** | Each challenge pulls base images (`python:3.12-slim`, `node:18-alpine`) even if pulled by the previous challenge | Pre-pull common images before the challenge loop; use a local Docker registry cache on the runner | Breaks at ~10 challenges (adds 30-60 seconds pull time per challenge) |
| **Unbounded `strix_runs/` directory growth** | strix writes agent trajectories, tool outputs, and logs for every scan turn. Over 104 challenges, this can exceed 50 GB | Set `STRIX_LOG_LEVEL=WARNING` in CI (reduce log verbosity). Delete agent trajectory files after flag extraction. Only preserve `result.json` and the evaluation report. | Breaks at ~60 challenges on a 100 GB runner disk |
| **No `max_turns` limit on strix** | A single challenge can loop for 300 turns, consuming 30+ minutes. One stuck challenge blocks the entire queue. | Set `--max-turns 150` in CI evaluation mode. The point is to measure capability, not to wait indefinitely. Flag challenges that hit the turn limit as "timeout" not "unsolved." | Breaks at 1 stuck challenge (blocks all subsequent challenges in sequential mode) |
| **Docker Compose build per challenge** | Each challenge has its own Dockerfile. Building all 104 from scratch takes ~2-4 minutes per challenge | Pre-build common challenge images in a batch step before the evaluation loop. The XBEN challenges share base patterns (Python WSGI, Node.js Express, PHP Apache) -- these can be built once and cached. | Breaks at ~20 challenges (adds 40-80 minutes of build time) |
| **Docker network exhaustion** | Default Docker bridge network pool is 31 networks (172.17.0.0/16). Each `docker compose up` creates at least 1 network. | Expand pool to 255 networks via daemon.json. Clean up networks aggressively after each challenge. | Breaks at ~31 challenges |

---

## Security Mistakes

Beyond general CI security -- specific to running AI-driven security testing tool evaluation.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Running XBEN challenges on the same host as production services** | A challenge container with a real vulnerability (by design) could be exploited by an attacker who gains network access to the CI host | Run XBEN evaluation on an ISOLATED host or VM with no access to production networks, databases, or credentials |
| **Using the same LLM API key for evaluation and production** | If the evaluation runner logs the key, or if a challenge captures environment variables, the key is exposed | Create a DEDICATED LLM API key for evaluation with spending limits (e.g., $100/month cap) and restricted model access (evaluation-only models) |
| **Leaving strix sandbox images on the CI host** | A 7.38 GB Kali-based image with hundreds of security tools is a powerful attack platform. If an attacker gains access to the CI host, they have a pre-built penetration testing environment | Delete sandbox images from the runner after each job (`docker rmi strix-sandbox:*`). Re-pull on next run. Small cost in bandwidth, huge reduction in attack surface. |
| **Not auditing XBEN challenge source code before running in CI** | XBEN challenges are CTF applications with intentional vulnerabilities. A challenge could contain malicious code (crypto miners, reverse shells) disguised as a "vulnerable app." | Audit challenge source code before first CI run. Pin the challenge repository to a known-good commit SHA. Never auto-update challenges in CI. |
| **Logging full LLM responses in CI** | LLM responses may contain challenge flags, API keys echoed back, or sensitive target information | Scrub flags from CI logs. Use `STRIX_LOG_LEVEL=WARNING` to suppress verbose LLM call logging. Only log evaluation metrics (solved/unsolved/duration), not full agent trajectories. |
| **Exposing the Docker socket via `docker compose` port mappings** | A challenge's `docker-compose.yml` might map ports that conflict with Docker's own API port (2375/2376). | Audit all challenge compose files for port conflicts with system services before running. Rewrite port mappings to use high ephemeral ports (30000+). |

---

## UX Pitfalls (for developers using the pipeline)

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **One-click build script that requires 12 undocumented environment variables** | Developer runs `./build.sh`, gets "Error: STRIX_LLM not set," then "Error: LLM_API_KEY not set," then a Docker pull timeout. Abandons after 3 attempts. | Pre-flight checks at script start that validate ALL required variables and print a single summary of what's missing: "Missing: STRIX_LLM, LLM_API_KEY. Set these in .env or environment." |
| **CI failure with "Docker not found" and no explanation** | Developer pushed code, CI fails, error is `docker: command not found`. They waste time checking if Docker is installed, when the real issue is a self-hosted runner that wasn't configured. | Add explicit error messages for the CI context: "Docker not available on this runner. XBEN evaluation requires a self-hosted runner with Docker daemon. This workflow cannot run on GitHub-hosted runners." |
| **XBEN results table showing 0% solve rate because the model isn't configured** | Developer runs `python run_infer_cli.py`, sees 0/104 solved, thinks strix is broken. Actually, `STRIX_LLM` was set but `LLM_API_KEY` was empty -- every challenge failed at the LLM warm-up step. | Distinguish "evaluation error" (API key, Docker, network) from "challenge unsolved" (strix ran, didn't find flag). An ERROR column in the results table is more useful than lumping errors into UNSOLVED. |
| **`--limit 1` takes 45 minutes because it picks the first challenge alphabetically (which happens to be a hard one)** | Developer wants a quick smoke test, gets blocked for 45 minutes. | Sort challenges by difficulty (Level 1 first) for `--limit N`. Or provide `--difficulty easy` filter. The quick validation path should always use the easiest challenges. |

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Pitfall 1: Docker socket compromise** | VERY HIGH | Rotate ALL credentials on the CI host (GITHUB_TOKEN, GHCR_PAT, LLM_API_KEY, SSH keys, cloud credentials). Rebuild runner from scratch. Audit all GitHub Actions logs for credential exfiltration patterns (outbound connections to unknown IPs). Run `step-security/harden-runner` forensics report. |
| **Pitfall 2: Resource starvation** | MEDIUM | SSH into runner. Run `docker system prune -a -f --volumes` (only if this is a dedicated runner with no other jobs!). Expand network pool in daemon.json. Restart Docker daemon. Pre-flight cleanup (see Pitfall 2 prevention) handles this automatically. |
| **Pitfall 3: LLM API cost explosion** | LOW-MEDIUM | Immediately revoke the evaluation API key. Review LLM provider dashboard for total spend. If within acceptable range, rotate key and re-enable with stricter limits. If excessive, contact provider for potential credit. Implement budget enforcement BEFORE re-enabling CI. |
| **Pitfall 4: 6-hour timeout** | MEDIUM | Results from completed challenges are valid (they completed before SIGKILL). Results from the interrupted challenge are lost. Re-run using shard mode, starting from the first uncompleted challenge. Delete partial results from the interrupted challenge. |
| **Pitfall 8: Flag leakage** | HIGH | ALL results from the affected run are suspect. Delete all results. Fix the `--volumes` flag and project naming. Re-run full evaluation. Add a flag uniqueness validator to the results processing pipeline. |
| **Pitfall 9: SDK upgrade breaks Docker client** | MEDIUM | Revert the SDK version in `pyproject.toml`. Re-merge `_create_container` from the NEW SDK version into `docker_client.py`. Update the pin comment. Run the container-creation test. Re-release. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Pitfall 1: Docker socket escape | Phase 1 -- Pipeline Foundation | Confirm self-hosted runner uses rootless Docker; confirm ephemeral runner lifecycle; confirm `pull_request` from forks does NOT trigger XBEN evaluation |
| Pitfall 2: Cleanup failure | Phase 1 -- Pipeline Foundation | Run 3 consecutive XBEN smoke-test runs; confirm zero orphaned containers/networks/volumes after each |
| Pitfall 6: Version drift | Phase 1 -- Pipeline Foundation | Create a test release; verify `strix --version`, Docker image label, Git tag, and `pyproject.toml` all match |
| Pitfall 7: Cache busting | Phase 1 -- Pipeline Foundation | Run CI build twice on same commit; second run must show CACHED layers and complete in <5 minutes |
| Pitfall 9: SDK pin break | Phase 1 -- Pipeline Foundation | CI check that verifies `docker_client.py` pin comment matches installed `openai-agents` version |
| Pitfall 10: No baseline | Phase 1 (recording) & Phase 2 (regression) | `BASELINE.md` exists with exact model, mode, commit SHA, solve rate; CI smoke-test compares against it |
| Pitfall 3: Cost explosion | Phase 2 -- XBEN Runner Hardening | `XBEN_MAX_COST_PER_RUN` env var enforced; smoke-test subset costs <$5 per run; budget-tracking dashboard configured |
| Pitfall 4: 6-hour limit | Phase 2 -- XBEN Runner Hardening | `--shard` argument accepted by runner; CI matrix splits challenges across shards; each shard completes in <5 hours |
| Pitfall 8: Flag leakage | Phase 2 -- XBEN Runner Hardening | Run two consecutive challenges known to use similar tech stack; verify flags are NOT cross-contaminated; `--volumes` flag present on every `docker compose down` |
| Pitfall 5: PyInstaller cross-platform | Phase 3 -- Cross-Platform Hardening | Windows runner in CI matrix; Windows `.exe` smoke-tested on clean Windows VM; `warn-*.txt` shows only known-safe false positives |

---

## Sources

### Direct codebase observation (confidence: HIGH):
- `strix/runtime/docker_client.py` -- SDK pinning comment (lines 19-21), NET_ADMIN/NET_RAW injection (lines 107-108), host-gateway extra_hosts (line 112), verbatim SDK body copy (lines 56-100)
- `strix/config/settings.py` -- STRIX_IMAGE default, LLM settings, environment variable alias chains
- `strix/interface/main.py` -- Docker hard dependency (`check_docker_installed()` → `sys.exit(1)`)
- `strix/report/state.py` -- LiteLLM cost tracking callback (global)
- `.planning/BUILD-SESSION.md` -- containerd compatibility issue, Docker Desktop Windows HTTP proxy failures, Linux ELF vs Windows `.exe` binary format incompatibility
- `.planning/XBEN-SETUP-SUMMARY.md` -- DeepSeek tool_call format error (Section 6, Problem 3), Docker Desktop port forwarding delay (Section 6, Problem 5), output directory name mismatch (Section 6, Problem 4), flag leakage from missing `--volumes` (Section 6, Problem 5 context)
- `.planning/codebase/CONCERNS.md` -- zero automated tests (Critical), SDK pinning medium severity, missing CI quality gates, Docker dependency coupling
- `xben-benchmarks/XBEN/run_infer_cli.py` -- strix subprocess invocation, flag detection logic, `docker compose down` without `--volumes`

### Web research (confidence: MEDIUM, cross-referenced across multiple sources):
- PyInstaller official documentation -- cross-platform build requirements, `--hidden-import`, `.spec` file platform awareness, `warn-*.txt` diagnostics. https://pyinstaller.org/en/stable/when-things-go-wrong.html
- CVE-2025-32955 (April 2025) -- Docker group privilege escalation bypassing `disable-sudo` policy. Affected step-security/harden-runner. https://github.com/step-security/harden-runner/security/advisories/GHSA-mxr3-8whj-j74r
- TeamPCP Cascade (March 2026) -- Supply chain attack compromising CI/CD workflows including LiteLLM, Trivy, and 60+ npm packages. 10,000+ workflows affected.
- tj-actions/changed-files (March 2025) -- Compromised GitHub Action used by 23,000+ repositories exfiltrating runner memory and secrets. CISA advisory.
- Docker layer caching in CI -- GHA cache 10 GB limit, `mode=max` export bottleneck (67% of build time), `build-push-action` v6.4.0 regression, registry cache as alternative to GHA cache. https://github.com/docker/build-push-action/discussions/943
- GitHub Actions 6-hour job timeout -- hard limit on GitHub-hosted runners, no limit on self-hosted. Job sharding via matrix strategy as workaround. https://github.com/orgs/community/discussions/108006
- AIRTBench paper -- LLM API rate limiting impacts across models (Claude 16.4% error rate at 46.9% solve rate, Gemini 38.1% at 34.3%). Cost scaling concerns for batch evaluation.
- picoCTF/docker-reaper -- CTF-specific Docker resource reaper for time-based cleanup. https://github.com/picoCTF/docker-reaper
- StepSecurity Harden-Runner -- Runtime security monitoring for self-hosted runners, egress filtering, `disable-sudo-and-containers` policy.

### Known XBEN historical context from documentation:
- XBEN v0.4.0 solve rates: Level 1 100% (45/45), Level 2 96% (49/51), Level 3 75% (6/8) -- from `.planning/XBEN-SETUP-SUMMARY.md` Section 1.2. These were achieved with an unknown model and configuration, making them unreliable as a performance target.

---

*Pitfalls research for: Adding CI/CD build pipeline and XBEN automated benchmarking to Strix*
*Researched: 2026-06-17*
