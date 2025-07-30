#!/bin/bash
# Installation script for remote SSH box setup
set -e

curl -LsSf https://astral.sh/uv/install.sh | sh

# Source shell configuration to make uv available in current session
source ~/.zshrc

# Install system monitoring tools
echo "Installing system monitoring tools..."

# Detect OS and install nvtop, btop, and tmux
if command -v apt &> /dev/null; then
    # Ubuntu/Debian
    apt update
    apt install -y nvtop btop tmux
elif command -v dnf &> /dev/null; then
    # Fedora/RHEL/CentOS
    dnf install -y nvtop btop tmux
elif command -v yum &> /dev/null; then
    # Older RHEL/CentOS
    yum install -y tmux
    # nvtop and btop might not be available in older repos
    echo "Note: nvtop and btop may need to be installed from EPEL or compiled from source"
elif command -v apk &> /dev/null; then
    # Alpine Linux
    apk update
    apk add tmux
    echo "Note: nvtop and btop may need to be installed manually on Alpine"
elif command -v brew &> /dev/null; then
    # macOS with Homebrew
    brew install nvtop btop tmux
else
    echo "Warning: Could not detect package manager"
    echo "You may need to install tmux, nvtop, and btop manually"
fi

# Configure tmux with scrolling enabled
echo "Configuring tmux..."
cat > ~/.tmux.conf << 'EOF'
# Enable mouse mode (scrolling, pane selection, etc.)
set -g mouse on

# Increase scrollback buffer size
set -g history-limit 10000

# Improve colors
set -g default-terminal "screen-256color"

# Enable vi mode
setw -g mode-keys vi

# Better copy/paste bindings
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi r send-keys -X rectangle-toggle

# Easy config reload
bind-key r source-file ~/.tmux.conf \; display-message "~/.tmux.conf reloaded"

# Better pane splitting
bind | split-window -h
bind - split-window -v

# Enable clipboard integration (if available)
set -g set-clipboard on

# macOS clipboard integration
if command -v pbcopy &> /dev/null; then
    bind-key -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"
    bind-key -T copy-mode-vi Enter send-keys -X copy-pipe-and-cancel "pbcopy"
fi

# Status bar configuration  
set -g status-bg green
set -g status-fg black
set -g status-left-length 40
set -g status-left "#[fg=black,bold]Session: #S #[fg=black]#I #[fg=black]#P"
set -g status-right "#[fg=black]%d %b %R"
set -g status-interval 60
EOF

echo "Tmux configuration saved to ~/.tmux.conf"

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
echo "To use tmux with scrolling:"
echo "  - Start tmux: 'tmux'"
echo "  - Scroll with mouse wheel or trackpad"
echo "  - Reload config: 'tmux source ~/.tmux.conf'"
