#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting E-Commerce AI Assistant (Local Mode)${NC}"

# Function to kill processes on exit
cleanup() {
    echo -e "\n${RED}🛑 Stopping services...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit
}

trap cleanup SIGINT SIGTERM

# 1. Load Environment Variables
if [ -f .env ]; then
    echo -e "${GREEN}📝 Loading .env file...${NC}"
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
else
    echo -e "${RED}❌ .env file not found! Please create one.${NC}"
    exit 1
fi

# 2. Dependency Check & Install
echo -e "${BLUE}📦 Checking dependencies...${NC}"

# Backend Dependencies
if [ -f "requirements.txt" ]; then
    echo -e "   Installing backend dependencies..."
    pip install -r requirements.txt > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "   ${GREEN}Backend dependencies installed.${NC}"
    else
        echo -e "   ${RED}Failed to install backend dependencies.${NC}"
    fi
fi

# 3. Port Configuration
BACKEND_PORT=8001
FRONTEND_PORT=3001

echo -e "${BLUE}📋 Port Configuration:${NC}"
echo -e "   Backend:  $BACKEND_PORT"
echo -e "   Frontend: $FRONTEND_PORT"
echo ""

# 4. Check for npm
# Check for npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed.${NC}"
    echo -e "${YELLOW}Running in BACKEND-ONLY mode.${NC}"
    echo -e "${YELLOW}You can test the API using 'python3 tests/api_test.py' or curl.${NC}"
    echo -e "${BLUE}Backend is running at http://localhost:$BACKEND_PORT${NC}"
    echo -e "${BLUE}Press Ctrl+C to stop.${NC}"
    wait $BACKEND_PID
    exit 0
fi

# Check Node version and install if needed
NODE_VERSION=$(node -v 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1)
if [ -z "$NODE_VERSION" ] || [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${YELLOW}⚠️  Node.js version is ${NODE_VERSION:-missing} (Required: 18+).${NC}"
    echo -e "${BLUE}📦 Installing NVM and Node.js 18...${NC}"
    
    # Define NVM directory
    export NVM_DIR="$HOME/.nvm"
    
    # Install NVM if not present
    if [ ! -d "$NVM_DIR" ]; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    fi
    
    # Load NVM
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    
    # Install and use Node 18
    nvm install 18
    nvm use 18
    
    # Verify installation
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        echo -e "${GREEN}✅ Node.js updated to $(node -v)${NC}"
    else
        echo -e "${RED}❌ Failed to update Node.js. Running in BACKEND-ONLY mode.${NC}"
        echo -e "${BLUE}Backend is running at http://localhost:$BACKEND_PORT${NC}"
        wait $BACKEND_PID
        exit 0
    fi
fi

# Function to kill process on a port
kill_port() {
    local port=$1
    echo -e "${YELLOW}⚠️  Checking port $port...${NC}"
    if fuser -k -9 $port/tcp > /dev/null 2>&1; then
        echo -e "${GREEN}   Port $port cleared (process killed).${NC}"
        sleep 2 # Wait for socket to release
    else
        echo -e "${GREEN}   Port $port is free.${NC}"
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local timeout=60
    local count=0
    echo -e "${BLUE}⏳ Waiting for $service_name at $url...${NC}"
    while ! curl -s $url > /dev/null; do
        sleep 1
        count=$((count+1))
        if [ $count -ge $timeout ]; then
            echo -e "${RED}❌ $service_name did not become ready in time.${NC}"
            cleanup
        fi
        echo -n "."
    done
    echo -e "\n${GREEN}✅ $service_name is ready.${NC}"
}

# 1. Cleanup Ports
echo -e "${BLUE}🧹 Cleaning up ports $BACKEND_PORT and $FRONTEND_PORT...${NC}"
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# 2. Start Backend
echo -e "${BLUE}🚀 Starting Backend on port $BACKEND_PORT...${NC}"
export PYTHONPATH=$PYTHONPATH:$(pwd)
export PORT=$BACKEND_PORT
mkdir -p logs # Ensure logs directory exists
python3 ai_server/server.py > server_debug.txt 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}   Backend started (PID $BACKEND_PID). Logs: server_debug.txt${NC}"

# Wait for backend to be ready
wait_for_service "http://localhost:$BACKEND_PORT/health" "Backend"

# 3. Start Frontend
echo -e "${BLUE}⚛️  Starting Frontend on port $FRONTEND_PORT...${NC}"
cd frontend

# Install dependencies if needed (fast check)
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install --ignore-scripts > /dev/null 2>&1
fi

export BACKEND_URL="http://localhost:$BACKEND_PORT"
export NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT"
# Ensure Next.js picks up the env var
npm run dev -- -p $FRONTEND_PORT > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}✅ Services started successfully!${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   🌐 Frontend:${NC} http://localhost:$FRONTEND_PORT"
echo -e "${GREEN}   🔧 Backend:${NC}  http://localhost:$BACKEND_PORT"
echo -e "${GREEN}   📚 API Docs:${NC} http://localhost:$BACKEND_PORT/docs"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo -e "   Backend:  server_debug.txt"
echo -e "   Frontend: frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
