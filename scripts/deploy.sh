#!/bin/bash
# 🦅 Falcon Finance Deployment Script
# Usage: ./scripts/deploy.sh [dev|prod]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV="${1:-dev}"

echo "🦅 Falcon Finance Deployment"
echo "================================"
echo "Environment: $ENV"
echo "Project Root: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT"

# Check for required files
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Copy .env.example to .env and fill in your values"
    exit 1
fi

# Validate required environment variables
source .env
REQUIRED_VARS=("STRIPE_SECRET_KEY" "STRIPE_WEBHOOK_SECRET" "POSTGRES_PASSWORD")
MISSING=""

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ] || [[ "${!var}" == *"..."* ]] || [[ "${!var}" == *"your_"* ]]; then
        MISSING="$MISSING $var"
    fi
done

if [ -n "$MISSING" ]; then
    echo "⚠️  Missing or placeholder values for:$MISSING"
    echo "   Please update your .env file with real values"
    if [ "$ENV" == "prod" ]; then
        echo "   Cannot deploy to production with missing values"
        exit 1
    fi
fi

# Function to check if service is healthy
wait_for_health() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "   Waiting for $name..."
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo " ✅"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    echo " ❌ (timeout)"
    return 1
}

if [ "$ENV" == "prod" ]; then
    echo "🚀 Deploying PRODUCTION stack..."
    
    # Pull latest images
    docker-compose -f docker-compose.prod.yml pull
    
    # Build and start
    docker-compose -f docker-compose.prod.yml up -d --build
    
    # Wait for services
    echo ""
    echo "⏳ Waiting for services to start..."
    wait_for_health "http://localhost:8010/health" "API Gateway"
    wait_for_health "http://localhost:8011/health" "Billing"
    wait_for_health "http://localhost:8012/health" "Alerts"
    wait_for_health "http://localhost:8002/health" "Dashboard"
    
else
    echo "🔧 Starting DEVELOPMENT stack..."
    
    # Build and start with dev compose
    docker-compose up -d --build
    
    # Wait for services
    echo ""
    echo "⏳ Waiting for services to start..."
    sleep 5
    wait_for_health "http://localhost:8010/health" "API Gateway"
    wait_for_health "http://localhost:8011/health" "Billing"
fi

echo ""
echo "================================"
echo "🎉 Deployment Complete!"
echo ""
echo "📍 Service URLs:"
echo "   • API Gateway:  http://localhost:8010"
echo "   • Billing:      http://localhost:8011"
echo "   • Alerts:       http://localhost:8012"
echo "   • Dashboard:    http://localhost:8002"
echo "   • Landing Page: http://localhost:8080"
echo "   • API Docs:     http://localhost:8000"
echo ""
echo "📋 Useful commands:"
echo "   • View logs:    docker-compose logs -f"
echo "   • Stop:         docker-compose down"
echo "   • Restart:      docker-compose restart"
echo ""

# Show quick health check
echo "🏥 Health Check:"
for service in "8010:API Gateway" "8011:Billing" "8012:Alerts"; do
    port="${service%%:*}"
    name="${service##*:}"
    if curl -sf "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "   ✅ $name (port $port)"
    else
        echo "   ❌ $name (port $port) - not responding"
    fi
done
