"""
EarningsData - Manages earnings dates and analysis window calculations.

Handles multi-quarter earnings dates and calculates trading day offsets
using available OHLCV data as the trading calendar.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd


class EarningsData:
    """Manages earnings dates and analysis window calculations."""
    
    # Analysis window definitions (trading days relative to earnings date T)
    OBSERVATION_START = -20  # T-20
    OBSERVATION_END = 40     # T+40
    ACCUMULATION_START = -10 # T-10
    ACCUMULATION_END = -2    # T-2
    
    def __init__(self, config_path: str = "configs/stockSymbolDetails.json"):
        """
        Initialize EarningsData with stock symbol details.
        
        Args:
            config_path: Path to stockSymbolDetails.json
        """
        self.config_path = Path(config_path)
        self.stock_details: list[dict] = []
        self.earnings_dates: dict[str, list[str]] = {}
        self._load_stock_details()
    
    def _load_stock_details(self) -> None:
        """Load stock details from consolidated JSON config."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Stock details config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.stock_details = json.load(f)
        
        # Build earnings_dates dict for backward compatibility
        for stock in self.stock_details:
            symbol = stock['symbol']
            self.earnings_dates[symbol] = stock.get('earnings_dates', [])
    
    def get_earnings_dates(self, symbol: str) -> list[datetime]:
        """
        Get all earnings dates for a stock.
        
        Args:
            symbol: Stock symbol (e.g., "POLYCAB")
            
        Returns:
            List of earnings dates sorted descending (most recent first)
            
        Raises:
            ValueError: If symbol not found in config
        """
        if symbol not in self.earnings_dates:
            raise ValueError(f"No earnings dates found for symbol: {symbol}")
        
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in self.earnings_dates[symbol]]
        return sorted(dates, reverse=True)
    
    def get_available_quarters(self, symbol: str) -> list[str]:
        """
        Get list of available quarters for UI dropdown.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of quarter labels (e.g., ["Q3 FY25", "Q2 FY25", ...])
        """
        dates = self.get_earnings_dates(symbol)
        return [self._date_to_quarter_label(d) for d in dates]
    
    def _date_to_quarter_label(self, date: datetime) -> str:
        """
        Convert date to Indian FY quarter label.
        
        Indian FY: Apr-Mar
        Q1: Apr-Jun, Q2: Jul-Sep, Q3: Oct-Dec, Q4: Jan-Mar
        """
        month = date.month
        year = date.year
        
        if month in [4, 5, 6]:
            quarter = "Q1"
            fy = year + 1
        elif month in [7, 8, 9]:
            quarter = "Q2"
            fy = year + 1
        elif month in [10, 11, 12]:
            quarter = "Q3"
            fy = year + 1
        else:  # Jan, Feb, Mar
            quarter = "Q4"
            fy = year
        
        return f"{quarter} FY{str(fy)[-2:]}"
    
    def get_trading_day_offset(
        self, 
        earnings_date: datetime, 
        offset: int, 
        trading_days: list[datetime]
    ) -> Optional[datetime]:
        """
        Calculate T+N or T-N using trading days calendar.
        
        Args:
            earnings_date: The earnings announcement date (T)
            offset: Number of trading days (+ve for future, -ve for past)
            trading_days: List of valid trading days from OHLCV data
            
        Returns:
            The date at the specified offset, or None if out of range
        """
        trading_days_sorted = sorted(trading_days)
        
        # Find the index of earnings date or nearest trading day
        earnings_idx = self._find_nearest_trading_day_index(
            earnings_date, trading_days_sorted
        )
        
        if earnings_idx is None:
            return None
        
        target_idx = earnings_idx + offset
        
        if 0 <= target_idx < len(trading_days_sorted):
            return trading_days_sorted[target_idx]
        return None
    
    def _find_nearest_trading_day_index(
        self, 
        target_date: datetime, 
        trading_days: list[datetime]
    ) -> Optional[int]:
        """
        Find index of target date or nearest trading day.
        
        If target_date is not a trading day, returns the next trading day.
        """
        for i, td in enumerate(trading_days):
            if td.date() >= target_date.date():
                return i
        return None
    
    def get_analysis_windows(
        self, 
        earnings_date: datetime, 
        trading_days: list[datetime]
    ) -> dict:
        """
        Calculate all analysis windows for an earnings event.
        
        Args:
            earnings_date: The earnings announcement date (T)
            trading_days: List of valid trading days from OHLCV data
            
        Returns:
            Dict with window boundaries:
            {
                "observation": {"start": date, "end": date},
                "accumulation": {"start": date, "end": date},
                "earnings_date": date,
                "t_minus_1": date,
                "t_plus_2": date,
                "t_plus_5": date,
                "t_plus_10": date,
                "t_plus_20": date
            }
        """
        windows = {
            "earnings_date": earnings_date,
            "observation": {
                "start": self.get_trading_day_offset(earnings_date, self.OBSERVATION_START, trading_days),
                "end": self.get_trading_day_offset(earnings_date, self.OBSERVATION_END, trading_days)
            },
            "accumulation": {
                "start": self.get_trading_day_offset(earnings_date, self.ACCUMULATION_START, trading_days),
                "end": self.get_trading_day_offset(earnings_date, self.ACCUMULATION_END, trading_days)
            },
            "t_minus_1": self.get_trading_day_offset(earnings_date, -1, trading_days),
            "t_plus_2": self.get_trading_day_offset(earnings_date, 2, trading_days),
            "t_plus_5": self.get_trading_day_offset(earnings_date, 5, trading_days),
            "t_plus_10": self.get_trading_day_offset(earnings_date, 10, trading_days),
            "t_plus_20": self.get_trading_day_offset(earnings_date, 20, trading_days)
        }
        
        return windows
    
    def get_all_symbols(self) -> list[str]:
        """Get list of all symbols with earnings dates configured."""
        return list(self.earnings_dates.keys())
