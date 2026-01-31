# Earnings Event Alpha Tool

A Python tool for analyzing pre-earnings stock accumulation zones with dual-mode support (Swing & Positional trading).

## Features

- **Dual RVOL Analysis**: RVOL_20 (tactical/swing) and RVOL_50 (strategic/positional)
- **Multi-Quarter Support**: Analyze multiple earnings events per stock
- **Extended Observation Window**: T-20 to T+40 for comprehensive analysis
- **Fixed-Interval Returns**: T+2, T+5, T+10, T+20 exit points
- **Master File Caching**: Builds up historical data over time
- **Interactive Dashboard**: Streamlit-based UI with candlestick charts

## Project Structure

```
StockEarningAnalyzer/
├── configs/
│   ├── stockSymbolDetails.json    # Consolidated stock data (NEW)
│   ├── api_config.json             # Kite API credentials
│   └── access_token.json           # Kite access token (auto-generated)
├── data/                           # Cached OHLCV data
├── src/
│   ├── api/
│   │   ├── earnings_data.py        # Earnings dates & window calculations
│   │   └── data_fetcher.py         # Kite data retrieval & caching
│   ├── logic/
│   │   └── analyzer.py             # Dip detection & metrics
│   └── ui/
│       └── app.py                  # Streamlit dashboard
├── adhoc_script/
│   └── instrument_finder.py        # Update instrument tokens
├── kite_auth.py                    # Kite authentication
├── main.py                         # Entry point
└── requirements.txt                # Dependencies
```

## Configuration

### stockSymbolDetails.json (Consolidated Config)

This single JSON file contains all stock information:

```json
[
  {
    "stock_name": "Polycab India Ltd.",
    "symbol": "POLYCAB",
    "description": "Indian Stock Market Index",
    "instrument_token": 2455041,
    "earnings_dates": [
      "2026-01-16"
    ]
  }
]
```

**Fields:**
- `stock_name`: Full company name
- `symbol`: Trading symbol (NSE)
- `description`: Stock category/description
- `instrument_token`: Kite Connect instrument token (null if not found)
- `earnings_dates`: Array of earnings announcement dates (ISO format)

### Constants Configuration (src/config/constants.py)

All analysis parameters are centralized in `src/config/constants.py` for easy tuning:

**Analysis Windows:**
- `OBSERVATION_START_OFFSET = -20` (T-20)
- `OBSERVATION_END_OFFSET = 40` (T+40)
- `ACCUMULATION_START_OFFSET = -10` (T-10)
- `ACCUMULATION_END_OFFSET = -2` (T-2)

**Indicator Periods:**
- `RSI_PERIOD = 14`
- `ATR_PERIOD = 14`
- `BB_PERIOD = 20`, `BB_STD_DEV = 2.0`
- `SMA_SHORT_PERIOD = 20`, `SMA_MEDIUM_PERIOD = 50`, etc.

**Thresholds:**
- `RVOL_HIGH_PROBABILITY_THRESHOLD = 1.5`
- `RSI_OVERSOLD = 30`, `RSI_OVERBOUGHT = 70`

**Modify these values to tune the analysis behavior without changing code!**

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Kite Connect

Create `configs/api_config.json`:

```json
{
  "API_KEY": "your_api_key",
  "API_SECRET": "your_api_secret"
}
```

### 3. Authenticate

```bash
python3 kite_auth.py
```

Follow the prompts to authenticate. This creates `configs/access_token.json` (valid for 1 day).

### 4. Update Instrument Tokens (Optional)

If you add new stocks or have null tokens:

```bash
python3 adhoc_script/instrument_finder.py
```

This script:
- Reads `configs/stockSymbolDetails.json`
- Finds stocks with `instrument_token: null`
- Fetches tokens from Kite Connect NSE instruments
- Updates the JSON file

## Usage

### Launch Dashboard

```bash
# Option 1: Using main.py (with auto-reload enabled)
python3 main.py

# Option 2: Direct streamlit (with auto-reload)
streamlit run src/ui/app.py --server.runOnSave true
```

Dashboard opens at `http://localhost:8501`

**Auto-Reload**: The server automatically reloads when you save changes to any Python file. You'll see "Source file changed" in the browser and it will re-run automatically.

### Development Tips

- **Auto-reload is enabled** via `.streamlit/config.toml`
- Changes to `src/` files trigger automatic reload
- No need to restart the server during development
- Use `st.cache_resource` for expensive operations (already implemented)
- Press `R` in browser to manually rerun
- Press `C` to clear cache

### Dashboard Features

1. **Stock Selector**: Choose from your watchlist
2. **Quarter Selector**: Select earnings event to analyze
3. **Price Chart**: Candlestick with volume bars and markers:
   - Blue diamonds: Accumulation days (dip)
   - Purple: Reference high
   - Orange: T-1 (pre-earnings)
   - Green: T+2
   - Cyan: T+5
   - Magenta: T+10
   - Red: T+20
4. **Metrics Panel**:
   - Accumulation zone details (RVOL_20, RVOL_50, RSI)
   - Reference high & max drawdown
   - Strategy returns (Run-Up, Event)
   - Fixed-interval exits (T+2, T+5, T+10, T+20)

## Adding New Stocks

1. Edit `configs/stockSymbolDetails.json`:

```json
{
  "stock_name": "New Company Ltd.",
  "symbol": "NEWSYMBOL",
  "description": "Sector",
  "instrument_token": null,
  "earnings_dates": [
    "2026-02-15",
    "2025-11-15"
  ]
}
```

2. Run instrument finder to populate token:

```bash
python3 adhoc_script/instrument_finder.py
```

## Analysis Windows

All windows use **trading days** (NSE calendar):

- **Observation Period**: T-20 to T+40 (super-set for swing & positional)
- **Accumulation Window**: T-10 to T-2 (dip detection zone)
- **Run-Up Window**: Accumulation Date to T-1
- **Reaction Window**: T+0 to T+40

## Metrics Explained

### RVOL (Relative Volume)

- **RVOL_20**: Current volume / 20-day SMA (tactical/swing signal)
- **RVOL_50**: Current volume / 50-day SMA (strategic/positional signal)
- **Baseline**: Calculated up to T-11 to avoid pre-earnings contamination
- **High Probability**: RVOL_50 > 1.5 + price at accumulation low

### RSI (Relative Strength Index)

- **RSI_14**: Standard 14-period RSI (0-100)
  - < 30: Oversold
  - > 70: Overbought
  
- **RSI_Percentile**: Relative RSI vs 252-day history (0-100)
  - Shows how extreme current RSI is compared to past year
  - 0-20: Extremely oversold historically (rare opportunity)
  - 20-40: Below average
  - 40-60: Average range
  - 60-80: Above average
  - 80-100: Extremely overbought historically (caution)

**Example**: RSI = 35 (oversold) + RSI_Percentile = 15 (extremely low historically) = Strong accumulation signal

### ATR (Average True Range) - Volatility

- **ATR_14**: 14-period ATR (absolute volatility)
- **ATR_Percentile**: ATR vs 252-day history (0-100)
  - 0-20: Extremely low volatility (coiling spring)
  - 80-100: Extremely high volatility (explosive move)

**Use Case**: Low ATR + Low Price = Quiet accumulation before breakout

### Bollinger Bands - Price Extremes

- **BB_Lower/Upper**: 20-period bands (2 standard deviations)
- **BB_Width**: Band width as % of middle band
  - Narrow bands = Low volatility (consolidation)
  - Wide bands = High volatility (trending)

**Use Case**: Price at/below lower band = Objective oversold level

### Volume Percentile

- **Volume_Percentile**: Current volume vs 252-day history (0-100)
  - Complements RVOL analysis
  - 80-100: Unusually high volume (institutional activity)

**Use Case**: Volume_Percentile > 80 at dip = Strong accumulation signal

### Price Distance from SMAs

- **Distance_SMA_50/100/200**: (Close - SMA) / SMA × 100
  - Negative = Price below SMA (potential support)
  - Large negative = Oversold vs trend

**Use Case**: Distance_SMA_200 = -15% = Significantly below major trend (opportunity)

### Returns

- **Run-Up Trade**: Accumulation Price → T-1 Close (avoids event risk)
- **Event Trade**: T-1 Close → T+2 Close (takes event risk)
- **Profit_T2/T5/T10/T20**: Accumulation Price → T+N Close (fixed exits)

## Data Caching

### OHLCV Data
- First fetch: Downloads 1 year of data from Kite Connect
- Subsequent fetches: Merges new data with existing cache
- Cache location: `data/{SYMBOL}_ohlcv.json`
- Buffer: Fetches 100+ days before analysis window for indicator initialization

### Pre-calculated Indicators (Cached)

All indicators are calculated once during data fetch and cached with OHLCV data:

| Indicator | Description | Usage |
|-----------|-------------|-------|
| **RSI_14** | 14-period Relative Strength Index | Momentum at accumulation points (0-100) |
| **RSI_Percentile** | RSI percentile vs 252-day history | Relative strength context (0-100) |
| **ATR_14** | 14-period Average True Range | Volatility measure (absolute) |
| **ATR_Percentile** | ATR percentile vs 252-day history | Relative volatility (0-100) |
| **BB_Lower/Upper** | Bollinger Bands (20-period, 2σ) | Price extremes |
| **BB_Width** | Bollinger Band Width | Volatility proxy (%) |
| **Volume_Percentile** | Volume percentile vs 252-day history | Relative volume context (0-100) |
| **SMA_20/50/100/200** | Price moving averages | Trend identification |
| **Volume_SMA_20/50** | Volume moving averages | RVOL baselines |
| **Distance_SMA_50/100/200** | Price distance from SMAs | Trend deviation (%) |

**Benefits:**
- ✅ Calculated once, used multiple times
- ✅ Consistent across all analyses
- ✅ Faster subsequent loads (no recalculation)
- ✅ Cached with OHLCV data for persistence

**Note:** If you update the indicator calculation logic, delete the cache files in `data/` to force recalculation.

## Troubleshooting

### "Failed to fetch or analyze data"

- Check Kite authentication: `python3 kite_auth.py`
- Verify `configs/access_token.json` has today's date
- Check API rate limits

### Indicators show "N/A"

- Insufficient historical data for 50-day SMA
- Normal for newly listed stocks

### Missing instrument token

- Run: `python3 adhoc_script/instrument_finder.py`
- Verify symbol exists on NSE

## Technical Stack

- **Framework**: Python 3.10+
- **UI**: Streamlit
- **Charts**: Plotly
- **Data**: Pandas, pandas-ta
- **API**: Kite Connect

## License

Personal use only.
