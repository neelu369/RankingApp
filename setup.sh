#!/bin/bash

echo "🏆 Universal Ranking App - Setup Script"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.10 or higher is required. You have Python $python_version"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK: $python_version${NC}"

# Check Node.js version
echo -e "${YELLOW}Checking Node.js version...${NC}"
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi
node_version=$(node --version | cut -d'v' -f2)
echo -e "${GREEN}✓ Node.js version OK: $node_version${NC}"

# Check MongoDB
echo -e "${YELLOW}Checking MongoDB...${NC}"
if ! command -v mongod &> /dev/null; then
    echo "Warning: MongoDB not found locally. Will use MongoDB URI from .env"
else
    echo -e "${GREEN}✓ MongoDB found${NC}"
fi

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv venv
echo -e "${GREEN}✓ Virtual environment created${NC}"

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Install Playwright browsers
echo -e "${YELLOW}Installing Playwright browsers...${NC}"
playwright install
echo -e "${GREEN}✓ Playwright browsers installed${NC}"

# Set up environment file
echo -e "${YELLOW}Setting up environment variables...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env file and add your API keys${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Install frontend dependencies
echo -e "${YELLOW}Installing frontend dependencies...${NC}"
cd frontend
npm install
cd ..
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

echo ""
echo "========================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys:"
echo "   - REPLICATE_API_KEY"
echo "   - OPENAI_API_KEY"
echo "   - MONGODB_URI (if using external MongoDB)"
echo ""
echo "2. Start MongoDB (if running locally):"
echo "   mongod"
echo ""
echo "3. Start the backend:"
echo "   source venv/bin/activate"
echo "   cd backend && python main.py"
echo ""
echo "4. Start the frontend (in a new terminal):"
echo "   cd frontend && npm start"
echo ""
echo "5. Open http://localhost:3000 in your browser"
echo ""
echo "Happy ranking! 🏆"
