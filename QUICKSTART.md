# 🦅 Falcon Finance - Quick Start Guide

Get your monetization stack running in 5 minutes!

## Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Stripe account (free test mode works)

## Step 1: Environment Setup

```bash
# Clone and enter the project
cd moon-dev-ai-agents

# Copy environment template
cp .env.example .env

# Edit .env with your values (see below)
```

### Required Environment Variables

```bash
# Get from https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY=sk_test_...

# Set a strong password
POSTGRES_PASSWORD=your_secure_password_123
```

## Step 2: Create Stripe Products

```bash
# This creates all subscription plans in Stripe
python scripts/setup_stripe_products.py
```

This will:
- Create Pro ($49/mo), Team ($149/mo), Enterprise ($299/mo) plans
- Create data pack products
- Update your .env with the price IDs

## Step 3: Deploy the Stack

```bash
# Development mode
./scripts/deploy.sh dev

# OR Production mode
./scripts/deploy.sh prod
```

## Step 4: Create Your First API Key

```bash
# Create a Pro tier key for testing
python scripts/create_api_key.py create --plan pro

# Save the key! Example output:
# Key: md_abc123...
```

## Step 5: Test Everything

```bash
# Test the API gateway
curl -H "X-API-Key: YOUR_KEY" http://localhost:8010/whoami

# Expected response:
# {"plan": "pro", "limit_per_min": 600, "mode": "keystore"}
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Landing Page | http://localhost:8080 | Sales & pricing page |
| API Gateway | http://localhost:8010 | Main API entry point |
| Billing | http://localhost:8011 | Stripe integration |
| Alerts | http://localhost:8012 | Alert management |
| Dashboard | http://localhost:8002 | Backtest dashboard |
| API Docs | http://localhost:8000 | Documentation |

## Setting Up Stripe Webhooks

1. Go to https://dashboard.stripe.com/test/webhooks
2. Add endpoint: `https://yourdomain.com/billing/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy the signing secret to `STRIPE_WEBHOOK_SECRET` in .env

## Monetization Features

### 1. API Subscriptions
Users pay monthly for API access with rate limits by tier.

### 2. Alerts Service
Sell market alerts (liquidation spikes, whale activity, etc.)

### 3. Backtest Dashboard
SaaS dashboard for running strategy backtests.

### 4. Licensed Agents
Gate premium agents (Focus, Phone, Video) by subscription tier.

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Create API keys
python scripts/create_api_key.py create --plan pro
python scripts/create_api_key.py list
python scripts/create_api_key.py revoke KEY

# Run tests
python -m pytest tests/ -v

# Stop everything
docker-compose down
```

## Revenue Projections

| Plan | Price | Target Customers | Monthly Revenue |
|------|-------|------------------|-----------------|
| Pro | $49 | 100 | $4,900 |
| Team | $149 | 30 | $4,470 |
| Enterprise | $299 | 10 | $2,990 |
| **Total** | | **140** | **$12,360** |

## Next Steps

1. ✅ Configure your domain
2. ✅ Set up SSL certificates
3. ✅ Configure production ALLOWED_ORIGINS
4. ✅ Set up monitoring (Prometheus metrics available)
5. ✅ Launch and start selling!

---

Built with 🌙 by Moon Dev
