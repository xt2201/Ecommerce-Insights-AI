#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print with color
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Error handling
set -e
trap 'print_error "An error occurred. Exiting..."; exit 1' ERR

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 E-Commerce AI Shopping Assistant - Docker Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Docker is running, if not, try to start it
if ! docker info > /dev/null 2>&1; then
    print_warning "Docker is not running. Attempting to start Docker..."
    
    # Detect OS and start Docker accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        print_step "Starting Docker Desktop on macOS..."
        open -a Docker
        
        # Wait for Docker to start (max 60 seconds)
        print_step "Waiting for Docker to start..."
        for i in {1..60}; do
            if docker info > /dev/null 2>&1; then
                print_success "Docker started successfully"
                break
            fi
            if [ $i -eq 60 ]; then
                print_error "Docker failed to start within 60 seconds"
                print_error "Please start Docker Desktop manually and try again"
                exit 1
            fi
            sleep 1
        done
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux with systemd
        print_step "Starting Docker on Linux..."
        
        # Check if Docker is installed
        if ! command -v docker &> /dev/null; then
            print_error "Docker is not installed. Please install Docker first:"
            echo "   Ubuntu/Debian: sudo apt-get install docker.io"
            echo "   Fedora: sudo dnf install docker"
            echo "   Arch: sudo pacman -S docker"
            exit 1
        fi
        
        # Try to start Docker service
        if command -v systemctl &> /dev/null; then
            print_step "Attempting to start Docker service..."
            # WARNING: Hardcoding password is a security risk!
            if echo "1" | sudo -S systemctl start docker 2>/dev/null; then
                sleep 3
                if docker info > /dev/null 2>&1; then
                    print_success "Docker started successfully"
                else
                    print_warning "Docker service started but not ready yet. Waiting..."
                    sleep 5
                    if docker info > /dev/null 2>&1; then
                        print_success "Docker is now ready"
                    else
                        print_error "Docker started but not responding."
                        echo ""
                        echo "Please try manually:"
                        echo "   sudo systemctl start docker"
                        echo "   sudo systemctl enable docker"
                        echo "   sudo usermod -aG docker $USER"
                        echo "   newgrp docker"
                        exit 1
                    fi
                fi
            else
                print_error "Failed to start Docker service."
                echo ""
                echo "Please start Docker manually:"
                echo "   sudo systemctl start docker"
                echo "   sudo systemctl status docker  # Check status"
                echo ""
                echo "If you need to add your user to docker group:"
                echo "   sudo usermod -aG docker $USER"
                echo "   newgrp docker  # Or logout and login again"
                exit 1
            fi
        else
            print_error "systemctl not found. Cannot auto-start Docker."
            echo ""
            echo "Please start Docker manually and try again."
            exit 1
        fi
    else
        print_error "Unsupported OS. Please start Docker manually and try again."
        exit 1
    fi
else
    print_success "Docker is already running"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your API keys before continuing."
        exit 1
    else
        print_error "No .env or .env.example file found"
        exit 1
    fi
fi

print_success ".env file found"
echo ""

# Step 1: Stop and remove old containers
print_step "Stopping and removing old containers..."
docker-compose down --remove-orphans 2>/dev/null || true
print_success "Old containers removed"
echo ""

# Step 2: Build images
print_step "Building Docker images (this may take a few minutes)..."
docker-compose build --no-cache
print_success "Images built successfully"
echo ""

# Step 3: Start services
print_step "Starting services in detached mode..."
docker-compose up -d
print_success "Services started"
echo ""

# Step 4: Wait for services to be healthy
print_step "Waiting for services to be healthy..."
sleep 5

# Check backend health
print_step "Checking backend health..."
for i in {1..30}; do
    if docker-compose exec -T backend python -c "import requests; requests.get('http://localhost:8000/health')" 2>/dev/null; then
        print_success "Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Backend health check timeout"
        docker-compose logs backend
        exit 1
    fi
    sleep 2
done

# Check frontend health
print_step "Checking frontend health..."
for i in {1..30}; do
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        print_success "Frontend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Frontend health check timeout"
        docker-compose logs frontend
        exit 1
    fi
    sleep 2
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "All services are up and running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""

# Extract actual ports from docker-compose.yml
FRONTEND_PORT=$(grep -A 5 "frontend:" docker-compose.yml | grep "ports:" -A 1 | grep -oP '"\K[0-9]+(?=:)' | head -1)
BACKEND_PORT=$(grep -A 5 "backend:" docker-compose.yml | grep "ports:" -A 1 | grep -oP '"\K[0-9]+(?=:)' | head -1)

# Fallback to defaults if extraction fails
FRONTEND_PORT=${FRONTEND_PORT:-3000}
BACKEND_PORT=${BACKEND_PORT:-8000}

echo "🌐 Access URLs:"
echo "   Frontend: ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo "   Backend:  ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo "   API Docs: ${GREEN}http://localhost:${BACKEND_PORT}/docs${NC}"
echo ""
echo "📝 Useful commands:"
echo "   View logs:        docker-compose logs -f"
echo "   View backend:     docker-compose logs -f backend"
echo "   View frontend:    docker-compose logs -f frontend"
echo "   Stop services:    docker-compose down"
echo "   Restart:          docker-compose restart"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
