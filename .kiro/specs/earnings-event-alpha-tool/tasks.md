# Implementation Plan: Earnings Event Alpha Tool

## Overview

Three-phase implementation: Engine (Python backend with dual-mode Swing/Positional logic), Interface (Streamlit UI with quarter selector), Assembly (integration and testing).

## Tasks

- [ ] 1. Phase 1: The Engine (Python Backend)
  - [x] 1.1 Create earnings_dates.json config file
    - Add multi-quarter earnings dates for stocks
    - Format: `{"POLYCAB": ["2024-01-15", "2024-04-15", "2024-07-15", "2024-10-15"], ...}`
    - Include at least 2-4 quarters per stock for pattern validation
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 1.2 Create EarningsData class for date and window management
    - Create `src/api/earnings_data.py`
    - Load multi-quarter earnings dates from JSON (array format: `["2025-Q1", "2024-Q4", ...]`)
    - Calculate trading day offsets (T-N, T+N) using available OHLCV dates
    - Define super-set analysis windows: Observation (T-20 to T+40), Accumulation (T-10 to T-2)
    - Return list of available quarters for a given stock
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4_

  - [x] 1.3 Build DataFetcher with master file caching
    - Create `src/api/data_fetcher.py`
    - Use existing KiteAuthenticator from kite_auth.py
    - Fetch daily OHLCV from Kite Connect API
    - Fetch 100+ days buffer before observation window for indicator initialization
    - Implement master file cache: merge new data with existing `data/{symbol}_ohlcv.json`
    - Default to 1 year history to cover multiple quarters
    - _Requirements: 1.1, 1.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 14.1, 14.2, 14.3, 14.4_

  - [x] 1.4 Implement Analyzer with dual RVOL and fixed-interval returns
    - Create `src/logic/analyzer.py`
    - Find Accumulation Price (lowest Low in T-10 to T-2)
    - Find ALL accumulation days where Low = Accumulation Price
    - Calculate RVOL_20 (20-day SMA baseline ending at T-11) - Tactical/Swing
    - Calculate RVOL_50 (50-day SMA baseline ending at T-11) - Strategic/Positional
    - Store BOTH RVOL values for comparison (e.g., "tactical spike but quarterly quiet")
    - Calculate RSI (14-period) at each accumulation day
    - Calculate Reference High (highest High from T-20 to Dip-1)
    - Calculate Max Drawdown percentage
    - Calculate fixed-interval returns: Run-Up, Event, Profit_T2, Profit_T5, Profit_T10, Profit_T20
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 9.1, 9.2, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [ ] 2. Phase 2: The Interface (Streamlit)
  - [x] 2.1 Setup Streamlit layout with dual selectors
    - Create `src/ui/app.py`
    - Sidebar with stock selector dropdown (from trading_symbols.json)
    - Sidebar with quarter/date selector dropdown (dynamic based on selected stock)
    - Main area placeholder for chart and metrics
    - _Requirements: 11.1, 11.2, 11.3_

  - [x] 2.2 Integrate Plotly candlestick chart with extended markers
    - Render candlestick chart for Observation Period (T-20 to T+40)
    - Add volume bars below candlesticks
    - Add markers for: Accumulation Day(s), T-1, T+2, T+5, T+10, T+20, Reference High
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 2.3 Display extended metrics data panel
    - Show Stock Symbol, Earnings Date, Quarter
    - Show Accumulation Days table (Date, Low, RVOL_20, RVOL_50, RSI)
    - Show Reference High (Price, Date), Max Drawdown
    - Show Returns: Run-Up Trade, Event Trade
    - Show Extended Exits: Profit_T2, Profit_T5, Profit_T10, Profit_T20
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 3. Phase 3: The Assembly
  - [x] 3.1 Wire Engine to UI
    - Connect DataFetcher, EarningsData, and Analyzer to Streamlit app
    - Handle stock selection changes (update quarter dropdown)
    - Handle quarter selection changes (update analysis)
    - Enable rapid toggling between stocks and quarters
    - _Requirements: 11.4_

  - [-] 3.2 Test with POLYCAB across multiple quarters
    - Run end-to-end test with POLYCAB stock
    - Test switching between different quarters
    - Verify chart renders correctly with super-set window (T-20 to T+40)
    - Verify dual RVOL values display correctly (RVOL_20 vs RVOL_50)
    - Verify all fixed-interval returns display correctly (T+2, T+5, T+10, T+20)
    - Fix any integration issues

  - [ ] 3.3 Create requirements.txt
    - Add dependencies: kiteconnect, pandas, pandas_ta, streamlit, plotly

- [ ] 4. Final checkpoint
  - Ensure app runs without errors
  - Verify multi-quarter analysis works
  - Ask user if questions arise

## Notes

- Leverages existing kite_auth.py for authentication
- Uses existing configs/ folder structure
- 100-day data buffer ensures 50-day SMA can be calculated accurately
- Master file caching builds up history over time
- Super-set observation window (T-20 to T+40) supports both Swing and Positional analysis
- Dual RVOL (20-day tactical, 50-day strategic) allows comparing short vs long-term volume signals
- Fixed-interval returns (T+2, T+5, T+10, T+20) let you evaluate exit timing without code changes
