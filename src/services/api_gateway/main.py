import os
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Rate limiter integration
try:
    from src.services.api_gateway.rate_limiter import get_rate_limiter, RateLimitResult
    _RL_OK = True
except ImportError:
    try:
        from .rate_limiter import get_rate_limiter, RateLimitResult
        _RL_OK = True
    except ImportError:
        _RL_OK = False
        logging.warning("Rate limiter module not found. Using basic rate limiting.")

# Keystore integration
_KS_OK = False
try:
    from src.services.api_gateway.keystore import init_db, get_plan_and_override
    _KS_OK = True
except ImportError:
    try:
        from .keystore import init_db, get_plan_and_override
        _KS_OK = True
    except ImportError:
        logging.warning("Keystore module not found. Keystore features disabled.")

UPSTREAM = os.getenv("UPSTREAM_API_BASE_URL", "http://api.moondev.com:8000")
UPSTREAM_API_KEY = os.getenv("UPSTREAM_API_KEY")

# Keystore configuration - set USE_KEYSTORE=1 in .env to enable database-backed key management
KEYSTORE_ENABLED = os.getenv("USE_KEYSTORE", "0").lower() in ("1", "true", "yes")

# Optional usage store integration
_US_OK = False
try:
    from src.services.api_gateway.usage_store import init_db as init_usage_db, record_usage, summarize as usage_summarize
    _US_OK = True
except ImportError:
    try:
        from .usage_store import init_db as init_usage_db, record_usage, summarize as usage_summarize
        _US_OK = True
    except ImportError:
        logging.warning("Usage store module not found. Usage tracking disabled.")

def _parse_keys(env_val: str | None) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not env_val:
        return mapping
    for pair in env_val.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" in pair:
            key, plan = pair.split(":", 1)
        else:
            key, plan = pair, "free"
        mapping[key.strip()] = plan.strip()
    return mapping


API_KEYS: Dict[str, str] = _parse_keys(os.getenv("API_KEYS")) or {"demo-key": "free"}

PLAN_LIMITS: Dict[str, int] = {
    "free": 60,
    "pro": 600,
    "team": 2400,
    "enterprise": 10000,
}

PLANS_META: Dict[str, dict] = {}


def _load_plans_meta() -> Dict[str, dict]:
    """Load plan metadata from plans.json, falling back to PLAN_LIMITS.

    The JSON file is expected to live alongside this module and contain a
    mapping of plan name → { name, description, rpm }.
    """

    global PLANS_META
    if PLANS_META:
        return PLANS_META

    try:
        base = Path(__file__).resolve().parent
        plan_path = base / "plans.json"
        with plan_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Ensure rpm is always present, falling back to PLAN_LIMITS
        for plan, meta in data.items():
            rpm = meta.get("rpm") or PLAN_LIMITS.get(plan)
            if rpm is None:
                rpm = PLAN_LIMITS.get("free", 60)
            meta["rpm"] = int(rpm)

        PLANS_META = data
    except Exception:
        # Fallback: build simple metadata from PLAN_LIMITS only
        PLANS_META = {
            name: {
                "name": name,
                "description": "",
                "rpm": rpm,
            }
            for name, rpm in PLAN_LIMITS.items()
        }

    return PLANS_META


rate_state: Dict[str, Dict[str, int]] = {}

app = FastAPI(title="Moon Dev API Gateway")

# CORS configuration - use ALLOWED_ORIGINS env var in production
# Example: ALLOWED_ORIGINS=https://falconfinance.io,https://app.falconfinance.io
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if ALLOWED_ORIGINS == ["*"]:
    # Development mode - allow all origins
    logging.warning("⚠️ CORS: Allowing all origins (set ALLOWED_ORIGINS in production)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def _startup():
    # Load .env for local dev convenience
    try:
        load_dotenv()
    except Exception:
        pass
    if KEYSTORE_ENABLED and _KS_OK:
        init_db()
    if _US_OK:
        init_usage_db()
    global metrics
    metrics = {
        "requests_total": 0,
        "per_plan": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    logging.basicConfig(level=logging.INFO)


def _check_key_and_rate_limit(api_key: str | None) -> Tuple[str, int, int]:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    # Prefer keystore if enabled
    if KEYSTORE_ENABLED and _KS_OK:
        plan, rlo = get_plan_and_override(api_key)
        if not plan:
            raise HTTPException(status_code=403, detail="Invalid or revoked API key")
        limit = rlo if rlo is not None else PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    else:
        plan = API_KEYS.get(api_key)
        if not plan:
            raise HTTPException(status_code=403, detail="Invalid API key")
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    now = int(time.time())
    window = now // 60
    state = rate_state.get(api_key)
    if not state or state.get("window") != window:
        state = {"window": window, "count": 0}
        rate_state[api_key] = state
    if state["count"] >= limit:
        reset_in = 60 - (now % 60)
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded for plan '{plan}'. Try again in {reset_in}s.")
    state["count"] += 1
    try:
        metrics["requests_total"] += 1  # type: ignore[index, operator]
        per = metrics["per_plan"]  # type: ignore[index]
        per[plan] = per.get(plan, 0) + 1  # type: ignore[index]
    except Exception:
        pass
    return plan, limit, state["count"]


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "upstream": UPSTREAM,
    })


@app.get("/quota")
def quota(request: Request) -> JSONResponse:
    api_key = request.headers.get("X-API-Key")
    plan, limit, count = _check_key_and_rate_limit(api_key)
    # Quota checks should not consume the quota
    state = rate_state.get(api_key)  # type: ignore[index]
    if state:
        state["count"] = max(state["count"] - 1, 0)
    window_remaining = 60 - (int(time.time()) % 60)
    return JSONResponse({
        "plan": plan,
        "used": count - 1,
        "limit_per_min": limit,
        "resets_in_sec": window_remaining,
    })


@app.get("/whoami")
def whoami(request: Request) -> JSONResponse:
    api_key = request.headers.get("X-API-Key")
    plan, limit, count = _check_key_and_rate_limit(api_key)
    state = rate_state.get(api_key)  # type: ignore[index]
    if state:
        state["count"] = max(state["count"] - 1, 0)
    return JSONResponse({
        "plan": plan,
        "limit_per_min": limit,
        "mode": "keystore" if (KEYSTORE_ENABLED and _KS_OK) else "env_keys",
    })


@app.get("/plans")
def plans() -> JSONResponse:
    """Return plan metadata (names, descriptions, and RPM limits).

    This does not require authentication and is intended for frontends or
    dashboards that need to display plan information.
    """

    meta = _load_plans_meta()
    return JSONResponse({"plans": meta})


@app.get("/metrics")
def metrics_endpoint() -> JSONResponse:
    try:
        return JSONResponse(metrics)  # type: ignore[arg-type]
    except Exception:
        return JSONResponse({"requests_total": None, "per_plan": None, "started_at": None})


@app.get("/files/{filename:path}")
def proxy_files(filename: str, request: Request, limit: int | None = None):
    api_key = request.headers.get("X-API-Key")
    plan, _, _ = _check_key_and_rate_limit(api_key)

    params: Dict[str, str] = {}
    if limit is not None:
        params["limit"] = str(limit)

    headers: Dict[str, str] = {}
    rng = request.headers.get("range") or request.headers.get("Range")
    if rng:
        headers["Range"] = rng
    # Forward upstream auth
    if UPSTREAM_API_KEY:
        headers["X-API-Key"] = UPSTREAM_API_KEY
    else:
        # fallback: forward inbound key (suitable for testing)
        if api_key:
            headers["X-API-Key"] = api_key

    url = f"{UPSTREAM.rstrip('/')}/files/{filename}"
    try:
        upstream_resp = requests.get(
            url,
            params=params,
            headers=headers,
            stream=True,
            timeout=(10, 300),
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e.__class__.__name__}")

    if upstream_resp.status_code >= 400:
        raise HTTPException(
            status_code=upstream_resp.status_code,
            detail=f"Upstream returned {upstream_resp.status_code}",
        )

    content_type = upstream_resp.headers.get("content-type", "application/octet-stream")

    def _iter_stream():
        for chunk in upstream_resp.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    if _US_OK and api_key and plan:
        try:
            record_usage(api_key, plan, f"/files/{filename}")
        except Exception:
            pass

    return StreamingResponse(
        _iter_stream(),
        media_type=content_type,
        headers={
            "Content-Disposition": upstream_resp.headers.get("content-disposition", ""),
            "Content-Range": upstream_resp.headers.get("content-range", ""),
            "Accept-Ranges": upstream_resp.headers.get("accept-ranges", ""),
        },
    )


@app.get("/copybot/data/{resource:path}")
def proxy_copybot(resource: str, request: Request):
    api_key = request.headers.get("X-API-Key")
    plan, _, _ = _check_key_and_rate_limit(api_key)

    headers: Dict[str, str] = {}
    # Forward upstream auth
    if UPSTREAM_API_KEY:
        headers["X-API-Key"] = UPSTREAM_API_KEY
    else:
        if api_key:
            headers["X-API-Key"] = api_key

    url = f"{UPSTREAM.rstrip('/')}/copybot/data/{resource}"
    try:
        upstream_resp = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(10, 120),
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e.__class__.__name__}")

    if upstream_resp.status_code >= 400:
        raise HTTPException(
            status_code=upstream_resp.status_code,
            detail=f"Upstream returned {upstream_resp.status_code}",
        )

    content_type = upstream_resp.headers.get("content-type", "application/octet-stream")

    def _iter_stream2():
        for chunk in upstream_resp.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    if _US_OK and api_key and plan:
        try:
            record_usage(api_key, plan, f"/copybot/data/{resource}")
        except Exception:
            pass

    return StreamingResponse(_iter_stream2(), media_type=content_type)


@app.get("/usage/summary")
def usage_summary() -> JSONResponse:
    if not _US_OK:
        raise HTTPException(status_code=503, detail="Usage store not available")
    try:
        data = usage_summarize()
        return JSONResponse({"date": datetime.now(timezone.utc).date().isoformat(), "items": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Usage summary error: {e.__class__.__name__}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8010"))
    uvicorn.run(app, host="0.0.0.0", port=port)
