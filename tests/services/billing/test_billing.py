import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import os

# Import the app
from src.services.billing.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_checkout_session_invalid_plan():
    response = client.post("/billing/create-checkout-session", json={
        "plan": "invalid_plan",
        "success_url": "http://localhost/success",
        "cancel_url": "http://localhost/cancel",
        "customer_email": "test@example.com"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid plan"

def test_create_checkout_session_success(mock_stripe, monkeypatch):
    # Setup env vars
    monkeypatch.setenv("PRICE_ID_PRO", "price_123")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    # Setup mock
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
    mock_stripe.checkout.Session.create.return_value = mock_session
    
    response = client.post("/billing/create-checkout-session", json={
        "plan": "pro",
        "success_url": "http://localhost/success",
        "cancel_url": "http://localhost/cancel",
        "customer_email": "test@example.com"
    })
    
    assert response.status_code == 200
    assert response.json()["url"] == "https://checkout.stripe.com/pay/cs_test_123"
    
    # Verify stripe call
    mock_stripe.checkout.Session.create.assert_called_once()
    call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
    assert call_kwargs["line_items"][0]["price"] == "price_123"
    assert call_kwargs["customer_email"] == "test@example.com"

def test_webhook_checkout_completed(mock_stripe, mock_db_session, monkeypatch):
    # Setup env vars
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("PRICE_ID_PRO", "price_pro_123")
    
    # Setup mock event
    mock_event = MagicMock()
    mock_event.get.return_value = "checkout.session.completed"
    
    # Mock data inside event
    mock_data = {
        "subscription": "sub_123",
        "customer_email": "customer@example.com"
    }
    mock_event.get.side_effect = lambda k, default=None: {
        "type": "checkout.session.completed",
        "data": {"object": mock_data}
    }.get(k, default)
    
    mock_stripe.Webhook.construct_event.return_value = mock_event
    
    # Mock subscription retrieval
    mock_sub = {
        "items": {
            "data": [{"price": {"id": "price_pro_123"}}]
        }
    }
    mock_stripe.Subscription.retrieve.return_value = mock_sub
    
    # Mock add_key return value
    mock_db_session.return_value = "sk_live_new_key_123"
    
    # Send webhook
    response = client.post("/billing/webhook", 
                          headers={"Stripe-Signature": "t=123,v1=signature"},
                          content=b"raw_payload")
    
    assert response.status_code == 200
    assert response.json()["received"] == True
    
    # Verify key was added
    mock_db_session.assert_called_once()
    call_kwargs = mock_db_session.call_args[1]
    assert call_kwargs["plan"] == "pro"
