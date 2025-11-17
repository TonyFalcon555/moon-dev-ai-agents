# 🌙 Moon Dev Market Data API Documentation

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Authentication](#authentication)
- [Market Data Methods](#market-data-methods)
- [CopyBot Methods](#copybot-methods)
- [Example Usage](#example-usage)

## Overview

The Moon Dev Market Data API (`src/agents/api.py`) provides access to real-time market data. The API is designed to be easy to use while providing powerful features for market analysis and automated trading.

## Installation

1. Ensure you have the required dependencies:
```bash
pip install requests pandas python-dotenv termcolor
```

2. Set up your environment variables:
```bash
# Create a .env file and add your Moon Dev API key
MOONDEV_API_KEY=your_api_key_here
```

## Authentication

The API uses an API key for authentication. This key should be stored in your `.env` file and will be automatically loaded when initializing the API client.

```python
from src.agents.api import MoonDevAPI

# Initialize the API client
api = MoonDevAPI()  # Automatically loads API key from .env
```

## Market Data Methods

### Get Liquidation Data
```python
# Get latest 50,000 liquidation records (recommended for most use cases)
liq_data = api.get_liquidation_data(limit=50_000)

# Get the full historical dataset (large, 1.5GB+)
all_liq_data = api.get_liquidation_data()  # limit=None
```

### Get Funding Rate Data
```python
# Get current funding data across supported symbols/exchanges
funding_data = api.get_funding_data()
```

### Get Open Interest Data
```python
# Detailed open interest data (per symbol/exchange)
oi_data = api.get_oi_data()

# Total open interest aggregates
total_oi = api.get_oi_total()
```

### Get New Token Launches
```python
# Get latest token launches (e.g. new Solana tokens)
new_tokens = api.get_token_addresses()
```

## CopyBot Methods

### Get Follow List
```python
# Get current copy trading follow list
follow_list = api.get_copybot_follow_list()
```

### Get Recent Transactions
```python
# Get recent copy trading transactions
recent_txs = api.get_copybot_recent_transactions()
```

## Example Usage

Here's a complete example showing how to use the API:

```python
from src.agents.api import MoonDevAPI

# Initialize API (uses MOONDEV_API_KEY from .env if present)
api = MoonDevAPI()

# Market data
liq_data = api.get_liquidation_data(limit=50_000)
funding_data = api.get_funding_data()
oi_data = api.get_oi_data()
oi_total = api.get_oi_total()
new_tokens = api.get_token_addresses()

# CopyBot data
follow_list = api.get_copybot_follow_list()
recent_txs = api.get_copybot_recent_transactions()
```

## Data Storage

By default, all data is saved to `src/agents/api_data/`. Common files include:
- `liq_data.csv`: Liquidation data (latest chunked download)
- `funding.csv`: Funding rate data
- `oi.csv`: Detailed open interest data
- `oi_total.csv`: Total market open interest
- `new_token_addresses.csv`: New token launches
- `follow_list.csv`: Copy trading follow list
- `recent_txs.csv`: Recent copy trading transactions
- `whale_addresses.txt`: Whale address list

## Error Handling

The API includes built-in error handling and will:
- Print colored error messages for easy debugging
- Return `None` if an API call fails
- Create data directories automatically
- Validate API responses

## 🚨 Important Notes

1. Never share or commit your API key
2. Data is automatically saved to the `api_data` directory
3. All methods include error handling and logging
4. The API uses colorful console output for better visibility
5. Rate limiting is handled automatically

---
*Built with 🌙 by Moon Dev - Making trading data accessible and beautiful*
