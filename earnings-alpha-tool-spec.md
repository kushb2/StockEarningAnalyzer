# Earnings Event Alpha Tool - Complete Specification

## 1. Core Hypothesis

Stocks enter a liquidity-seeking "dip" (Accumulation Zone) approximately 10 trading days before earnings, run up into the event, and stabilize/revert 5 days after.

**Goal**: Systematically identify the "Dip" date/price and calculate the potential alpha (profit) of buying that dip vs. buying indiscriminately.

---

## 2. Data Inputs

| Input | Source | Notes |
|-------|--------|-------|
| Stock Universe | `trading_symbols.json` | Target stocks list |
| Earnings Calendar | `earnings_dates.json` | Manually updated, trusted source |
| Market Data | Zerodha Kite Connect API | Daily OHLCV, max 6 months |

---

## 3. Analysis Windows (Relative to Earnings Date 'T')

**All windows use TRADING DAYS (NSE calendar), not calendar days.**

| Window | Range | Purpose |
|--------|-------|---------|
| Observation Period | T-15 to T+10 | Full analysis scope (~25 sessions) |
| Accumulation Window | T-10 to T-2 | Search area for dip detection |
| Run-Up Window | Accumulation Date to T-1 | Measures pre-event momentum |
| Reaction Window | T+0 to T+5 | Post-event behavior |

---

## 4. Key Metrics

### 4.1 Accumulation Detection

| Metric | Definition |
|--------|------------|
| Accumulation Price | Lowest Low in T-10 to T-2 window |
| Accumulation Days | ALL days where Low = Lowest Low (show multiple) |
| Days Before Result | How many trading days before T the accumulation started |

**Output per Accumulation Day**: Date, Low Price, RVOL, RSI

### 4.2 Volume Confirmation (Drift vs Accumulation)

**Drift (Trap)**: Price drops on LOW volume → no institutional support, avoid.

**Accumulation (Signal)**: Price drops but volume SPIKES → absorption happening, institutions buying retail panic.

| Metric | Calculation |
|--------|-------------|
| RVOL (Relative Volume) | Current Volume / 20-day SMA Volume |
| RVOL Baseline | 20-day SMA computed UP TO T-11 (uncontaminated by pre-earnings volatility) |
| High Probability Flag | RVOL > 1.5x AND price at/near accumulation low |

**Note**: No hardcoded absorption confirmation rule (like "2-day hold"). Flag high RVOL days, visually confirm on chart. Automate in v2.0 after 50+ manual validations.

### 4.3 Drawdown Calculation (Dynamic)

| Metric | Calculation |
|--------|-------------|
| Reference High | Highest High from T-15 to (Dip Date - 1) — DYNAMIC, not fixed T-11 |
| Max Drawdown | % drop from Reference High to Accumulation Price |

**Reasoning**: Measures actual "pain" a holder felt before the bottom formed.

### 4.4 RSI Handling

| Approach | Details |
|----------|---------|
| RSI_at_Dip | Log RSI value (0-100) at each accumulation day |
| Filtering | NONE for MVP — let data reveal optimal range |
| Goal | Discover patterns like "80% of successful setups had RSI 35-45" |

### 4.5 Strategy Comparison (Two Distinct Trades)

**Why Split?** Holding through T+0 is "gambling on the gap." Executable alpha ≠ theoretical alpha.

| Strategy | Entry | Exit | Risk Profile |
|----------|-------|------|--------------|
| Run-Up Trade | Accumulation Price | T-1 Close | Avoids event risk |
| Event Trade | T-1 Close | T+2 Close | Takes event risk |

### 4.6 Exit Comparison

| Metric | Calculation | Purpose |
|--------|-------------|---------|
| Profit_T2 | % gain from entry to T+2 Close | Pure event play |
| Profit_T5 | % gain from entry to T+5 Close | Trend play |

**Goal**: If Profit_T5 < Profit_T2 consistently, alpha disappears after 48 hours.

---

## 5. Technical Architecture

### 5.1 Stack

| Component | Technology |
|-----------|------------|
| Framework | Python 3.10+ |
| UI | Streamlit |
| Data Storage | Local JSON/CSV (simulating DB) |
| Libraries | kiteconnect, pandas, pandas_ta (or ta-lib), streamlit, plotly |

### 5.2 Project Structure

```
EarningsAlphaTool/
├── config/             # API keys, token files
├── data/               # Raw cache (OHLCV jsons), earnings_dates.json, trading_symbols.json
├── src/
│   ├── api/            # kite_auth.py, data_fetcher.py
│   ├── logic/          # analyzer.py (dip detection, metrics calculation)
│   └── ui/             # app.py (Streamlit dashboard)
├── requirements.txt
└── main.py             # Entry point
```

### 5.3 Modules (Roadmap)

| Module | Name | Status |
|--------|------|--------|
| 1 | Data Fetcher & Caching (Engine) | MVP |
| 2 | Event Logic & Calculator (Brain) | MVP |
| 3 | Streamlit Dashboard (Face) | MVP |
| 4 | Backtesting Engine (Simulator) | Future |

---

## 6. MVP Output: Streamlit Dashboard

### 6.1 Primary Chart

**Candlestick with Volume Bars** + markers for:
- Dip date(s) — highlighted
- T-1 (pre-result)
- T+2 (post-result)
- Reference High

**Why Candlestick?** Line charts hide wicks. Dip identification relies on seeing long lower wicks (price rejection).

### 6.2 Data Panel (Per Stock/Event)

| Field | Value |
|-------|-------|
| Stock Symbol | e.g., RELIANCE |
| Earnings Date (T) | e.g., 2025-01-15 |
| Accumulation Days | List with Date, Low, RVOL, RSI |
| Reference High | Price + Date |
| Max Drawdown | % |
| Run-Up Trade Return | % (Dip → T-1) |
| Event Trade Return | % (T-1 → T+2) |
| Profit_T2 | % |
| Profit_T5 | % |

### 6.3 Interactivity

- Stock selector dropdown
- Date range filter
- Toggle between stocks rapidly
- Visual correlation between metrics and chart

---

## 7. Constraints & Assumptions

| Item | Decision |
|------|----------|
| Data Limit | 6 months max (Kite API sufficient) |
| Earnings Source | Manual JSON, trusted without validation |
| Overlapping Events | Not handled — user provides single earnings date per analysis |
| Absorption Rule | Visual confirmation only (no automated 2-day hold filter) |
| RSI Filter | None — log only, analyze patterns post-hoc |

---

## 8. Summary of Refined Logic

1. **Time = Trading Days** (ignore NSE holidays)
2. **RVOL baseline = 20-day SMA ending at T-11** (clean baseline)
3. **Show ALL accumulation days** with full detail (Date, RVOL, RSI)
4. **Dynamic drawdown** = High before dip, not fixed T-11
5. **Two strategies**: Run-Up (safe) vs Event (risky)
6. **Two exits**: T+2 vs T+5 comparison
7. **No hardcoded filters** — flag and visually confirm
8. **Candlestick + volume** as primary visualization

---

## 9. Next Steps

1. Set up project structure in correct workspace
2. Build Module 1: Kite Connect auth + OHLCV fetcher with caching
3. Build Module 2: Analyzer (dip detection, RVOL, drawdown, returns)
4. Build Module 3: Streamlit dashboard with candlestick charts
5. Iterate based on 50+ manual validations
