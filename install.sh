#!/bin/bash
# Zabob Memgraph Installation Script
# This is a simple wrapper that downloads and runs the Python installation script

set -e

echo "🧠 Zabob Memgraph Knowledge Graph Server"
echo "========================================"
echo ""

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ uv is required but not installed."
    echo ""
    echo "Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "Then restart your terminal or run:"
    echo "  source ~/.bashrc"
    echo ""
    exit 1
fi

echo "✅ uv found"
echo ""

# Download and run the Python installation script
INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/your-username/zabob-memgraph/main/zabob-memgraph-install.py"
TEMP_SCRIPT="/tmp/zabob-memgraph-install.py"

echo "📥 Downloading installation script..."

if command -v curl &> /dev/null; then
    curl -L -o "$TEMP_SCRIPT" "$INSTALL_SCRIPT_URL"
elif command -v wget &> /dev/null; then
    wget -O "$TEMP_SCRIPT" "$INSTALL_SCRIPT_URL"
else
    echo "❌ Neither curl nor wget found. Please install one of them."
    exit 1
fi

echo "🚀 Running installation..."
chmod +x "$TEMP_SCRIPT"
"$TEMP_SCRIPT" install "$@"

# Clean up
rm -f "$TEMP_SCRIPT"

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "  zabob-memgraph start     # Start the server"
echo "  zabob-memgraph --help    # Get help"
