#!/bin/bash
# build-all.sh — Full strix build pipeline orchestrator
#
# Usage: bash build_script/build-all.sh
#
# Runs build-binary.sh and build-sandbox.sh sequentially,
# then generates SHA256 checksums for all dist/ artifacts.
#
# Requirements: Docker

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

trap 'error_exit "Build pipeline aborted."' ERR

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}  Strix Full Build Pipeline${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# Step 1: Build binaries
echo -e "${BLUE}[1/3] Building binaries...${NC}"
if ! bash "$SCRIPT_DIR/build-binary.sh"; then
    echo -e "${RED}  ✗ Binary build failed${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Binaries built${NC}"
echo ""

# Step 2: Build sandbox image
echo -e "${BLUE}[2/3] Building sandbox image...${NC}"
if ! bash "$SCRIPT_DIR/build-sandbox.sh"; then
    echo -e "${RED}  ✗ Sandbox image build failed${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Sandbox image built${NC}"
echo ""

# Step 3: Generate checksums
echo -e "${BLUE}[3/3] Generating checksums...${NC}"
if [ ! -d "$PROJECT_ROOT/dist" ]; then
    error_exit "dist/ directory not found — build steps may have failed silently"
fi
cd "$PROJECT_ROOT/dist"
sha256sum * > checksums.txt
if [ ! -f checksums.txt ]; then
    error_exit "checksums.txt was not created"
fi
echo -e "${GREEN}  ✓ Checksums generated${NC}"
echo ""

echo "────────────────────────────────────────"
cat checksums.txt
echo "────────────────────────────────────────"
echo ""

echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  Build pipeline complete${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "Output files:"
ls -lh "$PROJECT_ROOT/dist/"
