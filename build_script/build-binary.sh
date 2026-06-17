#!/bin/bash
# build-binary.sh — Build strix binary via Docker container
#
# Usage: bash build_script/build-binary.sh
#
# Builds the strix binary using Dockerfile.build (PyInstaller inside a container),
# then copies the resulting binary to dist/ with version-embedded filenames.
# Produces .tar.gz on Linux, .zip on Windows.
#
# Requirements: Docker

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source version
source "$SCRIPT_DIR/version.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Strix Binary Build Script${NC}"
echo "================================"

# Detect platform
OS="$(uname -s)"
case "$OS" in
    Linux*)     OS_NAME="linux" ;;
    MINGW*|MSYS*|CYGWIN*) OS_NAME="windows" ;;
    *)          echo -e "${RED}Error: Unsupported OS: $OS${NC}" >&2
                echo "This script supports Linux and Windows (Git Bash/MSYS2/Cygwin)." >&2
                exit 1 ;;
esac

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64) ARCH_NAME="x86_64" ;;
    *)           ARCH_NAME="$ARCH" ;;
esac

echo -e "${YELLOW}Platform:${NC} $OS_NAME-$ARCH_NAME"
echo -e "${YELLOW}Version:${NC} $STRIX_VERSION"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not on PATH${NC}" >&2
    exit 1
fi

# Check Dockerfile.build
if [ ! -f "$PROJECT_ROOT/Dockerfile.build" ]; then
    echo -e "${RED}Error: Dockerfile.build not found at $PROJECT_ROOT${NC}" >&2
    exit 1
fi

# Clean and create dist
echo -e "\n${BLUE}Cleaning previous builds...${NC}"
rm -rf "$PROJECT_ROOT/dist"
mkdir -p "$PROJECT_ROOT/dist"

cd "$PROJECT_ROOT"

BUILDER_IMAGE="strix-builder:${STRIX_VERSION}"
BUILDER_CONTAINER="strix-builder-${STRIX_VERSION}"

echo -e "\n${BLUE}Building Docker builder image...${NC}"
docker build -f Dockerfile.build -t "$BUILDER_IMAGE" .

echo -e "\n${BLUE}Extracting binary from container...${NC}"
# Create a temporary container (don't auto-remove — we need docker cp)
docker create --name "$BUILDER_CONTAINER" "$BUILDER_IMAGE" > /dev/null

# Copy the binary out
docker cp "$BUILDER_CONTAINER:/output/strix" "$PROJECT_ROOT/dist/strix"

# Cleanup the container
docker rm "$BUILDER_CONTAINER" > /dev/null

# Verify binary exists
if [ ! -f "$PROJECT_ROOT/dist/strix" ]; then
    echo -e "${RED}Build failed: Binary not found in dist/${NC}" >&2
    exit 1
fi

echo -e "\n${GREEN}Binary built successfully!${NC}"

# Platform-specific packaging
RELEASE_DIR="$PROJECT_ROOT/dist/release"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

if [ "$OS_NAME" = "windows" ]; then
    BINARY_NAME="strix-${STRIX_VERSION}-windows-${ARCH_NAME}.exe"
    cp "$PROJECT_ROOT/dist/strix" "$RELEASE_DIR/$BINARY_NAME"

    echo -e "\n${BLUE}Creating zip archive...${NC}"
    ARCHIVE_NAME="strix-${STRIX_VERSION}-windows-${ARCH_NAME}.zip"
    if command -v 7z &> /dev/null; then
        7z a "$RELEASE_DIR/$ARCHIVE_NAME" "$RELEASE_DIR/$BINARY_NAME" > /dev/null
    else
        powershell -Command "Compress-Archive -Path '$RELEASE_DIR/$BINARY_NAME' -DestinationPath '$RELEASE_DIR/$ARCHIVE_NAME'" 2>/dev/null || {
            echo -e "${RED}Error: Neither 7z nor PowerShell available for zip creation${NC}" >&2
            exit 1
        }
    fi
    echo -e "${GREEN}Created:${NC} $RELEASE_DIR/$ARCHIVE_NAME"
else
    # Linux
    BINARY_NAME="strix-${STRIX_VERSION}-linux-${ARCH_NAME}"
    cp "$PROJECT_ROOT/dist/strix" "$RELEASE_DIR/$BINARY_NAME"
    chmod +x "$RELEASE_DIR/$BINARY_NAME"

    echo -e "\n${BLUE}Creating tarball...${NC}"
    ARCHIVE_NAME="strix-${STRIX_VERSION}-linux-${ARCH_NAME}.tar.gz"
    tar -czf "$RELEASE_DIR/$ARCHIVE_NAME" -C "$RELEASE_DIR" "$BINARY_NAME"
    echo -e "${GREEN}Created:${NC} $RELEASE_DIR/$ARCHIVE_NAME"
fi

# Summary
echo -e "\n${GREEN}Build successful!${NC}"
echo "================================"
echo -e "${YELLOW}Binary:${NC} $RELEASE_DIR/$BINARY_NAME"

if [ "$OS_NAME" != "windows" ]; then
    SIZE=$(ls -lh "$RELEASE_DIR/$BINARY_NAME" | awk '{print $5}')
    echo -e "${YELLOW}Size:${NC} $SIZE"

    echo -e "\n${BLUE}Testing binary...${NC}"
    if "$RELEASE_DIR/$BINARY_NAME" --help > /dev/null 2>&1; then
        echo -e "${GREEN}Binary test passed!${NC}"
    else
        echo -e "${RED}Binary test failed — --help returned non-zero${NC}" >&2
    fi
fi

echo -e "\n${GREEN}Done!${NC}"
