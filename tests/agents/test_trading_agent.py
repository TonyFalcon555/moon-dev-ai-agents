import pytest
from unittest.mock import MagicMock, patch
import sys
import pandas as pd
import json

# Mock the exchange modules BEFORE importing trading_agent
# This prevents the sys.exit(1) in nice_funcs_aster.py
mock_aster = MagicMock()
sys.modules["src.nice_funcs_aster"] = mock_aster
sys.modules["src.nice_funcs_hyperliquid"] = MagicMock()
sys.modules["src.nice_funcs"] = MagicMock()

# Mock model factory to avoid importing all model SDKs (anthropic, openai, etc)
mock_factory = MagicMock()
sys.modules["src.models.model_factory"] = mock_factory
sys.modules["src.models"] = MagicMock()

from src.agents.trading_agent import TradingAgent, calculate_position_size

@pytest.fixture
def mock_model_factory(mocker):
    return mocker.patch("src.agents.trading_agent.model_factory")

@pytest.fixture
def mock_nice_funcs(mocker):
    # Mock the exchange functions module
    # We need to patch it where it is imported in trading_agent.py
    # Since it's imported conditionally, we might need to patch the module in sys.modules or patch the alias 'n'
    # But 'n' is a local name in the module.
    # A better way is to patch the functions that are called on 'n'.
    # However, 'n' is imported at module level.
    # Let's try to patch the module 'src.nice_funcs_aster' assuming default config
    return mocker.patch("src.agents.trading_agent.n")

@pytest.fixture
def trading_agent(mock_model_factory):
    # Setup mock model
    mock_model = MagicMock()
    mock_model.model_name = "test_model"
    mock_model_factory.get_model.return_value = mock_model
    
    # Initialize agent
    agent = TradingAgent()
    return agent

def test_calculate_position_size_aster():
    # Mock config values
    with patch("src.agents.trading_agent.EXCHANGE", "ASTER"), \
         patch("src.agents.trading_agent.MAX_POSITION_PERCENTAGE", 50), \
         patch("src.agents.trading_agent.LEVERAGE", 10):
        
        balance = 1000.0
        # Margin = 1000 * 0.50 = 500
        # Notional = 500 * 10 = 5000
        size = calculate_position_size(balance)
        assert size == 5000.0

def test_calculate_position_size_solana():
    with patch("src.agents.trading_agent.EXCHANGE", "SOLANA"), \
         patch("src.agents.trading_agent.MAX_POSITION_PERCENTAGE", 50):
        
        balance = 1000.0
        # Size = 1000 * 0.50 = 500
        size = calculate_position_size(balance)
        assert size == 500.0

def test_analyze_market_data_buy(trading_agent, sample_market_data):
    # Mock AI response
    trading_agent.model.generate_response.return_value = "BUY\nConfidence: 80%\nReasoning: Bullish trend."
    
    with patch("src.agents.trading_agent.USE_SWARM_MODE", False):
        response = trading_agent.analyze_market_data("BTC", sample_market_data)
        
        assert response == "BUY\nConfidence: 80%\nReasoning: Bullish trend."
        assert len(trading_agent.recommendations_df) == 1
        row = trading_agent.recommendations_df.iloc[0]
        assert row['token'] == "BTC"
        assert row['action'] == "BUY"
        assert row['confidence'] == 80

def test_analyze_market_data_sell(trading_agent, sample_market_data):
    # Mock AI response
    trading_agent.model.generate_response.return_value = "SELL\nConfidence: 90%\nReasoning: Bearish divergence."
    
    with patch("src.agents.trading_agent.USE_SWARM_MODE", False):
        response = trading_agent.analyze_market_data("ETH", sample_market_data)
        
        assert "SELL" in response
        row = trading_agent.recommendations_df.iloc[0]
        assert row['action'] == "SELL"
        assert row['confidence'] == 90

def test_analyze_market_data_swarm(trading_agent, sample_market_data):
    # Mock Swarm Agent
    mock_swarm = MagicMock()
    trading_agent.swarm = mock_swarm
    
    # Mock swarm response
    swarm_result = {
        "responses": {
            "Model A": {"success": True, "response": "Buy"},
            "Model B": {"success": True, "response": "Buy"},
            "Model C": {"success": True, "response": "Sell"},
            "Model D": {"success": True, "response": "Buy"},
            "Model E": {"success": True, "response": "Do Nothing"},
            "Model F": {"success": True, "response": "Buy"}
        }
    }
    mock_swarm.query.return_value = swarm_result
    
    with patch("src.agents.trading_agent.USE_SWARM_MODE", True):
        # Re-init to pick up swarm mode if needed, but we patched the instance
        # The method checks the global USE_SWARM_MODE, so patching it is enough
        
        result = trading_agent.analyze_market_data("SOL", sample_market_data)
        
        assert result == swarm_result
        row = trading_agent.recommendations_df.iloc[0]
        assert row['action'] == "BUY"
        # 4 out of 6 votes = 66%
        assert row['confidence'] == 66 
