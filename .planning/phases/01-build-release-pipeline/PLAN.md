---
wave: 1
depends_on: []
files_modified: ["build_script/build-binary.sh", "build_script/build-sandbox.sh", "build_script/build-all.sh", ".github/workflows/build-release.yml"]
autonomous: true
---

# Phase 1: Build & Release Pipeline - Plan

<task_summary>
2 waves. 4 tasks. Wave 1 creates the three build scripts (build-binary.sh, build-sandbox.sh, build-all.sh) including local checksums generation. Wave 2 refactors the CI workflow to call build scripts and integrate checksums + sandbox push into GitHub Release.
</task_summary>

## Requirements Covered

| ID | Requirement | Covered By |
|----|-------------|------------|
| BUILD-01 | Single-command binary build | Task 1.1 (build-binary.sh) |
| BUILD-02 | Single-command sandbox image build | Task 1.2 (build-sandbox.sh) |
| BUILD-03 | Version from pyproject.toml only | All tasks — every script reads version from pyproject.toml |
| BUILD-05 | workflow_dispatch one-click release trigger | Task 2.1 (build-release.yml) |
| BUILD-06 | GitHub Release with Linux binary, Docker image push, checksums | Tasks 1.3, 2.1 |

**BUILD-04 REMOVED from this phase** per CONTEXT.md decision D-06.

## Artifacts This Phase Produces

### New Files
| File | Description |
|------|-------------|
| `build_script/build-binary.sh` | Docker-driven PyInstaller binary build script (Linux + Windows) |
| `build_script/build-sandbox.sh` | Docker sandbox image build + push script |
| `build_script/build-all.sh` | Orchestrator: calls sub-scripts, generates checksums.txt |
| `dist/` | Flat output directory for build artifacts (created by scripts at runtime) |

### New Shell Functions (in build scripts)
| Function | File | Description |
|----------|------|-------------|
| `extract_version()` | build-binary.sh, build-sandbox.sh, build-all.sh | Extracts version from pyproject.toml using grep pattern |
| `check_docker()` | build-binary.sh, build-sandbox.sh | Verifies Docker is available and daemon is running |
| `build_linux_binary()` | build-binary.sh | Builds Linux binary inside Docker container via Dockerfile.build |
| `build_windows_binary()` | build-binary.sh | Cross-compiles Windows .exe inside Docker container |
| `archive_artifacts()` | build-binary.sh | Creates .tar.gz for Linux binary, .zip for Windows binary |
| `build_and_push_image()` | build-sandbox.sh | Builds containers/Dockerfile, tags with version, pushes to Docker Hub |
| `generate_checksums()` | build-all.sh | Runs sha256sum over all files in dist/ |

### New Workflow Properties (in build-release.yml)
| Property | Value |
|----------|-------|
| `on.workflow_dispatch` | Retained from existing workflow |
| `on.push.tags` | `'v*'` (retained) |
| `jobs.build.matrix.include` | Reduced to linux-x86_64 (ubuntu-latest) and windows-x86_64 (windows-latest) |
| `jobs.release.permissions` | `contents: write` (retained) |

### Constants
| Constant | Value | Used In |
|----------|-------|---------|
| `DOCKER_HUB_IMAGE` | `usestrix/strix-sandbox` | build-sandbox.sh |
| `OUTPUT_DIR` | `dist` | All build scripts |

## Threat Model

### Attack Surface Analysis

**1. Supply Chain — PyInstaller Build Container**
- **Threat:** Malicious code injected into Dockerfile.build dependencies (pip packages, base image)
- **Severity:** HIGH — compromised binary would execute on user machines
- **Mitigation:** Dockerfile.build pins exact Python image (`python:3.12-slim`) and exact pip versions (`openai-agents[litellm]==0.14.6`); no `latest` tags. `--no-cache-dir` prevents poisoned cache. Build script verifies Docker daemon is running before build.

**2. Supply Chain — Docker Base Image**
- **Threat:** Compromised `kalilinux/kali-rolling:latest` base image in containers/Dockerfile
- **Severity:** HIGH — sandbox container runs security tools with elevated privileges
- **Mitigation:** Build script logs the exact image digest pulled; CONTEXT.md notes this as a known risk (kali-rolling:latest). Phase 1 documents this as accepted risk for v1.0 — will pin digest in future version.

**3. Secret Management — Docker Hub Credentials**
- **Threat:** Docker Hub credentials leaked via script logging or CI output
- **Severity:** HIGH — compromised credentials allow pushing malicious images
- **Mitigation:** Scripts read credentials from environment variables only (never hardcoded). CI uses `secrets.DOCKERHUB_USERNAME` / `secrets.DOCKERHUB_TOKEN` GitHub Secrets. Scripts use `docker login` with `--password-stdin` to avoid shell history exposure. Scripts check for credentials before attempting push; fail with clear error if missing.

**4. Secret Management — GitHub Actions Tokens**
- **Threat:** Excessive permissions on GITHUB_TOKEN allowing unauthorized release creation
- **Severity:** MEDIUM — could create spoofed releases
- **Mitigation:** Workflow uses minimum required `permissions: contents: write` scoped to release job only (not globally). `softprops/action-gh-release@v2` pinned to major version.

**5. Artifact Integrity — Binary Tampering**
- **Threat:** Binary modified between build and release without detection
- **Severity:** MEDIUM — users download compromised binary
- **Mitigation:** `build-all.sh` generates `checksums.txt` with SHA256 hashes of all dist files. Checksums published as part of GitHub Release alongside binaries. Users can verify downloads against checksums.

**6. Artifact Integrity — Docker Image Tag Overwrite**
- **Threat:** Attacker pushes image with same version tag, overwriting legitimate image
- **Severity:** MEDIUM — users pull compromised sandbox image
- **Mitigation:** Version tags are immutable in practice (Docker Hub does not prevent overwrites, but CI uses unique version per release). Script logs exact image digest after push for audit trail.

### Threat Summary

| # | Threat | Severity | Mitigation Strategy |
|---|--------|----------|---------------------|
| T1 | Malicious pip packages in build container | HIGH | Pinned versions in Dockerfile.build, --no-cache-dir |
| T2 | Compromised Kali base image | HIGH | Log digest; pin in future version (accepted risk for v1.0) |
| T3 | Docker Hub credential leak | HIGH | Env-var only, --password-stdin, GitHub Secrets |
| T4 | Excessive GITHUB_TOKEN permissions | MEDIUM | Scoped permissions: contents: write on release job |
| T5 | Binary tampering pre-release | MEDIUM | SHA256 checksums in GitHub Release |
| T6 | Docker image tag overwrite | MEDIUM | Log digest, unique version per release |

---

## Waves

### Wave 1: Build Scripts (no CI dependency)
Build scripts are independent of CI — they can be tested locally without GitHub Actions.
Tasks 1.1 and 1.2 have no dependencies and can be executed in parallel.
Task 1.3 depends on Task 1.1 (calls build-binary.sh).

**Wave 1 goals:** All three build scripts exist and can be run locally.

### Wave 2: CI Workflow (depends on Wave 1)
The workflow calls build_script/ scripts, so it depends on the scripts existing first. Checksums generation is integrated into both the local build-all.sh orchestrator (Wave 1, Task 1.3) and the CI release job (Wave 2, Task 2.1).

**Wave 2 goals:** GitHub Actions workflow produces release artifacts automatically with checksums integrity.

---

## Tasks

### Task 1.1: Create build-binary.sh — Docker-driven PyInstaller binary build

**Requirement:** BUILD-01 (single-command binary build)
**File:** `build_script/build-binary.sh` (NEW)
**Wave:** 1
**Depends on:** None

<read_first>
- scripts/build.sh (pattern analog — shebang, set -e, SCRIPT_DIR/PROJECT_ROOT resolution, ANSI colors, version extraction, error checking, chmod +x, archive creation)
- Dockerfile.build (existing build container — lines 1-14: base image, PyInstaller install, build commands)
- strix.spec (PyInstaller spec — lines 1-10, 232-267: project root resolution, Analysis config, EXE config with name='strix')
- pyproject.toml (version source — line 3: version = "1.0.4")
</read_first>

<action>
Create `build_script/build-binary.sh` — a bash script following the structural conventions in `scripts/build.sh`:

1. Shebang `#!/bin/bash` + `set -euo pipefail`
2. `SCRIPT_DIR` and `PROJECT_ROOT` resolution (same pattern as `scripts/build.sh:4-5`)
3. ANSI color variables: RED, GREEN, YELLOW, BLUE, NC (same pattern as `scripts/build.sh:7-11`)
4. `extract_version()` function: runs `grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'` from `$PROJECT_ROOT`, validates result is non-empty, fails with error if not found
5. `check_docker()` function: verifies `docker` command exists and `docker info` succeeds, fails with error message and exit 1 if not
6. Main flow:
   - Print banner "Strix Binary Build" with BLUE color
   - Call `extract_version()` and print version in YELLOW
   - Call `check_docker()`
   - Clean: `rm -rf "$PROJECT_ROOT/dist/"` (removes previous dist dir, but preserve any existing artifacts outside dist)
   - Build Linux binary:
     a. `docker build -f "$PROJECT_ROOT/Dockerfile.build" -t strix-builder:latest "$PROJECT_ROOT"` — builds the PyInstaller container (this reuses Dockerfile.build exactly as-is)
     b. `docker run --rm -v "$PROJECT_ROOT/dist:/output" strix-builder:latest` — runs container, PyInstaller outputs to /output which maps to dist/
     c. Verify binary exists: `[ -f "$PROJECT_ROOT/dist/strix" ]` — fail with error if not found
     d. Copy + rename: `cp "$PROJECT_ROOT/dist/strix" "$PROJECT_ROOT/dist/strix-${VERSION}-linux-x86_64"`
     e. `chmod +x "$PROJECT_ROOT/dist/strix-${VERSION}-linux-x86_64"`
     f. Create tar.gz: `tar -czvf "$PROJECT_ROOT/dist/strix-${VERSION}-linux-x86_64.tar.gz" -C "$PROJECT_ROOT/dist" "strix-${VERSION}-linux-x86_64"`
   - Build Windows binary:
     a. Use the same Docker build (`Dockerfile.build`) but with a wine-based approach: create a temporary Dockerfile.wine that extends `python:3.12-slim`, installs `wine wine32` and `pyinstaller`, copies source, and produces `strix.exe`
     b. `docker build -f "$PROJECT_ROOT/Dockerfile.wine" -t strix-builder-wine:latest "$PROJECT_ROOT"`
     c. `docker run --rm -v "$PROJECT_ROOT/dist:/output" strix-builder-wine:latest`
     d. Verify: `[ -f "$PROJECT_ROOT/dist/strix.exe" ]`
     e. Rename: `cp "$PROJECT_ROOT/dist/strix.exe" "$PROJECT_ROOT/dist/strix-${VERSION}-windows-x86_64.exe"`
     f. Create zip: `zip -j "$PROJECT_ROOT/dist/strix-${VERSION}-windows-x86_64.zip" "$PROJECT_ROOT/dist/strix-${VERSION}-windows-x86_64.exe"` (if `zip` not available, fallback to `7z a` or error)
   - Print summary with GREEN "Build successful" and list all output files with sizes
   - Exit 0
7. Error handling: if any docker command fails, print RED error message and exit 1. Use `trap` for cleanup of temporary Dockerfile.wine if created.
8. Do NOT change the Makefile or add Makefile targets
</action>

<acceptance_criteria>
- `bash build_script/build-binary.sh` exits 0 when Docker daemon is running
- File `dist/strix-{version}-linux-x86_64` exists after execution (where {version} is value from pyproject.toml)
- File `dist/strix-{version}-linux-x86_64.tar.gz` exists and contains the Linux binary
- File `dist/strix-{version}-windows-x86_64.exe` exists after execution
- File `dist/strix-{version}-windows-x86_64.zip` exists and contains the Windows binary
- Script exits non-zero with error message when Docker is not available
- Script exits non-zero when pyproject.toml has no version field
- `grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'` pattern is present in the script
</acceptance_criteria>

---

### Task 1.2: Create build-sandbox.sh — Docker sandbox image build + push

**Requirement:** BUILD-02 (single-command Docker build), BUILD-03 (version from pyproject.toml)
**File:** `build_script/build-sandbox.sh` (NEW)
**Wave:** 1
**Depends on:** None

<read_first>
- scripts/docker.sh (pattern analog — lines 1-16: shebang, set -e, SCRIPT_DIR/PROJECT_ROOT, image name, TAG variable, docker build command)
- containers/Dockerfile (sandbox image — understand the build context is PROJECT_ROOT and contains COPY directives for strix source)
- pyproject.toml (version source — line 3)
- scripts/install.sh (lines 7, 157-161: image reference pattern `usestrix/strix-sandbox:1.0.0` and Docker Hub naming convention)
</read_first>

<action>
Create `build_script/build-sandbox.sh` — a bash script following the structural conventions in `scripts/docker.sh`:

1. Shebang `#!/bin/bash` + `set -euo pipefail`
2. `SCRIPT_DIR` and `PROJECT_ROOT` resolution (same pattern as `scripts/docker.sh:4-5`)
3. ANSI color variables: RED, GREEN, YELLOW, BLUE, NC
4. Constants: `IMAGE_NAME="usestrix/strix-sandbox"` — Docker Hub repository (NOT ghcr.io)
5. `extract_version()` function: same grep pattern as build-binary.sh — `grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'` from `$PROJECT_ROOT`
6. `check_docker()` function: verifies `docker` command exists and daemon is running
7. Main flow:
   - Print banner "Strix Sandbox Image Build" with BLUE
   - Call `extract_version()`, print version in YELLOW
   - Call `check_docker()`
   - Validate version is non-empty
   - Build image: `docker build -f "$PROJECT_ROOT/containers/Dockerfile" -t "$IMAGE_NAME:$VERSION" -t "$IMAGE_NAME:latest" "$PROJECT_ROOT"`
   - Report build success with image name and tag in GREEN
   - Check for Docker Hub credentials:
     a. If `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` env vars are both set, proceed with push
     b. `echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin` (uses --password-stdin to avoid shell history exposure)
     c. `docker push "$IMAGE_NAME:$VERSION"`
     d. `docker push "$IMAGE_NAME:latest"`
     e. Print pushed image name + tag in GREEN and log the image digest with `docker image inspect "$IMAGE_NAME:$VERSION" --format '{{.RepoDigests}}'`
     f. `docker logout`
     g. If credentials are not set, print YELLOW warning "Docker Hub credentials not set — skipping push. Set DOCKERHUB_USERNAME and DOCKERHUB_TOKEN to enable push."
   - Exit 0
8. Tag both `$IMAGE_NAME:$VERSION` and `$IMAGE_NAME:latest` so latest always points to the most recent build
</action>

<acceptance_criteria>
- `bash build_script/build-sandbox.sh` exits 0 when Docker daemon is running
- `docker image inspect usestrix/strix-sandbox:{version}` succeeds (image exists locally, {version} from pyproject.toml)
- `docker image inspect usestrix/strix-sandbox:latest` succeeds (latest tag exists locally)
- Script exits non-zero when Docker is not available
- When `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` are set and valid, image is pushed to Docker Hub
- When credentials are not set, script prints a warning about skipping push but still exits 0
- `--password-stdin` is used for docker login (not `-p` flag with password in command line)
- Image reference `usestrix/strix-sandbox` appears in the script (not ghcr.io)
- `grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'` pattern is present
</acceptance_criteria>

---

### Task 1.3: Create build-all.sh — Orchestrator script

**Requirement:** BUILD-01, BUILD-02 (orchestrates both builds), BUILD-06 (checksums generation)
**File:** `build_script/build-all.sh` (NEW)
**Wave:** 1
**Depends on:** Task 1.1 (build-binary.sh must exist to be called)

<read_first>
- build_script/build-binary.sh (created in Task 1.1 — understand the interface: script exits 0 on success, non-zero on failure, outputs to dist/)
- build_script/build-sandbox.sh (created in Task 1.2 — understand the interface: script exits 0 on success, non-zero on failure)
- scripts/build.sh (pattern analog — lines 48-99: sequential step execution with colored output, cleaning phase, build phase, archive phase, verify phase)
- Makefile (lines 53-54: orchestration pattern — `check-all: format lint type-check security` calls sub-targets sequentially)
- pyproject.toml (version source — line 3)
</read_first>

<action>
Create `build_script/build-all.sh` — orchestrator script following the sequential step execution pattern from `scripts/build.sh`:

1. Shebang `#!/bin/bash` + `set -euo pipefail`
2. `SCRIPT_DIR` and `PROJECT_ROOT` resolution
3. ANSI color variables: RED, GREEN, YELLOW, BLUE, NC
4. `extract_version()` function: same grep pattern as other build scripts
5. Main flow:
   - Print banner "Strix Full Build Pipeline" with BLUE
   - Call `extract_version()`, print version in YELLOW
   - Step 1: "Building binaries..." in BLUE
     a. `bash "$SCRIPT_DIR/build-binary.sh"` — call sub-script, propagate exit code on failure
     b. Check exit code: if non-zero, print RED error and exit 1
   - Step 2: "Building sandbox image..." in BLUE
     a. `bash "$SCRIPT_DIR/build-sandbox.sh"` — call sub-script, propagate exit code
     b. Check exit code: if non-zero, print RED error and exit 1
   - Step 3: "Generating checksums..." in BLUE
     a. Verify `dist/` directory exists: `[ -d "$PROJECT_ROOT/dist" ]` else error
     b. Generate checksums: `cd "$PROJECT_ROOT/dist" && sha256sum * > checksums.txt`
     c. Verify checksums.txt was created: `[ -f "$PROJECT_ROOT/dist/checksums.txt" ]` else error
     d. Print "Checksums generated" in GREEN and display file contents with `cat dist/checksums.txt`
   - Print final summary: "Full build pipeline complete" in GREEN, list all files in dist/ with sizes
   - Exit 0
6. Error handling: if any step fails, print which step failed, print RED error, exit 1
7. Do NOT clean dist/ before calling sub-scripts (each sub-script handles its own cleaning) — dist/ accumulates outputs from both build-binary.sh and build-sandbox.sh
8. Checksums file covers ALL files in dist/ directory including: the Linux binary, the Windows .exe, the .tar.gz archive, the .zip archive
</action>

<acceptance_criteria>
- `bash build_script/build-all.sh` exits 0 when sub-scripts succeed
- After execution, `dist/checksums.txt` exists
- `dist/checksums.txt` contains SHA256 hashes for all files in dist/ directory (Linux binary, Windows exe, archives)
- `grep 'strix-.*-linux-x86_64' dist/checksums.txt` returns a line with a 64-character hex hash
- `grep 'strix-.*-windows-x86_64.exe' dist/checksums.txt` returns a line with a 64-character hex hash
- Script exits non-zero if build-binary.sh fails (test by temporarily breaking a dependency)
- Script exits non-zero if build-sandbox.sh fails
- Script calls sub-scripts via `bash "$SCRIPT_DIR/build-binary.sh"` (relative via SCRIPT_DIR)
</acceptance_criteria>

---

### Task 2.1: Refactor build-release.yml — Dual trigger CI/CD with build_script/ integration

**Requirement:** BUILD-05 (workflow_dispatch trigger), BUILD-06 (GitHub Release)
**File:** `.github/workflows/build-release.yml` (MODIFY)
**Wave:** 2
**Depends on:** Wave 1 (all build scripts must exist)

<read_first>
- .github/workflows/build-release.yml (current workflow — lines 1-79: triggers, matrix, build job, release job)
- build_script/build-binary.sh (created in Wave 1 — understand it runs standalone and outputs to dist/)
- build_script/build-sandbox.sh (created in Wave 1 — understand it runs standalone, optionally pushes)
- build_script/build-all.sh (created in Wave 1 — understand it orchestrates and generates checksums)
- pyproject.toml (version source)
</read_first>

<action>
Modify the existing `.github/workflows/build-release.yml`:

1. **Keep** the existing dual trigger at lines 3-7:
   ```yaml
   on:
     push:
       tags:
         - 'v*'
     workflow_dispatch:
   ```

2. **Modify `jobs.build`** (the build job):
   - Keep `strategy.fail-fast: false`
   - Reduce `matrix.include` from 4 platforms to 2:
     - `{ os: ubuntu-latest, target: linux-x86_64 }`
     - `{ os: windows-latest, target: windows-x86_64 }`
   - Remove macOS entries: `{ os: macos-latest, target: macos-arm64 }` and `{ os: macos-15-intel, target: macos-x86_64 }`
   - Keep `runs-on: ${{ matrix.os }}`
   
3. **Modify build steps** to call build_script/ scripts instead of inline commands:
   - Step 1: `actions/checkout@v4` (keep)
   - Step 2: `actions/setup-python@v5` with `python-version: '3.12'` (keep — needed for uv)
   - Step 3: `astral-sh/setup-uv@v5` (keep)
   - Step 4: Replace inline `uv sync --frozen` + `uv run pyinstaller` block with:
     ```
     name: Build binary
     shell: bash
     run: bash build_script/build-binary.sh
     ```
     Note: The script builds BOTH Linux and Windows binaries per invocation (via Docker containers). On the ubuntu-latest runner this works for both platforms. On the windows-latest runner, the script's docker-based Linux build may not work — so for the windows-latest matrix entry, only the Windows binary matters. The workflow should handle this by:
     - Adding a `PLATFORM` env var to the step: `PLATFORM: ${{ matrix.target }}`
     - The build-binary.sh script checks `PLATFORM` env var and skips the platform that doesn't match if set
   
   - Step 5: Replace inline archive logic with:
     ```
     name: Upload artifact
     uses: actions/upload-artifact@v4
     with:
       name: strix-${{ matrix.target }}
       path: |
         dist/strix-*-${{ matrix.target }}
         dist/strix-*-${{ matrix.target }}.*
       if-no-files-found: error
     ```

4. **Modify `jobs.release`** (the release job):
   - Keep `needs: build`
   - Keep `runs-on: ubuntu-latest`
   - Keep `permissions: contents: write`
   - Add steps:
     a. `actions/checkout@v4` (NEW — needed to access build-all.sh for checksums)
     b. `actions/download-artifact@v4` with `path: dist` and `merge-multiple: true` (MODIFIED — download to dist/ not release/)
     c. Generate checksums:
        ```
        name: Generate checksums
        shell: bash
        run: |
          VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
          cd dist
          sha256sum * > checksums.txt
          cat checksums.txt
        ```
     d. Build and push sandbox image:
        ```
        name: Build and push sandbox image
        shell: bash
        env:
          DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}
          DOCKERHUB_TOKEN: ${{ secrets.DOCKERHUB_TOKEN }}
        run: bash build_script/build-sandbox.sh
        ```
     e. Create Release:
        ```
        name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          prerelease: ${{ !startsWith(github.ref, 'refs/tags/') }}
          generate_release_notes: true
          files: dist/*
        ```
        Note: `files: dist/*` includes all binaries, archives, AND checksums.txt because checksums was generated into dist/ in step (c).

5. **Remove** the `checkout` step from the `release` job if `actions/download-artifact@v4` is sufficient — but keep `checkout` so the release job can read `build_script/build-sandbox.sh` from the repo.

6. **Add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets configuration** as a comment in the workflow file documenting required secrets:
   ```yaml
   # Required GitHub Secrets:
   #   DOCKERHUB_USERNAME - Docker Hub username for pushing sandbox image
   #   DOCKERHUB_TOKEN    - Docker Hub access token (not password)
   ```

7. The workflow name remains "Build & Release"
</action>

<acceptance_criteria>
- `.github/workflows/build-release.yml` contains `workflow_dispatch:` trigger
- `.github/workflows/build-release.yml` contains `push: tags: ['v*']` trigger
- `matrix.include` has exactly 2 entries: ubuntu-latest/linux-x86_64 and windows-latest/windows-x86_64
- No macOS entries in matrix.include
- Build step calls `bash build_script/build-binary.sh` (not inline uv run pyinstaller)
- Release job has `permissions: contents: write`
- Release job uses `softprops/action-gh-release@v2`
- Release job's `files` glob is `dist/*` (not `release/*`)
- Release job includes step to generate `checksums.txt` via `sha256sum * > checksums.txt`
- Release job includes step to call `bash build_script/build-sandbox.sh`
- Workflow contains comment documenting `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets
- `actions/upload-artifact@v4` path pattern references `dist/` directory (not `dist/release/`)
</acceptance_criteria>

---

## Verification Criteria

### Goal-Backward Verification (does this plan achieve the phase goal?)

| Success Criterion (from ROADMAP) | How Plan Achieves It |
|----------------------------------|---------------------|
| 1. Single command to compile Linux binary via PyInstaller | Task 1.1: `bash build_script/build-binary.sh` builds via Docker container |
| 2. Single command to build Docker sandbox image with correct version tag | Task 1.2: `bash build_script/build-sandbox.sh` builds and tags with version |
| 3. Version identical across binary, image, git tag, pyproject.toml | All tasks extract version from pyproject.toml using identical grep pattern; workflow triggers on `v*` tags |
| 4. Deploy via `docker compose up` | **REMOVED (BUILD-04)** — deferred to future version |
| 5. workflow_dispatch full release | Task 2.1: workflow_dispatch trigger + release job creates GitHub Release with all artifacts |

### must_haves (what MUST be true for phase success)

1. `bash build_script/build-binary.sh` produces `dist/strix-{version}-linux-x86_64` and `dist/strix-{version}-windows-x86_64.exe`
2. `bash build_script/build-sandbox.sh` produces Docker image `usestrix/strix-sandbox:{version}`
3. `bash build_script/build-all.sh` produces `dist/checksums.txt`
4. Every script extracts version from `pyproject.toml` using: `grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'`
5. `.github/workflows/build-release.yml` has `workflow_dispatch` AND `push: tags: ['v*']` triggers
6. GitHub Release includes: Linux binary archive, Windows binary archive, checksums.txt
7. Docker Hub push uses `--password-stdin` (not `-p` flag)
8. Makefile is NOT modified (no build targets added)

### Integration Test (E2E verification)

After implementation, verify with:
```bash
# Local test
bash build_script/build-all.sh
# Then verify:
ls -la dist/
# Should show: strix-{version}-linux-x86_64, strix-{version}-linux-x86_64.tar.gz,
#              strix-{version}-windows-x86_64.exe, strix-{version}-windows-x86_64.zip,
#              checksums.txt

# Docker image
docker image inspect usestrix/strix-sandbox:{version}

# Checksums integrity
cd dist && sha256sum -c checksums.txt
# Should show "OK" for all files
```
