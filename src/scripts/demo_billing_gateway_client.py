"""Demo client for Billing Service + API Gateway.

This script shows how to:
- Create a Stripe Checkout session via the Billing service
- Call the API Gateway /whoami and /quota endpoints for a given key

Usage examples:

  # 1) Create a Checkout session for plan=pro
  BILLING_BASE_URL=http://127.0.0.1:8011 \
  BILLING_PLAN=pro \
  BILLING_SUCCESS_URL=http://localhost/success \
  BILLING_CANCEL_URL=http://localhost/cancel \
  BILLING_CUSTOMER_EMAIL=you@example.com \
  python src/scripts/demo_billing_gateway_client.py checkout

  # 2) Call API Gateway with an existing key (after webhook has provisioned it)
  GATEWAY_BASE_URL=http://127.0.0.1:8010 \
  GATEWAY_API_KEY=md_your_key_here \
  python src/scripts/demo_billing_gateway_client.py gateway
"""

import os
import sys
import json
import requests


BILLING_BASE_URL = os.getenv("BILLING_BASE_URL", "http://127.0.0.1:8011")
GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8010")


def create_checkout_session() -> None:
    plan = os.getenv("BILLING_PLAN", "pro")
    success_url = os.getenv("BILLING_SUCCESS_URL", "http://localhost/success")
    cancel_url = os.getenv("BILLING_CANCEL_URL", "http://localhost/cancel")
    customer_email = os.getenv("BILLING_CUSTOMER_EMAIL", "demo@example.com")

    payload = {
        "plan": plan,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "customer_email": customer_email,
    }

    url = f"{BILLING_BASE_URL.rstrip('/')}/billing/create-checkout-session"
    print(f"➡️  POST {url}")
    print(f"   payload={payload}")

    resp = requests.post(url, json=payload, timeout=20)
    print(f"↩️  Status: {resp.status_code}")
    try:
        data = resp.json()
    except Exception:
        print(resp.text)
        return

    checkout_url = data.get("url")
    if not checkout_url:
        print("❌ No 'url' field returned from billing service:")
        print(json.dumps(data, indent=2))
        return

    print("✅ Checkout session created. Open this URL in your browser:")
    print(checkout_url)
    print("\nAfter completing a test payment and handling the webhook, the billing\nservice will provision an API key into the gateway keystore.")


def gateway_demo() -> None:
    api_key = os.getenv("GATEWAY_API_KEY")
    if not api_key:
        print("❌ GATEWAY_API_KEY env var is required for gateway demo.")
        sys.exit(1)

    headers = {"X-API-Key": api_key}

    # /whoami
    whoami_url = f"{GATEWAY_BASE_URL.rstrip('/')}/whoami"
    print(f"➡️  GET {whoami_url}")
    r1 = requests.get(whoami_url, headers=headers, timeout=10)
    print(f"↩️  Status: {r1.status_code}")
    try:
        print(json.dumps(r1.json(), indent=2))
    except Exception:
        print(r1.text)

    print("\n---\n")

    # /quota
    quota_url = f"{GATEWAY_BASE_URL.rstrip('/')}/quota"
    print(f"➡️  GET {quota_url}")
    r2 = requests.get(quota_url, headers=headers, timeout=10)
    print(f"↩️  Status: {r2.status_code}")
    try:
        print(json.dumps(r2.json(), indent=2))
    except Exception:
        print(r2.text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/scripts/demo_billing_gateway_client.py [checkout|gateway]")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "checkout":
        print("🌙 Billing Service Demo (Checkout Session)")
        print(f"BILLING_BASE_URL={BILLING_BASE_URL}")
        create_checkout_session()
    elif mode == "gateway":
        print("🌙 API Gateway Demo (whoami/quota)")
        print(f"GATEWAY_BASE_URL={GATEWAY_BASE_URL}")
        gateway_demo()
    else:
        print("❌ Unknown mode. Use 'checkout' or 'gateway'.")
        sys.exit(1)
