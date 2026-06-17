#!/bin/bash
# build-binary.sh — Build strix binary
#
# Usage:
#   bash build_script/build-binary.sh                  Build for current OS (default)
#   bash build_script/build-binary.sh --target linux   Build Linux binary via Docker
#   bash build_script/build-binary.sh --target windows Build Windows .exe via local PyInstaller
#   bash build_script/build-binary.sh --target all     Build both
#
# Outputs versioned binaries to dist/release/.
#
# Requirements: Docker (for Linux target), Python 3.12+ + PyInstaller (for Windows target)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/version.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TARGET=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target) TARGET="$2"; shift 2 ;;
        --target=*) TARGET="${1#*=}"; shift ;;
        *) echo -e "${RED}Error: Unknown argument: $1${NC}" >&2; exit 1 ;;
    esac
done

# Resolve target
CURRENT_OS="$(uname -s)"
case "$CURRENT_OS" in
    Linux*)     HOST_OS="linux" ;;
    MINGW*|MSYS*|CYGWIN*) HOST_OS="windows" ;;
    *)          HOST_OS="unknown" ;;
esac

if [ -z "$TARGET" ]; then
    TARGET="$HOST_OS"
fi

if [ "$TARGET" != "linux" ] && [ "$TARGET" != "windows" ] && [ "$TARGET" != "all" ]; then
    echo -e "${RED}Error: --target must be linux, windows, or all (got: $TARGET)${NC}" >&2
    exit 1
fi

echo -e "${BLUE}Strix Binary Build Script${NC}"
echo "================================"
echo -e "${YELLOW}Target:${NC} $TARGET"
echo -e "${YELLOW}Host OS:${NC} $HOST_OS"
echo -e "${YELLOW}Version:${NC} $STRIX_VERSION"

clean_dist() {
    echo -e "\n${BLUE}Cleaning previous builds...${NC}"
    rm -rf "$PROJECT_ROOT/dist/release"/* 2>/dev/null || true
    mkdir -p "$PROJECT_ROOT/dist/release"
}

# ──── Linux build (Docker) ────

build_linux() {
    echo -e "\n${BLUE}[Linux] Building via Docker + PyInstaller...${NC}"

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker not available — cannot build Linux binary${NC}" >&2
        return 1
    fi

    local builder_img="strix-builder:${STRIX_VERSION}"
    local builder_ctr="strix-builder-linux-${STRIX_VERSION}"

    cd "$PROJECT_ROOT"

    echo -e "  Building Docker image from Dockerfile.build..."
    docker build -f Dockerfile.build -t "$builder_img" . 2>&1 | grep -Ev '^(#[0-9]|DONE| >)' || true

    echo -e "  Extracting binary..."
    docker create --name "$builder_ctr" "$builder_img" > /dev/null
    docker cp "$builder_ctr:/output/strix" "$PROJECT_ROOT/dist/strix-linux"
    docker rm "$builder_ctr" > /dev/null

    if [ ! -f "$PROJECT_ROOT/dist/strix-linux" ]; then
        echo -e "${RED}Error: Linux binary not found after build${NC}" >&2
        return 1
    fi

    local bin_name="strix-${STRIX_VERSION}-linux-x86_64"
    cp "$PROJECT_ROOT/dist/strix-linux" "$PROJECT_ROOT/dist/release/$bin_name"
    chmod +x "$PROJECT_ROOT/dist/release/$bin_name"

    echo -e "  Creating tarball..."
    local tar_name="strix-${STRIX_VERSION}-linux-x86_64.tar.gz"
    tar -czf "$PROJECT_ROOT/dist/release/$tar_name" -C "$PROJECT_ROOT/dist/release" "$bin_name"

    local sz=$(ls -lh "$PROJECT_ROOT/dist/release/$bin_name" | awk '{print $5}')
    echo -e "${GREEN}  Linux binary:${NC} $bin_name ($sz)"
    echo -e "${GREEN}  Linux archive:${NC} $tar_name"
    return 0
}

# ──── Windows build (local PyInstaller) ────

build_windows() {
    echo -e "\n${BLUE}[Windows] Building via local PyInstaller...${NC}"

    if ! command -v python &> /dev/null; then
        echo -e "${RED}Error: Python not found — cannot build Windows binary${NC}" >&2
        return 1
    fi

    if ! python -c "import PyInstaller" 2>/dev/null; then
        echo -e "${YELLOW}  PyInstaller not found, installing...${NC}"
        pip install pyinstaller --quiet
    fi

    # Ensure dependencies are installed
    echo -e "  Installing dependencies..."
    pip install --quiet "openai-agents[litellm]==0.14.6" "pydantic>=2.11.3" "pydantic-settings>=2.13.0" \
        rich docker "textual>=6.0.0" "requests>=2.32.0" "cvss>=3.2" "caido-sdk-client>=0.2.0" 2>&1 | tail -1

    cd "$PROJECT_ROOT"

    echo -e "  Running PyInstaller..."
    pyinstaller strix.spec --noconfirm 2>&1 | grep -E '(INFO: Building|INFO: Appending|Copying|Building EXE)' | tail -5

    if [ ! -f "$PROJECT_ROOT/dist/strix.exe" ]; then
        echo -e "${RED}Error: Windows .exe not found after build${NC}" >&2
        return 1
    fi

    local bin_name="strix-${STRIX_VERSION}-windows-x86_64.exe"
    cp "$PROJECT_ROOT/dist/strix.exe" "$PROJECT_ROOT/dist/release/$bin_name"

    echo -e "  Creating zip archive..."
    local zip_name="strix-${STRIX_VERSION}-windows-x86_64.zip"
    local zipped=false
    if command -v zip &> /dev/null; then
        (cd "$PROJECT_ROOT/dist/release" && zip -q "$zip_name" "$bin_name") && zipped=true
    fi
    if [ "$zipped" = false ] && command -v 7z &> /dev/null; then
        7z a -tzip "$PROJECT_ROOT/dist/release/$zip_name" "$PROJECT_ROOT/dist/release/$bin_name" > /dev/null 2>&1 && zipped=true
    fi
    if [ "$zipped" = false ]; then
        if python -c "import zipfile" 2>/dev/null; then
            python -c "
import zipfile, os
d = os.path.join(os.getcwd(), 'dist', 'release')
with zipfile.ZipFile(os.path.join(d, '$zip_name'), 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write(os.path.join(d, '$bin_name'), '$bin_name')
" && zipped=true
        fi
    fi

    local sz=$(ls -lh "$PROJECT_ROOT/dist/release/$bin_name" | awk '{print $5}')
    echo -e "${GREEN}  Windows binary:${NC} $bin_name ($sz)"
    if [ "$zipped" = true ]; then
        echo -e "${GREEN}  Windows archive:${NC} $zip_name"
    else
        echo -e "${YELLOW}  No zip tool — archive skipped${NC}"
    fi
    return 0
}

# ──── Main ────

clean_dist
FAILED=0

case "$TARGET" in
    linux)
        build_linux || FAILED=1
        ;;
    windows)
        build_windows || FAILED=1
        ;;
    all)
        build_linux || FAILED=1
        build_windows || FAILED=1
        ;;
esac

echo -e "\n${BLUE}────────────────────────────────────────${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}Build complete:${NC}"
    ls -lh "$PROJECT_ROOT/dist/release/" | tail -20
    echo -e "\n${GREEN}Done!${NC}"
else
    echo -e "${YELLOW}Build completed with errors (see above).${NC}"
    ls -lh "$PROJECT_ROOT/dist/release/" 2>/dev/null | tail -20 || echo "  (no output files)"
    echo -e "\n${YELLOW}Some targets failed.${NC}"
fi
exit $FAILED
