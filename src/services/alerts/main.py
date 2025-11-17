"""
Moon Dev Alerts Service

FastAPI service that lets users register alerts based on Moon Dev market data
(liquidations, funding, etc.) and delivers notifications via Discord webhooks.

This is an initial, in-memory implementation intended for:
- Prototyping alert types
- Integrating with the existing MoonDevAPI data layer
- Validating demand for alerts as a product

It authenticates requests using the same API keys as the API Gateway
(through the keystore when available).
"""

import os
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Local Moon Dev API client
from src.agents.api import MoonDevAPI

# Optional keystore integration (same pattern as API gateway)
try:
    from src.services.api_gateway.keystore import get_plan_for_key
    _KS_OK = True
except Exception:
    try:
        from ..api_gateway.keystore import get_plan_for_key  # type: ignore
        _KS_OK = True
    except Exception:  # pragma: no cover - keystore optional
        _KS_OK = False

load_dotenv()

app = FastAPI(title="Moon Dev Alerts Service")

# In-memory alert storage (per-process). For production you would
# replace this with a persistent store (SQLite/Postgres/Redis).
ALERTS: Dict[str, Dict] = {}
ALERT_STATE: Dict[str, Dict] = {}

scheduler: Optional[AsyncIOScheduler] = None


class AlertCreate(BaseModel):
    """Payload for creating an alert.

    type: one of:
      - liquidation_spike  → sum of liquidations (USD) over a window
      - funding_extreme    → extreme funding rates by absolute value
      - whale_activity     → large changes in whale address count
    threshold: numeric threshold (semantics depend on type).
      - liquidation_spike: total USD size over window
      - funding_extreme:   absolute funding rate (e.g. 0.001 = 0.1%)
      - whale_activity:    absolute change in whale count since last check
    window_minutes: lookback / cooldown window size in minutes
    symbol: optional symbol (e.g. BTC, ETH) to filter on when applicable
    description: optional free-text description
    """

    type: str
    threshold: float
    window_minutes: int = 15
    symbol: Optional[str] = None
    description: Optional[str] = None


class AlertOut(BaseModel):
    id: str
    type: str
    threshold: float
    window_minutes: int
    symbol: Optional[str]
    description: Optional[str]
    created_at: str


def _hash_key(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()


def _get_owner_and_plan(request: Request) -> Tuple[str, str]:
    """Resolve the caller's API key and plan via keystore when available.

    Returns (owner_hash, plan).
    """

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")

    plan = "free"
    if _KS_OK:
        p = get_plan_for_key(api_key)
        if not p:
            raise HTTPException(status_code=403, detail="Invalid or revoked API key")
        plan = p

    owner_hash = _hash_key(api_key)
    return owner_hash, plan


def _get_moon_api() -> MoonDevAPI:
    # Simple singleton stored on app.state
    if not hasattr(app.state, "moon_api"):
        app.state.moon_api = MoonDevAPI()
    return app.state.moon_api  # type: ignore[attr-defined]


def _send_discord_notification(message: str) -> None:
    url = os.getenv("ALERTS_DISCORD_WEBHOOK_URL")
    if not url:
        # No webhook configured; silently ignore
        return
    try:
        requests.post(url, json={"content": message}, timeout=5)
    except Exception:
        # Do not crash scheduler on notification failures
        pass


def _evaluate_liquidation_spike(alert_id: str, alert_data: Dict) -> None:
    """Check for liquidation spikes using MoonDevAPI liquidation data.

    This implementation is intentionally conservative: if it cannot reliably
    identify timestamps or USD sizes, it simply skips the alert.
    """

    cfg: AlertCreate = alert_data["config"]
    symbol = cfg.symbol
    threshold = cfg.threshold
    window_minutes = cfg.window_minutes

    api = _get_moon_api()
    df = api.get_liquidation_data(limit=50000)
    if df is None or len(df) == 0:
        return

    # Filter by symbol if provided
    try:
        if symbol and "symbol" in df.columns:
            df = df[df["symbol"] == symbol]
    except Exception:
        return

    # Determine timestamp column
    ts_col = None
    if "datetime" in df.columns:
        ts_col = "datetime"
        df[ts_col] = pd.to_datetime(df[ts_col])
    elif "order_trade_time" in df.columns:
        ts_col = "order_trade_time"
        df[ts_col] = pd.to_datetime(df[ts_col], unit="ms", errors="coerce")
    if ts_col is None:
        return

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)
    try:
        df_window = df[df[ts_col] >= cutoff]
    except Exception:
        return

    if df_window.empty:
        return

    # Determine USD size column
    usd_col = None
    if "usd_size" in df_window.columns:
        usd_col = "usd_size"
    elif "size" in df_window.columns:
        usd_col = "size"
    if usd_col is None:
        return

    try:
        total_usd = float(df_window[usd_col].astype(float).sum())
    except Exception:
        return

    if total_usd < threshold:
        return

    # Debounce: only trigger once per window per alert
    state = ALERT_STATE.setdefault(alert_id, {})
    last_ts: Optional[datetime] = state.get("last_trigger")
    if last_ts and (now - last_ts) < timedelta(minutes=window_minutes):
        return

    state["last_trigger"] = now

    symbol_str = symbol or "ALL"
    msg = (
        f"🌙 Moon Dev Alert: Liquidation spike detected for {symbol_str} "
        f"over last {window_minutes}m. Total ≈ ${total_usd:,.0f} (threshold ${threshold:,.0f})."
    )
    _send_discord_notification(msg)


def _evaluate_funding_extreme(alert_id: str, alert_data: Dict) -> None:
    """Check for extreme funding rates using MoonDevAPI funding data.

    This looks for the maximum absolute funding rate across one or more
    numeric "funding" / "rate" columns and compares it to the threshold.
    The alert is debounced using window_minutes as a cooldown.
    """

    cfg: AlertCreate = alert_data["config"]
    symbol = cfg.symbol
    threshold = cfg.threshold
    window_minutes = cfg.window_minutes

    api = _get_moon_api()
    df = api.get_funding_data()
    if df is None or len(df) == 0:
        return

    try:
        if symbol and "symbol" in df.columns:
            df = df[df["symbol"] == symbol]
    except Exception:
        return

    if df.empty:
        return

    # Heuristically detect funding / rate columns
    candidate_cols: List[str] = []
    for col in df.columns:
        name = str(col).lower()
        if "fund" in name or "rate" in name:
            candidate_cols.append(col)

    if not candidate_cols:
        return

    max_abs_rate: Optional[float] = None
    for col in candidate_cols:
        try:
            series = pd.to_numeric(df[col], errors="coerce").abs()
            if series.notna().any():
                col_max = float(series.max())
                if max_abs_rate is None or col_max > max_abs_rate:
                    max_abs_rate = col_max
        except Exception:
            continue

    if max_abs_rate is None or max_abs_rate < threshold:
        return

    now = datetime.now(timezone.utc)
    state = ALERT_STATE.setdefault(alert_id, {})
    last_ts: Optional[datetime] = state.get("last_trigger")
    if last_ts and (now - last_ts) < timedelta(minutes=window_minutes):
        return

    state["last_trigger"] = now

    symbol_str = symbol or "ALL"
    msg = (
        f"🌙 Moon Dev Alert: Extreme funding detected for {symbol_str}. "
        f"max |funding| ≈ {max_abs_rate:.4f} (threshold {threshold:.4f})."
    )
    _send_discord_notification(msg)


def _evaluate_whale_activity(alert_id: str, alert_data: Dict) -> None:
    """Check for changes in whale address count.

    Uses MoonDevAPI.get_whale_addresses() and compares the absolute change in
    count since the last evaluation to the threshold. The alert is debounced
    using window_minutes as a cooldown.
    """

    cfg: AlertCreate = alert_data["config"]
    threshold = cfg.threshold
    window_minutes = cfg.window_minutes

    api = _get_moon_api()
    addresses = api.get_whale_addresses()
    if not addresses:
        return

    current_count = len(addresses)
    now = datetime.now(timezone.utc)

    state = ALERT_STATE.setdefault(alert_id, {})
    last_count = state.get("last_count")

    # First run: store baseline and return without alerting
    if last_count is None:
        state["last_count"] = current_count
        return

    delta = current_count - int(last_count)
    if abs(delta) < threshold:
        # Update baseline but do not alert
        state["last_count"] = current_count
        return

    last_ts: Optional[datetime] = state.get("last_trigger")
    if last_ts and (now - last_ts) < timedelta(minutes=window_minutes):
        state["last_count"] = current_count
        return

    state["last_count"] = current_count
    state["last_trigger"] = now

    direction = "increased" if delta > 0 else "decreased"
    msg = (
        f"🌙 Moon Dev Alert: Whale activity detected. Whale address count has "
        f"{direction} by {abs(delta)} (current total {current_count}, "
        f"threshold {threshold:.0f})."
    )
    _send_discord_notification(msg)


def _run_all_alerts() -> None:
    # Evaluate all alerts; errors should not stop the scheduler
    for alert_id, data in list(ALERTS.items()):
        try:
            cfg: AlertCreate = data["config"]
            if cfg.type == "liquidation_spike":
                _evaluate_liquidation_spike(alert_id, data)
            elif cfg.type == "funding_extreme":
                _evaluate_funding_extreme(alert_id, data)
            elif cfg.type == "whale_activity":
                _evaluate_whale_activity(alert_id, data)
        except Exception:
            # Swallow errors; log later if we add logging here
            continue


@app.on_event("startup")
def _startup() -> None:
    global scheduler
    # For local dev convenience
    try:
        load_dotenv()
    except Exception:
        pass

    poll_interval = int(os.getenv("ALERTS_POLL_INTERVAL", "60"))
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_run_all_alerts, "interval", seconds=poll_interval)
    scheduler.start()


@app.on_event("shutdown")
def _shutdown() -> None:
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "alerts_count": len(ALERTS),
    })


@app.post("/alerts", response_model=AlertOut)
async def create_alert(alert: AlertCreate, request: Request) -> AlertOut:
    owner_hash, plan = _get_owner_and_plan(request)

    # Basic per-plan quota example (can be tuned later)
    per_plan_limits = {
        "free": int(os.getenv("ALERTS_MAX_FREE", "3")),
        "pro": int(os.getenv("ALERTS_MAX_PRO", "20")),
        "team": int(os.getenv("ALERTS_MAX_TEAM", "50")),
        "enterprise": int(os.getenv("ALERTS_MAX_ENTERPRISE", "200")),
    }
    max_alerts = per_plan_limits.get(plan, per_plan_limits["free"])

    existing_for_owner = [a for a in ALERTS.values() if a.get("owner") == owner_hash]
    if len(existing_for_owner) >= max_alerts:
        raise HTTPException(status_code=429, detail="Alert quota exceeded for your plan")

    now = datetime.now(timezone.utc)
    alert_id = f"a_{int(time.time() * 1000)}_{len(ALERTS) + 1}"
    data = {
        "id": alert_id,
        "owner": owner_hash,
        "plan": plan,
        "config": alert,
        "created_at": now,
    }
    ALERTS[alert_id] = data

    return AlertOut(
        id=alert_id,
        type=alert.type,
        threshold=alert.threshold,
        window_minutes=alert.window_minutes,
        symbol=alert.symbol,
        description=alert.description,
        created_at=now.isoformat(),
    )


@app.get("/alerts", response_model=List[AlertOut])
async def list_alerts(request: Request) -> List[AlertOut]:
    owner_hash, _ = _get_owner_and_plan(request)
    out: List[AlertOut] = []
    for data in ALERTS.values():
        if data.get("owner") != owner_hash:
            continue
        cfg: AlertCreate = data["config"]
        created_at: datetime = data["created_at"]
        out.append(
            AlertOut(
                id=data["id"],
                type=cfg.type,
                threshold=cfg.threshold,
                window_minutes=cfg.window_minutes,
                symbol=cfg.symbol,
                description=cfg.description,
                created_at=created_at.isoformat(),
            )
        )
    return out


@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, request: Request) -> JSONResponse:
    owner_hash, _ = _get_owner_and_plan(request)
    data = ALERTS.get(alert_id)
    if not data or data.get("owner") != owner_hash:
        raise HTTPException(status_code=404, detail="Alert not found")
    ALERTS.pop(alert_id, None)
    ALERT_STATE.pop(alert_id, None)
    return JSONResponse({"deleted": True, "id": alert_id})


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ALERTS_PORT", "8012"))
    uvicorn.run(app, host="0.0.0.0", port=port)
