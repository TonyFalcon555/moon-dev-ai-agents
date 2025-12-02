#!/usr/bin/env python3
"""
🌙 Moon Dev's API Key Management Script

Create, list, and manage API keys for the Falcon Finance platform.

Usage:
    python scripts/create_api_key.py create --plan pro
    python scripts/create_api_key.py list
    python scripts/create_api_key.py revoke <key>
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Set up database URL for keystore
db_url = os.getenv("KEYSTORE_DB_URL", f"sqlite:///{PROJECT_ROOT}/data/keystore.db")
os.environ["KEYSTORE_DB_URL"] = db_url

from src.services.api_gateway.keystore import (
    init_db, 
    add_key, 
    list_keys, 
    revoke_key, 
    get_plan_for_key
)


def cmd_create(args):
    """Create a new API key"""
    init_db()
    
    plan = args.plan
    rate_limit = args.rate_limit
    metadata = args.metadata
    
    valid_plans = ["free", "pro", "team", "enterprise"]
    if plan not in valid_plans:
        print(f"❌ Invalid plan: {plan}")
        print(f"   Valid plans: {', '.join(valid_plans)}")
        sys.exit(1)
    
    key = add_key(
        plan=plan,
        rate_limit_override=rate_limit,
        metadata=metadata
    )
    
    print("\n🔑 API Key Created Successfully!")
    print("=" * 50)
    print(f"   Key:  {key}")
    print(f"   Plan: {plan}")
    if rate_limit:
        print(f"   Rate Limit Override: {rate_limit} req/min")
    if metadata:
        print(f"   Metadata: {metadata}")
    print("=" * 50)
    print("\n⚠️  Save this key securely - it won't be shown again!")
    print(f"\n📋 Test with:")
    print(f'   curl -H "X-API-Key: {key}" http://localhost:8010/whoami')


def cmd_list(args):
    """List all API keys"""
    init_db()
    
    keys = list_keys()
    
    if not keys:
        print("No API keys found.")
        return
    
    print("\n📋 API Keys")
    print("=" * 80)
    print(f"{'ID':<6} {'Plan':<12} {'Created':<20} {'Status':<10} {'Key Prefix':<20}")
    print("-" * 80)
    
    for key_info in keys:
        key_id = key_info.get("id", "?")
        plan = key_info.get("plan", "unknown")
        created = key_info.get("created_at", "unknown")
        revoked = key_info.get("revoked_at")
        status = "REVOKED" if revoked else "ACTIVE"
        key_hash = key_info.get("key_hash", "")[:12] + "..."
        
        print(f"{key_id:<6} {plan:<12} {str(created):<20} {status:<10} {key_hash:<20}")
    
    print("=" * 80)
    print(f"Total: {len(keys)} keys")


def cmd_revoke(args):
    """Revoke an API key"""
    init_db()
    
    key = args.key
    
    # Verify key exists
    plan = get_plan_for_key(key)
    if not plan:
        print(f"❌ Key not found or already revoked: {key[:12]}...")
        sys.exit(1)
    
    if revoke_key(key):
        print(f"✅ Key revoked successfully: {key[:12]}...")
    else:
        print(f"❌ Failed to revoke key: {key[:12]}...")
        sys.exit(1)


def cmd_test(args):
    """Test an API key"""
    init_db()
    
    key = args.key
    plan = get_plan_for_key(key)
    
    if plan:
        print(f"✅ Key is valid")
        print(f"   Plan: {plan}")
    else:
        print(f"❌ Key is invalid or revoked")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="🦅 Falcon Finance API Key Management"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument(
        "--plan", "-p",
        required=True,
        choices=["free", "pro", "team", "enterprise"],
        help="Subscription plan for this key"
    )
    create_parser.add_argument(
        "--rate-limit", "-r",
        type=int,
        default=None,
        help="Custom rate limit override (requests per minute)"
    )
    create_parser.add_argument(
        "--metadata", "-m",
        default=None,
        help="Optional metadata (e.g., user email, notes)"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all API keys")
    
    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key")
    revoke_parser.add_argument("key", help="The API key to revoke")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test if an API key is valid")
    test_parser.add_argument("key", help="The API key to test")
    
    args = parser.parse_args()
    
    if args.command == "create":
        cmd_create(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "revoke":
        cmd_revoke(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
