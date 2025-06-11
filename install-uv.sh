#!/bin/bash
# Simple uv installation script for Zabob Memgraph

set -e

echo "🚀 Installing uv..."

# Check if uv is already installed
if command -v uv &> /dev/null; then
    echo "✅ uv already installed"
    uv --version
    exit 0
fi

# Check for curl or wget
if command -v curl &> /dev/null; then
    echo "📦 Installing uv with curl..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
elif command -v wget &> /dev/null; then
    echo "📦 Installing uv with wget..."
    wget -qO- https://astral.sh/uv/install.sh | sh
else
    echo "❌ Neither curl nor wget found. Please install one of them first."
    exit 1
fi

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
if command -v uv &> /dev/null; then
    echo "✅ uv installed successfully!"
    uv --version
    echo ""
    echo "💡 You may need to restart your shell or run:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
else
    echo "❌ uv installation failed"
    exit 1
fi
