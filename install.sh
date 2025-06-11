#!/bin/bash
# Quick installation script for Memgraph Knowledge Graph Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Memgraph Knowledge Graph Server Installation${NC}"
echo "=================================================="

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ git is not installed. Please install git first.${NC}"
    exit 1
fi

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl is not installed. Please install curl first.${NC}"
    exit 1
fi

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}📦 Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    
    # Check if uv is now available
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}❌ Failed to install uv. Please install manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ uv installed successfully${NC}"
else
    echo -e "${GREEN}✅ uv already installed${NC}"
fi

# Install git-lfs if not present
if ! git lfs version &> /dev/null; then
    echo -e "${YELLOW}📦 Installing git-lfs...${NC}"
    
    # Try to install git-lfs based on the OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y git-lfs
        elif command -v yum &> /dev/null; then
            sudo yum install -y git-lfs
        elif command -v pacman &> /dev/null; then
            sudo pacman -S git-lfs
        else
            echo -e "${YELLOW}⚠️  Could not auto-install git-lfs. Please install manually.${NC}"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install git-lfs
        else
            echo -e "${YELLOW}⚠️  Please install git-lfs manually: brew install git-lfs${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Please install git-lfs manually for your system${NC}"
    fi
    
    # Initialize git-lfs
    git lfs install
    echo -e "${GREEN}✅ git-lfs configured${NC}"
else
    echo -e "${GREEN}✅ git-lfs already installed${NC}"
fi

# Clone repository if we're not already in it
if [ ! -f "pyproject.toml" ] || [ ! -d "memgraph" ]; then
    echo -e "${BLUE}📂 Cloning repository...${NC}"
    echo "Please enter the repository URL:"
    read -r REPO_URL
    
    if [ -z "$REPO_URL" ]; then
        echo -e "${RED}❌ No repository URL provided${NC}"
        exit 1
    fi
    
    git clone "$REPO_URL" memgraph-server
    cd memgraph-server
    echo -e "${GREEN}✅ Repository cloned${NC}"
else
    echo -e "${GREEN}✅ Already in memgraph repository${NC}"
fi

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
uv sync

# Test installation
echo -e "${BLUE}🧪 Testing installation...${NC}"
if uv run launcher.py --help > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Installation successful!${NC}"
else
    echo -e "${RED}❌ Installation test failed${NC}"
    exit 1
fi

# Show completion message
echo ""
echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo "=========================="
echo ""
echo "Quick start commands:"
echo -e "  ${BLUE}uv run launcher.py${NC}          # Start the server"
echo -e "  ${BLUE}uv run launcher.py --status${NC}  # Check server status"
echo -e "  ${BLUE}uv run launcher.py --stop${NC}    # Stop the server"
echo -e "  ${BLUE}make run${NC}                    # Alternative start (if make available)"
echo -e "  ${BLUE}make help${NC}                   # Show all available commands"
echo ""
echo "Development utilities:"
echo -e "  ${BLUE}uv run dev_utils.py test${NC}     # Test server endpoints"
echo -e "  ${BLUE}uv run dev_utils.py stats${NC}    # Show server statistics"
echo -e "  ${BLUE}uv run dev_utils.py monitor${NC}  # Monitor server health"
echo ""
echo -e "The server will be available at: ${BLUE}http://localhost:8080${NC}"
echo -e "Configuration and logs: ${BLUE}~/.memgraph/${NC}"
echo ""
echo -e "${YELLOW}💡 Tip: Run 'make setup' to verify all dependencies are correct${NC}"
