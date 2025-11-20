import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from unittest.mock import patch, MagicMock
from src.services.alerts import main
from src.services.api_gateway import keystore

# Use in-memory SQLite for testing
TEST_DB_URL = "sqlite:///:memory:"

from sqlalchemy.pool import StaticPool

@pytest.fixture(autouse=True)
def setup_teardown():
    # Create test engine with StaticPool to persist in-memory DB
    test_engine = create_engine(
        TEST_DB_URL, 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool,
        future=True
    )
    
    # Configure keystore to use test engine
    keystore.engine = test_engine
    keystore.init_db()
    
    # Patch the engine in main module
    with patch("src.services.alerts.main.engine", test_engine):
        yield

client = TestClient(main.app)

@pytest.fixture
def mock_api_key():
    # Create a key in the DB
    return keystore.add_key(plan="pro", metadata="test_user")

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_alert(mock_api_key):
    payload = {
        "type": "liquidation_spike",
        "threshold": 1000000,
        "window_minutes": 15,
        "symbol": "BTC"
    }
    headers = {"X-API-Key": mock_api_key}
    
    response = client.post("/alerts", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "liquidation_spike"
    assert data["symbol"] == "BTC"
    assert data["id"].startswith("a_")

def test_list_alerts(mock_api_key):
    # Create two alerts
    headers = {"X-API-Key": mock_api_key}
    client.post("/alerts", json={"type": "whale_activity", "threshold": 5}, headers=headers)
    client.post("/alerts", json={"type": "funding_extreme", "threshold": 0.01}, headers=headers)
    
    response = client.get("/alerts", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_delete_alert(mock_api_key):
    headers = {"X-API-Key": mock_api_key}
    create_resp = client.post("/alerts", json={"type": "whale_activity", "threshold": 5}, headers=headers)
    alert_id = create_resp.json()["id"]
    
    # Delete it
    del_resp = client.delete(f"/alerts/{alert_id}", headers=headers)
    assert del_resp.status_code == 200
    
    # Verify it's gone
    list_resp = client.get("/alerts", headers=headers)
    assert len(list_resp.json()) == 0

def test_quota_exceeded():
    # Create a 'free' key with limit 3 (default env)
    free_key = keystore.add_key(plan="free")
    headers = {"X-API-Key": free_key}
    
    # Create 3 alerts (allowed)
    for i in range(3):
        resp = client.post("/alerts", json={"type": "whale_activity", "threshold": i}, headers=headers)
        assert resp.status_code == 200
        
    # Create 4th (should fail)
    resp = client.post("/alerts", json={"type": "whale_activity", "threshold": 99}, headers=headers)
    assert resp.status_code == 429
