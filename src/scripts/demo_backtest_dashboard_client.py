"""Simple demo client for the Moon Dev Backtest Dashboard.

Usage:
  DASHBOARD_BASE_URL=http://127.0.0.1:8002 \
  DASHBOARD_API_KEY=your_key (optional) \
  DASHBOARD_WORKSPACE=my-workspace (optional) \
  python src/scripts/demo_backtest_dashboard_client.py

Defaults:
  - DASHBOARD_BASE_URL: http://127.0.0.1:8002
  - If DASHBOARD_API_KEY is set, it is sent as X-API-Key.
  - If DASHBOARD_WORKSPACE is set, it is passed as ?workspace=...
"""

import os
import sys
import json
import requests


BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://127.0.0.1:8002")
API_KEY = os.getenv("DASHBOARD_API_KEY")
WORKSPACE = os.getenv("DASHBOARD_WORKSPACE")


def _make_headers() -> dict:
    headers: dict = {"Accept": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def _make_params() -> dict:
    params: dict = {}
    if WORKSPACE:
        params["workspace"] = WORKSPACE
    return params


def fetch_stats() -> None:
    url = f"{BASE_URL.rstrip('/')}/api/stats"
    print(f"➡️  GET {url}")
    resp = requests.get(url, headers=_make_headers(), params=_make_params(), timeout=20)
    print(f"↩️  Status: {resp.status_code}")
    try:
        data = resp.json()
    except Exception:
        print(resp.text)
        return

    print(json.dumps(data, indent=2))


def fetch_backtests(limit: int = 5) -> None:
    url = f"{BASE_URL.rstrip('/')}/api/backtests"
    print(f"➡️  GET {url}")
    resp = requests.get(url, headers=_make_headers(), params=_make_params(), timeout=20)
    print(f"↩️  Status: {resp.status_code}")
    try:
        data = resp.json()
    except Exception:
        print(resp.text)
        return

    items = data.get("data", []) if isinstance(data, dict) else []
    ws = data.get("workspace") if isinstance(data, dict) else None
    print(f"✅ Workspace: {ws}")
    print(f"✅ Total backtests: {len(items)}")
    print()
    for i, row in enumerate(items[:limit], start=1):
        name = row.get("Strategy Name") or row.get("Strategy") or "?"
        ret = row.get("Return %")
        ev = row.get("EV %")
        print(f" {i:>2}. {name} | Return={ret} | EV={ev}")


if __name__ == "__main__":
    print("🌙 Moon Dev Backtest Dashboard Demo Client")
    print(f"BASE_URL={BASE_URL} WORKSPACE={WORKSPACE} API_KEY_SET={'yes' if API_KEY else 'no'}")

    fetch_stats()
    print("\n---\n")
    fetch_backtests()
