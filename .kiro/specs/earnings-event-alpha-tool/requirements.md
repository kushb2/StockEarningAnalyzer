# Requirements Document

## Introduction

The Earnings Event Alpha Tool is a personal weekend project for systematic analysis of quarterly earnings trading opportunities. The tool tests the hypothesis that stocks enter a liquidity-seeking "dip" (Accumulation Zone) approximately 10 trading days before earnings, run up into the event, and can sustain trends for 2-4 weeks post-event. It provides data-driven insights for positional trading around the 4 major quarterly events per year.

**Note**: This is a single-user tool for personal use. The design is intentionally minimal to allow rapid pivoting during implementation.

## Glossary

- **Accumulation_Zone**: The price area where institutional buying absorbs retail selling, typically identified by low prices with high volume
- **Trading_Day**: A day when the NSE (National Stock Exchange) is open for trading, excluding weekends and holidays
- **Earnings_Date (T)**: The date when a company announces its quarterly/annual earnings results
- **OHLCV**: Open, High, Low, Close, Volume - standard market data format
- **RVOL_20 (Tactical)**: Current volume divided by the 20-day SMA of volume (short-term signal)
- **RVOL_50 (Strategic)**: Current volume divided by the 50-day SMA of volume (quarterly baseline)
- **RSI (Relative_Strength_Index)**: A momentum oscillator measuring speed and magnitude of price changes (0-100 scale)
- **Drawdown**: The percentage decline from a reference high to a subsequent low
- **Run_Up_Trade**: A trading strategy that enters at the accumulation price and exits at T-1 close
- **Event_Trade**: A trading strategy that enters at T-1 close and exits at T+2 close
- **Positional_Trade**: A trading strategy that holds through the event for 2-4 weeks (T+10 to T+20)
- **Kite_Connect_API**: Zerodha's trading API for fetching market data
- **Data_Fetcher**: The module responsible for retrieving and caching OHLCV data from Kite Connect
- **Analyzer**: The module responsible for calculating dip detection, metrics, and returns
- **Dashboard**: The Streamlit-based user interface for visualization and interaction

## Requirements

### Requirement 1: Stock Universe Management

**User Story:** As a trader, I want to manage a list of target stocks, so that I can analyze earnings events for my watchlist.

#### Acceptance Criteria

1. WHEN the system starts, THE Data_Fetcher SHALL load the stock universe from `trading_symbols.json`
2. WHEN a stock symbol is requested, THE Data_Fetcher SHALL retrieve the corresponding instrument token from `instrument_tokens.json`
3. IF a requested symbol is not found in the configuration, THEN THE Data_Fetcher SHALL return a descriptive error message

### Requirement 2: Earnings Calendar Management (Multi-Quarter)

**User Story:** As a trader, I want to maintain multiple earnings dates per stock, so that I can validate patterns across quarters.

#### Acceptance Criteria

1. WHEN the system starts, THE Data_Fetcher SHALL load earnings dates from `earnings_dates.json`
2. THE Data_Fetcher SHALL support a list of dates per stock for multi-quarter backtesting
3. THE Data_Fetcher SHALL parse earnings dates in ISO format (YYYY-MM-DD)
4. IF no earnings dates exist for a requested stock, THEN THE Data_Fetcher SHALL return a descriptive error message

### Requirement 3: Market Data Retrieval (With Indicator Buffer)

**User Story:** As a trader, I want to fetch historical OHLCV data with sufficient history for indicator calculation.

#### Acceptance Criteria

1. WHEN market data is requested, THE Data_Fetcher SHALL retrieve daily OHLCV data from Kite Connect API
2. THE Data_Fetcher SHALL retrieve data starting at least 100 trading days prior to the Observation Window start date to initialize indicators (50-day SMA, RSI)
3. THE Data_Fetcher SHALL support fetching up to 6 months of historical data
4. WHEN data is fetched, THE Data_Fetcher SHALL cache it locally as JSON files in the `data/` directory
5. THE Data_Fetcher SHALL use a "Master File" approach - cache should contain full history and be updated/merged, not overwritten
6. WHEN cached data exists and covers the required date range, THE Data_Fetcher SHALL use the cached data instead of making an API call
7. IF the Kite Connect API returns an error, THEN THE Data_Fetcher SHALL return a descriptive error message with the API error details

### Requirement 4: Trading Day Calculation

**User Story:** As a trader, I want all date calculations to use trading days, so that weekends and holidays are excluded from analysis windows.

#### Acceptance Criteria

1. THE Analyzer SHALL calculate all date offsets using NSE trading days, not calendar days
2. WHEN calculating T-N or T+N dates, THE Analyzer SHALL skip non-trading days (weekends and NSE holidays)
3. THE Analyzer SHALL derive the trading day calendar from the available OHLCV data dates

### Requirement 5: Analysis Window Definition (Super-Set for Swing & Positional)

**User Story:** As a trader, I want extended analysis windows to evaluate both swing and positional trade potential.

#### Acceptance Criteria

1. THE Analyzer SHALL define the Observation Period as T-20 to T+40 trading days (super-set covering both styles)
2. THE Analyzer SHALL define the Accumulation Window as T-10 to T-2 trading days
3. THE Analyzer SHALL define the Run-Up Window as Accumulation Date to T-1 trading day
4. THE Analyzer SHALL define the Reaction Window as T+0 to T+40 trading days

### Requirement 6: Accumulation Detection

**User Story:** As a trader, I want to identify the accumulation zone (dip), so that I can find optimal entry points.

#### Acceptance Criteria

1. THE Analyzer SHALL identify the Accumulation Price as the lowest Low within the T-10 to T-2 window
2. THE Analyzer SHALL identify ALL days where the Low equals the Accumulation Price
3. FOR EACH Accumulation Day, THE Analyzer SHALL calculate and store: Date, Low Price, RVOL_20, RVOL_50, and RSI
4. THE Analyzer SHALL calculate Days Before Result as the number of trading days between each Accumulation Day and T

### Requirement 7: Volume Confirmation (Dual-Mode RVOL)

**User Story:** As a trader, I want both tactical (swing) and strategic (positional) volume signals to distinguish drift from accumulation.

#### Acceptance Criteria

1. THE Analyzer SHALL calculate RVOL_20 as Current Volume divided by the 20-day SMA of Volume (Tactical/Swing signal)
2. THE Analyzer SHALL calculate RVOL_50 as Current Volume divided by the 50-day SMA of Volume (Strategic/Positional baseline)
3. THE Analyzer SHALL store BOTH RVOL values for each day to allow comparison (e.g., "tactical spike but quarterly quiet")
4. THE Analyzer SHALL calculate the RVOL baselines using SMAs ending at T-11 trading days
5. THE Analyzer SHALL flag days as "High Probability" when RVOL_50 exceeds 1.5 AND price is at or near the accumulation low
6. THE Analyzer SHALL NOT apply automated absorption confirmation rules in the MVP

### Requirement 8: Drawdown Calculation

**User Story:** As a trader, I want to measure the maximum drawdown before the dip, so that I can understand the "pain" experienced before the bottom.

#### Acceptance Criteria

1. THE Analyzer SHALL calculate the Reference High as the highest High from T-15 to (Accumulation Date - 1)
2. THE Analyzer SHALL calculate Max Drawdown as the percentage drop from Reference High to Accumulation Price
3. THE Analyzer SHALL store both the Reference High price and its date

### Requirement 9: RSI Calculation

**User Story:** As a trader, I want to see RSI values at accumulation points, so that I can discover patterns in successful setups.

#### Acceptance Criteria

1. THE Analyzer SHALL calculate RSI using a 14-period lookback
2. FOR EACH Accumulation Day, THE Analyzer SHALL log the RSI value (0-100)
3. THE Analyzer SHALL NOT apply RSI-based filtering in the MVP

### Requirement 10: Return Calculation at Fixed Intervals

**User Story:** As a trader, I want returns calculated at multiple fixed intervals, so that I can evaluate swing vs positional potential without changing code.

#### Acceptance Criteria

1. THE Analyzer SHALL calculate Run-Up Trade Return as the percentage gain from Accumulation Price to T-1 Close
2. THE Analyzer SHALL calculate Event Trade Return as the percentage gain from T-1 Close to T+2 Close
3. THE Analyzer SHALL calculate Profit_T2 as the percentage gain from Accumulation Price to T+2 Close
4. THE Analyzer SHALL calculate Profit_T5 as the percentage gain from Accumulation Price to T+5 Close
5. THE Analyzer SHALL calculate Profit_T10 as the percentage gain from Accumulation Price to T+10 Close
6. THE Analyzer SHALL calculate Profit_T20 as the percentage gain from Accumulation Price to T+20 Close

### Requirement 11: Dashboard Stock and Quarter Selection

**User Story:** As a trader, I want to select stocks and specific quarters, so that I can analyze individual events.

#### Acceptance Criteria

1. WHEN the Dashboard loads, THE Dashboard SHALL display a dropdown populated with all stocks from the stock universe
2. WHEN a user selects a stock, THE Dashboard SHALL display a second dropdown with available earnings dates (quarters) for that stock
3. WHEN a user selects a stock and quarter, THE Dashboard SHALL load and display the analysis for that event
4. THE Dashboard SHALL allow rapid toggling between stocks and quarters without page reload

### Requirement 12: Dashboard Chart Visualization

**User Story:** As a trader, I want to see candlestick charts with volume, so that I can visually identify price patterns and wicks.

#### Acceptance Criteria

1. THE Dashboard SHALL display a candlestick chart for the Observation Period (T-20 to T+40)
2. THE Dashboard SHALL display volume bars below the candlestick chart
3. THE Dashboard SHALL highlight Accumulation Day(s) with visual markers on the chart
4. THE Dashboard SHALL mark T-1 (pre-result), T+2, T+5, T+10, and T+20 dates on the chart
5. THE Dashboard SHALL mark the Reference High on the chart

### Requirement 13: Dashboard Data Panel

**User Story:** As a trader, I want to see all calculated metrics in a data panel, so that I can make informed decisions.

#### Acceptance Criteria

1. THE Dashboard SHALL display: Stock Symbol, Earnings Date (T), Quarter
2. THE Dashboard SHALL display: Accumulation Days table (Date, Low, RVOL_20, RVOL_50, RSI for each)
3. THE Dashboard SHALL display: Reference High (Price and Date), Max Drawdown percentage
4. THE Dashboard SHALL display: Run-Up Trade Return, Event Trade Return
5. THE Dashboard SHALL display: Profit_T2, Profit_T5, Profit_T10, Profit_T20

### Requirement 14: Data Persistence (Master File)

**User Story:** As a trader, I want my fetched data to be cached as a master file, so that I can build up history over time.

#### Acceptance Criteria

1. WHEN OHLCV data is fetched, THE Data_Fetcher SHALL merge it with existing cached data (append-only or merge strategy)
2. THE Data_Fetcher SHALL name cached files using the pattern `{symbol}_ohlcv.json`
3. WHEN loading cached data, THE Data_Fetcher SHALL parse the JSON and convert it to a pandas DataFrame
4. THE Data_Fetcher SHALL fetch sufficient history (1 year default) to cover multiple quarterly events in one file
