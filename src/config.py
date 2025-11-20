import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# 🔧 TRADING AGENT CONFIGURATION
# ============================================================================

# 🏦 EXCHANGE SELECTION
EXCHANGE = os.getenv("EXCHANGE", "ASTER")  # Options: "ASTER", "HYPERLIQUID", "SOLANA"

# 🌊 AI MODE SELECTION
USE_SWARM_MODE = os.getenv("USE_SWARM_MODE", "True").lower() == "true"

# 📈 TRADING MODE SETTINGS
LONG_ONLY = os.getenv("LONG_ONLY", "True").lower() == "true"

# 🤖 SINGLE MODEL SETTINGS
AI_MODEL_TYPE = os.getenv("AI_MODEL_TYPE", "xai")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", None)
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1024"))

# 💰 POSITION SIZING & RISK MANAGEMENT
USE_PORTFOLIO_ALLOCATION = os.getenv("USE_PORTFOLIO_ALLOCATION", "False").lower() == "true"
MAX_POSITION_PERCENTAGE = float(os.getenv("MAX_POSITION_PERCENTAGE", "90"))
LEVERAGE = int(os.getenv("LEVERAGE", "9"))
STOP_LOSS_PERCENTAGE = float(os.getenv("STOP_LOSS_PERCENTAGE", "5.0"))
TAKE_PROFIT_PERCENTAGE = float(os.getenv("TAKE_PROFIT_PERCENTAGE", "5.0"))
PNL_CHECK_INTERVAL = int(os.getenv("PNL_CHECK_INTERVAL", "5"))

# 📊 MARKET DATA COLLECTION
DAYSBACK_4_DATA = int(os.getenv("DAYSBACK_4_DATA", "3"))
DATA_TIMEFRAME = os.getenv("DATA_TIMEFRAME", "1H")
SAVE_OHLCV_DATA = os.getenv("SAVE_OHLCV_DATA", "False").lower() == "true"

# ⚡ TRADING EXECUTION SETTINGS
SLIPPAGE = int(os.getenv("SLIPPAGE", "199"))
SLEEP_BETWEEN_RUNS_MINUTES = int(os.getenv("SLEEP_BETWEEN_RUNS_MINUTES", "15"))

# 🎯 TOKEN CONFIGURATION
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL_ADDRESS = "So11111111111111111111111111111111111111111"
EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS]

# Default monitored tokens (can be overridden by env var if needed, but list parsing is complex)
MONITORED_TOKENS = [
    '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump',    # FART
    #'DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump',   # housecoin
]

SYMBOLS = [
    'BTC',
    #'ETH',
    #'SOL',
]
