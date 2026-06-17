#!/bin/bash
# build-sandbox.sh — Build Docker sandbox image for strix
#
# Usage:
#   bash build_script/build-sandbox.sh          Build locally with version + latest tags
#   bash build_script/build-sandbox.sh --push   Build and push to Docker Hub
#
# Image: usestrix/strix-sandbox:{VERSION} and usestrix/strix-sandbox:latest
# Dockerfile: containers/Dockerfile
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

IMAGE="usestrix/strix-sandbox"
DOCKERFILE="$PROJECT_ROOT/containers/Dockerfile"
PUSH_MODE=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --push) PUSH_MODE=true ;;
        *)      echo -e "${RED}Error: Unknown argument: $arg${NC}" >&2
                echo "Usage: bash build_script/build-sandbox.sh [--push]" >&2
                exit 1 ;;
    esac
done

echo -e "${BLUE}Strix Sandbox Image Build Script${NC}"
echo "============================================"
echo -e "${YELLOW}Image:${NC} $IMAGE"
echo -e "${YELLOW}Version:${NC} $STRIX_VERSION"
echo -e "${YELLOW}Dockerfile:${NC} containers/Dockerfile"

if [ "$PUSH_MODE" = true ]; then
    echo -e "${YELLOW}Mode:${NC} Build + Push"
else
    echo -e "${YELLOW}Mode:${NC} Build only (use --push to push to Docker Hub)"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not on PATH${NC}" >&2
    exit 1
fi

# Check Dockerfile
if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${RED}Error: Dockerfile not found: $DOCKERFILE${NC}" >&2
    exit 1
fi

cd "$PROJECT_ROOT"

echo -e "\n${BLUE}Building sandbox image...${NC}"
echo "This may take several minutes on first build..."

docker build \
    -f "$DOCKERFILE" \
    -t "$IMAGE:$STRIX_VERSION" \
    -t "$IMAGE:latest" \
    "$PROJECT_ROOT"

echo -e "\n${GREEN}Image built successfully!${NC}"
echo -e "${YELLOW}Tags:${NC}"
echo "  $IMAGE:$STRIX_VERSION"
echo "  $IMAGE:latest"

# Show image size
IMAGE_SIZE=$(docker images "$IMAGE:$STRIX_VERSION" --format "{{.Size}}" 2>/dev/null || echo "unknown")
echo -e "${YELLOW}Size:${NC} $IMAGE_SIZE"

if [ "$PUSH_MODE" = true ]; then
    echo -e "\n${BLUE}Pushing to Docker Hub...${NC}"

    echo -e "${BLUE}Pushing $IMAGE:$STRIX_VERSION ...${NC}"
    if docker push "$IMAGE:$STRIX_VERSION"; then
        echo -e "${GREEN}Pushed: $IMAGE:$STRIX_VERSION${NC}"
    else
        echo -e "${RED}Failed to push $IMAGE:$STRIX_VERSION${NC}" >&2
        echo "Check that you are logged in: docker login" >&2
        exit 1
    fi

    echo -e "${BLUE}Pushing $IMAGE:latest ...${NC}"
    if docker push "$IMAGE:latest"; then
        echo -e "${GREEN}Pushed: $IMAGE:latest${NC}"
    else
        echo -e "${RED}Failed to push $IMAGE:latest${NC}" >&2
        exit 1
    fi

    echo -e "\n${GREEN}Push complete!${NC}"
fi

echo -e "\n${GREEN}Done!${NC}"
