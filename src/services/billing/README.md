# Moon Dev Billing Service

FastAPI service integrating Stripe subscriptions with the API Gateway keystore. Handles Checkout session creation and webhooks to auto‑provision API keys with per‑plan rate limits.

## Endpoints

- POST /billing/create-checkout-session
  - body: { "plan": "pro|team|enterprise", "success_url": "https://...", "cancel_url": "https://...", "customer_email": "user@example.com" }
  - returns: { url } — open this URL to pay via Stripe Checkout

- POST /billing/webhook
  - Stripe signature‑verified endpoint. On `checkout.session.completed` it:
    - Resolves `price_id` → plan (pro/team/enterprise)
    - Creates a keystore API key with optional per‑plan rate‑limit override
    - Stores metadata: customer_email, subscription_id, price_id

- GET /health — simple healthcheck

## Environment

Required:
- STRIPE_SECRET_KEY=sk_test_...
- STRIPE_WEBHOOK_SECRET=whsec_...
- PRICE_ID_PRO=price_...
- PRICE_ID_TEAM=price_...
- PRICE_ID_ENTERPRISE=price_...

Optional per‑plan rate limits (forwarded to keystore):
- RATE_LIMIT_PRO=600
- RATE_LIMIT_TEAM=2400
- RATE_LIMIT_ENTERPRISE=10000

An example file is provided at `.env.example` in this folder.

## Run locally

- Using uvicorn (from repo root):
```bash
uvicorn src.services.billing.main:app --host 127.0.0.1 --port 8011
```

- With Docker:
```bash
docker build -t moondev-billing src/services/billing
docker run --rm -p 8011:8011 \
  -e STRIPE_SECRET_KEY \
  -e STRIPE_WEBHOOK_SECRET \
  -e PRICE_ID_PRO -e PRICE_ID_TEAM -e PRICE_ID_ENTERPRISE \
  -e RATE_LIMIT_PRO -e RATE_LIMIT_TEAM -e RATE_LIMIT_ENTERPRISE \
  moondev-billing
```

## Create a Checkout session (test)

```bash
curl -s -X POST http://127.0.0.1:8011/billing/create-checkout-session \
  -H 'Content-Type: application/json' \
  -d '{
    "plan": "pro",
    "success_url": "http://localhost/success",
    "cancel_url": "http://localhost/cancel",
    "customer_email": "user@example.com"
  }'
```
This returns `{ "url": "https://checkout.stripe.com/..." }`. Open it and complete the test payment.

## Webhook testing (Stripe CLI)

```bash
stripe listen --forward-to localhost:8011/billing/webhook
```
Set `STRIPE_WEBHOOK_SECRET` to the signing secret printed by the CLI.

After completing checkout, the webhook provisions an API key into the gateway keystore. Use it with the API Gateway:
```bash
curl -H "X-API-Key: <NEW_KEY>" http://127.0.0.1:8010/whoami
```

## Notes
- Ensure the API Gateway keystore database is accessible (same volume or shared path if running in containers).
- Webhook must be reachable by Stripe (use Stripe CLI or a tunnel in development).
