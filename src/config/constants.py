"""
Constants and Configuration Values for Earnings Event Alpha Tool

Centralized configuration for all indicators, windows, and thresholds.
Modify these values to tune the analysis behavior.
"""

# ============================================================================
# ANALYSIS WINDOWS (Trading Days Relative to Earnings Date T)
# ============================================================================

# Observation Period
OBSERVATION_START_OFFSET = -20  # T-20
OBSERVATION_END_OFFSET = 40     # T+40

# Accumulation Window (Dip Detection Zone)
ACCUMULATION_START_OFFSET = -10  # T-10
ACCUMULATION_END_OFFSET = -2     # T-2

# RVOL Baseline Cutoff
RVOL_BASELINE_OFFSET = -11  # T-11 (freeze baseline here)


# ============================================================================
# INDICATOR PERIODS
# ============================================================================

# RSI (Relative Strength Index)
RSI_PERIOD = 14
RSI_PERCENTILE_WINDOW = 252  # 1 year of trading days

# Moving Averages (Price)
SMA_SHORT_PERIOD = 20
SMA_MEDIUM_PERIOD = 50
SMA_LONG_PERIOD = 100
SMA_MAJOR_PERIOD = 200

# Moving Averages (Volume)
VOLUME_SMA_SHORT_PERIOD = 20   # Tactical/Swing
VOLUME_SMA_MEDIUM_PERIOD = 50  # Strategic/Positional

# ATR (Average True Range)
ATR_PERIOD = 14
ATR_PERCENTILE_WINDOW = 252  # 1 year of trading days

# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2.0

# Volume Percentile
VOLUME_PERCENTILE_WINDOW = 252  # 1 year of trading days


# ============================================================================
# THRESHOLDS
# ============================================================================

# RVOL Thresholds
RVOL_HIGH_PROBABILITY_THRESHOLD = 1.5  # RVOL_50 > 1.5 = high probability

# RSI Thresholds (Standard)
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# RSI Percentile Thresholds
RSI_PERCENTILE_EXTREMELY_LOW = 20   # 0-20: Extremely oversold historically
RSI_PERCENTILE_LOW = 40             # 20-40: Below average
RSI_PERCENTILE_HIGH = 60            # 60-80: Above average
RSI_PERCENTILE_EXTREMELY_HIGH = 80  # 80-100: Extremely overbought historically


# ============================================================================
# DATA FETCHING
# ============================================================================

# Buffer for indicator initialization
INDICATOR_BUFFER_DAYS = 100  # Fetch 100+ days before analysis window

# Default history to fetch
DEFAULT_HISTORY_DAYS = 365  # 1 year


# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Required indicators for cache validation
REQUIRED_INDICATORS = [
    'RSI_14',
    'RSI_Percentile',
    'ATR_14',
    'ATR_Percentile',
    'BB_Lower',
    'BB_Upper',
    'BB_Width',
    'Volume_Percentile',
    'SMA_20',
    'SMA_50',
    'SMA_100',
    'SMA_200',
    'Volume_SMA_20',
    'Volume_SMA_50',
    'Distance_SMA_50',
    'Distance_SMA_100',
    'Distance_SMA_200'
]


# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

# Currency symbol
CURRENCY_SYMBOL = "₹"

# Date format
DATE_FORMAT = "%Y-%m-%d"

# Decimal places
PRICE_DECIMALS = 2
PERCENTAGE_DECIMALS = 2
INDICATOR_DECIMALS = 2
