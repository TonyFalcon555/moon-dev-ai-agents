"""Licensing helpers for Moon Dev agents.

This module provides a simple way to gate agent usage on API plans,
by checking an API key against the Moon Dev API Gateway.

Design goals:
- Do NOT break local development when license env vars are missing
- Fail closed only when explicitly requested (REQUIRE_LICENSE=1)
- Keep implementation minimal and HTTP-only (no DB access here)

Env vars:
- LICENSE_API_KEY: key used for license checks (usually tied to your plan)
- LICENSE_GATEWAY_URL: base URL for the API Gateway (default: http://127.0.0.1:8010)
- REQUIRE_LICENSE: if set to 1/true/yes, exit on failed license checks
- LICENSE_MIN_PLAN_FOCUS: minimum plan for focus agent (default: free)
- LICENSE_MIN_PLAN_PHONE: minimum plan for phone agent (default: free)
- LICENSE_MIN_PLAN_VIDEO: minimum plan for video agent (default: free)
- LICENSE_MIN_PLAN_CLIPS: minimum plan for realtime clips agent (default: free)
"""

from __future__ import annotations

import os
from typing import Dict

import requests
from termcolor import cprint


_PLAN_RANK: Dict[str, int] = {
    "free": 0,
    "pro": 1,
    "team": 2,
    "enterprise": 3,
}


_FEATURE_MIN_PLAN_ENV: Dict[str, str] = {
    "focus": "LICENSE_MIN_PLAN_FOCUS",
    "phone": "LICENSE_MIN_PLAN_PHONE",
    "video": "LICENSE_MIN_PLAN_VIDEO",
    "clips": "LICENSE_MIN_PLAN_CLIPS",
}


def _plan_rank(plan: str) -> int:
    return _PLAN_RANK.get(plan.lower(), 0)


def _get_min_plan_for_feature(feature: str) -> str:
    env_name = _FEATURE_MIN_PLAN_ENV.get(feature, "")
    if not env_name:
        return "free"
    return os.getenv(env_name, "free").lower()


def _get_gateway_url() -> str:
    return os.getenv("LICENSE_GATEWAY_URL", os.getenv("API_GATEWAY_URL", "http://127.0.0.1:8010")).rstrip("/")


def ensure_feature_license(feature: str) -> None:
    """Ensure that the current environment has a valid license for a feature.

    - If LICENSE_API_KEY is not set, run in dev mode (print warning, continue)
    - If REQUIRE_LICENSE is not set, failures print a warning but do not exit
    - If REQUIRE_LICENSE is set (1/true/yes), failures cause SystemExit(1)
    """

    api_key = os.getenv("LICENSE_API_KEY")
    if not api_key:
        cprint(f"⚠️ License check: LICENSE_API_KEY not set for feature '{feature}'. Running in dev mode.", "yellow")
        return

    gateway = _get_gateway_url()
    min_plan = _get_min_plan_for_feature(feature)

    try:
        resp = requests.get(
            f"{gateway}/whoami",
            headers={"X-API-Key": api_key},
            timeout=5,
        )
    except Exception as exc:
        _handle_failure(feature, f"Gateway request failed: {exc}")
        return

    if resp.status_code != 200:
        _handle_failure(feature, f"Gateway responded with status {resp.status_code}")
        return

    try:
        data = resp.json()
    except Exception:
        _handle_failure(feature, "Gateway returned non-JSON response")
        return

    plan = str(data.get("plan", "free")).lower()
    if _plan_rank(plan) < _plan_rank(min_plan):
        _handle_failure(
            feature,
            f"Plan '{plan}' does not meet minimum '{min_plan}' for feature '{feature}'",
        )
        return

    cprint(f"✅ License check passed for feature '{feature}' (plan: {plan}, min: {min_plan})", "green")


def _handle_failure(feature: str, reason: str) -> None:
    cprint(f"❌ License check failed for feature '{feature}': {reason}", "red")
    require = os.getenv("REQUIRE_LICENSE", "0").lower() in ("1", "true", "yes")
    if require:
        cprint("🚫 REQUIRE_LICENSE is set; exiting due to failed license check.", "red")
        raise SystemExit(1)
    else:
        cprint("⚠️ Continuing in dev mode despite license failure (REQUIRE_LICENSE is not set).", "yellow")
