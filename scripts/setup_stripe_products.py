#!/usr/bin/env python3
"""
🌙 Moon Dev's Stripe Product Setup Script
Creates all required Stripe products and prices for monetization

Run: python scripts/setup_stripe_products.py

This will create:
- Pro Plan ($49/mo)
- Team Plan ($149/mo) 
- Enterprise Plan ($299/mo)
- Alert Packs (one-time purchases)
- Data Packs (one-time purchases)
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

try:
    import stripe
except ImportError:
    print("❌ Stripe not installed. Run: pip install stripe")
    sys.exit(1)


# Configuration
PRODUCTS = {
    "subscriptions": [
        {
            "name": "Falcon Pro",
            "description": "600 API requests/min, 20 alerts, real-time data, priority support",
            "price_cents": 4900,  # $49
            "interval": "month",
            "env_key": "PRICE_ID_PRO",
            "metadata": {"plan": "pro", "rate_limit": "600"}
        },
        {
            "name": "Falcon Team",
            "description": "2400 API requests/min, 50 alerts, multiple API keys, white-label ready",
            "price_cents": 14900,  # $149
            "interval": "month",
            "env_key": "PRICE_ID_TEAM",
            "metadata": {"plan": "team", "rate_limit": "2400"}
        },
        {
            "name": "Falcon Enterprise",
            "description": "10000 API requests/min, 200 alerts, SLA, dedicated support, custom integrations",
            "price_cents": 29900,  # $299
            "interval": "month",
            "env_key": "PRICE_ID_ENTERPRISE",
            "metadata": {"plan": "enterprise", "rate_limit": "10000"}
        },
    ],
    "one_time": [
        {
            "name": "Alert Pack - Starter",
            "description": "10 additional alert slots",
            "price_cents": 1500,  # $15
            "env_key": "PRICE_ID_ALERT_PACK_STARTER",
            "metadata": {"type": "alert_pack", "alerts": "10"}
        },
        {
            "name": "Alert Pack - Pro",
            "description": "50 additional alert slots",
            "price_cents": 4900,  # $49
            "env_key": "PRICE_ID_ALERT_PACK_PRO",
            "metadata": {"type": "alert_pack", "alerts": "50"}
        },
        {
            "name": "Liquidation Data Pack",
            "description": "Full historical liquidation dataset (CSV + Jupyter notebook)",
            "price_cents": 2900,  # $29
            "env_key": "PRICE_ID_DATA_LIQUIDATIONS",
            "metadata": {"type": "data_pack", "dataset": "liquidations"}
        },
        {
            "name": "Complete Data Bundle",
            "description": "All datasets: Liquidations, Funding, OI, Whale addresses + quarterly refresh",
            "price_cents": 19900,  # $199
            "env_key": "PRICE_ID_DATA_BUNDLE",
            "metadata": {"type": "data_pack", "dataset": "all"}
        },
    ]
}


def setup_stripe():
    """Initialize Stripe with API key"""
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        print("❌ STRIPE_SECRET_KEY not found in environment")
        print("   Set it in your .env file or export it")
        sys.exit(1)
    
    stripe.api_key = api_key
    
    # Verify connection
    try:
        stripe.Account.retrieve()
        print("✅ Connected to Stripe")
    except stripe.error.AuthenticationError:
        print("❌ Invalid Stripe API key")
        sys.exit(1)


def create_product_and_price(product_config: dict, is_recurring: bool = True) -> tuple:
    """Create a Stripe product and its price"""
    
    # Check if product already exists
    existing = stripe.Product.search(query=f"name:'{product_config['name']}'")
    
    if existing.data:
        product = existing.data[0]
        print(f"  ℹ️  Product '{product_config['name']}' already exists")
    else:
        product = stripe.Product.create(
            name=product_config["name"],
            description=product_config["description"],
            metadata=product_config.get("metadata", {})
        )
        print(f"  ✅ Created product: {product_config['name']}")
    
    # Create price
    price_data = {
        "product": product.id,
        "unit_amount": product_config["price_cents"],
        "currency": "usd",
        "metadata": product_config.get("metadata", {})
    }
    
    if is_recurring:
        price_data["recurring"] = {"interval": product_config.get("interval", "month")}
    
    price = stripe.Price.create(**price_data)
    print(f"  💰 Created price: ${product_config['price_cents']/100:.2f}")
    
    return product, price


def main():
    print("\n🦅 Falcon Finance - Stripe Product Setup")
    print("=" * 50)
    
    setup_stripe()
    
    env_updates = {}
    
    # Create subscription products
    print("\n📦 Creating Subscription Products...")
    for product_config in PRODUCTS["subscriptions"]:
        print(f"\n  Creating: {product_config['name']}")
        product, price = create_product_and_price(product_config, is_recurring=True)
        env_updates[product_config["env_key"]] = price.id
    
    # Create one-time products
    print("\n📦 Creating One-Time Products...")
    for product_config in PRODUCTS["one_time"]:
        print(f"\n  Creating: {product_config['name']}")
        product, price = create_product_and_price(product_config, is_recurring=False)
        env_updates[product_config["env_key"]] = price.id
    
    # Output env updates
    print("\n" + "=" * 50)
    print("📋 Add these to your .env file:\n")
    for key, value in env_updates.items():
        print(f"{key}={value}")
    
    # Optionally update .env file
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print(f"\n💾 Updating {env_file}...")
        
        content = env_file.read_text()
        for key, value in env_updates.items():
            if f"{key}=" in content:
                # Update existing
                import re
                content = re.sub(
                    rf"^{key}=.*$",
                    f"{key}={value}",
                    content,
                    flags=re.MULTILINE
                )
            else:
                # Append
                content += f"\n{key}={value}"
        
        env_file.write_text(content)
        print("✅ .env file updated!")
    
    print("\n🎉 Stripe setup complete!")
    print("\n📖 Next steps:")
    print("   1. Set up webhook endpoint in Stripe Dashboard")
    print("   2. Add webhook URL: https://yourdomain.com/billing/webhook")
    print("   3. Select events: checkout.session.completed, customer.subscription.*")
    print("   4. Copy webhook secret to STRIPE_WEBHOOK_SECRET in .env")


if __name__ == "__main__":
    main()
