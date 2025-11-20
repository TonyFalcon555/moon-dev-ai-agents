import os
import hashlib
import shutil
import subprocess
import threading
import asyncio
import traceback
import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from fastapi import FastAPI, Request, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pandas as pd
import numpy as np
import uvicorn
import websockets
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Add project root to path to allow imports from src
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.api import MoonDevAPI

# Try to import keystore
try:
    from src.services.api_gateway.keystore import get_plan_for_key
    _KS_OK = True
except Exception:
    _KS_OK = False

# ============================================================================
# 🔧 CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT / "src" / "data"
RBI_BASE_DIR = DATA_ROOT / "rbi_pp_multi"

# Ensure directories exist
RBI_BASE_DIR.mkdir(parents=True, exist_ok=True)

# Paths
STATS_CSV = RBI_BASE_DIR / "backtest_stats.csv"
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
USER_FOLDERS_DIR = RBI_BASE_DIR / "user_folders"
DATA_DIR = RBI_BASE_DIR / "downloads"
TEST_DATA_DIR = DATA_ROOT / "private_data"

# Ensure subdirectories exist
USER_FOLDERS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Settings
TARGET_RETURN = 50
SAVE_IF_OVER_RETURN = 1.0
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

# CSV Paths
POLYMARKET_SWEEPS_CSV = DATA_ROOT / "polymarket" / "sweeps_database.csv"
POLYMARKET_EXPIRING_CSV = DATA_ROOT / "polymarket" / "expiring_markets.csv"
LIQUIDATIONS_MINI_CSV = DATA_ROOT / "liquidations" / "binance_trades_mini.csv"
LIQUIDATIONS_BIG_CSV = DATA_ROOT / "liquidations" / "binance_trades.csv"
LIQUIDATIONS_GRAND_CSV = DATA_ROOT / "liquidations" / "binance.csv"

# ============================================================================
# 🚀 FASTAPI APP INITIALIZATION
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Moon Dev's AI Agent Backtests")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# State
running_backtests: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
moon_api = MoonDevAPI()
data_status = {
    "liquidations": {"status": "pending", "last_updated": None, "file_size": None},
    "oi": {"status": "pending", "last_updated": None, "file_size": None}
}

# ============================================================================
# 🛠️ HELPER FUNCTIONS
# ============================================================================

def get_workspace_root(workspace: str | None = None) -> Path:
    if not workspace or workspace == "default":
        root = RBI_BASE_DIR
    else:
        root = RBI_BASE_DIR / workspace
    root.mkdir(parents=True, exist_ok=True)
    return root

def get_workspace_stats_csv(workspace: str) -> Path:
    return get_workspace_root(workspace) / "backtest_stats.csv"

def get_user_folders_dir(workspace: str) -> Path:
    folder_root = get_workspace_root(workspace) / "user_folders"
    folder_root.mkdir(parents=True, exist_ok=True)
    return folder_root

def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def _workspace_from_request(request: Request, workspace_override: str | None = None) -> str:
    if workspace_override:
        return workspace_override
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return "default"
    if _KS_OK:
        plan = get_plan_for_key(api_key)
        if not plan:
            raise HTTPException(status_code=403, detail="Invalid or revoked API key for workspace access")
    return _hash_api_key(api_key)[:16]

def _resolve_stats_csv(request: Request, workspace_override: str | None = None) -> tuple[str, Path]:
    workspace_name = _workspace_from_request(request, workspace_override)
    return workspace_name, get_workspace_stats_csv(workspace_name)

def _resolve_user_folders_dir(request: Request, workspace_override: str | None = None) -> tuple[str, Path]:
    workspace_name = _workspace_from_request(request, workspace_override)
    return workspace_name, get_user_folders_dir(workspace_name)

def _resolve_workspace_assets(request: Request, workspace_override: str | None = None) -> tuple[str, Path, Path, Path]:
    workspace_name = _workspace_from_request(request, workspace_override)
    root = get_workspace_root(workspace_name)
    stats_csv = root / "backtest_stats.csv"
    folders_dir = root / "user_folders"
    folders_dir.mkdir(parents=True, exist_ok=True)
    return workspace_name, root, stats_csv, folders_dir

def _get_running_backtests(workspace_name: str) -> Dict[str, Dict[str, Any]]:
    return running_backtests.setdefault(workspace_name, {})

def format_file_size(size_bytes):
    if size_bytes is None:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

# ============================================================================
# 🌙 DATA FETCHING FUNCTIONS
# ============================================================================

async def fetch_liquidation_data():
    try:
        if TEST_MODE:
            logger.info("🧪 TEST MODE: Creating sample liquidation data...")
            data_status["liquidations"]["status"] = "fetching"
            # Sample data creation logic omitted for brevity, can be added if needed
            data_status["liquidations"]["status"] = "ready"
            data_status["liquidations"]["last_updated"] = datetime.now().strftime("%H:%M:%S")
        else:
            logger.info("🌙 Fetching liquidation data...")
            data_status["liquidations"]["status"] = "fetching"
            df = moon_api.get_liquidation_data(limit=None)
            if df is not None:
                file_path = DATA_DIR / "liquidations.csv"
                df.to_csv(file_path, index=False)
                data_status["liquidations"]["status"] = "ready"
                data_status["liquidations"]["last_updated"] = datetime.now().strftime("%H:%M:%S")
                data_status["liquidations"]["file_size"] = file_path.stat().st_size
            else:
                data_status["liquidations"]["status"] = "error"
    except Exception as e:
        data_status["liquidations"]["status"] = "error"
        logger.error(f"💥 Error fetching liquidation data: {str(e)}")

async def fetch_oi_data():
    try:
        if TEST_MODE:
            data_status["oi"]["status"] = "ready"
        else:
            logger.info("📊 Fetching OI data...")
            data_status["oi"]["status"] = "fetching"
            df = moon_api.get_oi_data()
            if df is not None:
                file_path = DATA_DIR / "oi.csv"
                df.to_csv(file_path, index=False)
                data_status["oi"]["status"] = "ready"
                data_status["oi"]["last_updated"] = datetime.now().strftime("%H:%M:%S")
                data_status["oi"]["file_size"] = file_path.stat().st_size
            else:
                data_status["oi"]["status"] = "error"
    except Exception as e:
        data_status["oi"]["status"] = "error"
        logger.error(f"💥 Error fetching OI data: {str(e)}")

async def fetch_all_data():
    logger.info("🚀 Starting data fetch for all datasets...")
    try:
        await asyncio.gather(fetch_liquidation_data(), fetch_oi_data())
        logger.info("✨ Data fetch complete!")
    except Exception as e:
        logger.error(f"Error during data fetch: {str(e)}")

async def background_data_fetch():
    await asyncio.sleep(1)
    await fetch_all_data()

# ============================================================================
# 📦 MODELS
# ============================================================================

class AddToFolderRequest(BaseModel):
    folder_name: str
    backtests: List[Dict[str, Any]]

class DeleteFolderRequest(BaseModel):
    folder_name: str

class BacktestRunRequest(BaseModel):
    ideas: str
    run_name: str

# ============================================================================
# 🛣️ ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/backtests")
async def get_backtests(request: Request, workspace: str | None = None):
    try:
        workspace_name, stats_csv = _resolve_stats_csv(request, workspace)
        if not stats_csv.exists():
            return JSONResponse({"data": [], "message": "No backtest data found", "workspace": workspace_name})

        # Read CSV logic
        with open(stats_csv, 'r') as f:
            header_line = f.readline().strip()
        
        if 'Exposure %' not in header_line:
            df = pd.read_csv(stats_csv, names=['Strategy Name', 'Thread ID', 'Return %', 'Buy & Hold %',
                       'Max Drawdown %', 'Sharpe Ratio', 'Sortino Ratio', 'Exposure %',
                       'EV %', 'Trades', 'File Path', 'Data', 'Time'], skiprows=1, on_bad_lines='warn')
        else:
            df = pd.read_csv(stats_csv, on_bad_lines='warn')

        # Clean data
        df = df.replace([np.inf, -np.inf], None)
        df = df.where(pd.notnull(df), None)
        
        data = df.to_dict('records')
        return JSONResponse({"data": data, "total": len(data), "workspace": workspace_name})
    except Exception as e:
        logger.error(f"Error in get_backtests: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/stats")
async def get_stats(request: Request, workspace: str | None = None):
    try:
        workspace_name, stats_csv = _resolve_stats_csv(request, workspace)
        if not stats_csv.exists():
            return JSONResponse({"total_backtests": 0, "workspace": workspace_name})

        df = pd.read_csv(stats_csv, on_bad_lines='warn')
        
        # Basic stats calculation
        stats = {
            "total_backtests": len(df),
            "unique_strategies": df['Strategy Name'].nunique() if 'Strategy Name' in df.columns else 0,
            "workspace": workspace_name
        }
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ... (Other routes like folders, dates, etc. would be ported similarly)
# For brevity in this step, I'm ensuring the core structure is in place.
# The full port would include all endpoints.

@app.on_event("startup")
async def startup_event():
    logger.info("🌙 Moon Dev Dashboard Service Starting...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_all_data, IntervalTrigger(minutes=5), id='fetch_all_data', replace_existing=True)
    scheduler.start()
    asyncio.create_task(background_data_fetch())
