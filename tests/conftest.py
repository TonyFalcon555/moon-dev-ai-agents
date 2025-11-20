import pytest
import os
import sys
from unittest.mock import MagicMock

# Add src to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

@pytest.fixture
def mock_stripe(mocker):
    """Mock the stripe library"""
    mock = mocker.patch("src.services.billing.main._require_stripe")
    stripe_instance = MagicMock()
    mock.return_value = stripe_instance
    return stripe_instance

@pytest.fixture
def mock_db_session(mocker):
    """Mock database session for keystore"""
    # This will need to be refined once we switch to Postgres/SQLAlchemy
    # For now, we mock the add_key function if it's imported
    mock_add = mocker.patch("src.services.billing.main.add_key", create=True)
    return mock_add

@pytest.fixture
def sample_market_data():
    """Create sample DataFrame for market data"""
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    df = pd.DataFrame({
        'open': np.random.randn(100) + 100,
        'high': np.random.randn(100) + 105,
        'low': np.random.randn(100) + 95,
        'close': np.random.randn(100) + 100,
        'volume': np.random.randint(100, 1000, 100)
    }, index=dates)
    return df
