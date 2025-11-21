# 🦅 Falcon Finance: Personal Use Guide

Welcome to the personal use guide for Falcon Finance (formerly Moon Dev AI Agents)! This guide will help you run the powerful AI agents on your local machine for your own trading and research.

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**: Ensure you have Python installed.
- **API Keys**: You'll need keys for the AI models you want to use (e.g., OpenAI, Anthropic, DeepSeek).
- **Data**: Some agents require market data (the RBI agent has sample data).

### 2. Installation

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/moondevonyt/moon-dev-ai-agents.git
cd moon-dev-ai-agents

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  Open `.env` and add your API keys:
    - `OPENAI_KEY`: For GPT-4/GPT-5 models.
    - `ANTHROPIC_KEY`: For Claude 3.5 Sonnet (highly recommended).
    - `DEEPSEEK_KEY`: For DeepSeek models (great for reasoning).
    - `PERPLEXITY_KEY`: For research agent web searches.
    - `RESTREAM_CLIENT_ID` & `RESTREAM_CLIENT_SECRET`: Required if using the Chat Agent.

---

## 🤖 Available Agents

Here are the most popular agents you can run right now:

### 1. 🧠 Swarm Agent (`src/agents/swarm_agent.py`)
**What it does:** Queries multiple AI models (Claude, OpenAI, DeepSeek, etc.) simultaneously to get diverse perspectives on a question, then synthesizes a consensus answer.
**Best for:** Making difficult decisions, validating trading ideas, or getting a "second opinion" (or third, or fourth...).

**How to run:**
```bash
python src/agents/swarm_agent.py
```
*Follow the interactive prompts to ask your question.*

### 2. 🔬 RBI Agent (`src/agents/rbi_agent.py`)
**What it does:** **R**esearch, **B**acktest, **I**mplement. It takes a trading idea (text, YouTube video, PDF), researches it, writes a backtest in Python, and debugs it until it works.
**Best for:** Quants and traders who want to rapidly test new strategies.

**How to run:**
1.  Add your ideas to `src/data/rbi/ideas.txt` (one per line).
2.  Run the agent:
```bash
python src/agents/rbi_agent.py
```

### 3. 📈 Trading Agent (`src/agents/trading_agent.py`)
**What it does:** An autonomous agent that can analyze market data, make trading decisions, and execute trades (paper or live).
**Best for:** Automating your trading strategy.

**How to run:**
```bash
python src/agents/trading_agent.py
```
*Note: Check `src/config.py` to configure the strategy, symbol, and risk settings.*

### 4. 💬 Chat Agent (`src/agents/chat_agent.py`)
**What it does:** A specialized chat interface for discussing trading, coding, and crypto with an AI that has context about your project.
**Best for:** General assistance and brainstorming.

**How to run:**
```bash
python src/agents/chat_agent.py
```

---

## 🛠️ Troubleshooting

- **Missing Modules**: If you see `ModuleNotFoundError`, make sure you activated your venv and ran `pip install -r requirements.txt`.
- **API Errors**: Double-check your `.env` file. Ensure keys are correct and have no extra spaces.
- **Rate Limits**: If an agent fails due to rate limits, try switching to a different model in `src/config.py` or waiting a few minutes.

## 📚 Documentation
For more details on the architecture and advanced configuration, check the main `README.md` and the `docs/` folder.

Happy Trading! 🦅
