# RSI Percentile Calculation Explained

## What is RSI Percentile?

RSI Percentile shows **where the current RSI sits within its historical range** over the past 252 trading days (approximately 1 year).

## Formula

```
RSI_Percentile = (Current_RSI - Min_RSI_252) / (Max_RSI_252 - Min_RSI_252) × 100
```

## Step-by-Step Example

### Scenario:
- Current RSI: 35
- 252-day RSI history: Min = 20, Max = 80

### Calculation:
```
RSI_Percentile = (35 - 20) / (80 - 20) × 100
               = 15 / 60 × 100
               = 25%
```

### Interpretation:
- **RSI = 35**: Currently oversold (< 30 threshold)
- **RSI_Percentile = 25%**: In the bottom 25% of its 252-day range
- **Signal**: Moderately oversold historically

## Why Use RSI Percentile?

### Problem with Standard RSI:
- Stock A: RSI = 30 (oversold)
- Stock B: RSI = 30 (oversold)

Both look the same, but:
- Stock A typically ranges between RSI 25-75 → RSI 30 is **normal**
- Stock B typically ranges between RSI 40-90 → RSI 30 is **extremely rare**

### Solution: RSI Percentile
- Stock A: RSI_Percentile = 50% (middle of range, not special)
- Stock B: RSI_Percentile = 5% (bottom 5%, very rare!)

## Interpretation Guide

| RSI_Percentile | Meaning | Action |
|----------------|---------|--------|
| 0-10% | Extremely oversold (bottom 10% historically) | **Strong buy signal** |
| 10-20% | Very oversold | Strong buy signal |
| 20-40% | Below average | Moderate buy signal |
| 40-60% | Average range | Neutral |
| 60-80% | Above average | Caution |
| 80-90% | Very overbought | Strong sell signal |
| 90-100% | Extremely overbought (top 10% historically) | **Strong sell signal** |

## Real-World Examples

### Example 1: Strong Accumulation Signal
```
Date: 2025-01-15 (T-5 before earnings)
RSI: 28 (oversold)
RSI_Percentile: 12% (very low historically)

Interpretation: Not just oversold, but at historically rare levels.
This is a strong accumulation opportunity.
```

### Example 2: Weak Signal
```
Date: 2025-01-15 (T-5 before earnings)
RSI: 28 (oversold)
RSI_Percentile: 55% (average)

Interpretation: Oversold by standard definition, but normal for this stock.
Weaker signal - this stock often trades at RSI 28.
```

### Example 3: False Oversold
```
Date: 2025-01-15 (T-5 before earnings)
RSI: 32 (near oversold)
RSI_Percentile: 85% (very high historically)

Interpretation: RSI looks okay, but historically this is elevated.
Avoid - stock is actually expensive relative to its history.
```

## Implementation Details

### Window Size: 252 Trading Days
- Approximately 1 year of trading data
- Captures seasonal patterns
- Enough data for statistical significance

### Rolling Calculation:
For each day, we:
1. Look back 252 trading days (or less if insufficient data)
2. Find Min and Max RSI in that window
3. Calculate where current RSI sits in that range
4. Express as percentage (0-100)

### Edge Cases:
- **Insufficient data** (< 2 days): Returns None
- **All RSI values identical**: Returns 50% (middle)
- **NaN RSI values**: Skipped in calculation

## Code Implementation

```python
def _calculate_percentile(self, series: pd.Series, window: int = 252) -> pd.Series:
    """
    Calculate percentile rank using rolling window.
    
    Formula: (Current_Value - Min_Value) / (Max_Value - Min_Value) * 100
    """
    percentile = pd.Series(index=series.index, dtype=float)
    
    for i in range(len(series)):
        if pd.isna(series.iloc[i]):
            percentile.iloc[i] = None
            continue
        
        # Get 252-day window ending at current position
        start_idx = max(0, i - window + 1)
        window_data = series.iloc[start_idx:i+1]
        
        # Remove NaN values
        window_data = window_data.dropna()
        
        if len(window_data) < 2:
            percentile.iloc[i] = None
            continue
        
        current_value = series.iloc[i]
        min_value = window_data.min()
        max_value = window_data.max()
        
        # Calculate percentile
        if max_value - min_value > 0:
            pct = ((current_value - min_value) / (max_value - min_value)) * 100
            percentile.iloc[i] = pct
        else:
            # All values are the same in the window
            percentile.iloc[i] = 50.0
    
    return percentile
```

## Comparison with Other Methods

### Method 1: Our Approach (Min-Max Normalization)
```
RSI_Percentile = (Current - Min) / (Max - Min) × 100
```
- **Pros**: Simple, intuitive, fast
- **Cons**: Sensitive to outliers

### Method 2: scipy.stats.percentileofscore
```python
from scipy.stats import percentileofscore
RSI_Percentile = percentileofscore(window_data, current_rsi)
```
- **Pros**: More statistically robust
- **Cons**: Slower, requires scipy dependency

### Why We Chose Method 1:
- Faster computation (no scipy dependency)
- Easier to understand
- Sufficient for our use case
- Consistent with other percentile indicators (ATR, Volume)

## Usage in Accumulation Analysis

Combine RSI_Percentile with other indicators:

```
Strong Accumulation Signal:
✓ RSI < 30 (oversold)
✓ RSI_Percentile < 20% (historically rare)
✓ RVOL_50 > 1.5 (high volume)
✓ Volume_Percentile > 80% (unusual volume)
✓ Price at BB_Lower (price extreme)

Result: High-probability accumulation zone
```

## Tuning the Window

Current: 252 days (1 year)

**Shorter window (126 days / 6 months):**
- More responsive to recent changes
- Better for volatile stocks
- May miss longer-term patterns

**Longer window (504 days / 2 years):**
- More stable
- Better for stable stocks
- May be slow to adapt

**Recommendation**: Keep 252 days for most stocks, adjust in `constants.py` if needed.

---

## Summary

RSI_Percentile answers the question:

> "Is this RSI level normal for this stock, or is it historically unusual?"

It transforms absolute RSI values into **relative context**, making it easier to identify truly exceptional opportunities.
