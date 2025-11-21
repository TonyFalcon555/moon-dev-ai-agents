# Falcon Finance Launch Checklist

## Pre-Launch (Do this BEFORE going live)

### 1. Stripe Setup
- [ ] Create Stripe account and complete business verification
- [ ] Create products for Pro, Team, and Enterprise plans
- [ ] Copy Price IDs to `.env`
- [ ] Set up webhook endpoint
- [ ] Test checkout flow in Stripe **Test Mode**

### 2. Server Setup
- [ ] Provision VPS (DigitalOcean, AWS, Hetzner, etc.)
- [ ] Point domain to server IP (A record)
- [ ] SSH into server and clone repo
- [ ] Create `.env` file (use `.env.example` as template)
- [ ] Run `./deploy.sh`

### 3. Security Configuration
- [ ] Change `POSTGRES_PASSWORD` to a strong password
- [ ] Ensure `.env` is in `.gitignore` (not committed)
- [ ] Set up SSL/TLS (use Caddy or Let's Encrypt)
- [ ] Enable firewall (allow only 22, 80, 443, 8080)

### 4. Service Verification
- [ ] Visit `http://your-ip:8080` → Sales page loads
- [ ] Visit `http://your-ip:8002` → Dashboard loads
- [ ] Visit `http://your-ip:8000` → API Docs load
- [ ] Check logs: `docker-compose logs -f`

### 5. Test End-to-End Flow
- [ ] Click "Get Pro" on sales page
- [ ] Complete test purchase (use Stripe test card: `4242 4242 4242 4242`)
- [ ] Verify webhook received: `docker-compose logs billing`
- [ ] Check API key generated: `docker exec -it falcon-api-gateway bash` → inspect DB

## Launch Day

### 1. Go Live
- [ ] Switch Stripe to **Live Mode**
- [ ] Update `.env` with live Stripe keys
- [ ] Restart services: `docker-compose restart`

### 2. Announce
- [ ] Post on Twitter/X about launch
- [ ] Share in crypto Discord/Telegram groups
- [ ] Email your list (if you have one)

### 3. Monitor
- [ ] Watch error logs: `docker-compose logs -f | grep ERROR`
- [ ] Check Stripe Dashboard for real purchases
- [ ] Test a real purchase yourself ($29 for Pro)

## Post-Launch (First Week)

### 1. First Customer Setup
When you get your first customer:
- [ ] Verify API key was auto-generated
- [ ] Send welcome email with dashboard link
- [ ] Check their usage in the API Gateway logs

### 2. Content Flywheel
- [ ] Start `auto_content.py` to generate videos
- [ ] Upload videos to TikTok/YouTube with CTA to your site
- [ ] Monitor traffic from social media

### 3. Optimization
- [ ] Set up Google Analytics on the sales page
- [ ] A/B test pricing (try $39 vs $29)
- [ ] Add testimonials to sales page (once you have them)

## Ongoing Operations

### Daily
- [ ] Check Stripe Dashboard for new customers
- [ ] Review error logs
- [ ] Respond to support emails

### Weekly
- [ ] Generate content (videos, posts)
- [ ] Check server resources (CPU, RAM, disk)
- [ ] Backup database: `pg_dump`

### Monthly
- [ ] Review revenue and churn rate
- [ ] Experiment with new pricing or features
- [ ] Update roadmap based on customer feedback

## Emergency Procedures

### If Site Goes Down
```bash
# SSH into server
ssh root@your-server-ip

# Check service status
docker-compose ps

# Restart everything
docker-compose down && docker-compose up -d

# Check logs
docker-compose logs -f
```

### If Payments Stop Working
1. Check Stripe Dashboard → Webhooks → Recent deliveries
2. Verify webhook secret in `.env` matches Stripe
3. Restart billing service: `docker-compose restart billing`
