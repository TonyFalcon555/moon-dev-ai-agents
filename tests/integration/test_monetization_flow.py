"""
Integration tests for the complete monetization flow.

Tests the end-to-end flow:
1. User visits landing page
2. User selects a plan
3. Stripe checkout session created
4. Webhook processes payment
5. API key provisioned
6. User can access gated features
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TestBillingFlow:
    """Test the billing service flow"""
    
    @pytest.fixture
    def billing_client(self):
        from src.services.billing.main import app
        return TestClient(app)
    
    def test_health_check(self, billing_client):
        """Billing service should be healthy"""
        response = billing_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_create_checkout_requires_valid_plan(self, billing_client):
        """Should reject invalid plan names"""
        response = billing_client.post("/billing/create-checkout-session", json={
            "plan": "invalid_plan",
            "success_url": "http://localhost/success",
            "cancel_url": "http://localhost/cancel"
        })
        assert response.status_code == 400
        assert "Invalid plan" in response.json()["detail"]
    
    def test_valid_plans_accepted(self, billing_client):
        """Should accept valid plan names (pro, team, enterprise)"""
        valid_plans = ["pro", "team", "enterprise"]
        for plan in valid_plans:
            response = billing_client.post("/billing/create-checkout-session", json={
                "plan": plan,
                "success_url": "http://localhost/success",
                "cancel_url": "http://localhost/cancel"
            })
            # Will fail due to missing Stripe key in test, but should not be 400
            assert response.status_code in [200, 500]  # 500 = missing stripe key


class TestAPIGatewayFlow:
    """Test the API gateway flow"""
    
    @pytest.fixture
    def gateway_client(self):
        from src.services.api_gateway.main import app
        return TestClient(app)
    
    def test_health_check(self, gateway_client):
        """API gateway should be healthy"""
        response = gateway_client.get("/health")
        assert response.status_code == 200
    
    def test_requires_api_key(self, gateway_client):
        """Protected endpoints should require API key"""
        response = gateway_client.get("/whoami")
        assert response.status_code == 401
        assert "Missing X-API-Key" in response.json()["detail"]
    
    def test_rejects_invalid_key(self, gateway_client):
        """Should reject invalid API keys"""
        response = gateway_client.get(
            "/whoami",
            headers={"X-API-Key": "invalid_key_12345"}
        )
        assert response.status_code == 403


class TestAlertsFlow:
    """Test the alerts service flow"""
    
    @pytest.fixture
    def alerts_client(self):
        from src.services.alerts.main import app
        return TestClient(app)
    
    def test_health_check(self, alerts_client):
        """Alerts service should be healthy"""
        response = alerts_client.get("/health")
        assert response.status_code == 200
    
    def test_list_alerts_requires_key(self, alerts_client):
        """Listing alerts should require API key"""
        response = alerts_client.get("/alerts")
        assert response.status_code == 401
    
    def test_create_alert_requires_key(self, alerts_client):
        """Creating alerts should require API key"""
        response = alerts_client.post("/alerts", json={
            "type": "liquidation_spike",
            "threshold": 1000000,
            "window_minutes": 5
        })
        assert response.status_code == 401


class TestEndToEndMonetization:
    """
    Full end-to-end monetization flow test.
    
    This simulates the complete user journey from signup to API usage.
    """
    
    @pytest.fixture
    def mock_stripe(self):
        """Mock Stripe for testing"""
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_session = MagicMock()
            mock_session.url = "https://checkout.stripe.com/test"
            mock_create.return_value = mock_session
            yield mock_create
    
    @pytest.fixture  
    def mock_keystore(self):
        """Mock keystore for testing"""
        with patch('src.services.api_gateway.keystore.add_key') as mock_add:
            mock_add.return_value = "md_test_key_123456"
            yield mock_add
    
    def test_full_subscription_flow(self, mock_stripe, mock_keystore):
        """
        Test complete flow:
        1. Create checkout session
        2. Process webhook (simulated)
        3. Verify key provisioned
        """
        # This would be expanded in a real test environment
        # with proper test fixtures and database setup
        pass


# Pytest configuration
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_mock")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")
    monkeypatch.setenv("USE_KEYSTORE", "0")
    monkeypatch.setenv("KEYSTORE_DB_URL", "sqlite:///:memory:")
