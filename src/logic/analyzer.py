"""
Analyzer - Dip detection, dual RVOL calculation, and fixed-interval returns.

Implements the core earnings alpha analysis logic:
- Accumulation zone detection (lowest Low in T-10 to T-2)
- Dual RVOL (20-day tactical, 50-day strategic)
- RSI calculation
- Dynamic drawdown from reference high
- Fixed-interval returns (T+2, T+5, T+10, T+20)
"""

from datetime import datetime
from typing import Optional
import pandas as pd
import pandas_ta as ta


class Analyzer:
    """Analyzes earnings event data for accumulation zones and returns."""
    
    # RVOL thresholds
    RVOL_HIGH_PROBABILITY_THRESHOLD = 1.5
    
    # RSI period
    RSI_PERIOD = 14
    
    def __init__(self):
        """Initialize Analyzer."""
        pass
    
    def analyze_earnings_event(
        self,
        df: pd.DataFrame,
        windows: dict
    ) -> dict:
        """
        Perform complete earnings event analysis.
        
        Args:
            df: OHLCV DataFrame with buffered data
            windows: Analysis windows from EarningsData.get_analysis_windows()
            
        Returns:
            Dict with analysis results:
            {
                "accumulation_price": float,
                "accumulation_days": [{"date": ..., "low": ..., "rvol_20": ..., "rvol_50": ..., "rsi": ...}],
                "reference_high": {"price": float, "date": datetime},
                "max_drawdown_pct": float,
                "returns": {
                    "run_up": float,  # Accumulation -> T-1
                    "event": float,   # T-1 -> T+2
                    "profit_t2": float,
                    "profit_t5": float,
                    "profit_t10": float,
                    "profit_t20": float
                }
            }
        """
        # Calculate indicators
        df = self._calculate_indicators(df, windows)
        
        # Find accumulation zone
        accumulation_price, accumulation_days = self._find_accumulation_zone(df, windows)
        
        if accumulation_price is None:
            return self._empty_result()
        
        # Calculate reference high and drawdown
        reference_high = self._calculate_reference_high(df, windows, accumulation_days[0]['date'])
        max_drawdown_pct = self._calculate_drawdown(reference_high['price'], accumulation_price)
        
        # Calculate returns
        returns = self._calculate_returns(df, windows, accumulation_price)
        
        return {
            "accumulation_price": accumulation_price,
            "accumulation_days": accumulation_days,
            "reference_high": reference_high,
            "max_drawdown_pct": max_drawdown_pct,
            "returns": returns
        }
    
    def _calculate_indicators(self, df: pd.DataFrame, windows: dict) -> pd.DataFrame:
        """
        Calculate technical indicators: RVOL_20, RVOL_50, RSI.
        
        RVOL baselines end at T-11 to avoid contamination from pre-earnings volatility.
        """
        df = df.copy()
        
        # Get T-11 date for baseline cutoff
        earnings_date = windows['earnings_date']
        t_minus_11_idx = None
        
        for idx, row in df.iterrows():
            if row['date'].date() >= earnings_date.date():
                # Found earnings date, go back 11 trading days
                if idx >= 11:
                    t_minus_11_idx = idx - 11
                break
        
        # Calculate volume SMAs
        df['volume_sma_20'] = df['volume'].rolling(window=20, min_periods=20).mean()
        df['volume_sma_50'] = df['volume'].rolling(window=50, min_periods=50).mean()
        
        # For RVOL baseline, use SMA values up to T-11
        if t_minus_11_idx is not None:
            # Freeze baseline at T-11
            baseline_20 = df.loc[t_minus_11_idx, 'volume_sma_20']
            baseline_50 = df.loc[t_minus_11_idx, 'volume_sma_50']
            
            # Calculate RVOL using frozen baseline for dates after T-11
            df['rvol_20'] = df['volume'] / df['volume_sma_20']
            df['rvol_50'] = df['volume'] / df['volume_sma_50']
            
            # For accumulation window (T-10 to T-2), use the T-11 baseline
            for idx in range(t_minus_11_idx + 1, len(df)):
                if pd.notna(baseline_20) and baseline_20 > 0:
                    df.loc[idx, 'rvol_20'] = df.loc[idx, 'volume'] / baseline_20
                if pd.notna(baseline_50) and baseline_50 > 0:
                    df.loc[idx, 'rvol_50'] = df.loc[idx, 'volume'] / baseline_50
        else:
            # Fallback: use rolling SMA
            df['rvol_20'] = df['volume'] / df['volume_sma_20']
            df['rvol_50'] = df['volume'] / df['volume_sma_50']
        
        # Calculate RSI
        df['rsi'] = ta.rsi(df['close'], length=self.RSI_PERIOD)
        
        return df
    
    def _find_accumulation_zone(
        self,
        df: pd.DataFrame,
        windows: dict
    ) -> tuple[Optional[float], list[dict]]:
        """
        Find accumulation price and all accumulation days.
        
        Accumulation Price = Lowest Low in T-10 to T-2 window
        Accumulation Days = ALL days where Low equals Accumulation Price
        
        Returns:
            (accumulation_price, list of accumulation day dicts)
        """
        acc_start = windows['accumulation']['start']
        acc_end = windows['accumulation']['end']
        
        if acc_start is None or acc_end is None:
            return None, []
        
        # Filter to accumulation window
        mask = (df['date'].dt.date >= acc_start.date()) & (df['date'].dt.date <= acc_end.date())
        acc_window = df[mask].copy()
        
        if acc_window.empty:
            return None, []
        
        # Find lowest Low
        accumulation_price = acc_window['low'].min()
        
        # Find ALL days with this low
        acc_days_mask = acc_window['low'] == accumulation_price
        acc_days_df = acc_window[acc_days_mask]
        
        # Build accumulation days list
        accumulation_days = []
        earnings_date = windows['earnings_date']
        
        for _, row in acc_days_df.iterrows():
            days_before = self._calculate_trading_days_between(
                row['date'], earnings_date, df
            )
            
            accumulation_days.append({
                "date": row['date'],
                "low": row['low'],
                "rvol_20": row.get('rvol_20'),
                "rvol_50": row.get('rvol_50'),
                "rsi": row.get('rsi'),
                "days_before_earnings": days_before
            })
        
        return accumulation_price, accumulation_days
    
    def _calculate_reference_high(
        self,
        df: pd.DataFrame,
        windows: dict,
        accumulation_date: datetime
    ) -> dict:
        """
        Calculate reference high (highest High from T-20 to Dip-1).
        
        Dynamic calculation based on actual accumulation date.
        """
        obs_start = windows['observation']['start']
        
        if obs_start is None:
            return {"price": None, "date": None}
        
        # Filter from T-20 to day before accumulation
        mask = (
            (df['date'].dt.date >= obs_start.date()) &
            (df['date'].dt.date < accumulation_date.date())
        )
        ref_window = df[mask]
        
        if ref_window.empty:
            return {"price": None, "date": None}
        
        # Find highest High
        max_idx = ref_window['high'].idxmax()
        max_row = ref_window.loc[max_idx]
        
        return {
            "price": max_row['high'],
            "date": max_row['date']
        }
    
    def _calculate_drawdown(self, reference_high: float, accumulation_price: float) -> Optional[float]:
        """Calculate max drawdown percentage."""
        if reference_high is None or accumulation_price is None or reference_high == 0:
            return None
        
        drawdown_pct = ((accumulation_price - reference_high) / reference_high) * 100
        return drawdown_pct
    
    def _calculate_returns(
        self,
        df: pd.DataFrame,
        windows: dict,
        accumulation_price: float
    ) -> dict:
        """
        Calculate fixed-interval returns.
        
        Returns:
            - run_up: Accumulation Price -> T-1 Close
            - event: T-1 Close -> T+2 Close
            - profit_t2: Accumulation Price -> T+2 Close
            - profit_t5: Accumulation Price -> T+5 Close
            - profit_t10: Accumulation Price -> T+10 Close
            - profit_t20: Accumulation Price -> T+20 Close
        """
        returns = {
            "run_up": None,
            "event": None,
            "profit_t2": None,
            "profit_t5": None,
            "profit_t10": None,
            "profit_t20": None
        }
        
        # Get prices at key dates
        t_minus_1_price = self._get_close_price(df, windows['t_minus_1'])
        t_plus_2_price = self._get_close_price(df, windows['t_plus_2'])
        t_plus_5_price = self._get_close_price(df, windows['t_plus_5'])
        t_plus_10_price = self._get_close_price(df, windows['t_plus_10'])
        t_plus_20_price = self._get_close_price(df, windows['t_plus_20'])
        
        # Calculate returns
        if accumulation_price and t_minus_1_price:
            returns['run_up'] = ((t_minus_1_price - accumulation_price) / accumulation_price) * 100
        
        if t_minus_1_price and t_plus_2_price:
            returns['event'] = ((t_plus_2_price - t_minus_1_price) / t_minus_1_price) * 100
        
        if accumulation_price and t_plus_2_price:
            returns['profit_t2'] = ((t_plus_2_price - accumulation_price) / accumulation_price) * 100
        
        if accumulation_price and t_plus_5_price:
            returns['profit_t5'] = ((t_plus_5_price - accumulation_price) / accumulation_price) * 100
        
        if accumulation_price and t_plus_10_price:
            returns['profit_t10'] = ((t_plus_10_price - accumulation_price) / accumulation_price) * 100
        
        if accumulation_price and t_plus_20_price:
            returns['profit_t20'] = ((t_plus_20_price - accumulation_price) / accumulation_price) * 100
        
        return returns
    
    def _get_close_price(self, df: pd.DataFrame, target_date: Optional[datetime]) -> Optional[float]:
        """Get close price for a specific date."""
        if target_date is None:
            return None
        
        mask = df['date'].dt.date == target_date.date()
        matches = df[mask]
        
        if matches.empty:
            return None
        
        return matches.iloc[0]['close']
    
    def _calculate_trading_days_between(
        self,
        start_date: datetime,
        end_date: datetime,
        df: pd.DataFrame
    ) -> int:
        """Calculate number of trading days between two dates."""
        mask = (df['date'].dt.date >= start_date.date()) & (df['date'].dt.date < end_date.date())
        return len(df[mask])
    
    def _empty_result(self) -> dict:
        """Return empty result structure when analysis fails."""
        return {
            "accumulation_price": None,
            "accumulation_days": [],
            "reference_high": {"price": None, "date": None},
            "max_drawdown_pct": None,
            "returns": {
                "run_up": None,
                "event": None,
                "profit_t2": None,
                "profit_t5": None,
                "profit_t10": None,
                "profit_t20": None
            }
        }
