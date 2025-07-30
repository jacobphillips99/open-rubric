#!/bin/bash
# Installation script for remote SSH box setup
set -e

curl -LsSf https://astral.sh/uv/install.sh | sh

# Source shell configuration to make uv available in current session
source ~/.zshrc

# Install system monitoring tools
echo "Installing system monitoring tools..."

# Detect OS and install nvtop and btop
if command -v apt &> /dev/null; then
    # Ubuntu/Debian
    sudo apt update
    sudo apt install -y nvtop btop
elif command -v dnf &> /dev/null; then
    # Fedora/RHEL/CentOS  
    sudo dnf install -y nvtop btop
elif command -v brew &> /dev/null; then
    # macOS with Homebrew
    brew install nvtop btop
else
    # Fallback to snap if available
    if command -v snap &> /dev/null; then
        sudo snap install nvtop
        sudo snap install btop
    else
        echo "Warning: Could not install nvtop and btop - no supported package manager found"
    fi
fi

# Clone repository if not already in it
if [[ ! -f "pyproject.toml" ]]; then
    git clone https://github.com/jacobphillips99/open-rubric.git
    cd open-rubric
fi

# Install dependencies
uv sync --extra all
uv pip install flash-attn --no-build-isolation
uv pip install -e .

echo "Installation complete!"
