# Stripe Setup Guide for Falcon Finance

This guide walks you through setting up Stripe to accept payments for Falcon Finance.

## Step 1: Create Stripe Account

1. Go to [stripe.com](https://stripe.com) and sign up.
2. Complete business verification (required for live mode).
3. Navigate to the **Dashboard**.

## Step 2: Get API Keys

1. In the Stripe Dashboard, go to **Developers** → **API keys**.
2. Copy your **Publishable key** and **Secret key**.
3. For testing, use the **Test mode** toggle to get test keys.

**Add to your `.env` file:**
```bash
STRIPE_SECRET_KEY=sk_test_... # Or sk_live_... for production
```

## Step 3: Create Products & Prices

### Pro Plan
1. Go to **Products** → **Add product**.
2. **Name**: `Falcon Finance Pro`
3. **Pricing**:
   - **Amount**: $29
   - **Billing period**: Monthly (recurring)
4. Click **Save product**.
5. Copy the **Price ID** (starts with `price_...`).

### Team Plan  
1. Repeat for "Falcon Finance Team" at $149/month.

### Enterprise Plan
1. Repeat for "Falcon Finance Enterprise" at $999/month (or custom).

**Add to your `.env` file:**
```bash
PRICE_ID_PRO=price_...
PRICE_ID_TEAM=price_...
PRICE_ID_ENTERPRISE=price_...
```

## Step 4: Configure Webhooks

1. Go to **Developers** → **Webhooks** → **Add endpoint**.
2. **Endpoint URL**: `https://yourdomain.com/billing/webhook` (or `http://your-ip:8011/webhook` for testing).
3. **Events to send**:
   - `checkout.session.completed`
4. Click **Add endpoint**.
5. Copy the **Signing secret** (starts with `whsec_...`).

**Add to your `.env` file:**
```bash
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Step 5: Test the Integration

### Local Testing

```bash
# 1. Start the stack
docker-compose up -d

# 2. Use Stripe CLI to forward webhooks
stripe listen --forward-to localhost:8011/webhook

# 3. Create a test checkout session
curl -X POST http://localhost:8011/create-checkout-session \
  -H "Content-Type: application/json" \
  -d '{"plan": "pro"}'

# 4. Use the returned URL to complete a test checkout
```

## Step 6: Go Live

1. **Activate your Stripe account** (complete business verification).
2. **Toggle to Live mode** in the Stripe Dashboard.
3. Update `.env` with **live keys**:
   - Replace `sk_test_...` with `sk_live_...`
   - Replace webhook secret with live endpoint secret.
4. **Restart services**: `docker-compose restart billing`

## Troubleshooting

### "API key invalid"
- Ensure you're using the correct key for the mode (test vs live).
- Check that `STRIPE_SECRET_KEY` is set in `.env`.

### "Webhook signature verification failed"
- Ensure `STRIPE_WEBHOOK_SECRET` matches the endpoint in Stripe Dashboard.
- Check that the webhook URL is publicly accessible.

### "Price not found"
- Verify `PRICE_ID_PRO` etc. match the IDs in your Stripe Dashboard.
