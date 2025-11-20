import pytest
from fastapi.testclient import TestClient
from src.services.backtest_dashboard.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_home_page():
    """Test that the home page loads successfully"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Moon Dev" in response.text

def test_get_stats_no_data():
    """Test stats endpoint when no data exists"""
    with patch("src.services.backtest_dashboard.main._resolve_stats_csv") as mock_resolve:
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_resolve.return_value = ("default", mock_path)
        
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_backtests"] == 0
        assert data["workspace"] == "default"

def test_get_backtests_no_data():
    """Test backtests endpoint when no data exists"""
    with patch("src.services.backtest_dashboard.main._resolve_stats_csv") as mock_resolve:
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_resolve.return_value = ("default", mock_path)
        
        response = client.get("/api/backtests")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["message"] == "No backtest data found"

def test_static_files():
    """Test that static files are served"""
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
