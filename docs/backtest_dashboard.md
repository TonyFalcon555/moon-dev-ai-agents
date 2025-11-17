# Backtest Dashboard

Web dashboard for viewing and organizing RBI agent backtest results.

## What It Does
- Displays backtest statistics in a sortable table
- Shows summary stats (total backtests, avg return, max return)
- Organize backtests into folders
- Copy file paths for easy access
- Run new backtests directly from the UI (work in progress, idk if i will build this out as i just run from terminal)

## Quick Start

### 1. Generate Backtest Data
First, run the RBI agent to create backtest results for your **default** workspace:
```bash
python src/agents/rbi_agent_pp_multi.py
```

By default, this writes to:

```text
src/data/rbi_pp_multi/backtest_stats.csv
```

In multi-tenant mode (when the dashboard sets `RBI_WORKSPACE_NAME`), each workspace
gets its own directory:

```text
src/data/rbi_pp_multi/<workspace>/backtest_stats.csv
```

### 2. Run Dashboard
```bash
python src/scripts/backtestdashboard.py
```

### 3. Open Browser
Navigate to: `http://localhost:8002`

## Features

### Stats Cards
- Total Backtests
- Unique Strategies
- Data Sources Tested
- Average Return
- Max Return
- Average Sortino Ratio

### Table View
- Strategy Name (click to copy file path)
- Return %
- Buy & Hold %
- Max Drawdown %
- Sharpe Ratio
- Sortino Ratio
- Expectancy %
- Number of Trades
- Data Source
- Timestamp

### Folder Management
- Select multiple backtests (Shift-click, Cmd-click)
- Add to folders for organization
- Copy all paths from a folder
- Delete folders

### New Backtests (WIP - Work in Progress)
- Run backtests directly from UI
- Add strategy ideas in text box
- Auto-creates folder with results
- Background processing with status updates

## Configuration

You can still customize paths in `src/scripts/backtestdashboard.py`, but by
default everything is wired off the project root and per-workspace helpers:

```python
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_ROOT = BASE_DIR / "src" / "data"
RBI_BASE_DIR = DATA_ROOT / "rbi_pp_multi"

# Legacy single-tenant CSV (used when workspace == "default")
STATS_CSV = RBI_BASE_DIR / "backtest_stats.csv"

# Templates/static live under RBI_BASE_DIR
TEMPLATE_BASE_DIR = RBI_BASE_DIR

# Default user folders root (per-workspace helpers are preferred)
USER_FOLDERS_DIR = TEMPLATE_BASE_DIR / "user_folders"

TARGET_RETURN = 50        # Optimization goal
SAVE_IF_OVER_RETURN = 1.0 # Minimum return to auto-save
```

For multi-tenant setups, the dashboard uses helpers like
`get_workspace_root()` and `_workspace_from_request()` to resolve
workspace-specific paths without manual editing.

## Port Settings
- Default: `8002`
- Change at the bottom of `backtestdashboard.py`:
  ```python
  uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
  ```

## Requirements
- FastAPI
- Uvicorn
- Pandas
- NumPy

All included in main `requirements.txt`

## File Structure

Single-tenant (default workspace):

```text
src/data/rbi_pp_multi/
├── backtest_stats.csv         # Main results CSV (default workspace)
├── user_folders/              # Organized folders (default workspace)
├── templates/
│   └── index.html             # Dashboard UI
└── static/
    └── style.css              # Styling
```

Multi-tenant (per workspace):

```text
src/data/rbi_pp_multi/
├── backtest_stats.csv         # Optional legacy CSV (default workspace)
├── user_folders/              # Legacy default folder root
├── <workspace_a>/
│   ├── backtest_stats.csv     # Workspace A results
│   └── user_folders/
│       └── ...                # Workspace A folders
└── <workspace_b>/
    ├── backtest_stats.csv     # Workspace B results
    └── user_folders/
        └── ...
```

## Tips
- **Strategy column**: Hover to see full file path
- **Multi-select**: Shift-click for range, Cmd-click for individual
- **Copy paths**: Select rows → "Copy Paths" button
- **Large returns**: Values ≥1000% display without decimals

## Troubleshooting

**Port already in use:**
- Change port in line 625
- Update browser URL accordingly

**No data showing:**
- Verify you’ve generated data:
  - For default workspace: run `python src/agents/rbi_agent_pp_multi.py`
  - For other workspaces: run from the dashboard so it sets `RBI_WORKSPACE_NAME`
- Check the CSV exists under the expected workspace directory
- Check CSV has proper column headers

**Templates not found:**
- Verify `TEMPLATE_BASE_DIR` points to the correct location
- Ensure `static/` and `templates/` folders exist under `src/data/rbi_pp_multi`

## API Examples (Multi-Tenant)

The dashboard exposes JSON APIs that are workspace-aware. Workspaces are
resolved either from the `workspace` query parameter or from `X-API-Key`.

### 1. Using explicit workspace (no API key)

```bash
curl "http://localhost:8002/api/backtests?workspace=my-workspace"

curl "http://localhost:8002/api/stats?workspace=my-workspace"
```

### 2. Using X-API-Key (recommended for SaaS)

When you issue keys via the keystore, the dashboard can derive a stable
workspace ID from each key. Just send the key in headers:

```bash
curl \
  -H "X-API-Key: YOUR_USER_KEY" \
  "http://localhost:8002/api/backtests"

curl \
  -H "X-API-Key: YOUR_USER_KEY" \
  "http://localhost:8002/api/stats"
```

The JSON response for these endpoints includes a `"workspace"` field so
you can verify which workspace you’re hitting.

### 3. Python example (requests)

```python
import requests

BASE_URL = "http://localhost:8002"
API_KEY = "YOUR_USER_KEY"

headers = {"X-API-Key": API_KEY}

# Option A: let server derive workspace from API key
r = requests.get(f"{BASE_URL}/api/backtests", headers=headers)
print(r.json()["workspace"], len(r.json()["data"]))

r = requests.get(f"{BASE_URL}/api/stats", headers=headers)
print(r.json()["workspace"], r.json()["total_backtests"])

# Option B: explicitly specify a workspace
params = {"workspace": "my-workspace"}
r = requests.get(f"{BASE_URL}/api/backtests", headers=headers, params=params)
print(r.json()["workspace"], len(r.json()["data"]))
```
