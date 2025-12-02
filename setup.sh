#!/bin/bash

# Setup script for Redis Semantic Cache System
# This script initializes Redis and verifies the installation

set -e

echo "================================================"
echo "Redis Semantic Cache Setup"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Create redis.conf from the artifact if it doesn't exist
if [ ! -f redis.conf ]; then
    echo -e "${RED}Error: redis.conf not found${NC}"
    echo "Please create redis.conf in the current directory using the configuration artifact"
    exit 1
fi

echo -e "${GREEN}✓ redis.conf found${NC}"
echo ""

# Stop and remove existing containers (if any)
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker compose down 2>/dev/null || true

# Start Redis with Docker Compose
echo -e "${YELLOW}Starting Redis 8.4.0...${NC}"
docker compose up -d

# Wait for Redis to be ready
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec redis-semantic-cache redis-cli ping 2>/dev/null | grep -q PONG; then
        echo -e "${GREEN}✓ Redis is ready!${NC}"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}Error: Redis failed to start${NC}"
        docker compose logs redis
        exit 1
    fi
    
    sleep 1
done

echo ""
echo "================================================"
echo -e "${GREEN}Redis Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Redis is now running on:"
echo "  - Redis Protocol: localhost:6380"
echo "  - RedisInsight UI: http://localhost:5540"
echo ""
echo "Useful commands:"
echo "  - View logs:    docker compose logs -f redis"
echo "  - Stop Redis:   docker compose down"
echo "  - Restart:      docker compose restart"
echo "  - Redis CLI:    docker exec -it redis-semantic-cache redis-cli"
echo ""

# Test Redis connection
echo -e "${YELLOW}Testing Redis connection...${NC}"
docker exec redis-semantic-cache redis-cli ping

# Display Redis info
echo ""
echo -e "${YELLOW}Redis Server Info:${NC}"
docker exec redis-semantic-cache redis-cli INFO server | grep -E "redis_version|os|arch_bits|gcc_version"

# Check if search module is loaded (for vector similarity)
echo ""
echo -e "${YELLOW}Checking Redis modules...${NC}"
docker exec redis-semantic-cache redis-cli MODULE LIST || echo "Note: Redis 8.4.0-alpine may not include modules by default"

echo ""
echo -e "${GREEN}Setup complete! You can now run your semantic cache application.${NC}"
echo ""
echo "Next steps:"
echo "  1. Install Python dependencies: pip install redisvl sentence-transformers redis"
echo "  2. Run your semantic cache application"
echo "  3. Monitor with RedisInsight at http://localhost:5540"
echo ""