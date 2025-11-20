#!/bin/bash

# Falcon Finance Deployment Script
# Usage: ./deploy.sh

set -e

echo "🦅 Starting Falcon Finance Deployment..."

# 1. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker installed."
else
    echo "✅ Docker is already installed."
fi

# 2. Check for Docker Compose
if ! docker compose version &> /dev/null; then
     echo "🐳 Docker Compose plugin not found. Installing..."
     sudo apt-get update
     sudo apt-get install -y docker-compose-plugin
     echo "✅ Docker Compose installed."
fi

# 3. Setup Environment
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    # In a real scenario, you might pull this from a secure vault or ask user input
    # For now, we create a basic one
    cat <<EOF > .env
POSTGRES_PASSWORD=$(openssl rand -hex 16)
STRIPE_SECRET_KEY=sk_test_placeholder
STRIPE_WEBHOOK_SECRET=whsec_placeholder
ALERTS_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/placeholder
OPENAI_KEY=sk-placeholder
EOF
    echo "⚠️  Created .env with placeholder values. PLEASE EDIT IT!"
else
    echo "✅ .env file exists."
fi

# 4. Build and Launch
echo "🚀 Launching Production Stack..."
docker compose -f docker-compose.prod.yml up -d --build

echo "
✨ Deployment Complete!
-----------------------
🌍 Sales Page: http://localhost:8080
📊 Dashboard:  http://localhost:8002
📚 API Docs:   http://localhost:8000
gateway:       http://localhost:8010

👉 Next Step: Configure your .env file with real keys and restart:
   nano .env
   docker compose -f docker-compose.prod.yml up -d
"
