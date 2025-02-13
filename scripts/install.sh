#!/bin/bash
set -e

echo "Welcome to Basic Memory installer"

# 1. Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://github.com/astral-sh/uv/releases/download/0.1.23/uv-installer.sh | sh
fi

# 2. Configure Claude Desktop
echo "Configuring Claude Desktop..."
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Create config directory if it doesn't exist
mkdir -p "$(dirname "$CONFIG_FILE")"

# If config file doesn't exist, create it with initial structure
if [ ! -f "$CONFIG_FILE" ]; then
    echo '{"mcpServers": {}}' > "$CONFIG_FILE"
fi

# Add/update the basic-memory config using jq
jq '.mcpServers."basic-memory" = {
    "command": "uvx",
    "args": ["basic-memory"]
}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

echo "Installation complete! Basic Memory is now available in Claude Desktop."
echo "Please restart Claude Desktop for changes to take effect."

echo -e "\nQuick Start:"
echo "1. You can run sync directly using: uvx basic-memory sync"
echo "2. Optionally, install globally with: uv pip install basic-memory"
echo -e "\nBuilt with ♥️ by Basic Machines."