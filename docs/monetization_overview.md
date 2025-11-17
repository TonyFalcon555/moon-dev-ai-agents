# Moon Dev Monetization Overview

This repo can be run as a small stack of monetized services. This page
connects the pieces so you can see **what is being sold**, **how access
is controlled**, and **where to point customers**.

## Components

- **API Gateway** – FastAPI gateway that enforces API keys, per‑plan rate
  limits, and usage metrics.
- **Billing Service** – FastAPI + Stripe service that sells subscriptions
  and auto‑provisions API keys in the gateway keystore.
- **Alerts Service** – FastAPI service that turns Moon Dev market data
  into alert subscriptions (Discord webhooks).
- **Backtest Dashboard** – Multi‑tenant FastAPI dashboard for RBI
  backtests, with workspace isolation via API keys.
- **Licensed Agents** – Focus, Phone, Video, and Realtime Clips agents
  that check entitlements via the gateway.

All of these can be run locally or together via Docker Compose. See
`docs/deployment_stack.md` for the operational side.

## Products / What You Can Sell

### 1. Data API Plans

**Stack pieces:**

- `src/services/api_gateway` – API Gateway
- `src/services/billing` – Billing Service
- `src/services/api_gateway/keystore.py` – API key store
- `src/services/api_gateway/usage_store.py` – Usage tracking

**Value:**

- Sell tiered access to Moon Dev market data (liquidations, funding,
  OI, copybot, etc.).
- Plans map to rate limits (`free`, `pro`, `team`, `enterprise`).

**Flow:**

1. User buys a subscription via Stripe Checkout (`/billing/create-checkout-session`).
2. Stripe webhook hits `/billing/webhook`.
3. Billing service creates a key in the gateway keystore with a plan and
   optional rate‑limit override.
4. User calls your gateway with `X-API-Key: ...`.

See:

- `docs/api.md` – how MoonDevAPI consumes data
- `src/services/api_gateway/README.md`
- `src/services/billing/README.md`

### 2. Alerts SaaS

**Stack pieces:**

- `src/services/alerts` – Alerts service
- `src/agents/api.py` – Market data client

**Value:**

- Users pay for alerts instead of raw data: liquidation spikes,
  funding extremes, and whale activity.

**Alert types:**

- `liquidation_spike` – sum of liquidations (USD) over a window.
- `funding_extreme` – max absolute funding rate over a window.
- `whale_activity` – changes in whale address counts.

**Flow:**

1. User obtains an API key (same keystore as gateway).
2. User calls `POST /alerts` with `X-API-Key` and an alert config.
3. Scheduler polls data and posts to `ALERTS_DISCORD_WEBHOOK_URL`.

See:

- `src/services/alerts/README.md`

### 3. Multi‑Tenant Backtest Dashboard SaaS

**Stack pieces:**

- `src/scripts/backtestdashboard.py` – Backtest dashboard
- `src/agents/rbi_agent_pp_multi.py` – RBI multi backtester

**Value:**

- Sell per‑workspace backtest dashboards instead of CSV downloads.
- Each workspace corresponds to a user or team.

**Workspace rules:**

- Explicit `workspace` query param **or**
- `X-API-Key` → hashed workspace ID (via keystore plan lookups).
- `default` workspace maps to legacy single‑user directory.

**Flow:**

1. User has an API key.
2. Dashboard derives workspace from key or `workspace` param.
3. Backtests and folders are stored under
   `src/data/rbi_pp_multi/<workspace>/`.
4. `POST /api/backtest/run` spawns RBI runs with `RBI_WORKSPACE_NAME`
   set so results stay isolated.

See:

- `docs/backtest_dashboard.md`

### 4. Licensed Agents (Add‑On Products)

**Stack pieces:**

- `src/licensing.py` – Licensing helper
- `src/agents/focus_agent.py`
- `src/agents/phone_agent.py`
- `src/agents/video_agent.py`
- `src/agents/realtime_clips_agent.py`

**Value:**

- Sell higher‑tier plans that unlock agents:
  - Focus agent (research / focus coach)
  - Phone agent (Twilio voice assistant)
  - Video agent (video generation)
  - Realtime clips agent (recording + clipping)

**Env contract:**

- `LICENSE_API_KEY` – key used for license checks
- `LICENSE_GATEWAY_URL` – where `/whoami` lives
- `REQUIRE_LICENSE` – whether to exit on failure
- `LICENSE_MIN_PLAN_FOCUS` / `PHONE` / `VIDEO` / `CLIPS`

Agents call `ensure_feature_license(feature)` on startup and will only
run if the plan returned by the gateway meets the minimum.

See:

- `docs/licensing.md`

## Running Everything Together

For a single‑host deployment with all monetization surfaces running:

- See `docs/deployment_stack.md` and `docker-compose.yml`.
- That stack runs:
  - API Gateway (8010)
  - Billing (8011)
  - Alerts (8012)
  - Backtest Dashboard (8002)

From there you can:

- Point Stripe Checkout success pages at your front‑end.
- Let advanced users hit raw data via the gateway.
- Offer alerts and dashboard access to the same keys.
- Gate premium agents with `LICENSE_*` env vars.

## Demo Scripts

Two small demo clients are provided to exercise the services end‑to‑end
without writing code:

- `src/scripts/demo_alerts_client.py`
  - Creates a demo alert and then lists alerts for your key.
  - Uses env vars:
    - `ALERTS_BASE_URL` (default `http://127.0.0.1:8012`)
    - `ALERTS_API_KEY` (required)
    - `ALERTS_DEMO_TYPE` (`liquidation_spike` | `funding_extreme` | `whale_activity`)

- `src/scripts/demo_backtest_dashboard_client.py`
  - Fetches `/api/stats` and `/api/backtests` for a workspace and prints
    a small summary.
  - Uses env vars:
    - `DASHBOARD_BASE_URL` (default `http://127.0.0.1:8002`)
    - `DASHBOARD_API_KEY` (optional; sent as `X-API-Key`)
    - `DASHBOARD_WORKSPACE` (optional; sent as `workspace` query param)

- `src/scripts/demo_billing_gateway_client.py`
  - Two modes:
    - `checkout` → creates a Stripe Checkout session via Billing.
    - `gateway` → calls API Gateway `/whoami` and `/quota` for a key.
  - Uses env vars:
    - `BILLING_BASE_URL` (default `http://127.0.0.1:8011`)
    - `BILLING_PLAN`, `BILLING_SUCCESS_URL`, `BILLING_CANCEL_URL`, `BILLING_CUSTOMER_EMAIL`
    - `GATEWAY_BASE_URL` (default `http://127.0.0.1:8010`)
    - `GATEWAY_API_KEY` (required for `gateway` mode)

These demos assume the services are running (locally or via
`docker-compose`) and that you have at least one API key in the
keystore for exercising alerts and workspaces.
