# Deployment: Moon Dev Monetization Stack

This document describes how to run the full monetization stack using Docker
Compose:

- API Gateway (keys, rate limits, usage)
- Billing Service (Stripe → keystore)
- Alerts Service (Discord alerts)
- Backtest Dashboard (multi-tenant SaaS)

## 1. Prerequisites

- Docker and Docker Compose (v2+)
- Stripe test keys (if you want billing to work end-to-end)

## 2. Services and Ports

- API Gateway: http://localhost:8010
- Billing: http://localhost:8011
- Alerts: http://localhost:8012
- Backtest Dashboard: http://localhost:8002

All services are defined in `docker-compose.yml` at the repo root.

## 3. Configure Environment

Edit `docker-compose.yml` and set these placeholders before running in
production:

- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `PRICE_ID_PRO`, `PRICE_ID_TEAM`, `PRICE_ID_ENTERPRISE`
- `ALERTS_DISCORD_WEBHOOK_URL`
- Optional gateway upstream: `UPSTREAM_API_BASE_URL`, `UPSTREAM_API_KEY`

The keystore and usage databases are stored in a named volume (`api_data`)
mounted at `/data` in the containers via:

- `KEYSTORE_DB_PATH=/data/keystore.sqlite3`
- `USAGE_DB_PATH=/data/usage.sqlite3`

Backtest data is stored under a separate volume (`backtest_data`) mounted at
`/app/src/data` inside the backtest dashboard container.

## 4. Start the Stack

From the repo root:

```bash
docker compose up --build -d
```

This will build and start:

- `moondev-api-gateway`
- `moondev-billing`
- `moondev-alerts`
- `moondev-backtest-dashboard`

Check containers:

```bash
docker compose ps
```

## 5. Basic Workflows

### 5.1 Stripe → Keys → Gateway

1. Configure Stripe env vars in `docker-compose.yml`.
2. Start the stack.
3. Use the Billing service `POST /billing/create-checkout-session` to create
   a Checkout URL.
4. After test payment completes and webhook is received, a key is
   provisioned into the keystore.
5. Use that key against the API Gateway (`X-API-Key`) and, optionally, the
   Alerts service.

### 5.2 Alerts

- Call `POST /alerts` on the Alerts service with `X-API-Key` from the
  keystore and a liquidation spike config.
- Alerts are evaluated on a schedule and posted to your Discord webhook.

### 5.3 Backtest Dashboard SaaS

- Open http://localhost:8002
- Use the API endpoints or UI to:
  - View backtests per workspace (`workspace` query or `X-API-Key`).
  - Trigger new RBI runs via `/api/backtest/run`.
- Data is stored per-workspace under `src/data/rbi_pp_multi/<workspace>`
  inside the container (persisted via `backtest_data` volume).

## 6. Licensing and Agents

Agents like Focus, Phone, Video, and Realtime Clips call the API Gateway for
license checks via the helper in `src/licensing.py`. See `docs/licensing.md`
for details.

When running these agents outside Docker on the same machine, point them at
`LICENSE_GATEWAY_URL=http://127.0.0.1:8010` and set `LICENSE_API_KEY` to a
key managed by the keystore.
