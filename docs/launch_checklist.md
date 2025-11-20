# 🚀 Moon Dev SaaS Launch Checklist

Your step-by-step guide to turn this codebase into a profitable product.

---

## ✅ Phase 1: Test Everything Locally (1-2 days)

**Goal:** Make sure the whole stack works on your laptop before touching production.

### □ 1.1 Set up your environment files

- [ ] Copy `.env_example` → `.env` in repo root
- [ ] Copy `src/.env_example` → `src/.env`
- [ ] Fill in these critical values in `src/.env`:
  - [ ] `MOONDEV_API_KEY` (your Moon Dev data API key)
  - [ ] `STRIPE_SECRET_KEY` (use test mode: `sk_test_...`)
  - [ ] `ALERTS_DISCORD_WEBHOOK_URL` (create a private test channel)
  - [ ] `USE_KEYSTORE=1`

### □ 1.2 Start the stack

```bash
cd /path/to/moon-dev-ai-agents
docker compose up --build
```

Wait for all services to start:
- ✓ Gateway on http://127.0.0.1:8010
- ✓ Billing on http://127.0.0.1:8011
- ✓ Alerts on http://127.0.0.1:8012
- ✓ Dashboard on http://127.0.0.1:8002

### □ 1.3 Test billing → gateway flow

```bash
# Create a Stripe checkout session
export BILLING_BASE_URL=http://127.0.0.1:8011
python src/scripts/demo_billing_gateway_client.py checkout
```

- [ ] Open the printed URL in your browser
- [ ] Complete a test payment (use Stripe test card: 4242 4242 4242 4242)
- [ ] Check Docker logs to confirm webhook ran
- [ ] Copy the new API key from logs

```bash
# Test the new key
export GATEWAY_API_KEY=md_your_new_key_here
python src/scripts/demo_billing_gateway_client.py gateway
```

- [ ] Confirm `/whoami` shows correct plan
- [ ] Confirm `/quota` shows usage limits

### □ 1.4 Test alerts

```bash
export ALERTS_API_KEY=md_your_key_here
python src/scripts/demo_alerts_client.py
```

- [ ] Alert created successfully
- [ ] Alert appears in Discord (when conditions met)

### □ 1.5 Test backtest dashboard

```bash
export DASHBOARD_API_KEY=md_your_key_here
python src/scripts/demo_backtest_dashboard_client.py
```

- [ ] Stats endpoint responds
- [ ] Backtests endpoint responds
- [ ] Workspace is correctly identified

**🎉 Checkpoint:** If all tests pass, you're ready for production!

---

## ✅ Phase 2: Deploy to Production (1 day)

**Goal:** Get your stack running on a real server with HTTPS.

### □ 2.1 Get a server

- [ ] Sign up for hosting (Hetzner, DigitalOcean, Linode, etc.)
- [ ] Create a VPS:
  - Recommended: 2-4 vCPU, 8GB RAM
  - OS: Ubuntu 22.04 or similar
- [ ] Note your server IP: `___.___.___.___ `

### □ 2.2 Set up the server

SSH into your server and run:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Install Caddy (for HTTPS)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### □ 2.3 Copy your code to the server

From your local machine:

```bash
# Copy the repo
scp -r moon-dev-ai-agents root@YOUR_SERVER_IP:/opt/

# Copy your .env files
scp .env root@YOUR_SERVER_IP:/opt/moon-dev-ai-agents/
scp src/.env root@YOUR_SERVER_IP:/opt/moon-dev-ai-agents/src/
```

### □ 2.4 Point your domain to the server

- [ ] Buy a domain (if you don't have one): Namecheap, Cloudflare, etc.
- [ ] Create an A record: `yourdomain.com` → `YOUR_SERVER_IP`
- [ ] Wait 5-10 minutes for DNS to propagate

### □ 2.5 Configure Caddy for HTTPS

On the server, create `/etc/caddy/Caddyfile`:

```caddyfile
yourdomain.com {
    reverse_proxy /gateway* 127.0.0.1:8010
    reverse_proxy /billing* 127.0.0.1:8011
    reverse_proxy /alerts* 127.0.0.1:8012
    reverse_proxy /dashboard* 127.0.0.1:8002
    reverse_proxy /* 127.0.0.1:8002
}
```

Start Caddy:

```bash
sudo systemctl restart caddy
```

### □ 2.6 Start your stack

```bash
cd /opt/moon-dev-ai-agents
docker compose up --build -d
```

### □ 2.7 Test production endpoints

- [ ] Visit `https://yourdomain.com/dashboard` (should load)
- [ ] Test gateway: `curl https://yourdomain.com/gateway/health`
- [ ] Test billing: `curl https://yourdomain.com/billing/health`

**🎉 Checkpoint:** Your stack is live and secure!

---

## ✅ Phase 3: Set Up Stripe for Real Money (2-3 hours)

**Goal:** Connect Stripe so people can actually pay you.

### □ 3.1 Create Stripe products

Go to https://dashboard.stripe.com/products

Create 3 products:

**Product 1: Builder**
- [ ] Name: "Builder Plan"
- [ ] Price: $49/month (or your choice)
- [ ] Copy the price ID: `price_________________`
- [ ] Save to `src/.env` as `PRICE_ID_PRO=price_...`

**Product 2: Desk**
- [ ] Name: "Desk Plan"
- [ ] Price: $149/month
- [ ] Copy the price ID: `price_________________`
- [ ] Save as `PRICE_ID_TEAM=price_...`

**Product 3: Fund**
- [ ] Name: "Fund Plan"
- [ ] Price: $299/month
- [ ] Copy the price ID: `price_________________`
- [ ] Save as `PRICE_ID_ENTERPRISE=price_...`

### □ 3.2 Set up webhook

In Stripe dashboard → Developers → Webhooks:

- [ ] Click "Add endpoint"
- [ ] URL: `https://yourdomain.com/billing/webhook`
- [ ] Events to listen for:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- [ ] Copy the signing secret: `whsec_________________`
- [ ] Save to `src/.env` as `STRIPE_WEBHOOK_SECRET=whsec_...`

### □ 3.3 Update your production .env

On the server:

```bash
cd /opt/moon-dev-ai-agents
nano src/.env
```

Update these lines:
- `STRIPE_SECRET_KEY=sk_live_...` (switch to live mode)
- `STRIPE_WEBHOOK_SECRET=whsec_...`
- `PRICE_ID_PRO=price_...`
- `PRICE_ID_TEAM=price_...`
- `PRICE_ID_ENTERPRISE=price_...`

Restart:

```bash
docker compose down
docker compose up -d
```

### □ 3.4 Test a real payment

- [ ] Create a checkout session (use the demo script or manually)
- [ ] Complete a payment with a real card
- [ ] Check logs: `docker compose logs billing`
- [ ] Verify key was created in keystore
- [ ] Test the key against gateway

**🎉 Checkpoint:** You can now accept real payments!

---

## ✅ Phase 4: Create Your Sales Page (1 day)

**Goal:** A simple page where people can see plans and buy.

### □ 4.1 Choose your tool

Pick one (easiest to hardest):
- [ ] Notion (free, 5 min setup)
- [ ] Framer (beautiful, $5-20/mo)
- [ ] Webflow (powerful, $14/mo)
- [ ] Custom HTML (free, more work)

### □ 4.2 Write your copy

Use this structure:

**Hero Section:**
```
Moon Dev Trading Stack
Professional-grade crypto data, alerts, and backtesting for serious traders

[Get Started →]
```

**What You Get:**
- Real-time liquidation, funding, and OI data via API
- Discord alerts on market extremes
- Multi-tenant backtest dashboard with RBI agent
- Premium AI agents (Focus, Video, Clips)

**Pricing:**

| Feature | Builder | Desk | Fund |
|---------|---------|------|------|
| Price | $49/mo | $149/mo | $299/mo |
| API Requests | 600/min | 2,400/min | 10,000/min |
| Alerts | 10 | 50 | 200 |
| Workspaces | 1 | 3 | Unlimited |
| Agents | Focus | Focus + Video + Clips | All |
| [Buy Now] | [Buy Now] | [Contact] |

### □ 4.3 Link to Stripe

For each "Buy Now" button:

1. Create a Stripe Payment Link:
   - Go to Stripe → Payment Links
   - Select your product
   - Copy the link
2. Set button URL to that link

### □ 4.4 Add docs links

At the bottom:
- [ ] Link to `docs/api.md` (API documentation)
- [ ] Link to `docs/backtest_dashboard.md`
- [ ] Link to alerts README
- [ ] Discord invite link

**🎉 Checkpoint:** You have a working sales page!

---

## ✅ Phase 5: Launch & Get Your First Customers (1-2 weeks)

**Goal:** 10-20 paying users in the first month.

### □ 5.1 Prepare your launch content

**YouTube Video:**
- [ ] Title: "I Built a Trading Data SaaS (Open Source + Managed)"
- [ ] Show:
  - Quick demo of API calls
  - Alerts firing in Discord
  - Dashboard with backtests
  - Licensed agents running
- [ ] CTA: Link to your sales page
- [ ] Duration: 10-15 minutes

**Discord Announcement:**
```
🚀 BIG NEWS: Moon Dev Stack is now available as a managed service!

I've been running this for my own trading and now you can too:
✅ Professional data API (liq, funding, OI, whales)
✅ Discord alerts on market extremes
✅ Multi-tenant backtest dashboard
✅ Premium AI agents

🎁 FOUNDING MEMBERS (Limited to 20):
- 50% off for life
- Direct access to me for support
- Shape the product roadmap

Link: [your sales page]
```

### □ 5.2 Launch sequence

**Day 1:**
- [ ] Post YouTube video
- [ ] Pin Discord announcement
- [ ] Tweet about it (if you use Twitter)

**Day 2-3:**
- [ ] Answer questions in Discord
- [ ] Help first users get set up
- [ ] Fix any obvious bugs

**Week 1:**
- [ ] Check: How many checkouts?
- [ ] Check: How many active API keys?
- [ ] Collect feedback from early users

### □ 5.3 Onboard each customer personally

For each new paying user:

1. Send them an email:
```
Hey [name],

Thanks for joining Moon Dev Stack!

Your API Key: md_xxxxxxxxxxxxx

Quick Start:
- API Docs: [link to docs/api.md]
- Create an alert: [link to alerts README]
- Dashboard: https://yourdomain.com/dashboard

Questions? Reply to this email or ping me in Discord.

- Moon Dev
```

2. Give them a role in Discord
3. Invite them to a private "customers" channel

### □ 5.4 Track your metrics

Create a simple spreadsheet:

| Week | MRR | Active Keys | Support Hours | Notes |
|------|-----|-------------|---------------|-------|
| 1 | $0 | 0 | 0 | Launch |
| 2 | $XXX | X | X | ... |

**Target for Month 1:**
- [ ] 10-20 paying customers
- [ ] $500-2,000 MRR
- [ ] <5 hours/week support time

**🎉 Checkpoint:** You're making money!

---

## ✅ Phase 6: Optimize & Scale (Ongoing)

### □ 6.1 Improve based on feedback

- [ ] What features do people actually use?
- [ ] What questions keep coming up? → Add to docs
- [ ] Any bugs or issues? → Fix immediately

### □ 6.2 Add monitoring

- [ ] Set up basic uptime monitoring (UptimeRobot, free)
- [ ] Get alerts if services go down
- [ ] Check disk space weekly

### □ 6.3 Consider next features

Based on usage:
- [ ] More alert types (funding + OI combos, Polymarket)
- [ ] Admin dashboard for managing keys
- [ ] API usage analytics for customers
- [ ] More licensed agents
- [ ] Team features (shared workspaces)

### □ 6.4 Scale pricing

Once you hit 20+ customers:
- [ ] Raise prices for new customers
- [ ] Grandfather existing customers
- [ ] Add annual plans (2 months free)

---

## 🎯 Success Metrics

**Month 1 Goal:** $500-2,000 MRR  
**Month 3 Goal:** $3,000-5,000 MRR  
**Month 6 Goal:** $10,000+ MRR

**You're profitable when:** MRR > (Server costs + Your time × hourly rate)

---

## 🆘 Troubleshooting

**Webhook not working?**
- Check Stripe logs in dashboard
- Check `docker compose logs billing`
- Verify webhook URL is correct

**Keys not being created?**
- Check keystore DB exists: `docker compose exec api-gateway ls -la /data`
- Check billing logs for errors

**High support load?**
- Improve docs with common questions
- Create video tutorials
- Add FAQ section to sales page

**Not getting customers?**
- Make another YouTube video
- Offer free trial (7 days)
- Ask existing users for testimonials

---

## 📞 Need Help?

- Check `docs/` folder for technical docs
- Review demo scripts in `src/scripts/`
- Discord community for peer support

**You've got this! 🚀**
