# Moon Dev Products & Plans (Conceptual)

This repo can power several different products. This page describes them
in plain language so you can turn them into actual offers, landing
pages, or pricing tables.

Nothing here is binding; treat it as a menu of ways to monetize what
already exists in the codebase.

---

## 1. Market Data API

**What users get**

- Programmatic access to:
  - Liquidations (full historical + incremental)
  - Funding rates
  - Open interest (per-exchange + total)
  - Copybot data (follow list + recent transactions)
  - Whale address lists
- Simple API key auth via `X-API-Key`.
- Per-plan rate limits and usage tracking.

**How it works under the hood**

- API Gateway: `src/services/api_gateway` (FastAPI, rate limiting,
  keystore, usage store).
- Billing: `src/services/billing` (Stripe Checkout + webhooks → grants
  keys in keystore).
- Market data is served either from Moon Dev’s upstream or your own
  deployment.

**Example plan structure (you can change)**

- **Free**
  - Low RPM, limited endpoints, test only.
- **Pro**
  - Higher RPM, access to core data (liq, funding, OI).
- **Team**
  - Higher RPM, historical downloads, more concurrent usage.
- **Enterprise**
  - Custom RPM, SLAs, dedicated endpoints.

See:

- `docs/api.md`
- `src/services/api_gateway/README.md`
- `src/services/billing/README.md`

---

## 2. Alerts SaaS

**What users get**

- Hosted alerts based on Moon Dev data, delivered to their Discord.
- They configure alerts via API (or a small UI you build later).

**Current alert types**

- `liquidation_spike` – alert when liquidations exceed a USD threshold
  over a time window.
- `funding_extreme` – alert when absolute funding rate exceeds a
  threshold (e.g. |funding| > 0.1%).
- `whale_activity` – alert when whale address count changes by at least
  N since the last check.

**How it works under the hood**

- Service: `src/services/alerts/main.py` (FastAPI + scheduler).
- Uses `MoonDevAPI` (`src/agents/api.py`) for data.
- Auth: same keystore keys as the API Gateway.
- Delivery: Discord webhook (`ALERTS_DISCORD_WEBHOOK_URL`).

**How you might price it**

- Free: few alerts per key, basic types only.
- Pro: more alerts, more frequent polling.
- Team: many alerts, short polling interval, priority queue.
- Enterprise: custom SLA & channels (Telegram, email, SMS, etc.).

See:

- `src/services/alerts/README.md`

---

## 3. Backtest Dashboard SaaS

**What users get**

- A hosted dashboard showing their strategies’ backtests.
- Workspaces per key or per team so data stays separated.
- Optionally, a button to trigger new RBI runs.

**How it works under the hood**

- Dashboard: `src/scripts/backtestdashboard.py` (FastAPI + Jinja).
- RBI engine: `src/agents/rbi_agent_pp_multi.py`.
- Data per workspace under `src/data/rbi_pp_multi/<workspace>/`.
- Workspace derived from:
  - `workspace` query param, or
  - hashed `X-API-Key` (via keystore).

**Example offerings**

- Hobbyist: 1 workspace, limited backtests, manual runs.
- Pro: multiple workspaces, higher data retention.
- Team: shared workspaces, more concurrent runs.
- Enterprise: custom data feeds + priority RBI runs.

See:

- `docs/backtest_dashboard.md`

---

## 4. Licensed Agents (Add‑On Products)

**What users get**

You can sell access to specific agents as add‑ons on top of the plans
above. For example:

- **Focus Agent** – personal focus / productivity coach.
- **Phone Agent** – Twilio‑based AI receptionist / call handler.
- **Video Agent** – AI video generation (Sora 2) from text prompts.
- **Realtime Clips Agent** – automated clipping system for streams.

**How it works under the hood**

- Licensing helper: `src/licensing.py`.
- Env vars:
  - `LICENSE_API_KEY`, `LICENSE_GATEWAY_URL`, `REQUIRE_LICENSE`.
  - `LICENSE_MIN_PLAN_FOCUS`, `LICENSE_MIN_PLAN_PHONE`,
    `LICENSE_MIN_PLAN_VIDEO`, `LICENSE_MIN_PLAN_CLIPS`.
- Agents call `ensure_feature_license("focus"|"phone"|"video"|"clips")`
  on startup.
- Gateway `/whoami` returns the plan for the licensing key.

**Example packaging**

- Focus add‑on: included at Pro+.
- Phone add‑on: separate monthly “seat” per number.
- Video & Clips: credit‑based (N jobs per month per plan).

See:

- `docs/licensing.md`
- Individual agent docs in `docs/*.md` (focus, phone, video, clips).

---

## 5. Running Everything

For how to run all of this on a single machine with Docker Compose and
how to use the demo scripts, see:

- `docs/deployment_stack.md`
- `docs/monetization_overview.md`
