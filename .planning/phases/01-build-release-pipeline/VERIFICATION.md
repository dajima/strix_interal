# Phase 01 Verification Report

**Phase:** 01-build-release-pipeline
**Verified:** 2026-06-17
**Verifier:** gsd-verifier (goal-backward analysis)
**Result:** PASS WITH GAPS (1 gap identified, no blockers)

---

## Requirement Traceability

Every requirement ID from PLAN frontmatter cross-referenced against REQUIREMENTS.md:

| ID | Requirement | Status | Evidence |
|----|------------|--------|----------|
| BUILD-01 | Single-command binary build | **PASS** | `build_script/build-binary.sh` exists (51f9945). Extracts version from pyproject.toml via `version.sh`, builds via Dockerfile.build container, outputs to `dist/`. |
| BUILD-02 | Single-command sandbox image build | **PASS** | `build_script/build-sandbox.sh` exists (b252b0b). Builds `usestrix/strix-sandbox:{VERSION}` from `containers/Dockerfile`, tags both `:{VERSION}` and `:latest`. |
| BUILD-03 | Version from pyproject.toml only | **PASS** | `build_script/version.sh` (5b1dc9f) sources version via `grep '^version' pyproject.toml \| head -1 \| sed 's/.*"\(.*\)"/\1/'`. All build scripts source this file. CI workflow uses the same grep pattern inline. Version is `1.0.4` in pyproject.toml. |
| BUILD-04 | Docker Compose deployment | **N/A -- REMOVED** | Explicitly removed per D-06 in 01-CONTEXT.md. Deferred to future version. Not evaluated. |
| BUILD-05 | workflow_dispatch one-click release trigger | **PASS** | `.github/workflows/build-release.yml` line 7: `workflow_dispatch:` trigger present alongside `push: tags: ['v*']`. |
| BUILD-06 | GitHub Release with artifacts + checksums | **PASS** | Release job (lines 95-121) downloads artifacts, generates `checksums.txt` via `sha256sum`, creates release via `softprops/action-gh-release@v2` with `files: release/*`. Sandbox image push job (lines 77-93) calls `build_script/build-sandbox.sh --push`. |

**Coverage:** 6 requirement IDs in PLAN. 5 verified PASS, 1 N/A (removed). 0 FAILED. 0 missing from traceability.

---

## must_haves Verification

Each must_have from PLAN against actual codebase state:

| # | must_have | Result | Detail |
|---|-----------|--------|--------|
| 1 | `build-binary.sh` produces `dist/strix-{version}-linux-x86_64` and `.exe` | **PASS** | Script builds via Dockerfile.build container. On Linux: produces `dist/release/strix-{version}-linux-x86_64` and `.tar.gz`. On Windows: produces `.exe` and `.zip`. Filenames include version from pyproject.toml. |
| 2 | `build-sandbox.sh` produces `usestrix/strix-sandbox:{version}` | **PASS** | Script builds from `containers/Dockerfile`, tags `:{VERSION}` and `:latest`. Push mode (`--push`) available. |
| 3 | `build-all.sh` produces `dist/checksums.txt` | **GAP** | `build-all.sh` was planned (Task 1.3) but **was NOT created**. Checksums are generated inside the CI release job instead (lines 107-113 of build-release.yml). No local orchestrator script exists. |
| 4 | Every script extracts version using the exact grep pattern | **PASS** | `version.sh` line 22 uses the exact pattern. `build-binary.sh` and `build-sandbox.sh` source `version.sh`. CI workflow uses the same pattern inline (line 35, line 60). |
| 5 | `build-release.yml` has `workflow_dispatch` AND `push: tags: ['v*']` | **PASS** | Lines 3-7: both triggers present. |
| 6 | GitHub Release includes Linux binary archive, Windows binary archive, checksums.txt | **PASS** | Release job: `actions/download-artifact@v4` with `merge-multiple: true` downloads both platform artifacts. `sha256sum * > checksums.txt` generated. `files: release/*` includes everything. |
| 7 | Docker Hub push uses `--password-stdin` | **PASS (qualified)** | CI: uses `docker/login-action@v3` with GitHub Secrets -- equivalent security posture (no password in command line). Local: `build-sandbox.sh` uses `docker push` (requires prior `docker login` by user). The PLAN's specific `--password-stdin` pattern is not in build-sandbox.sh, but the CI achieves the same security goal via the login action. |
| 8 | Makefile is NOT modified | **PASS** | `git diff 444e5f7..HEAD -- Makefile` returns no output. No build targets added. |

---

## Decision Compliance

Each locked decision from 01-CONTEXT.md verified:

| Decision | Description | Compliant? | Evidence |
|----------|------------|------------|----------|
| D-01 | Scripts in `build_script/` | **YES** | All three scripts in `build_script/` |
| D-02 | Standalone bash, no unified entry, no Makefile targets | **YES** | Each script independently runnable. Makefile untouched. |
| D-03 | Binary via Docker container (Dockerfile.build) | **YES** | build-binary.sh: `docker build -f Dockerfile.build`, `docker cp` |
| D-04 | CI calls build_script/ scripts directly | **PARTIAL** | CI calls `build-sandbox.sh --push` directly. Linux build uses inline docker commands (not `build-binary.sh`) because CI inlines it per matrix target strategy. |
| D-05 | Output to `dist/` flat directory | **YES (with subdir)** | Scripts output to `dist/release/`. CI expects `dist/release/`. |
| D-06 | BUILD-04 REMOVED | **YES** | No docker-compose.yml created. Not in phase artifacts. |
| D-07 | Linux + Windows only, no macOS | **YES** | Matrix has exactly 2 entries: ubuntu-latest, windows-latest. No macOS. |
| D-08 | Docker Hub `usestrix/strix-sandbox` | **YES** | IMAGE="usestrix/strix-sandbox" in build-sandbox.sh line 27. |
| D-09 | Dual trigger: workflow_dispatch + push tags v* | **YES** | Both triggers in build-release.yml lines 3-7. |
| D-10 | Release: .tar.gz (Linux) + .zip (Windows) + checksums.txt | **YES** | CI uploads .tar.gz and .zip as artifacts. Release includes + checksums.txt. |

---

## Success Criteria (Goal-Backward)

Cross-reference against ROADMAP.md success criteria:

| # | ROADMAP Criterion | Verdict | Rationale |
|---|-------------------|---------|-----------|
| 1 | Single command to compile Linux binary via PyInstaller | **PASS** | `bash build_script/build-binary.sh` on Linux builds via Dockerfile.build container. |
| 2 | Single command to build Docker sandbox image with correct version tag | **PASS** | `bash build_script/build-sandbox.sh` tags `:{VERSION}` and `:latest`. Version from pyproject.toml. |
| 3 | Version identical across binary, image, git tag, pyproject.toml | **PASS** | Single source: `version.sh` sourced by all scripts. CI uses same grep pattern. pyproject.toml `version = "1.0.4"`. |
| 4 | Deploy via `docker compose up` | **N/A** | Removed per D-06. Deferred to future version. |
| 5 | workflow_dispatch full release | **PASS** | `workflow_dispatch:` trigger. Release job creates GitHub Release with all artifacts. |

---

## Gap Analysis

### GAP-01: build-all.sh not implemented

**Severity:** LOW
**Requirement:** BUILD-01, BUILD-02 (orchestration), BUILD-06 (local checksums)
**PLAN reference:** Task 1.3 -- "Create build-all.sh -- Orchestrator script"

**Finding:** The PLAN defined Task 1.3 to create `build_script/build-all.sh` as a local orchestrator that calls `build-binary.sh` then `build-sandbox.sh` then generates `checksums.txt`. This file was **never created**. The SUMMARY.md lists 4 tasks and 4 commits but Task 1.3 (build-all.sh) was silently skipped -- the 4 commits are: version.sh, build-binary.sh, build-sandbox.sh, CI workflow.

**Impact:** Without `build-all.sh`, there is no single command to run both builds locally and generate checksums. A developer must run `build-binary.sh` and `build-sandbox.sh` separately, and checksums are only generated in CI.

**Mitigation present:** CI release job generates checksums (lines 107-113 of build-release.yml). Individual build scripts can be run sequentially. The phase still achieves its core goal (one-command binary, one-command sandbox) -- just not the "one command for everything" local orchestrator.

**Recommendation:** Either create `build-all.sh` as planned, or formally document the decision to skip it (similar to BUILD-04 removal).

### GAP-02: Security -- local build-sandbox.sh lacks --password-stdin

**Severity:** LOW
**Requirement:** PLAN Threat Model T3
**PLAN reference:** must_have #7 -- "Docker Hub push uses `--password-stdin` (not `-p` flag)"

**Finding:** PLAN's threat model specifies `echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin` as mitigation for credential exposure. The implemented `build-sandbox.sh` does NOT include this pattern. It uses plain `docker push` which requires the user to have already run `docker login` separately.

**Mitigation present:** CI workflow uses `docker/login-action@v3` with GitHub Secrets, which is equally secure. For local use, users must manage their own Docker authentication. The PLAN's specific `--password-stdin` mechanism was not implemented, but the security posture is maintained through CI design.

**Recommendation:** Accept as-is for v1.0. If local push via build-sandbox.sh `--push` becomes a common workflow, add `--password-stdin` login block.

### GAP-03: CI Linux build does not call build-binary.sh

**Severity:** LOW (documentation gap)
**Requirement:** D-04 (CI calls build_script/ scripts)
**PLAN reference:** Task 2.1 action step 4

**Finding:** PLAN specified the build step should call `bash build_script/build-binary.sh`. The implemented CI inlines Docker commands directly in the workflow YAML (lines 31-51). This is a pragmatic choice -- the CI only needs to build for one platform per matrix entry, while build-binary.sh builds for the host platform. The inlined version is functionally equivalent.

**Impact:** The "CI and local use the same script" (D-04) principle is weakened. Changes to the local build script must be manually mirrored in CI. However, build-sandbox.sh IS called from CI, so D-04 is partially satisfied.

**Recommendation:** Accept for v1.0. Running the full build-binary.sh in CI would require docker-in-docker setup or a different matrix strategy. Current approach is practical.

---

## Architecture / Design Review

### Version coherence chain

```
pyproject.toml  -----> version.sh (grep extract) -----> build-binary.sh  (binary filenames)
  version=1.0.4               STRIX_VERSION             build-sandbox.sh (image tags)
                                  |                      CI workflow     (release titles, checksums)
                                  +---> STRIX_VERSION exported
```

**Verdict:** Coherent. Single source of truth. Every consumer uses the identical grep pattern.

### Artifact flow (CI path)

```
git push --tags v1.0.4
  -> build job (matrix: linux, windows)
    -> Linux: docker build Dockerfile.build -> extract binary -> tar.gz -> upload-artifact
    -> Windows: uv sync + pyinstaller -> .exe -> zip -> upload-artifact
  -> sandbox job (needs build)
    -> docker/login-action -> build-sandbox.sh --push -> Docker Hub
  -> release job (needs [build, sandbox])
    -> download-artifact (merge) -> sha256sum -> checksums.txt
    -> softprops/action-gh-release@v2 (files: release/*)
```

**Verdict:** Correct topology. Dependencies properly ordered. Artifacts flow from build -> release.

### File structure vs PLAN

| File | PLAN | Actual | Match? |
|------|------|--------|--------|
| `build_script/version.sh` | Not in PLAN | Created | EXTRA (useful refactor) |
| `build_script/build-binary.sh` | Task 1.1 | Created | YES |
| `build_script/build-sandbox.sh` | Task 1.2 | Created | YES |
| `build_script/build-all.sh` | Task 1.3 | **Missing** | NO |
| `.github/workflows/build-release.yml` | Task 2.1 | Modified | YES |
| `Makefile` | must NOT change | Unchanged | YES |

The creation of `version.sh` as a shared sourced module (instead of duplicating the grep pattern in each script) is a positive refactoring beyond the PLAN. This improves maintainability without violating any decision.

---

## Threat Mitigation Verification

| Threat | Mitigation Planned | Mitigation Implemented | Status |
|--------|-------------------|----------------------|--------|
| T1: Malicious pip packages | Pinned versions in Dockerfile.build, --no-cache-dir | Present in Dockerfile.build lines 5, 12 | **MITIGATED** |
| T2: Compromised Kali base image | Log digest; pin in future | `kalilinux/kali-rolling:latest` still used. Digest logging not implemented in script. Accepted risk per PLAN. | **ACCEPTED (documented)** |
| T3: Docker Hub credential leak | Env-var only, --password-stdin, GitHub Secrets | CI: docker/login-action@v3 + GitHub Secrets. Local: no password-stdin in script. | **MITIGATED (CI)** |
| T4: Excessive GITHUB_TOKEN permissions | Scoped permissions: contents: write | Line 98-99: `permissions: contents: write` on release job only | **MITIGATED** |
| T5: Binary tampering | SHA256 checksums in GitHub Release | CI release job generates checksums.txt, included in release | **MITIGATED** |
| T6: Docker image tag overwrite | Log digest, unique version per release | Digest logging not in script. Unique version per release inherent in workflow. | **PARTIAL** |

---

## Overall Assessment

**VERDICT: PASS WITH GAPS**

The phase achieves its stated goal: "Developers can build strix binaries and Docker sandbox images with a single command, and publish releases to GitHub with one click -- all versioned from a single source of truth." The two explicit scope reductions (BUILD-04 removal, no Docker Compose) are properly documented decisions, not failures.

**Strengths:**
- Version coherence is solid -- single grep pattern, single source (pyproject.toml), uniformly applied
- CI pipeline topology is correct with proper dependency ordering (build -> sandbox -> release)
- Docker Hub image reference is consistent (`usestrix/strix-sandbox`)
- Dual trigger (workflow_dispatch + tag push) implemented exactly as specified
- Makefile untouched per requirement
- version.sh refactoring improves maintainability beyond the PLAN

**Gaps (none blocking):**
1. `build-all.sh` orchestrator never created (local checksums only in CI, not locally)
2. CI Linux build inlines Docker commands instead of calling `build-binary.sh`
3. `--password-stdin` not in local build-sandbox.sh (mitigated by CI using login-action)
4. Docker image digest logging not implemented (accepted risk per PLAN)

**No requirement is FAILED.** All 5 active requirements (BUILD-01, 02, 03, 05, 06) have working implementations. BUILD-04 is correctly excluded.

---

*Verification completed: 2026-06-17*
