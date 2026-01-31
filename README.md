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
# Option 1: Using main.py
python3 main.py

# Option 2: Direct streamlit
streamlit run src/ui/app.py
```

Dashboard opens at `http://localhost:8501`

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

### Interpretation

- **High RVOL + Low Price**: Accumulation (institutions buying retail panic)
- **Low RVOL + Low Price**: Drift/trap (no support, avoid)

### Returns

- **Run-Up Trade**: Accumulation Price → T-1 Close (avoids event risk)
- **Event Trade**: T-1 Close → T+2 Close (takes event risk)
- **Profit_T2/T5/T10/T20**: Accumulation Price → T+N Close (fixed exits)

## Data Caching

- First fetch: Downloads 1 year of data from Kite Connect
- Subsequent fetches: Merges new data with existing cache
- Cache location: `data/{SYMBOL}_ohlcv.json`
- Buffer: Fetches 100+ days before analysis window for indicator initialization

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
