"""
DataFetcher - Retrieves and caches OHLCV data from Kite Connect API.

Implements master file caching strategy: merges new data with existing cache
to build up history over time. Fetches 100+ day buffer for indicator initialization.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
import pandas_ta as ta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kite_auth import KiteAuthenticator, load_api_config
from src.config.constants import (
    INDICATOR_BUFFER_DAYS,
    DEFAULT_HISTORY_DAYS,
    REQUIRED_INDICATORS,
    RSI_PERIOD,
    RSI_PERCENTILE_WINDOW,
    SMA_SHORT_PERIOD,
    SMA_MEDIUM_PERIOD,
    SMA_LONG_PERIOD,
    SMA_MAJOR_PERIOD,
    VOLUME_SMA_SHORT_PERIOD,
    VOLUME_SMA_MEDIUM_PERIOD,
    ATR_PERIOD,
    ATR_PERCENTILE_WINDOW,
    BB_PERIOD,
    BB_STD_DEV,
    VOLUME_PERCENTILE_WINDOW
)


class DataFetcher:
    """Fetches and caches OHLCV data from Kite Connect API."""
    
    def __init__(
        self,
        config_path: str = "configs/stockSymbolDetails.json",
        cache_dir: str = "data"
    ):
        """
        Initialize DataFetcher.
        
        Args:
            config_path: Path to stockSymbolDetails.json
            cache_dir: Directory for cached OHLCV files
        """
        self.config_path = Path(config_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.stock_details: list[dict] = []
        self.instrument_tokens: dict[str, int] = {}
        self.kite = None
        
        self._load_configs()
    
    def _load_configs(self) -> None:
        """Load stock details from consolidated JSON."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Stock details config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.stock_details = json.load(f)
        
        # Build instrument_tokens dict
        for stock in self.stock_details:
            symbol = stock['symbol']
            token = stock.get('instrument_token')
            if token is not None:
                self.instrument_tokens[symbol] = token
    
    def _init_kite(self) -> bool:
        """Initialize Kite Connect client if not already done."""
        if self.kite is not None:
            return True
        
        try:
            api_key, api_secret = load_api_config()
            auth = KiteAuthenticator(api_key, api_secret)
            
            if not auth.is_authenticated():
                print("Kite Connect not authenticated. Please run kite_auth.py first.")
                return False
            
            self.kite = auth.kite
            return True
        except Exception as e:
            print(f"Error initializing Kite Connect: {e}")
            return False
    
    def get_all_symbols(self) -> list[str]:
        """Get list of all available stock symbols."""
        return [s["symbol"] for s in self.stock_details]
    
    def get_instrument_token(self, symbol: str) -> Optional[int]:
        """
        Get instrument token for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "POLYCAB")
            
        Returns:
            Instrument token or None if not found
        """
        token = self.instrument_tokens.get(symbol)
        if token is None:
            print(f"Instrument token not found for symbol: {symbol}")
        return token
    
    def _get_cache_path(self, symbol: str) -> Path:
        """Get cache file path for a symbol."""
        return self.cache_dir / f"{symbol}_ohlcv.json"
    
    def _load_cached_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load cached OHLCV data for a symbol."""
        cache_path = self._get_cache_path(symbol)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date').reset_index(drop=True)
        except Exception as e:
            print(f"Error loading cached data for {symbol}: {e}")
            return None
    
    def _save_cached_data(self, symbol: str, df: pd.DataFrame) -> None:
        """Save OHLCV data to cache."""
        cache_path = self._get_cache_path(symbol)
        
        # Convert datetime to string for JSON serialization
        data = df.copy()
        data['date'] = data['date'].dt.strftime('%Y-%m-%d')
        
        with open(cache_path, 'w') as f:
            json.dump(data.to_dict('records'), f, indent=2)
    
    def _merge_data(self, existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        """
        Merge new data with existing cached data.
        
        Uses append-only strategy: keeps all existing data and adds new dates.
        """
        if existing is None or existing.empty:
            return new
        
        if new is None or new.empty:
            return existing
        
        # Combine and remove duplicates (keep latest for each date)
        combined = pd.concat([existing, new], ignore_index=True)
        combined = combined.drop_duplicates(subset=['date'], keep='last')
        return combined.sort_values('date').reset_index(drop=True)
    
    def fetch_ohlcv(
        self,
        symbol: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for a symbol with master file caching.
        
        Args:
            symbol: Stock symbol
            from_date: Start date (defaults to 1 year ago)
            to_date: End date (defaults to today)
            force_refresh: If True, fetch from API even if cache exists
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, RSI_14
        """
        # Set default date range
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=DEFAULT_HISTORY_DAYS)
        
        # Load existing cache
        cached_df = self._load_cached_data(symbol)
        
        # Check if cache covers required range
        if not force_refresh and cached_df is not None and not cached_df.empty:
            cache_start = cached_df['date'].min()
            cache_end = cached_df['date'].max()
            
            # Check if cache covers date range and has all indicators
            has_all_indicators = all(col in cached_df.columns for col in REQUIRED_INDICATORS)
            
            if cache_start.date() <= from_date.date() and cache_end.date() >= to_date.date():
                if not has_all_indicators:
                    # Recalculate indicators if missing
                    cached_df = self._calculate_indicators(cached_df)
                    self._save_cached_data(symbol, cached_df)
                return self._filter_date_range(cached_df, from_date, to_date)
        
        # Fetch from API
        new_df = self._fetch_from_api(symbol, from_date, to_date)
        
        if new_df is None and cached_df is None:
            return None # No data available

        # Merge with existing cache
        merged_df = self._merge_data(cached_df, new_df)
        
        # Calculate indicators on the full dataset
        merged_df = self._calculate_indicators(merged_df)

        # Save updated cache
        self._save_cached_data(symbol, merged_df)
        
        return self._filter_date_range(merged_df, from_date, to_date)

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators and add them to the DataFrame.
        
        Calculates and caches:
        - RSI_14: 14-period Relative Strength Index
        - RSI_Percentile: Percentile rank of RSI vs 252-day history
        - ATR_14: 14-period Average True Range (volatility)
        - ATR_Percentile: Percentile rank of ATR vs 252-day history
        - BB_Lower, BB_Upper, BB_Width: Bollinger Bands (20-period, 2 std dev)
        - Volume_Percentile: Percentile rank of volume vs 252-day history
        - SMA_20, 50, 100, 200: Price moving averages
        - Volume_SMA_20, 50: Volume moving averages
        - Distance_SMA_50, 100, 200: Price distance from SMAs (%)
        """
        if df is None or df.empty:
            return df
        
        df = df.copy()
        
        # Ensure numeric types
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # ===== RSI Indicators =====
        df['RSI_14'] = ta.rsi(df['close'], length=RSI_PERIOD)
        df['RSI_Percentile'] = self._calculate_percentile(df['RSI_14'], RSI_PERCENTILE_WINDOW)
        
        # ===== ATR Indicators (Volatility) =====
        df['ATR_14'] = ta.atr(df['high'], df['low'], df['close'], length=ATR_PERIOD)
        df['ATR_Percentile'] = self._calculate_percentile(df['ATR_14'], ATR_PERCENTILE_WINDOW)
        
        # ===== Bollinger Bands =====
        bb = ta.bbands(df['close'], length=BB_PERIOD, std=BB_STD_DEV)
        df['BB_Lower'] = bb[f'BBL_{BB_PERIOD}_{BB_STD_DEV}']
        df['BB_Upper'] = bb[f'BBU_{BB_PERIOD}_{BB_STD_DEV}']
        bb_middle = bb[f'BBM_{BB_PERIOD}_{BB_STD_DEV}']
        df['BB_Width'] = ((df['BB_Upper'] - df['BB_Lower']) / bb_middle * 100)
        
        # ===== Volume Indicators =====
        df['Volume_Percentile'] = self._calculate_percentile(df['volume'], VOLUME_PERCENTILE_WINDOW)
        df['Volume_SMA_20'] = ta.sma(df['volume'], length=VOLUME_SMA_SHORT_PERIOD)
        df['Volume_SMA_50'] = ta.sma(df['volume'], length=VOLUME_SMA_MEDIUM_PERIOD)
        
        # ===== Price Moving Averages =====
        df['SMA_20'] = ta.sma(df['close'], length=SMA_SHORT_PERIOD)
        df['SMA_50'] = ta.sma(df['close'], length=SMA_MEDIUM_PERIOD)
        df['SMA_100'] = ta.sma(df['close'], length=SMA_LONG_PERIOD)
        df['SMA_200'] = ta.sma(df['close'], length=SMA_MAJOR_PERIOD)
        
        # ===== Price Distance from SMAs (%) =====
        df['Distance_SMA_50'] = ((df['close'] - df['SMA_50']) / df['SMA_50'] * 100)
        df['Distance_SMA_100'] = ((df['close'] - df['SMA_100']) / df['SMA_100'] * 100)
        df['Distance_SMA_200'] = ((df['close'] - df['SMA_200']) / df['SMA_200'] * 100)
        
        return df
    
    def _calculate_percentile(self, series: pd.Series, window: int) -> pd.Series:
        """
        Calculate percentile rank using rolling window.
        
        Formula: (Current_Value - Min_Value) / (Max_Value - Min_Value) * 100
        
        Args:
            series: Series of values
            window: Rolling window size (e.g., 252 trading days)
            
        Returns:
            Series of percentile values (0-100)
        """
        percentile = pd.Series(index=series.index, dtype=float)
        
        for i in range(len(series)):
            if pd.isna(series.iloc[i]):
                percentile.iloc[i] = None
                continue
            
            # Get window ending at current position
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
    
    def _fetch_from_api(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Kite Connect API."""
        if not self._init_kite():
            return None
        
        token = self.get_instrument_token(symbol)
        if token is None:
            return None
        
        try:
            # Kite Connect historical data API
            data = self.kite.historical_data(
                instrument_token=token,
                from_date=from_date,
                to_date=to_date,
                interval="day"
            )
            
            if not data:
                print(f"No data returned from API for {symbol}")
                return None
            
            df = pd.DataFrame(data)
            df = df.rename(columns={'date': 'date'})
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
            
            # Keep only required columns
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
            return df.sort_values('date').reset_index(drop=True)
            
        except Exception as e:
            print(f"Error fetching data from Kite API for {symbol}: {e}")
            return None
    
    def _filter_date_range(
        self,
        df: pd.DataFrame,
        from_date: datetime,
        to_date: datetime
    ) -> pd.DataFrame:
        """Filter DataFrame to specified date range."""
        mask = (df['date'].dt.date >= from_date.date()) & (df['date'].dt.date <= to_date.date())
        return df[mask].reset_index(drop=True)
    
    def fetch_with_buffer(
        self,
        symbol: str,
        analysis_start: datetime,
        analysis_end: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data with indicator buffer.
        
        Fetches 100+ days before analysis_start to ensure indicators
        (50-day SMA, RSI) can be calculated accurately.
        
        Args:
            symbol: Stock symbol
            analysis_start: Start of analysis window (e.g., T-20)
            analysis_end: End of analysis window (e.g., T+40)
            
        Returns:
            DataFrame with buffered data
        """
        buffer_start = analysis_start - timedelta(days=INDICATOR_BUFFER_DAYS + 50)
        return self.fetch_ohlcv(symbol, buffer_start, analysis_end)
    
    def get_trading_days(self, symbol: str) -> list[datetime]:
        """
        Get list of trading days from cached OHLCV data.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of trading day dates
        """
        df = self._load_cached_data(symbol)
        if df is None or df.empty:
            return []
        return df['date'].tolist()
    
    def get_available_indicators(self) -> dict:
        """
        Get list of available pre-calculated indicators.
        
        Returns:
            Dict with indicator names and descriptions
        """
        return {
            'RSI_14': '14-period Relative Strength Index (0-100)',
            'RSI_Percentile': 'RSI percentile vs 252-day history (0-100)',
            'ATR_14': '14-period Average True Range (volatility)',
            'ATR_Percentile': 'ATR percentile vs 252-day history (0-100)',
            'BB_Lower': 'Bollinger Band Lower (20-period, 2 std dev)',
            'BB_Upper': 'Bollinger Band Upper (20-period, 2 std dev)',
            'BB_Width': 'Bollinger Band Width (%)',
            'Volume_Percentile': 'Volume percentile vs 252-day history (0-100)',
            'SMA_20': '20-day Simple Moving Average (price)',
            'SMA_50': '50-day Simple Moving Average (price)',
            'SMA_100': '100-day Simple Moving Average (price)',
            'SMA_200': '200-day Simple Moving Average (price)',
            'Volume_SMA_20': '20-day Simple Moving Average (volume)',
            'Volume_SMA_50': '50-day Simple Moving Average (volume)',
            'Distance_SMA_50': 'Price distance from 50-day SMA (%)',
            'Distance_SMA_100': 'Price distance from 100-day SMA (%)',
            'Distance_SMA_200': 'Price distance from 200-day SMA (%)'
        }
