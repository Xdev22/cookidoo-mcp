#!/usr/bin/env bash
# Quick install for mcp-cookidoo-thermomix
# Usage: bash install.sh

set -e

# Resolve the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== mcp-cookidoo-thermomix ==="
echo ""

# 1. Check/install uv
if command -v uv &> /dev/null; then
    echo "uv OK"
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "uv OK"
fi

# 2. Install only if not already installed
if command -v mcp-cookidoo-setup &> /dev/null; then
    echo "mcp-cookidoo-thermomix OK"
else
    echo ""
    echo "Installing mcp-cookidoo-thermomix..."
    uv pip install --system "$SCRIPT_DIR"
fi

echo ""

# 3. Launch interactive setup
mcp-cookidoo-setup
