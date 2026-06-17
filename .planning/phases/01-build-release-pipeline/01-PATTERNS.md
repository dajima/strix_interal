# Phase 01: Build & Release Pipeline — Pattern Map

**Generated:** 2026-06-17
**Source:** CONTEXT.md decisions, existing codebase analogs

---

## File Inventory

### New Files to Create

| # | File | Role | Closest Analog |
|---|------|------|----------------|
| N1 | `build_script/build-binary.sh` | Docker-driven PyInstaller build, outputs `dist/` | `scripts/build.sh` |
| N2 | `build_script/build-sandbox.sh` | Docker image build + push to registry | `scripts/docker.sh` |
| N3 | `build_script/build-all.sh` | Orchestrator: calls build-binary.sh then build-sandbox.sh | `scripts/build.sh` (entry-point flow pattern) |

### Modified Files

| # | File | Change Summary | Closest Analog |
|---|------|----------------|----------------|
| M1 | `.github/workflows/build-release.yml` | Refactor to call `build_script/` scripts; reduce matrix to Linux + Windows only; add dual trigger (`workflow_dispatch` + `push tags: v*`); generate `checksums.txt` in release step | Current `.github/workflows/build-release.yml` (same file) |

### New Directory Structure (no file, just layout)

| Entry | Description |
|-------|-------------|
| `dist/` | Flat output directory: `strix-{version}-linux-x86_64`, `strix-{version}-windows-x86_64.exe`, `checksums.txt` |

---

## Data Flow & Version Pipeline

```
pyproject.toml (version = "1.0.4")
        │
        │  grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'
        ▼
    VERSION variable (injected into every build script)
        │
        ├─► dist/strix-{version}-linux-x86_64       ← Dockerfile.build → PyInstaller
        ├─► dist/strix-{version}-linux-x86_64.tar.gz ← tar archive
        ├─► dist/strix-{version}-windows-x86_64.exe  ← Dockerfile.build → PyInstaller
        ├─► dist/strix-{version}-windows-x86_64.zip  ← zip archive
        ├─► dist/checksums.txt                       ← sha256sum over all binaries + archives
        │
        ├─► Docker tag: usestrix/strix-sandbox:{version}
        │       └─► containers/Dockerfile → docker build + docker push (Docker Hub)
        │
        └─► GitHub Release tag: v{version}
                └─► triggered by: workflow_dispatch OR git push tag v*
```

---

## Pattern Analysis Per File

### N1: `build_script/build-binary.sh`

**Role:** Build strix binary (Linux + Windows) via Docker container using existing `Dockerfile.build` and `strix.spec`. Extract version from `pyproject.toml`.

**Closest Analog:** `scripts/build.sh`

**Analog Excerpt (pattern to follow):**

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- boilerplate above matches scripts/build.sh lines 1-11 ---

VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
# --- version extraction matches scripts/build.sh line 45 ---
```

**Key differences from analog:**
- Uses `docker build -f Dockerfile.build` instead of local `uv run pyinstaller`
- Outputs to `dist/` flat (not `dist/release/`) as per D-05
- No `--help` smoke test step (removed from CONTEXT.md scope)
- Builds Linux binary inside Docker container, copies out to `dist/`
- Windows cross-compilation: uses Docker with wine or a Windows build approach
- OS/arch detection is fixed (Linux host builds both Linux + Windows)

**Data I/O:**
- **Inputs:** `pyproject.toml` (version), `Dockerfile.build`, `strix.spec`, `strix/` source, `containers/` data
- **Outputs:** `dist/strix-{version}-linux-x86_64`, `dist/strix-{version}-windows-x86_64.exe`

**Pattern reference points from `scripts/build.sh`:**
| Pattern | Line(s) | Description |
|---------|---------|-------------|
| Shebang + `set -e` | 1-2 | Fail-fast bash |
| `SCRIPT_DIR` / `PROJECT_ROOT` resolution | 4-5 | Portable path resolution |
| ANSI color variables | 7-11 | Terminal output styling |
| `grep` version extraction | 45 | Single version source from pyproject.toml |
| Error-check guard (`if [ ! -f ... ]`) | 60-62, 76-78 | Binary existence validation |
| `chmod +x` for Linux binary | 81 | Executable permission |

**Docker build pattern from `Dockerfile.build`:**
```bash
# Actual Dockerfile.build lines 12-14 — the build invocation pattern:
RUN pip install --no-cache-dir "openai-agents[litellm]==0.14.6" ...
RUN pyinstaller strix.spec --noconfirm
RUN mkdir -p /output && cp dist/strix /output/ && chmod +x /output/strix
```

---

### N2: `build_script/build-sandbox.sh`

**Role:** Build Docker sandbox image from `containers/Dockerfile`, tag with version extracted from `pyproject.toml`, push to Docker Hub.

**Closest Analog:** `scripts/docker.sh`

**Analog Excerpt (pattern to follow):**

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE="strix-sandbox"
TAG="${1:-dev}"

echo "Building $IMAGE:$TAG ..."
docker build \
  -f "$PROJECT_ROOT/containers/Dockerfile" \
  -t "$IMAGE:$TAG" \
  "$PROJECT_ROOT"

echo "Done: $IMAGE:$TAG"
```

**Key differences from analog:**
- Tag comes from `pyproject.toml` version, not `$1` (no `dev` default)
- Adds `docker push` step targeting Docker Hub (`usestrix/strix-sandbox:{version}`)
- Includes `docker login` check or credential requirement
- Version tag must be validated (non-empty, semver-like)

**Data I/O:**
- **Inputs:** `pyproject.toml` (version), `containers/Dockerfile`, Docker Hub credentials
- **Outputs:** Docker image `usestrix/strix-sandbox:{version}` pushed to Docker Hub

**Docker Hub reference from `scripts/install.sh`:**
```bash
# scripts/install.sh line 7 — the registry + image pattern:
STRIX_IMAGE="ghcr.io/usestrix/strix-sandbox:1.0.0"
# Phase 1 changes registry: ghcr.io → Docker Hub (no org prefix needed, just usestrix/)
```

---

### N3: `build_script/build-all.sh`

**Role:** Orchestrator script that calls `build-binary.sh` and `build-sandbox.sh` in sequence. Generates `checksums.txt` after both complete.

**Closest Analog:** `Makefile` (orchestration targets) and `scripts/build.sh` (entry-point flow pattern)

**Analog Excerpt — Makefile orchestration pattern (lines 53):**

```makefile
check-all: format lint type-check security
	@echo "✅ All code quality checks passed!"
```

**Analog Excerpt — Build sequence pattern (`scripts/build.sh` lines 48-86):**

```bash
# Cleaning → build → archive → verify sequence
echo -e "\n${BLUE}Cleaning previous builds...${NC}"
rm -rf build/ dist/

echo -e "\n${BLUE}Building binary with PyInstaller...${NC}"
uv run pyinstaller strix.spec --noconfirm

# ... archive creation ...

echo -e "\n${GREEN}Build successful!${NC}"
```

**Pattern:** Sequential step execution with colored output at each stage. No parallelization needed — builds are sequential by nature.

**Data I/O:**
- **Inputs:** `pyproject.toml` (version), all dependencies of sub-scripts
- **Outputs:** `dist/checksums.txt` (SHA256 over all dist files), exit code summary

---

### M1: `.github/workflows/build-release.yml` (Modified)

**Role:** CI/CD workflow with dual trigger (`workflow_dispatch` + `push tags: v*`), calling `build_script/` scripts instead of inline build commands. Reduced matrix from 4 platforms to 2 (Linux `ubuntu-latest`, Windows `windows-latest`).

**Closest Analog:** Current `.github/workflows/build-release.yml` (same file — incremental refactor)

**Changes from existing:**

| Aspect | Current | Phase 1 Target |
|--------|---------|----------------|
| Matrix | macOS-arm64, macOS-x86_64, linux-x86_64, windows-x86_64 | linux-x86_64, windows-x86_64 |
| Build method | Inline `uv run pyinstaller` | `bash build_script/build-binary.sh` |
| Docker build | N/A | `bash build_script/build-sandbox.sh` (in release job) |
| Artifact structure | `dist/release/*.tar.gz` / `*.zip` | `dist/*.tar.gz` / `*.zip` (flat) |
| Checksums | Not generated | `dist/checksums.txt` via `sha256sum` |
| Permissions | `contents: write` | `contents: write` (unchanged) |
| Release action | `softprops/action-gh-release@v2` | `softprops/action-gh-release@v2` (unchanged) |

**Key excerpts to preserve from existing workflow:**

```yaml
# Current trigger pattern (lines 3-7) — KEEP and ensure both are present:
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

# Current release pattern (lines 73-78) — KEEP:
- name: Create Release
  uses: softprops/action-gh-release@v2
  with:
    prerelease: ${{ !startsWith(github.ref, 'refs/tags/') }}
    generate_release_notes: true
    files: release/*
```

**Version extraction pattern (inline from current workflow, lines 41):**

```bash
VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
# This pattern must be in every build_script/ script AND the workflow
```

---

## Structural Conventions (from Codebase)

### Shell Script Standards

All project shell scripts follow these conventions, which new `build_script/` scripts MUST adopt:

```bash
#!/bin/bash                    # Shebang: bash, not sh (D-01)
set -e                          # Fail on first error
# OR
set -euo pipefail              # Stricter: fail on undefined vars + pipe failures (scripts/install.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Portable path resolution — used in scripts/build.sh:4-5, scripts/docker.sh:4-5

# ANSI color pattern (scripts/build.sh:7-11)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
```

### Version Extraction (Consistent Pattern)

```bash
VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
```
Used identically in: `scripts/build.sh:45`, `.github/workflows/build-release.yml:41`, and cited in CONTEXT.md:93.

### Docker Commands

```bash
# Build pattern (scripts/docker.sh:10-14)
docker build -f "$PROJECT_ROOT/containers/Dockerfile" -t "$IMAGE:$TAG" "$PROJECT_ROOT"

# Push pattern (to add — Docker Hub)
docker push "usestrix/strix-sandbox:${VERSION}"

# Build from Dockerfile.build (existing file, line 12-14 pattern)
docker build -f Dockerfile.build -t strix-builder .
docker run --rm -v "$(pwd)/dist:/output" strix-builder
```

### CI Structure (from existing workflow)

```yaml
# Build job: matrix strategy, fail-fast: false
# Release job: needs: build, runs-on: ubuntu-latest, permissions: contents: write
# Steps pattern: checkout → build → upload-artifact (build job) → download-artifact → create-release (release job)
```

---

## File Role Classification

| Role | Files | Description |
|------|-------|-------------|
| **Build Logic** | `build_script/build-binary.sh` | PyInstaller binary generation via Docker |
| **Image Logic** | `build_script/build-sandbox.sh` | Docker sandbox image build + push |
| **Orchestrator** | `build_script/build-all.sh` | Sequential build + checksums aggregation |
| **CI Runner** | `.github/workflows/build-release.yml` | Automated CI/CD calling build logic |
| **Config** | `pyproject.toml`, `strix.spec`, `Dockerfile.build`, `containers/Dockerfile` | Already exist, consumed by build scripts |
| **Output** | `dist/` directory | Flat build artifacts directory |

---

## Key Constraints

1. **No Makefile changes** (D-01): Build targets do NOT go in `Makefile` — it remains dev-tools only (format/lint/type-check/security/clean).
2. **No Python build CLI** (D-01): Builds are bash scripts, not Python subcommands.
3. **Single version source** (STATE.md): `pyproject.toml` `[project] version` is the only authoritative version. No `.version` file, no `VERSION` env variable as source of truth.
4. **Docker required**: Scripts assume Docker is available (consistent with `scripts/build.sh` which assumes `uv`).
5. **Docker Hub target** (D-08): Sandbox image pushes to Docker Hub, NOT ghcr.io. Image name: `usestrix/strix-sandbox`.
6. **No macOS**: Phase 1 Linux + Windows only. MacOS deferred to v2.0.

---

*Phase: 01-build-release-pipeline*
*Generated via gsd-pattern-mapper*
