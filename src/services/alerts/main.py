"""
Moon Dev Alerts Service

FastAPI service that lets users register alerts based on Moon Dev market data
(liquidations, funding, etc.) and delivers notifications via Discord webhooks.

This implementation uses PostgreSQL for persistence via the keystore module.
"""

import os
import time
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, insert, delete, update

# Local Moon Dev API client
from src.agents.api import MoonDevAPI

# Keystore integration (Required for DB access)
try:
    from src.services.api_gateway.keystore import get_plan_for_key, engine, alerts_table, init_db
    _KS_OK = True
except Exception:
    # Fallback for tests if imports fail, though in this refactor we expect it to work
    _KS_OK = False

load_dotenv()

app = FastAPI(title="Moon Dev Alerts Service")

scheduler: Optional[AsyncIOScheduler] = None


class AlertCreate(BaseModel):
    """Payload for creating an alert."""
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
    """Resolve the caller's API key and plan via keystore."""
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
    if not hasattr(app.state, "moon_api"):
        app.state.moon_api = MoonDevAPI()
    return app.state.moon_api


def _send_discord_notification(message: str) -> None:
    url = os.getenv("ALERTS_DISCORD_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={"content": message}, timeout=5)
    except Exception:
        pass


# ============================================================================
# 🌙 ALERT EVALUATION LOGIC
# ============================================================================

def _evaluate_liquidation_spike(alert_id: str, config: Dict, state: Dict) -> Optional[Dict]:
    symbol = config.get("symbol")
    threshold = config.get("threshold")
    window_minutes = config.get("window_minutes", 15)

    api = _get_moon_api()
    df = api.get_liquidation_data(limit=50000)
    if df is None or len(df) == 0:
        return None

    try:
        if symbol and "symbol" in df.columns:
            df = df[df["symbol"] == symbol]
    except Exception:
        return None

    # Timestamp parsing
    ts_col = None
    if "datetime" in df.columns:
        ts_col = "datetime"
        df[ts_col] = pd.to_datetime(df[ts_col])
    elif "order_trade_time" in df.columns:
        ts_col = "order_trade_time"
        df[ts_col] = pd.to_datetime(df[ts_col], unit="ms", errors="coerce")
    
    if ts_col is None:
        return None

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)
    
    try:
        # Ensure timezone awareness compatibility
        if df[ts_col].dt.tz is None:
             df[ts_col] = df[ts_col].dt.tz_localize(timezone.utc)
        
        df_window = df[df[ts_col] >= cutoff]
    except Exception:
        return None

    if df_window.empty:
        return None

    # USD Size
    usd_col = None
    if "usd_size" in df_window.columns:
        usd_col = "usd_size"
    elif "size" in df_window.columns:
        usd_col = "size"
    
    if usd_col is None:
        return None

    try:
        total_usd = float(df_window[usd_col].astype(float).sum())
    except Exception:
        return None

    if total_usd < threshold:
        return None

    # Debounce
    last_ts_str = state.get("last_trigger")
    if last_ts_str:
        last_ts = datetime.fromisoformat(last_ts_str)
        if (now - last_ts) < timedelta(minutes=window_minutes):
            return None

    # Trigger!
    symbol_str = symbol or "ALL"
    msg = (
        f"🌙 Moon Dev Alert: Liquidation spike detected for {symbol_str} "
        f"over last {window_minutes}m. Total ≈ ${total_usd:,.0f} (threshold ${threshold:,.0f})."
    )
    _send_discord_notification(msg)
    
    state["last_trigger"] = now.isoformat()
    return state


def _evaluate_funding_extreme(alert_id: str, config: Dict, state: Dict) -> Optional[Dict]:
    symbol = config.get("symbol")
    threshold = config.get("threshold")
    window_minutes = config.get("window_minutes", 15)

    api = _get_moon_api()
    df = api.get_funding_data()
    if df is None or len(df) == 0:
        return None

    try:
        if symbol and "symbol" in df.columns:
            df = df[df["symbol"] == symbol]
    except Exception:
        return None

    if df.empty:
        return None

    candidate_cols = [c for c in df.columns if "fund" in str(c).lower() or "rate" in str(c).lower()]
    if not candidate_cols:
        return None

    max_abs_rate = None
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
        return None

    now = datetime.now(timezone.utc)
    last_ts_str = state.get("last_trigger")
    if last_ts_str:
        last_ts = datetime.fromisoformat(last_ts_str)
        if (now - last_ts) < timedelta(minutes=window_minutes):
            return None

    symbol_str = symbol or "ALL"
    msg = (
        f"🌙 Moon Dev Alert: Extreme funding detected for {symbol_str}. "
        f"max |funding| ≈ {max_abs_rate:.4f} (threshold {threshold:.4f})."
    )
    _send_discord_notification(msg)
    
    state["last_trigger"] = now.isoformat()
    return state


def _evaluate_whale_activity(alert_id: str, config: Dict, state: Dict) -> Optional[Dict]:
    threshold = config.get("threshold")
    window_minutes = config.get("window_minutes", 15)

    api = _get_moon_api()
    addresses = api.get_whale_addresses()
    if not addresses:
        return None

    current_count = len(addresses)
    now = datetime.now(timezone.utc)

    last_count = state.get("last_count")
    
    # First run
    if last_count is None:
        state["last_count"] = current_count
        return state

    delta = current_count - int(last_count)
    if abs(delta) < threshold:
        state["last_count"] = current_count
        return state

    last_ts_str = state.get("last_trigger")
    if last_ts_str:
        last_ts = datetime.fromisoformat(last_ts_str)
        if (now - last_ts) < timedelta(minutes=window_minutes):
            state["last_count"] = current_count
            return state

    direction = "increased" if delta > 0 else "decreased"
    msg = (
        f"🌙 Moon Dev Alert: Whale activity detected. Whale address count has "
        f"{direction} by {abs(delta)} (current total {current_count}, "
        f"threshold {threshold:.0f})."
    )
    _send_discord_notification(msg)
    
    state["last_count"] = current_count
    state["last_trigger"] = now.isoformat()
    return state


def _run_all_alerts() -> None:
    if not _KS_OK:
        return

    # Fetch all alerts from DB
    with engine.connect() as conn:
        stmt = select(alerts_table)
        rows = conn.execute(stmt).fetchall()

    for row in rows:
        try:
            alert_id = row.id
            config = row.config
            state = row.state or {}
            
            new_state = None
            
            if config["type"] == "liquidation_spike":
                new_state = _evaluate_liquidation_spike(alert_id, config, state)
            elif config["type"] == "funding_extreme":
                new_state = _evaluate_funding_extreme(alert_id, config, state)
            elif config["type"] == "whale_activity":
                new_state = _evaluate_whale_activity(alert_id, config, state)
            
            if new_state:
                # Update state in DB
                with engine.connect() as conn:
                    upd = update(alerts_table).where(alerts_table.c.id == alert_id).values(state=new_state)
                    conn.execute(upd)
                    conn.commit()
                    
        except Exception as e:
            print(f"Error processing alert {row.id}: {e}")
            continue


# ============================================================================
# 🛣️ ROUTES
# ============================================================================

@app.on_event("startup")
def _startup() -> None:
    global scheduler
    if _KS_OK:
        init_db()
    
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
    count = 0
    if _KS_OK:
        with engine.connect() as conn:
            count = conn.execute(select(alerts_table)).rowcount
            
    return JSONResponse({
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "alerts_count": count,
        "db_connected": _KS_OK
    })


import uuid

# ... (imports)

# ...

@app.post("/alerts", response_model=AlertOut)
async def create_alert(alert: AlertCreate, request: Request) -> AlertOut:
    owner_hash, plan = _get_owner_and_plan(request)

    if not _KS_OK:
        raise HTTPException(status_code=503, detail="Database unavailable")

    # Check quota
    per_plan_limits = {
        "free": int(os.getenv("ALERTS_MAX_FREE", "3")),
        "pro": int(os.getenv("ALERTS_MAX_PRO", "20")),
        "team": int(os.getenv("ALERTS_MAX_TEAM", "50")),
        "enterprise": int(os.getenv("ALERTS_MAX_ENTERPRISE", "200")),
    }
    max_alerts = per_plan_limits.get(plan, per_plan_limits["free"])

    with engine.connect() as conn:
        rows = conn.execute(
            select(alerts_table).where(alerts_table.c.owner_hash == owner_hash)
        ).fetchall()
        count = len(rows)
        
        if count >= max_alerts:
            raise HTTPException(status_code=429, detail="Alert quota exceeded for your plan")

        now = datetime.now(timezone.utc)
        alert_id = f"a_{uuid.uuid4().hex[:16]}"
        
        stmt = insert(alerts_table).values(
            id=alert_id,
            owner_hash=owner_hash,
            plan=plan,
            config=alert.model_dump(),
            state={},
            created_at=now
        )
        conn.execute(stmt)
        conn.commit()

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
    
    if not _KS_OK:
        raise HTTPException(status_code=503, detail="Database unavailable")

    with engine.connect() as conn:
        stmt = select(alerts_table).where(alerts_table.c.owner_hash == owner_hash)
        rows = conn.execute(stmt).fetchall()

    out: List[AlertOut] = []
    for row in rows:
        cfg = row.config
        out.append(
            AlertOut(
                id=row.id,
                type=cfg["type"],
                threshold=cfg["threshold"],
                window_minutes=cfg["window_minutes"],
                symbol=cfg.get("symbol"),
                description=cfg.get("description"),
                created_at=row.created_at.isoformat(),
            )
        )
    return out


@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, request: Request) -> JSONResponse:
    owner_hash, _ = _get_owner_and_plan(request)
    
    if not _KS_OK:
        raise HTTPException(status_code=503, detail="Database unavailable")

    with engine.connect() as conn:
        # Check ownership
        stmt = select(alerts_table).where(
            alerts_table.c.id == alert_id,
            alerts_table.c.owner_hash == owner_hash
        )
        if not conn.execute(stmt).fetchone():
            raise HTTPException(status_code=404, detail="Alert not found")
            
        # Delete
        del_stmt = delete(alerts_table).where(alerts_table.c.id == alert_id)
        conn.execute(del_stmt)
        conn.commit()

    return JSONResponse({"deleted": True, "id": alert_id})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ALERTS_PORT", "8012"))
    uvicorn.run(app, host="0.0.0.0", port=port)
