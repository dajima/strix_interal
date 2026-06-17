# Roadmap: Strix v1.0

**Created:** 2026-06-17
**Granularity:** Standard (compressed to 2 phases -- two independent tracks)
**Total phases:** 2
**Requirements covered:** 11/11 (100%)

## Phases

- [ ] **Phase 1: Build & Release Pipeline** -- One-click build scripts, version coherence, Docker Compose deployment, and GitHub Release automation
- [ ] **Phase 2: XBEN Evaluation Runner** -- CLI-driven challenge filtering, reliable Docker lifecycle, and structured pass/fail reporting by difficulty and vulnerability type

## Phase Details

### Phase 1: Build & Release Pipeline
**Goal:** Developers can build strix binaries and Docker sandbox images with a single command, deploy via Docker Compose, and publish releases to GitHub with one click -- all versioned from a single source of truth.

**Depends on:** Nothing (no prior phases)

**Requirements:** BUILD-01, BUILD-02, BUILD-03, BUILD-04, BUILD-05, BUILD-06

**Success Criteria** (what must be TRUE):
1. Developer can run a single command to compile the strix Linux binary via PyInstaller -- no manual Docker invocation or environment setup needed
2. Developer can run a single command to build the Docker sandbox image with the correct version tag
3. Version number in the binary (--version), Docker image tag, Git tag, and pyproject.toml are identical -- no manual version string updates across files
4. User can deploy and run strix on any machine with Docker by running `docker compose up` from the project root or downloaded docker-compose.yml
5. Maintainer can trigger a full release from the GitHub Actions UI (workflow_dispatch) that produces a GitHub Release containing the Linux binary, docker-compose.yml, and checksums file

**Plans:** TBD

### Phase 2: XBEN Evaluation Runner
**Goal:** Developers and reviewers can run automated benchmark evaluations against strix -- selecting challenge subsets by difficulty, tags, or count -- with reliable Docker cleanup between runs and structured pass/fail reports broken down by difficulty tier and vulnerability type.

**Depends on:** Phase 1 (requires a built strix binary to evaluate; Docker Compose deployment for challenge environments)

**Requirements:** XBEN-01, XBEN-02, XBEN-03, XBEN-04, XBEN-05

**Success Criteria** (what must be TRUE):
1. User can filter the 104-challenge benchmark set by difficulty level (--level), vulnerability tags (--tags), and maximum count (--limit) from the CLI
2. User receives a pass/fail summary report broken down by difficulty tier (Easy/Medium/Hard) showing solve rates per tier
3. User receives a pass/fail summary report broken down by vulnerability type showing which vulnerability classes strix detects reliably
4. After each challenge run completes (success or failure), no orphaned Docker containers, networks, or volumes remain on the host -- verified by running the full benchmark suite without resource accumulation
5. User can inspect a structured JSON results file containing per-challenge pass/fail status, elapsed time, and discovered flags for every challenge executed
6. User can open a formatted Markdown report with summary statistics, difficulty breakdown, vulnerability-type breakdown, and timing data

**Plans:** TBD
**UI hint:** yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Build & Release Pipeline | 0/0 | Not started | - |
| 2. XBEN Evaluation Runner | 0/0 | Not started | - |
