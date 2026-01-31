# Indicator Reference Guide

Complete reference for all pre-calculated indicators in the Earnings Event Alpha Tool.

## Quick Reference Table

| Indicator | Type | Period | Window | Purpose |
|-----------|------|--------|--------|---------|
| RSI_14 | Momentum | 14 | - | Standard momentum |
| RSI_Percentile | Momentum | - | 252 | Relative momentum context |
| ATR_14 | Volatility | 14 | - | Absolute volatility |
| ATR_Percentile | Volatility | - | 252 | Relative volatility context |
| BB_Lower/Upper | Volatility | 20 | 2σ | Price extremes |
| BB_Width | Volatility | 20 | - | Volatility proxy |
| Volume_Percentile | Volume | - | 252 | Relative volume context |
| SMA_20/50/100/200 | Trend | N | - | Price trends |
| Volume_SMA_20/50 | Volume | N | - | RVOL baselines |
| Distance_SMA_N | Trend | - | - | Trend deviation |

## Detailed Descriptions

### 1. RSI (Relative Strength Index)

**RSI_14**
- **Formula**: Standard 14-period RSI
- **Range**: 0-100
- **Interpretation**:
  - < 30: Oversold
  - 30-70: Normal range
  - > 70: Overbought

**RSI_Percentile**
- **Formula**: (Current_RSI - Min_RSI_252) / (Max_RSI_252 - Min_RSI_252) × 100
- **Range**: 0-100
- **Interpretation**:
  - 0-20: Extremely oversold historically
  - 20-40: Below average
  - 40-60: Average
  - 60-80: Above average
  - 80-100: Extremely overbought historically

**Combined Signal**:
- RSI = 35 + RSI_Percentile = 15 → **Strong buy** (oversold + historically rare)
- RSI = 35 + RSI_Percentile = 55 → **Weak buy** (oversold but normal)

---

### 2. ATR (Average True Range)

**ATR_14**
- **Formula**: 14-period Average True Range
- **Unit**: Price units (₹)
- **Interpretation**: Higher ATR = Higher volatility

**ATR_Percentile**
- **Formula**: (Current_ATR - Min_ATR_252) / (Max_ATR_252 - Min_ATR_252) × 100
- **Range**: 0-100
- **Interpretation**:
  - 0-20: Extremely low volatility (coiling spring)
  - 20-40: Below average volatility
  - 40-60: Average volatility
  - 60-80: Above average volatility
  - 80-100: Extremely high volatility (explosive)

**Use Case**:
- ATR_Percentile < 20 at dip → Quiet accumulation, potential breakout
- ATR_Percentile > 80 → High volatility, caution

---

### 3. Bollinger Bands

**BB_Lower / BB_Upper**
- **Formula**: SMA_20 ± (2 × Standard Deviation)
- **Unit**: Price units (₹)
- **Interpretation**:
  - Price at/below BB_Lower → Oversold
  - Price at/above BB_Upper → Overbought

**BB_Width**
- **Formula**: (BB_Upper - BB_Lower) / BB_Middle × 100
- **Unit**: Percentage
- **Interpretation**:
  - Low BB_Width → Low volatility (consolidation)
  - High BB_Width → High volatility (trending)

**Use Case**:
- Price touches BB_Lower + Low BB_Width → Potential reversal from oversold
- Narrow bands → Volatility contraction before breakout

---

### 4. Volume Indicators

**Volume_Percentile**
- **Formula**: (Current_Volume - Min_Volume_252) / (Max_Volume_252 - Min_Volume_252) × 100
- **Range**: 0-100
- **Interpretation**:
  - 0-20: Extremely low volume
  - 80-100: Extremely high volume (institutional activity)

**Volume_SMA_20 / Volume_SMA_50**
- **Formula**: Simple Moving Average of volume
- **Use**: Baselines for RVOL calculation

**RVOL_20 / RVOL_50** (Calculated in Analyzer)
- **Formula**: Current_Volume / Volume_SMA_N
- **Interpretation**:
  - RVOL > 1.5 → High volume (accumulation signal)
  - RVOL < 0.5 → Low volume (drift/trap)

**Combined Signal**:
- Volume_Percentile > 80 + RVOL_50 > 1.5 at dip → **Strong accumulation**

---

### 5. Price Moving Averages

**SMA_20 / SMA_50 / SMA_100 / SMA_200**
- **Formula**: Simple Moving Average of close price
- **Use**:
  - SMA_20: Short-term trend
  - SMA_50: Medium-term trend
  - SMA_100: Long-term reference
  - SMA_200: Major trend indicator

**Interpretation**:
- Price > SMA → Uptrend
- Price < SMA → Downtrend
- Price crossing SMA → Trend change

---

### 6. Price Distance from SMAs

**Distance_SMA_50 / Distance_SMA_100 / Distance_SMA_200**
- **Formula**: (Close - SMA_N) / SMA_N × 100
- **Unit**: Percentage
- **Interpretation**:
  - Positive → Price above SMA (strength)
  - Negative → Price below SMA (weakness)
  - Large negative → Oversold vs trend (opportunity)

**Use Case**:
- Distance_SMA_200 = -15% → Price 15% below 200-day MA (significant pullback)
- Distance_SMA_50 = -8% → Price 8% below 50-day MA (short-term oversold)

---

## Accumulation Signal Checklist

Use this checklist to evaluate accumulation quality:

### Strong Accumulation (5/5 signals)
- ✅ RSI < 30 AND RSI_Percentile < 20
- ✅ ATR_Percentile < 30 (low volatility)
- ✅ Price at/below BB_Lower
- ✅ Volume_Percentile > 70 AND RVOL_50 > 1.5
- ✅ Distance_SMA_200 < -10%

### Moderate Accumulation (3-4/5 signals)
- ⚠️ Some signals present but not all

### Weak/Avoid (< 3/5 signals)
- ❌ Insufficient confirmation
- ❌ Low volume (drift/trap)

---

## Configuration

All indicator parameters are defined in `src/config/constants.py`:

```python
# Indicator Periods
RSI_PERIOD = 14
ATR_PERIOD = 14
BB_PERIOD = 20
BB_STD_DEV = 2.0
SMA_SHORT_PERIOD = 20
SMA_MEDIUM_PERIOD = 50
SMA_LONG_PERIOD = 100
SMA_MAJOR_PERIOD = 200

# Percentile Windows
RSI_PERCENTILE_WINDOW = 252
ATR_PERCENTILE_WINDOW = 252
VOLUME_PERCENTILE_WINDOW = 252
```

Modify these values to tune indicator sensitivity!

---

## Cache Management

All indicators are calculated once and cached with OHLCV data.

**To recalculate indicators after changing constants:**
```bash
# Delete cache files
rm -rf data/*.json

# Restart the app - indicators will be recalculated
python3 main.py
```

---

## Performance Notes

- **Percentile calculations**: O(n) per row, optimized with rolling windows
- **Cache hit**: Instant load (no recalculation)
- **Cache miss**: ~2-3 seconds for 1 year of data per stock
- **Memory**: ~5-10 MB per stock with all indicators

---

## Future Enhancements

Potential indicators to add:
- **MACD**: Moving Average Convergence Divergence
- **Stochastic**: %K and %D oscillators
- **OBV**: On-Balance Volume
- **ADX**: Average Directional Index (trend strength)
- **Ichimoku Cloud**: Multi-timeframe support/resistance
