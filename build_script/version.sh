#!/bin/bash
# version.sh — Single-source version extraction from pyproject.toml
#
# Usage: source this file in other build scripts
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "$SCRIPT_DIR/version.sh"
#
# Sets: STRIX_VERSION
# Requires: pyproject.toml at PROJECT_ROOT

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "ERROR: pyproject.toml not found at $PROJECT_ROOT" >&2
    echo "This script must be run from the project root or a build_script/ subdirectory." >&2
    exit 1
fi

STRIX_VERSION=$(grep '^version' "$PROJECT_ROOT/pyproject.toml" | head -1 | sed 's/.*"\(.*\)"/\1/')

if [ -z "$STRIX_VERSION" ]; then
    echo "ERROR: Could not extract version from pyproject.toml" >&2
    echo "Expected a line like: version = \"1.2.3\"" >&2
    exit 1
fi
