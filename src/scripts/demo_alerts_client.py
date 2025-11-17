"""Simple demo client for the Moon Dev Alerts Service.

Usage:
  ALERTS_API_KEY=your_key \
  ALERTS_BASE_URL=http://127.0.0.1:8012 \
  python src/scripts/demo_alerts_client.py

Defaults:
  - ALERTS_BASE_URL: http://127.0.0.1:8012
  - ALERTS_DEMO_TYPE: liquidation_spike | funding_extreme | whale_activity
"""

import os
import sys
import json
import requests


BASE_URL = os.getenv("ALERTS_BASE_URL", "http://127.0.0.1:8012")
API_KEY = os.getenv("ALERTS_API_KEY")
DEMO_TYPE = os.getenv("ALERTS_DEMO_TYPE", "liquidation_spike")


def _require_api_key() -> str:
    if not API_KEY:
        print("❌ ALERTS_API_KEY not set. Please export it and try again.")
        sys.exit(1)
    return API_KEY


def create_demo_alert(alert_type: str) -> None:
    key = _require_api_key()
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": key,
    }

    if alert_type == "liquidation_spike":
        payload = {
            "type": "liquidation_spike",
            "threshold": 1_000_000,
            "window_minutes": 15,
            "symbol": "BTC",
            "description": "Demo BTC liq spike 1m+ in 15m",
        }
    elif alert_type == "funding_extreme":
        payload = {
            "type": "funding_extreme",
            "threshold": 0.001,  # 0.1% absolute funding
            "window_minutes": 15,
            "symbol": "BTC",
            "description": "Demo BTC extreme funding",
        }
    elif alert_type == "whale_activity":
        payload = {
            "type": "whale_activity",
            "threshold": 10,  # change in whale address count
            "window_minutes": 30,
            "description": "Demo whale activity >= 10 addresses",
        }
    else:
        print(f"❌ Unsupported DEMO_TYPE: {alert_type}")
        sys.exit(1)

    url = f"{BASE_URL.rstrip('/')}/alerts"
    print(f"➡️  Creating {alert_type} alert at {url}...")
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
    print(f"↩️  Status: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)


def list_alerts() -> None:
    key = _require_api_key()
    headers = {"X-API-Key": key}
    url = f"{BASE_URL.rstrip('/')}/alerts"
    print(f"➡️  Listing alerts at {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"↩️  Status: {resp.status_code}")
    try:
        alerts = resp.json()
    except Exception:
        print(resp.text)
        return

    if not alerts:
        print("ℹ️  No alerts for this key yet.")
        return

    print(f"✅ Found {len(alerts)} alerts:")
    for a in alerts:
        print(f" - {a.get('id')} | type={a.get('type')} | threshold={a.get('threshold')} | window={a.get('window_minutes')}m")


if __name__ == "__main__":
    print("🌙 Moon Dev Alerts Demo Client")
    print(f"BASE_URL={BASE_URL} DEMO_TYPE={DEMO_TYPE}")

    create_demo_alert(DEMO_TYPE)
    print("\n---\n")
    list_alerts()
