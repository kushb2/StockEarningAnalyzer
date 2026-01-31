# Design Document

## Overview

A minimal Python tool using Streamlit for analyzing pre-earnings stock dips with dual-mode support (Swing & Positional). Supports multi-quarter validation and extended observation window (T-20 to T+40).

## Architecture

Single-user local application with three modules: Data Fetcher, Analyzer, and Dashboard.

## Project Structure

```
EarningsAlphaTool/
├── configs/                    # Existing - API keys, tokens
│   ├── api_config.json
│   ├── access_token.json
│   ├── instrument_tokens.json
│   ├── trading_symbols.json
│   └── earnings_dates.json     # NEW - multi-quarter earnings calendar
├── data/                       # NEW - cached OHLCV master files
├── src/
│   ├── api/
│   │   ├── earnings_data.py    # Earnings dates + window calculations
│   │   └── data_fetcher.py     # Kite data retrieval + master file caching
│   ├── logic/
│   │   └── analyzer.py         # Dip detection, dual RVOL, fixed-interval returns
│   └── ui/
│       └── app.py              # Streamlit dashboard with quarter selector
├── kite_auth.py                # Existing - authentication
├── constants.py                # Existing
├── requirements.txt            # Dependencies
└── main.py                     # Entry point
```

## Components

| Component | File | Purpose |
|-----------|------|---------|
| Earnings Data | `src/api/earnings_data.py` | Load multi-quarter dates, calculate windows |
| Data Fetcher | `src/api/data_fetcher.py` | Fetch OHLCV with 100-day buffer, master file cache |
| Analyzer | `src/logic/analyzer.py` | Dip detection, dual RVOL_20/50, fixed-interval returns |
| Dashboard | `src/ui/app.py` | Stock + Quarter selectors, candlestick charts |

## Data Models

- **OHLCV DataFrame**: pandas DataFrame with Date, Open, High, Low, Close, Volume
- **Earnings Config**: `{"SYMBOL": ["2024-01-15", "2024-04-15", ...]}` (list per stock)
- **Analysis Result**: Dict with accumulation_days, reference_high, drawdown, returns (T2/T5/T10/T20)

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

Property 1: Trading day calculation consistency
*For any* earnings date T and offset N, calculating T-N then T+N should return to the original date T
**Validates: Requirements 4.2**

Property 2: Accumulation price is minimum
*For any* OHLCV data in the T-10 to T-2 window, the accumulation price should be less than or equal to all Low values in that window
**Validates: Requirements 6.1**

Property 3: RVOL baseline isolation
*For any* analysis, the RVOL baseline calculations (both 20-day and 50-day) should only use data from dates before T-10
**Validates: Requirements 7.3**

## Error Handling

- Missing config files: Return descriptive error
- API failures: Log error, return None
- Missing data: Skip analysis, show message in UI

## Testing Strategy

Manual testing during development. Property tests can be added post-MVP if needed.
