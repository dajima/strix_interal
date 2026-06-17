---
phase: 01-build-release-pipeline
plan: 01
subsystem: infra
tags: [bash, docker, pyinstaller, github-actions, ci-cd]

requires: []

provides:
  - "build_script/build-binary.sh — One-command strix binary compilation via Docker"
  - "build_script/build-sandbox.sh — One-command Docker sandbox image build + push"
  - "build_script/version.sh — Single-source version extraction from pyproject.toml"
  - ".github/workflows/build-release.yml — Dual-trigger CI producing GitHub Release artifacts"

affects:
  - Phase 2 (XBEN Evaluation Runner needs built binary + sandbox image)

tech-stack:
  added: []
  patterns:
    - "Standalone bash scripts in build_script/ (NO Makefile targets)"
    - "Version sourced from pyproject.toml (single source of truth)"
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
---

# Phase 01 Plan 01: Build & Release Pipeline

**Goal:** Create standalone bash build scripts and CI configuration so developers can build strix binaries and Docker sandbox images with one command, versioned from a single source of truth (`pyproject.toml`), publishing releases to GitHub.

## Tasks

---

<task id="1.1" type="auto">

### Task 1.1: build_script/version.sh -- Single-source version extractor

**Context:** Every build script needs the project version. Rather than duplicating `grep + sed` in each script, extract the version from `pyproject.toml` once in a shared utility. BUILD-03 requires version from pyproject.toml as the single source of truth.

<read_first>
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/pyproject.toml
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/scripts/build.sh
</read_first>

**Create:** `build_script/version.sh`

**Specification:**
- Sourced by other scripts (not executed directly) -- `source "$(dirname "${BASH_SOURCE[0]}")/version.sh"`
- Extracts version from `pyproject.toml` using grep+sed (same pattern as existing `scripts/build.sh` line 45)
- Sets `STRIX_VERSION` variable
- Validates that a version was found; exits with error if not
- Resolves PROJECT_ROOT relative to script location: `$(cd "$SCRIPT_DIR/.." && pwd)`

**Pattern to follow (from scripts/build.sh line 45):**
```bash
VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
```

<acceptance_criteria>
1. `bash -c 'SCRIPT_DIR="$(cd "$(dirname "build_script/version.sh")" && pwd)"; source build_script/version.sh; echo "$STRIX_VERSION"'` outputs a non-empty version string matching pyproject.toml
2. Running `source build_script/version.sh` from project root sets STRIX_VERSION correctly
3. If pyproject.toml has no version line, script exits with non-zero status and prints error
</acceptance_criteria>

</task>

---

<task id="1.2" type="auto">

### Task 1.2: build_script/build-binary.sh -- Build strix binary via Docker

**Context:** BUILD-01 requires a single-command build. D-03 specifies building via Docker container using `Dockerfile.build` (not local Python env). D-05 specifies output to `dist/` with version-embedded filenames. D-07 specifies Linux + Windows only.

The existing `scripts/build.sh` builds locally with `uv`. We need a Docker-based build script that:
1. Sources `version.sh` for the version
2. Runs `docker build -f Dockerfile.build` to compile the binary inside a container
3. Extracts the binary to `dist/` with version-embedded filenames
4. Creates archives: `.tar.gz` for Linux, `.zip` for Windows

<read_first>
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/build_script/version.sh (AFTER task 1.1 is complete)
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/Dockerfile.build
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/scripts/build.sh
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/scripts/docker.sh
</read_first>

**Create:** `build_script/build-binary.sh`

**Specification:**
- `#!/bin/bash` with `set -euo pipefail`
- Sources `version.sh` to get `STRIX_VERSION`
- Detects host OS (Linux/MINGW*/MSYS*/CYGWIN*) for platform-appropriate output
- Builds Docker image from `Dockerfile.build` with tag `strix-builder:latest`
- Runs container to copy binary out: `docker run --rm -v dist:/output strix-builder:latest cp /output/strix /output/`
- Alternative approach: use `docker cp` after running the container
- Cleans up intermediate builder container
- Output naming:
  - Linux: `dist/strix-{VERSION}-linux-x86_64` + `dist/strix-{VERSION}-linux-x86_64.tar.gz`
  - Windows: `dist/strix-{VERSION}-windows-x86_64.exe` + `dist/strix-{VERSION}-windows-x86_64.zip`
- Color-coded output (GREEN success, RED error, YELLOW warnings, BLUE steps) -- matching scripts/build.sh style
- Exits with error if Docker not available, build fails, or binary not found after build

**Platform note for Windows builds:** Windows cross-compilation via PyInstaller in Docker is not feasible. The Windows build path is documented in the script but will error with a clear message: "Windows binary must be built on a Windows host. Run this script on Windows to produce a .exe."

On Linux host: only produce Linux binary + tarball. On Windows host: only produce Windows binary + zip.

<acceptance_criteria>
1. On Linux: `bash build_script/build-binary.sh` produces `dist/strix-{VERSION}-linux-x86_64` and `dist/strix-{VERSION}-linux-x86_64.tar.gz`
2. Binary is executable (`chmod +x` applied)
3. `dist/strix-{VERSION}-linux-x86_64 --version` outputs version matching `pyproject.toml`
4. On Windows: `bash build_script/build-binary.sh` produces `dist/strix-{VERSION}-windows-x86_64.exe` and `dist/strix-{VERSION}-windows-x86_64.zip`
5. Script exits non-zero with clear error if Docker is not available
6. Script cleans up intermediate Docker resources (builder container removed)
</acceptance_criteria>

</task>

---

<task id="1.3" type="auto">

### Task 1.3: build_script/build-sandbox.sh -- Build Docker sandbox image

**Context:** BUILD-02 requires a single-command build of the Docker sandbox image. D-08 requires pushing to Docker Hub (`usestrix/strix-sandbox`), not ghcr.io. The sandbox image is built from `containers/Dockerfile`.

The existing `scripts/docker.sh` builds the image with a simple `docker build` command. We need a similar script in `build_script/` that sources version.sh and manages tags properly.

<read_first>
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/build_script/version.sh (AFTER task 1.1 is complete)
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/containers/Dockerfile
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/scripts/docker.sh
</read_first>

**Create:** `build_script/build-sandbox.sh`

**Specification:**
- `#!/bin/bash` with `set -euo pipefail`
- Sources `version.sh` to get `STRIX_VERSION`
- Image name: `usestrix/strix-sandbox` (per D-08)
- Tags: `latest` and `{VERSION}` (e.g., `usestrix/strix-sandbox:1.0.4` and `usestrix/strix-sandbox:latest`)
- Usage: `bash build_script/build-sandbox.sh [--push]`
- Without `--push`: only builds locally with both tags
- With `--push`: builds then runs `docker push` for both tags
- Respects Docker build context from project root
- Color-coded output (GREEN success, RED error, YELLOW warnings, BLUE steps)
- Exits with error if Docker not available, build fails, or push fails

<acceptance_criteria>
1. `bash build_script/build-sandbox.sh` builds the image and tags both `usestrix/strix-sandbox:latest` and `usestrix/strix-sandbox:{VERSION}`
2. `docker images usestrix/strix-sandbox` shows both tags present
3. `bash build_script/build-sandbox.sh --push` attempts push (may fail without credentials -- script should report auth error clearly)
4. Script exits non-zero with clear error if `containers/Dockerfile` not found
5. Script exits non-zero with clear error if Docker not available
</acceptance_criteria>

</task>

---

<task id="2.1" type="auto">

### Task 2.1: .github/workflows/build-release.yml -- Dual-trigger CI with GitHub Release

**Context:** BUILD-05 requires `workflow_dispatch` trigger. BUILD-06 requires GitHub Release with artifacts. D-09 specifies dual trigger: `workflow_dispatch` + `push tags: v*`. D-10 specifies artifacts: `.tar.gz` (Linux), `.zip` (Windows), and `checksums.txt`. D-07 specifies Linux + Windows only, NO macOS.

The existing `build-release.yml` includes macOS targets (macos-latest, macos-15-intel) which must be removed. It also uses local `uv run pyinstaller` instead of Docker-based build. The CI should call our `build_script/` scripts directly (per D-04).

However, since the Docker-based build in CI requires Docker-in-Docker or running on a Docker-capable runner, and the existing CI approach uses local Python + uv, we need to adapt. The CI workflow should use the Docker-based build approach from `build_script/build-binary.sh` where possible, or alternatively replicate the Docker build logic inline since CI runners have Docker available.

**Strategy:** CI uses the `Dockerfile.build` approach directly (same as `build-binary.sh`) but inline in the workflow, plus calls `build_script/build-sandbox.sh --push` for the sandbox image.

<read_first>
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/.github/workflows/build-release.yml
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/build_script/build-binary.sh (AFTER task 1.2 is complete)
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/build_script/build-sandbox.sh (AFTER task 1.3 is complete)
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/Dockerfile.build
- D:/AI/strix_interal/.claude/worktrees/agent-add1322ec6d8b9211/pyproject.toml
</read_first>

**Modify:** `.github/workflows/build-release.yml`

**Specification:**
- Name: "Build & Release"
- Triggers: `workflow_dispatch` + `push: tags: ['v*']` (per D-09)
- Jobs:

**Job 1: `build`** (runs-on: ubuntu-latest)
  - Checkout repo
  - Extract version from `pyproject.toml`
  - Build binary via Docker: `docker build -f Dockerfile.build --target builder -t strix-builder .` then extract binary
  - Name binary: `strix-{VERSION}-linux-x86_64`
  - Create `.tar.gz` archive
  - Build Windows binary: since true cross-compilation isn't feasible in CI, document that Windows binary is built on a Windows runner or use the local Python approach for Windows in a `windows-latest` matrix job
  - Matrix: `ubuntu-latest` + `windows-latest` (per D-07, Linux + Windows only)
  - On Windows: use existing uv + pyinstaller approach (Dockerfile.build is Linux-only)
  - On Linux: use Docker build approach
  - Upload artifacts

**Job 2: `sandbox`** (runs-on: ubuntu-latest, needs: build)
  - Checkout repo
  - Log into Docker Hub: `docker login -u ${{ secrets.DOCKERHUB_USERNAME }} -p ${{ secrets.DOCKERHUB_TOKEN }}`
  - Run `bash build_script/build-sandbox.sh --push`
  - Note: the sandbox script sources version.sh to get the correct version tag

**Job 3: `release`** (runs-on: ubuntu-latest, needs: [build, sandbox])
  - Download all artifacts
  - Generate `checksums.txt`: `sha256sum *.{tar.gz,zip} > checksums.txt`
  - Create GitHub Release via `softprops/action-gh-release@v2`
  - Include: `.tar.gz` (Linux), `.zip` (Windows), `checksums.txt`
  - `generate_release_notes: true`
  - `prerelease: ${{ !startsWith(github.ref, 'refs/tags/') }}`

**Key changes from existing:**
- REMOVE macOS matrix entries (macos-latest, macos-15-intel) per D-07
- ADD Docker Hub login step for sandbox push
- ADD sandbox job
- ADD checksums.txt generation
- KEEP `softprops/action-gh-release@v2` for GitHub Release creation
- USE `actions/checkout@v4`, `actions/setup-python@v5`, `astral-sh/setup-uv@v5`, `actions/upload-artifact@v4`, `actions/download-artifact@v4`

<acceptance_criteria>
1. Workflow triggers on `workflow_dispatch` and `push: tags: v*`
2. No macOS entries in build matrix (only ubuntu-latest + windows-latest)
3. Sandbox job uses `docker login` with secrets + calls `build_script/build-sandbox.sh --push`
4. Release job generates `checksums.txt` with sha256sum
5. Release job includes `.tar.gz`, `.zip`, and `checksums.txt` in GitHub Release
6. Valid YAML (can be parsed without errors)
</acceptance_criteria>

</task>

---

## Verification

After all tasks complete:

```bash
# Verify all build scripts exist and are executable
ls -la build_script/version.sh build_script/build-binary.sh build_script/build-sandbox.sh

# Verify no scripts in wrong directory
test ! -d scripts/build/ || (echo "FAIL: scripts/build/ exists" && false)

# Verify Makefile unchanged
git diff HEAD -- Makefile | test ! -s /dev/stdin || (echo "FAIL: Makefile was modified" && false)

# Verify no docker-compose.yml created
test ! -f docker-compose.yml || (echo "FAIL: docker-compose.yml created" && false)

# Verify version.sh works
source build_script/version.sh && test -n "$STRIX_VERSION" && echo "PASS: version.sh"

# Verify workflow YAML is valid
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-release.yml'))" && echo "PASS: YAML valid"

# Verify no ghcr.io in any build script
! grep -r 'ghcr.io' build_script/ || (echo "FAIL: ghcr.io reference found" && false)

# Verify usestrix/strix-sandbox in sandbox script
grep -q 'usestrix/strix-sandbox' build_script/build-sandbox.sh && echo "PASS: Docker Hub image" || (echo "FAIL: wrong Docker registry" && false)

# Verify build_script directory has EXACTLY 3 files
test $(ls build_script/ | wc -l) -eq 3 || (echo "WARN: build_script/ has unexpected files: $(ls build_script/)" && false)
```

## Success Criteria

- [ ] All 4 tasks executed (1.1, 1.2, 1.3, 2.1)
- [ ] Each task committed individually with descriptive commit messages
- [ ] `build_script/` contains exactly: `version.sh`, `build-binary.sh`, `build-sandbox.sh`
- [ ] All scripts are standalone bash with `set -euo pipefail`
- [ ] Version sourced from `pyproject.toml` (single source of truth)
- [ ] Docker Hub image name `usestrix/strix-sandbox` (NOT ghcr.io)
- [ ] CI workflow: Linux + Windows only, NO macOS
- [ ] CI workflow: dual trigger (`workflow_dispatch` + `push tags: v*`)
- [ ] CI release includes `.tar.gz`, `.zip`, `checksums.txt`
- [ ] No modifications to Makefile
- [ ] No `docker-compose.yml` created
- [ ] No files in `scripts/build/`
