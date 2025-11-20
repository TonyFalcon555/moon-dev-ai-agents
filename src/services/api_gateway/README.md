# Moon Dev API Gateway

FastAPI gateway that enforces API keys, per‑plan rate limits, and proxies to the upstream data API.

## Endpoints
- GET /health — status + upstream
- GET /whoami — checks your key (does not consume quota)
- GET /quota — returns per‑minute usage window (does not consume quota)
- GET /files/{filename}?limit=N — streaming proxy to upstream `/files/*`
 - GET /plans — returns plan metadata (name, description, rpm)

## Env vars
- UPSTREAM_API_BASE_URL (default: http://api.moondev.com:8000)
- UPSTREAM_API_KEY (optional; if set, forwarded to upstream as `X-API-Key`)
- USE_KEYSTORE=1 enables SQLite keystore (recommended)
- API_KEYS (fallback when keystore disabled), format: `key1:pro,key2:team`
- PORT (default 8010)

Optional config:

- `plans.json` file in this folder describing plans and their RPM limits.
  - If present, `/plans` returns its contents.
  - If missing or invalid, `/plans` falls back to the built-in `PLAN_LIMITS`.

## Keystore
- SQLite DB at `src/services/api_gateway/keystore.sqlite3` (override with KEYSTORE_DB_PATH)
- CLI: `python src/services/api_gateway/keystore.py create --plan pro`
- CLI: `list|revoke|rotate|verify`

## Local quickstart
```bash
# venv (example)
python3 -m venv .venv_gateway
source .venv_gateway/bin/activate
pip install fastapi==0.115.5 uvicorn==0.32.1 requests==2.32.3 python-dotenv==1.0.0

# start (keystore on)
USE_KEYSTORE=1 uvicorn src.services.api_gateway.main:app --host 127.0.0.1 --port 8010

# create key
echo $(python src/services/api_gateway/keystore.py create --plan pro)

# test
KEY=md_... 
curl -H "X-API-Key: $KEY" http://127.0.0.1:8010/whoami
curl -H "X-API-Key: $KEY" http://127.0.0.1:8010/quota
```

## Notes
- When `UPSTREAM_API_KEY` is not set, the gateway forwards the inbound `X-API-Key` to upstream (good for internal testing). For production, set a dedicated upstream key.
- Metrics available at GET /metrics.
