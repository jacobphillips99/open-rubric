#!/bin/bash
set -e

# Install uv package manager (installs to ~/.cargo/bin via Rust toolchain)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository if not already in it
if [[ ! -f "pyproject.toml" ]]; then
    git clone https://github.com/jacobphillips99/open-rubric.git
    cd open-rubric
fi

# Install dependencies
uv sync --extra all
uv pip install flash-attn --no-build-isolation

echo "Installation complete!"
echo "Set API keys: export OPENAI_API_KEY='your-key'"
