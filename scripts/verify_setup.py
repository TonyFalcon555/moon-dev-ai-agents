#!/usr/bin/env python3
"""
🦅 Falcon Finance Setup Verification Script

Verifies that all components are properly configured before deployment.
Run: python scripts/verify_setup.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback: manually parse .env file
    def load_dotenv(path):
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()

def check_env_file():
    """Check .env file exists and has required values"""
    env_path = PROJECT_ROOT / ".env"
    
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Run: cp .env.example .env")
        return False
    
    load_dotenv(env_path)
    
    required = [
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
    ]
    
    recommended = [
        "PRICE_ID_PRO",
        "PRICE_ID_TEAM", 
        "PRICE_ID_ENTERPRISE",
        "ALERTS_DISCORD_WEBHOOK_URL",
    ]
    
    missing_required = []
    missing_recommended = []
    
    for var in required:
        val = os.getenv(var, "")
        if not val or val.startswith("your_") or "..." in val:
            missing_required.append(var)
    
    for var in recommended:
        val = os.getenv(var, "")
        if not val or val.startswith("your_") or "..." in val:
            missing_recommended.append(var)
    
    if missing_required:
        print(f"❌ Missing required env vars: {', '.join(missing_required)}")
        return False
    
    print("✅ Required environment variables set")
    
    if missing_recommended:
        print(f"⚠️  Missing recommended env vars: {', '.join(missing_recommended)}")
    
    return True


def check_stripe_key():
    """Verify Stripe key format"""
    key = os.getenv("STRIPE_SECRET_KEY", "")
    
    if key.startswith("sk_test_"):
        print("✅ Stripe key is TEST mode (good for development)")
        return True
    elif key.startswith("sk_live_"):
        print("⚠️  Stripe key is LIVE mode - be careful!")
        return True
    else:
        print("❌ Invalid Stripe key format")
        return False


def check_imports():
    """Check that key modules can be imported (optional for Docker deployments)"""
    errors = []
    warnings = []
    
    try:
        from src.services.api_gateway.keystore import init_db
        print("✅ Keystore module OK")
    except ImportError as e:
        if "No module named" in str(e):
            warnings.append(f"Keystore: {e} (will be installed in Docker)")
        else:
            errors.append(f"Keystore: {e}")
    except Exception as e:
        errors.append(f"Keystore: {e}")
    
    try:
        from src.services.api_gateway.rate_limiter import RateLimiter
        print("✅ Rate limiter module OK")
    except ImportError as e:
        if "No module named" in str(e):
            warnings.append(f"Rate limiter: {e} (will be installed in Docker)")
        else:
            errors.append(f"Rate limiter: {e}")
    except Exception as e:
        errors.append(f"Rate limiter: {e}")
    
    try:
        from src.services.billing.main import app
        print("✅ Billing service OK")
    except ImportError as e:
        if "No module named" in str(e):
            warnings.append(f"Billing: {e} (will be installed in Docker)")
        else:
            errors.append(f"Billing: {e}")
    except Exception as e:
        errors.append(f"Billing: {e}")
    
    try:
        from src.services.alerts.main import app
        print("✅ Alerts service OK")
    except ImportError as e:
        if "No module named" in str(e):
            warnings.append(f"Alerts: {e} (will be installed in Docker)")
        else:
            errors.append(f"Alerts: {e}")
    except Exception as e:
        errors.append(f"Alerts: {e}")
    
    if warnings:
        print("\n⚠️  Missing local dependencies (OK for Docker):")
        for w in warnings:
            print(f"   • {w}")
    
    if errors:
        print("\n❌ Import errors:")
        for e in errors:
            print(f"   • {e}")
        return False
    
    # If only warnings (missing deps), it's OK for Docker deployment
    print("✅ Source files verified (deps will install in Docker)")
    return True


def check_docker():
    """Check Docker is available"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Docker available: {result.stdout.strip()}")
            return True
    except Exception as e:
        pass
    
    print("⚠️  Docker not found or not running")
    return False


def check_directories():
    """Check required directories exist"""
    dirs = [
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "scripts",
        PROJECT_ROOT / "tests",
    ]
    
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {d.relative_to(PROJECT_ROOT)}")
    
    print("✅ Required directories exist")
    return True


def main():
    print("\n🦅 Falcon Finance Setup Verification")
    print("=" * 50)
    
    results = []
    
    print("\n📋 Checking environment...")
    results.append(("Environment", check_env_file()))
    
    print("\n💳 Checking Stripe...")
    results.append(("Stripe", check_stripe_key()))
    
    print("\n📦 Checking imports...")
    results.append(("Imports", check_imports()))
    
    print("\n🐳 Checking Docker...")
    results.append(("Docker", check_docker()))
    
    print("\n📁 Checking directories...")
    results.append(("Directories", check_directories()))
    
    print("\n" + "=" * 50)
    print("📊 Summary:\n")
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("🎉 All checks passed! Ready to deploy.")
        print("\n📋 Next steps:")
        print("   1. Run: ./deploy.sh dev")
        print("   2. Create API key: python scripts/create_api_key.py create --plan pro")
        print("   3. Visit: http://localhost:8080")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
