#!/bin/bash
# 🦅 Falcon Finance Deployment Script
# Usage: ./deploy.sh [dev|prod]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV="${1:-dev}"

echo "🦅 Falcon Finance Deployment"
echo "================================"
echo "Environment: $ENV"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found! Copying from .env.example..."
    cp .env.example .env
    echo "📝 PLEASE EDIT .env WITH YOUR ACTUAL SECRETS!"
    echo "   Then run: ./deploy.sh $ENV"
    exit 1
fi

# Validate required environment variables
source .env
REQUIRED_VARS=("STRIPE_SECRET_KEY" "STRIPE_WEBHOOK_SECRET")
MISSING=""

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ] || [[ "${!var}" == *"..."* ]] || [[ "${!var}" == *"your_"* ]]; then
        MISSING="$MISSING $var"
    fi
done

if [ -n "$MISSING" ]; then
    echo "⚠️  Missing or placeholder values for:$MISSING"
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
    docker-compose -f docker-compose.prod.yml up -d --build
else
    echo "🔧 Starting DEVELOPMENT stack..."
    docker-compose up -d --build
fi

# Wait for services
echo ""
echo "⏳ Waiting for services to start..."
sleep 5
wait_for_health "http://localhost:8010/health" "API Gateway" || true
wait_for_health "http://localhost:8011/health" "Billing" || true

echo ""
echo "================================"
echo "🎉 Deployment Complete!"
echo ""
echo "📍 Service URLs:"
echo "   • Landing Page:  http://localhost:8080"
echo "   • API Gateway:   http://localhost:8010"
echo "   • Billing:       http://localhost:8011"
echo "   • Alerts:        http://localhost:8012"
echo "   • Dashboard:     http://localhost:8002"
echo ""
echo "📋 Next steps:"
echo "   1. Create an API key: python scripts/create_api_key.py create --plan pro"
echo "   2. Test the API: curl -H 'X-API-Key: YOUR_KEY' http://localhost:8010/whoami"
echo ""
