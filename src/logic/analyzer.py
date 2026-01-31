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

from src.config.constants import (
    RVOL_HIGH_PROBABILITY_THRESHOLD,
    RSI_PERIOD,
    RVOL_BASELINE_OFFSET
)


class Analyzer:
    """Analyzes earnings event data for accumulation zones and returns."""
    
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
        print("--- Analyzer Input ---")
        print("DataFrame columns:", df.columns.tolist())
        print("DataFrame head:\n", df.head())
        print("DataFrame info:")
        df.info()
        print("----------------------")
        
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
        Use pre-calculated indicators from DataFetcher and calculate RVOL.
        
        RVOL baselines end at T-11 to avoid contamination from pre-earnings volatility.
        Indicators (RSI, SMAs) are already calculated and cached by DataFetcher.
        """
        try:
            df = df.copy()
            
            # Get T-11 date for baseline cutoff
            earnings_date = windows['earnings_date']
            t_minus_11_idx = None
            
            for idx, row in df.iterrows():
                if row['date'].date() >= earnings_date.date():
                    # Found earnings date, go back 11 trading days
                    if idx >= abs(RVOL_BASELINE_OFFSET):
                        t_minus_11_idx = idx + RVOL_BASELINE_OFFSET  # RVOL_BASELINE_OFFSET is -11
                    break
            
            # Use pre-calculated volume SMAs from DataFetcher
            if 'Volume_SMA_20' not in df.columns or 'Volume_SMA_50' not in df.columns:
                # Fallback: calculate if not present (shouldn't happen)
                df['Volume_SMA_20'] = df['volume'].rolling(window=20, min_periods=20).mean()
                df['Volume_SMA_50'] = df['volume'].rolling(window=50, min_periods=50).mean()
            
            # Calculate RVOL using frozen baseline at T-11
            if t_minus_11_idx is not None:
                # Freeze baseline at T-11
                baseline_20 = df.loc[t_minus_11_idx, 'Volume_SMA_20']
                baseline_50 = df.loc[t_minus_11_idx, 'Volume_SMA_50']
                
                # Calculate RVOL using frozen baseline for dates after T-11
                df['rvol_20'] = df['volume'] / df['Volume_SMA_20']
                df['rvol_50'] = df['volume'] / df['Volume_SMA_50']
                
                # For accumulation window (T-10 to T-2), use the T-11 baseline
                for idx in range(t_minus_11_idx + 1, len(df)):
                    if pd.notna(baseline_20) and baseline_20 > 0:
                        df.loc[idx, 'rvol_20'] = df.loc[idx, 'volume'] / baseline_20
                    if pd.notna(baseline_50) and baseline_50 > 0:
                        df.loc[idx, 'rvol_50'] = df.loc[idx, 'volume'] / baseline_50
            else:
                # Fallback: use rolling SMA
                df['rvol_20'] = df['volume'] / df['Volume_SMA_20']
                df['rvol_50'] = df['volume'] / df['Volume_SMA_50']
            
            # Use pre-calculated RSI from DataFetcher
            if 'RSI_14' in df.columns:
                df['rsi'] = df['RSI_14']
            else:
                # Fallback: calculate if not present (shouldn't happen)
                df['rsi'] = ta.rsi(df['close'], length=RSI_PERIOD)
            
            # Use pre-calculated RSI Percentile
            if 'RSI_Percentile' in df.columns:
                df['rsi_percentile'] = df['RSI_Percentile']
            
            return df
        except KeyError as e:
            print(f"--- KeyError in _calculate_indicators ---")
            print(f"Missing column: {e}")
            print("Available columns:", df.columns.tolist())
            print("-----------------------------------------")
            raise
        except Exception as e:
            print(f"--- An unexpected error occurred in _calculate_indicators ---")
            print(f"Error: {e}")
            print("-----------------------------------------------------------")
            raise
    
    def _find_accumulation_zone(
        self,
        df: pd.DataFrame,
        windows: dict
    ) -> tuple[Optional[float], list[dict]]:
        """
        Find accumulation price and all accumulation days.
        
        Accumulation Price = Lowest Typical Price in T-10 to T-2 window
        Typical Price = (Low + High + Close) / 3
        Accumulation Days = ALL days where Typical Price equals Accumulation Price
        
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
        
        # Calculate typical price: (Low + High + Close) / 3
        acc_window['typical_price'] = (acc_window['low'] + acc_window['high'] + acc_window['close']) / 3
        
        # Find lowest Typical Price
        accumulation_price = acc_window['typical_price'].min()
        
        # Find ALL days with this typical price
        acc_days_mask = acc_window['typical_price'] == accumulation_price
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
                "high": row['high'],
                "close": row['close'],
                "typical_price": row['typical_price'],
                "rvol_20": row.get('rvol_20'),
                "rvol_50": row.get('rvol_50'),
                "rsi": row.get('rsi'),
                "rsi_percentile": row.get('rsi_percentile'),
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
        Calculate fixed-interval returns with multiple exit price methods.
        
        For each interval (T+0 to T+6), calculates returns using:
        - Close price (standard)
        - Low price (worst case scenario)
        - High price (best case scenario)
        - Typical price: (Low + High + Close) / 3 (average)
        
        Returns:
            - run_up: Accumulation Price -> T-1 Close
            - event: T-1 Close -> T+2 Close
            - profit_t0_close/low/high/typical: T+0 returns (earnings day)
            - profit_t1_close/low/high/typical: T+1 returns
            - profit_t2_close/low/high/typical: T+2 returns
            - profit_t3_close/low/high/typical: T+3 returns
            - profit_t4_close/low/high/typical: T+4 returns
            - profit_t5_close/low/high/typical: T+5 returns
            - profit_t6_close/low/high/typical: T+6 returns
        """
        returns = {
            "run_up": None,
            "event": None,
        }
        
        # Get prices at key dates
        t_minus_1_price = self._get_close_price(df, windows['t_minus_1'])
        
        # Calculate run-up and event returns
        if accumulation_price and t_minus_1_price:
            returns['run_up'] = ((t_minus_1_price - accumulation_price) / accumulation_price) * 100
        
        t_plus_2_price = self._get_close_price(df, windows['t_plus_2'])
        if t_minus_1_price and t_plus_2_price:
            returns['event'] = ((t_plus_2_price - t_minus_1_price) / t_minus_1_price) * 100
        
        # Calculate T+0 to T+6 returns with multiple price methods
        for day in range(0, 7):  # T+0 to T+6
            offset_date = windows.get(f't_plus_{day}')
            
            if offset_date and accumulation_price:
                # Get all price types for this day
                close_price = self._get_close_price(df, offset_date)
                low_price = self._get_low_price(df, offset_date)
                high_price = self._get_high_price(df, offset_date)
                
                # Calculate typical price: (Low + High + Close) / 3
                if low_price and high_price and close_price:
                    typical_price = (low_price + high_price + close_price) / 3
                else:
                    typical_price = None
                
                # Calculate returns for each price method
                if close_price:
                    returns[f'profit_t{day}_close'] = ((close_price - accumulation_price) / accumulation_price) * 100
                else:
                    returns[f'profit_t{day}_close'] = None
                
                if low_price:
                    returns[f'profit_t{day}_low'] = ((low_price - accumulation_price) / accumulation_price) * 100
                else:
                    returns[f'profit_t{day}_low'] = None
                
                if high_price:
                    returns[f'profit_t{day}_high'] = ((high_price - accumulation_price) / accumulation_price) * 100
                else:
                    returns[f'profit_t{day}_high'] = None
                
                if typical_price:
                    returns[f'profit_t{day}_typical'] = ((typical_price - accumulation_price) / accumulation_price) * 100
                else:
                    returns[f'profit_t{day}_typical'] = None
            else:
                # No data for this day
                returns[f'profit_t{day}_close'] = None
                returns[f'profit_t{day}_low'] = None
                returns[f'profit_t{day}_high'] = None
                returns[f'profit_t{day}_typical'] = None
        
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
    
    def _get_low_price(self, df: pd.DataFrame, target_date: Optional[datetime]) -> Optional[float]:
        """Get low price for a specific date."""
        if target_date is None:
            return None
        
        mask = df['date'].dt.date == target_date.date()
        matches = df[mask]
        
        if matches.empty:
            return None
        
        return matches.iloc[0]['low']
    
    def _get_high_price(self, df: pd.DataFrame, target_date: Optional[datetime]) -> Optional[float]:
        """Get high price for a specific date."""
        if target_date is None:
            return None
        
        mask = df['date'].dt.date == target_date.date()
        matches = df[mask]
        
        if matches.empty:
            return None
        
        return matches.iloc[0]['high']
    
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
        returns = {
            "run_up": None,
            "event": None,
        }
        
        # Add T+0 to T+6 returns with all price methods
        for day in range(0, 7):
            returns[f'profit_t{day}_close'] = None
            returns[f'profit_t{day}_low'] = None
            returns[f'profit_t{day}_high'] = None
            returns[f'profit_t{day}_typical'] = None
        
        return {
            "accumulation_price": None,
            "accumulation_days": [],
            "reference_high": {"price": None, "date": None},
            "max_drawdown_pct": None,
            "returns": returns
        }
