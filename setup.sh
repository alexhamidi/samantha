#!/bin/bash

set -e

echo "🎵 Samantha Setup Script"
echo "========================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
fi

echo -e "${BLUE}Detected OS: $OS${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install ffmpeg
echo -e "${YELLOW}📦 Checking ffmpeg...${NC}"
if command_exists ffmpeg; then
    echo -e "${GREEN}✓ ffmpeg is already installed${NC}"
else
    echo -e "${YELLOW}Installing ffmpeg...${NC}"
    if [ "$OS" == "macos" ]; then
        if ! command_exists brew; then
            echo -e "${RED}Error: Homebrew is not installed. Please install it from https://brew.sh${NC}"
            exit 1
        fi
        brew install ffmpeg
    elif [ "$OS" == "linux" ]; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    else
        echo -e "${RED}Unsupported OS. Please install ffmpeg manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ ffmpeg installed${NC}"
fi
echo ""

# Install Chrome/Chromium
echo -e "${YELLOW}🌐 Checking Chrome/Chromium...${NC}"
if command_exists google-chrome || command_exists chromium || command_exists chromium-browser || [ -d "/Applications/Google Chrome.app" ]; then
    echo -e "${GREEN}✓ Chrome/Chromium is already installed${NC}"
else
    echo -e "${YELLOW}Installing Chrome...${NC}"
    if [ "$OS" == "macos" ]; then
        if ! command_exists brew; then
            echo -e "${RED}Error: Homebrew is not installed. Please install it from https://brew.sh${NC}"
            exit 1
        fi
        brew install --cask google-chrome
    elif [ "$OS" == "linux" ]; then
        sudo apt-get update
        sudo apt-get install -y wget
        wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
        sudo apt install -y ./google-chrome-stable_current_amd64.deb
        rm google-chrome-stable_current_amd64.deb
    else
        echo -e "${RED}Unsupported OS. Please install Chrome manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Chrome installed${NC}"
fi
echo ""

# Check Python
echo -e "${YELLOW}🐍 Checking Python...${NC}"
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Setup Backend
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Backend Setup${NC}"
echo -e "${BLUE}================================${NC}"
cd backend

# Check for uv and create virtual environment
echo -e "${YELLOW}📦 Setting up Python environment...${NC}"
USING_UV=false
if command_exists uv; then
    USING_UV=true
    echo -e "${GREEN}✓ uv found, using uv for faster installation${NC}"
    if [ ! -d ".venv" ]; then
        uv venv
        echo -e "${GREEN}✓ Virtual environment created with uv${NC}"
    else
        echo -e "${GREEN}✓ Virtual environment already exists${NC}"
    fi
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    echo -e "${YELLOW}uv not found, using standard pip${NC}"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo -e "${GREEN}✓ Virtual environment already exists${NC}"
    fi
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# Install Playwright browsers and dependencies
echo -e "${YELLOW}🎭 Installing Playwright browsers and dependencies...${NC}"
if command_exists uv; then
    uv run playwright install chromium
    uv run playwright install-deps chromium 2>/dev/null || {
        echo -e "${YELLOW}Note: playwright install-deps requires sudo on some systems${NC}"
        sudo uv run playwright install-deps chromium
    }
else
    playwright install chromium
    playwright install-deps chromium 2>/dev/null || {
        echo -e "${YELLOW}Note: playwright install-deps requires sudo on some systems${NC}"
        sudo playwright install-deps chromium
    }
fi
echo -e "${GREEN}✓ Playwright setup complete${NC}"
echo ""

cd ..

# Setup Frontend
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Frontend Setup${NC}"
echo -e "${BLUE}================================${NC}"
cd frontend

# Check for Node.js
echo -e "${YELLOW}📦 Checking Node.js...${NC}"
if ! command_exists node; then
    echo -e "${RED}Error: Node.js is not installed.${NC}"
    if [ "$OS" == "macos" ]; then
        echo -e "${YELLOW}Installing Node.js via Homebrew...${NC}"
        brew install node
    elif [ "$OS" == "linux" ]; then
        echo -e "${YELLOW}Installing Node.js...${NC}"
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
    else
        echo -e "${RED}Please install Node.js manually from https://nodejs.org${NC}"
        exit 1
    fi
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
echo ""

# Install frontend dependencies
echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
if command_exists bun; then
    echo -e "${GREEN}✓ bun found, using bun for faster installation${NC}"
    bun install
elif command_exists pnpm; then
    echo -e "${GREEN}✓ pnpm found, using pnpm${NC}"
    pnpm install
else
    npm install
fi
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
echo ""

cd ..

# Create necessary directories
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p backend/uploads backend/outputs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Success message
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✨ Setup Complete! ✨${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Ask if user wants to start the services
echo -e "${YELLOW}Would you like to start the application now? (y/n)${NC}"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo -e "${BLUE}🚀 Starting Samantha...${NC}"
    echo ""
    
    # Function to cleanup on exit
    cleanup() {
        echo ""
        echo -e "${YELLOW}Shutting down...${NC}"
        kill $(jobs -p) 2>/dev/null
        exit
    }
    
    trap cleanup SIGINT SIGTERM
    
    # Start backend
    echo -e "${GREEN}Starting backend on port 8000...${NC}"
    cd backend
    if [ "$USING_UV" = true ]; then
        uv run python run.py &
    else
        source .venv/bin/activate
        python run.py &
    fi
    BACKEND_PID=$!
    
    # Wait a bit for backend to start
    sleep 2
    
    # Start frontend
    echo -e "${GREEN}Starting frontend on port 3000...${NC}"
    cd ../frontend
    if command_exists bun; then
        bun dev &
    else
        npm run dev &
    fi
    FRONTEND_PID=$!
    
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}✨ Samantha is running! ✨${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo -e "${BLUE}Backend:  ${GREEN}http://localhost:8000${NC}"
    echo -e "${BLUE}Frontend: ${GREEN}http://localhost:3000${NC}"
    echo ""
    echo -e "${YELLOW}👉 Open your browser and go to: ${GREEN}http://localhost:3000${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop both services${NC}"
    echo ""
    
    # Wait for both processes
    wait
else
    echo ""
    echo -e "${BLUE}To start the application later, run:${NC}"
    echo ""
    # echo -e "${YELLOW}Terminal 1 - Backend:${NC}"
    echo -e "  cd backend"
    if [ "$USING_UV" = true ]; then
        echo -e "  uv run python run.py"
    else
        echo -e "  source .venv/bin/activate"
        echo -e "  python run.py"
    fi
    echo ""
    echo -e "${YELLOW}Terminal 2 - Frontend:${NC}"
    echo -e "  cd frontend"
    if command_exists bun; then
        echo -e "  bun dev"
    else
        echo -e "  npm run dev"
    fi
    echo ""
    echo -e "${BLUE}Then open your browser and go to: ${GREEN}http://localhost:3000${NC}"
    echo ""
fi
