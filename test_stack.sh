#!/bin/bash

echo "🌙 Moon Dev - Stack Test"
echo "========================"
echo ""

# Test API Gateway
echo "Testing API Gateway..."
if curl -s -f http://127.0.0.1:8010/health > /dev/null; then
    echo "✅ Gateway health check passed"
    
    # Test /plans endpoint
    if curl -s -f http://127.0.0.1:8010/plans > /dev/null; then
        echo "✅ Gateway /plans endpoint works"
    else
        echo "❌ Gateway /plans endpoint failed"
    fi
else
    echo "❌ Gateway health check failed"
fi

echo ""

# Test Billing
echo "Testing Billing Service..."
if curl -s -f http://127.0.0.1:8011/health > /dev/null; then
    echo "✅ Billing health check passed"
else
    echo "❌ Billing health check failed"
fi

echo ""

# Test Alerts
echo "Testing Alerts Service..."
if curl -s -f http://127.0.0.1:8012/health > /dev/null; then
    echo "✅ Alerts health check passed"
else
    echo "❌ Alerts health check failed"
fi

echo ""

# Test Dashboard
echo "Testing Backtest Dashboard..."
if curl -s -f http://127.0.0.1:8002/health > /dev/null; then
    echo "✅ Dashboard health check passed"
else
    echo "❌ Dashboard health check failed"
fi

echo ""
echo "Run full demos:"
echo "  python src/scripts/demo_billing_gateway_client.py"
echo "  python src/scripts/demo_alerts_client.py"
echo "  python src/scripts/demo_backtest_dashboard_client.py"
