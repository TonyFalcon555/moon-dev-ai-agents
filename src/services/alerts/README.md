# Moon Dev Alerts Service

FastAPI service for registering market alerts (starting with liquidation spikes)
using Moon Dev's market data API. Alerts are evaluated on a schedule and
notifications are sent via Discord webhooks.

## Endpoints

- `GET /health`
  - Returns service status and current alert count.

- `POST /alerts`
  - Create an alert.
  - Auth: `X-API-Key` header (same keys as API Gateway / keystore).
  - Body (JSON):
    ```json
    {
      "type": "liquidation_spike",
      "threshold": 1000000,
      "window_minutes": 15,
      "symbol": "BTC",
      "description": "BTC liq spike 1m+ in 15m"
    }
    ```

- `GET /alerts`
  - List alerts owned by the caller (based on their API key).

- `DELETE /alerts/{alert_id}`
  - Delete one of your alerts.

## Environment

Required:

- `ALERTS_DISCORD_WEBHOOK_URL` — Discord webhook where alerts are posted.

Optional:

- `ALERTS_POLL_INTERVAL` — seconds between polling cycles (default: `60`).
- `ALERTS_MAX_FREE` — max alerts for `free` plan (default: `3`).
- `ALERTS_MAX_PRO` — max alerts for `pro` plan (default: `20`).
- `ALERTS_MAX_TEAM` — max alerts for `team` plan (default: `50`).
- `ALERTS_MAX_ENTERPRISE` — max alerts for `enterprise` plan (default: `200`).

The service optionally integrates with the API Gateway keystore to
resolve plans from API keys. If the keystore cannot be imported, it
falls back to allowing any non-empty `X-API-Key` (good for local
experimentation).

## Quickstart (local)

```bash
# Example venv
python3 -m venv .venv_alerts
source .venv_alerts/bin/activate
pip install fastapi uvicorn apscheduler requests python-dotenv pandas

# Run service
ALERTS_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/... \
uvicorn src.services.alerts.main:app --host 127.0.0.1 --port 8012

# Create an alert (assuming you have an API key KEY)
curl -X POST http://127.0.0.1:8012/alerts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: KEY' \
  -d '{
    "type": "liquidation_spike",
    "threshold": 1000000,
    "window_minutes": 15,
    "symbol": "BTC",
    "description": "BTC liq spike 1m+ in 15m"
  }'
```

This will send a Discord notification whenever the liquidation value
exceeds your threshold for the given window.

### Other alert types

The service also supports:

- `funding_extreme` — triggers when absolute funding rate exceeds a
  threshold.
- `whale_activity` — triggers when total whale address count changes by
  more than a threshold since the last check.

Examples:

```bash
# Extreme funding for BTC when |funding| > 0.1% (0.001)
curl -X POST http://127.0.0.1:8012/alerts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: KEY' \
  -d '{
    "type": "funding_extreme",
    "threshold": 0.001,
    "window_minutes": 15,
    "symbol": "BTC",
    "description": "BTC extreme funding alert"
  }'

# Whale activity when whale address count moves by at least 10
curl -X POST http://127.0.0.1:8012/alerts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: KEY' \
  -d '{
    "type": "whale_activity",
    "threshold": 10,
    "window_minutes": 30,
    "description": "Whale address count change >= 10"
  }'
```
