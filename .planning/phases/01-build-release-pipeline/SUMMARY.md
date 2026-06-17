---
phase: 01-build-release-pipeline
plan: 01
subsystem: infra
tags: [bash, docker, pyinstaller, github-actions, ci-cd]

requires: []

provides:
  - "build_script/version.sh — Single-source version extraction from pyproject.toml"
  - "build_script/build-binary.sh — One-command strix binary compilation via Docker"
  - "build_script/build-sandbox.sh — One-command Docker sandbox image build + push"
  - ".github/workflows/build-release.yml — Dual-trigger CI producing GitHub Release artifacts"

affects:
  - Phase 2 (XBEN Evaluation Runner needs built binary + sandbox image)

tech-stack:
  added: []
  patterns:
    - "Standalone bash scripts in build_script/ (NO Makefile targets)"
    - "Version sourced from pyproject.toml via shared version.sh (single source of truth)"
    - "Linux + Windows only (no macOS)"
    - "Docker Hub for sandbox image (usestrix/strix-sandbox)"

key-files:
  created:
    - build_script/version.sh
    - build_script/build-binary.sh
    - build_script/build-sandbox.sh
  modified:
    - .github/workflows/build-release.yml

key-decisions:
  - "D-01: Build scripts in build_script/ not scripts/build/"
  - "D-02: Standalone bash scripts, no unified entry point, no Makefile targets"
  - "D-03: Binary built via Docker container (Dockerfile.build)"
  - "D-05: Output to dist/ flat directory with version-embedded filenames"
  - "D-07: Linux + Windows only, NO macOS"
  - "D-08: Docker Hub usestrix/strix-sandbox, not ghcr.io"
  - "D-09: Dual trigger: workflow_dispatch + push tags: v*"
  - "D-10: GitHub Release includes .tar.gz (Linux), .zip (Windows), checksums.txt"

requirements-completed: ["BUILD-01", "BUILD-02", "BUILD-03", "BUILD-05", "BUILD-06"]

duration: 15 min
completed: 2026-06-17
---

# Phase 01 Plan 01: Build & Release Pipeline Summary

**Three standalone build scripts in build_script/ plus updated CI workflow -- one-command binary and sandbox image builds, version-coherent from pyproject.toml, with dual-trigger GitHub Release automation.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-17
- **Completed:** 2026-06-17
- **Tasks:** 4
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments
- Single-source version extraction via `build_script/version.sh` -- sources from `pyproject.toml`, used by all build scripts
- Docker-based binary compilation via `build_script/build-binary.sh` -- builds strix inside `Dockerfile.build` container, outputs to `dist/` with version-embedded filenames
- Sandbox image build via `build_script/build-sandbox.sh` -- builds `usestrix/strix-sandbox` from `containers/Dockerfile`, tags both `:latest` and `:{VERSION}`, optional `--push` to Docker Hub
- CI workflow updated to Linux+Windows matrix, Docker-based Linux build, sandbox push job, checksums.txt generation, and proper dual-trigger release

## Task Commits

1. **Task 1.1: version.sh** -- `5b1dc9f` (feat)
2. **Task 1.2: build-binary.sh** -- `51f9945` (feat)
3. **Task 1.3: build-sandbox.sh** -- `b252b0b` (feat)
4. **Task 2.1: CI workflow** -- `30a379b` (feat)

## Files Created/Modified
- `build_script/version.sh` -- Extracts STRIX_VERSION from pyproject.toml, sourced by other build scripts
- `build_script/build-binary.sh` -- Builds strix binary via Dockerfile.build container, outputs versioned binary + archive to dist/
- `build_script/build-sandbox.sh` -- Builds usestrix/strix-sandbox image with version and latest tags, optional --push
- `.github/workflows/build-release.yml` -- Updated: removed macOS, added Docker-based Linux build, sandbox push job, checksums.txt

## Decisions Made
- Followed all locked decisions (D-01 through D-10) exactly as specified
- Used the existing grep+sed version extraction pattern from `scripts/build.sh` for consistency
- CI Linux build uses Docker inline rather than calling `build-binary.sh` directly, since the CI runner has Docker available
- CI sandbox job calls `build_script/build-sandbox.sh --push` directly per D-04
- Windows CI build retains local uv+pyinstaller approach since Dockerfile.build is Linux-only

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None. All acceptance criteria passed on first attempt.

## Next Phase Readiness
- Phase 1 complete -- build infrastructure ready
- Phase 2 (XBEN Evaluation Runner) can proceed: binary compilation and sandbox image build are automated
- CI will produce release artifacts on tag push or workflow_dispatch
- Docker Hub credentials (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`) must be configured as GitHub Secrets before first release

---
*Phase: 01-build-release-pipeline*
*Completed: 2026-06-17*
