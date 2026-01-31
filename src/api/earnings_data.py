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

from src.config.constants import (
    OBSERVATION_START_OFFSET,
    OBSERVATION_END_OFFSET,
    ACCUMULATION_START_OFFSET,
    ACCUMULATION_END_OFFSET
)


class EarningsData:
    """Manages earnings dates and analysis window calculations."""
    
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
            The date at the specified offset, or nearest available date if out of range
        """
        trading_days_sorted = sorted(trading_days)
        
        if not trading_days_sorted:
            return None
        
        # Find the index of earnings date or nearest trading day
        earnings_idx = self._find_nearest_trading_day_index(
            earnings_date, trading_days_sorted
        )
        
        if earnings_idx is None:
            return None
        
        target_idx = earnings_idx + offset
        
        # Clamp to available range instead of returning None
        if target_idx < 0:
            # Requested date is before available data, return earliest date
            return trading_days_sorted[0]
        elif target_idx >= len(trading_days_sorted):
            # Requested date is after available data, return latest date
            return trading_days_sorted[-1]
        else:
            return trading_days_sorted[target_idx]
    
    def _find_nearest_trading_day_index(
        self, 
        target_date: datetime, 
        trading_days: list[datetime]
    ) -> Optional[int]:
        """
        Find index of target date or nearest trading day.
        
        If target_date is not a trading day, returns the next available trading day.
        If target_date is before all trading days, returns 0.
        If target_date is after all trading days, returns last index.
        """
        if not trading_days:
            return None
        
        # If target is before all trading days, return first
        if target_date.date() < trading_days[0].date():
            return 0
        
        # If target is after all trading days, return last
        if target_date.date() > trading_days[-1].date():
            return len(trading_days) - 1
        
        # Find exact match or next trading day
        for i, td in enumerate(trading_days):
            if td.date() >= target_date.date():
                return i
        
        # Fallback to last index
        return len(trading_days) - 1
    
    def get_analysis_windows(
        self, 
        earnings_date: datetime, 
        trading_days: list[datetime]
    ) -> dict:
        """
        Calculate all analysis windows for an earnings event.
        
        Observation period: T-20 to current date (latest available trading day)
        
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
        # Get current date (latest trading day available)
        trading_days_sorted = sorted(trading_days)
        current_date = trading_days_sorted[-1] if trading_days_sorted else datetime.now()
        
        windows = {
            "earnings_date": earnings_date,
            "observation": {
                "start": self.get_trading_day_offset(earnings_date, OBSERVATION_START_OFFSET, trading_days),
                "end": current_date  # Use current date instead of T+40
            },
            "accumulation": {
                "start": self.get_trading_day_offset(earnings_date, ACCUMULATION_START_OFFSET, trading_days),
                "end": self.get_trading_day_offset(earnings_date, ACCUMULATION_END_OFFSET, trading_days)
            },
            "t_minus_1": self.get_trading_day_offset(earnings_date, -1, trading_days),
            "t_plus_0": self.get_trading_day_offset(earnings_date, 0, trading_days),
            "t_plus_1": self.get_trading_day_offset(earnings_date, 1, trading_days),
            "t_plus_2": self.get_trading_day_offset(earnings_date, 2, trading_days),
            "t_plus_3": self.get_trading_day_offset(earnings_date, 3, trading_days),
            "t_plus_4": self.get_trading_day_offset(earnings_date, 4, trading_days),
            "t_plus_5": self.get_trading_day_offset(earnings_date, 5, trading_days),
            "t_plus_6": self.get_trading_day_offset(earnings_date, 6, trading_days),
            "t_plus_10": self.get_trading_day_offset(earnings_date, 10, trading_days),
            "t_plus_20": self.get_trading_day_offset(earnings_date, 20, trading_days)
        }
        
        return windows
    
    def get_all_symbols(self) -> list[str]:
        """Get list of all symbols with earnings dates configured."""
        return list(self.earnings_dates.keys())
