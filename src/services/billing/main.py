import os
import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

try:
    from src.services.api_gateway.keystore import add_key
except Exception:
    try:
        from ..api_gateway.keystore import add_key
    except Exception:
        add_key = None  # type: ignore

app = FastAPI(title="Moon Dev Billing Service")


def _require_stripe():
    try:
        import stripe  # type: ignore
        return stripe
    except Exception:
        raise HTTPException(status_code=500, detail="Stripe library not installed")


def _get_price_id(plan: str) -> Optional[str]:
    if plan == "pro":
        return os.getenv("PRICE_ID_PRO")
    if plan == "team":
        return os.getenv("PRICE_ID_TEAM")
    if plan == "enterprise":
        return os.getenv("PRICE_ID_ENTERPRISE")
    return None


@app.post("/billing/create-checkout-session")
async def create_checkout_session(payload: dict):
    plan = payload.get("plan")
    success_url = payload.get("success_url")
    cancel_url = payload.get("cancel_url")
    customer_email = payload.get("customer_email")

    if plan not in {"pro", "team", "enterprise"}:
        raise HTTPException(status_code=400, detail="Invalid plan")

    price_id = _get_price_id(plan)
    if not price_id:
        raise HTTPException(status_code=500, detail="Missing price id env var for plan")

    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=500, detail="Missing STRIPE_SECRET_KEY")

    stripe = _require_stripe()
    stripe.api_key = secret

    try:
        session = stripe.checkout.Session.create(  # type: ignore[attr-defined]
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=customer_email,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {e.__class__.__name__}")

    return JSONResponse({"url": session.url})


@app.post("/billing/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Missing STRIPE_WEBHOOK_SECRET")

    stripe = _require_stripe()

    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)  # type: ignore[attr-defined]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {e.__class__.__name__}")

    et = event.get("type")
    data = event.get("data", {}).get("object", {})

    if et == "checkout.session.completed":
        sub = data.get("subscription")
        price_id = None
        customer_email = data.get("customer_email")
        try:
            if sub:
                s = stripe.Subscription.retrieve(sub)  # type: ignore[attr-defined]
                items = s.get("items", {}).get("data", [])
                if items:
                    price_id = items[0].get("price", {}).get("id")
        except Exception:
            price_id = None

        plan = None
        if price_id and price_id == os.getenv("PRICE_ID_PRO"):
            plan = "pro"
        elif price_id and price_id == os.getenv("PRICE_ID_TEAM"):
            plan = "team"
        elif price_id and price_id == os.getenv("PRICE_ID_ENTERPRISE"):
            plan = "enterprise"

        if plan and add_key:
            try:
                # Optional per-plan overrides
                overrides = {
                    "pro": int(os.getenv("RATE_LIMIT_PRO", "600")),
                    "team": int(os.getenv("RATE_LIMIT_TEAM", "2400")),
                    "enterprise": int(os.getenv("RATE_LIMIT_ENTERPRISE", "10000")),
                }
                rlo = overrides.get(plan)
                meta = json.dumps({
                    "customer_email": customer_email,
                    "subscription_id": sub,
                    "price_id": price_id,
                })
                _ = add_key(plan=plan, rate_limit_override=rlo, metadata=meta)
            except Exception:
                pass

    return JSONResponse({"received": True, "type": et})
