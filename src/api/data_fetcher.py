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

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kite_auth import KiteAuthenticator, load_api_config


class DataFetcher:
    """Fetches and caches OHLCV data from Kite Connect API."""
    
    # Buffer days before observation window for indicator initialization (50-day SMA, RSI)
    INDICATOR_BUFFER_DAYS = 100
    # Default history to fetch (covers multiple quarters)
    DEFAULT_HISTORY_DAYS = 365
    
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
            DataFrame with columns: date, open, high, low, close, volume
        """
        # Set default date range
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=self.DEFAULT_HISTORY_DAYS)
        
        # Load existing cache
        cached_df = self._load_cached_data(symbol)
        
        # Check if cache covers required range
        if not force_refresh and cached_df is not None and not cached_df.empty:
            cache_start = cached_df['date'].min()
            cache_end = cached_df['date'].max()
            
            # If cache covers the range, return cached data
            if cache_start.date() <= from_date.date() and cache_end.date() >= to_date.date():
                return self._filter_date_range(cached_df, from_date, to_date)
        
        # Fetch from API
        new_df = self._fetch_from_api(symbol, from_date, to_date)
        
        if new_df is None:
            # Return cached data if API fails
            if cached_df is not None:
                return self._filter_date_range(cached_df, from_date, to_date)
            return None
        
        # Merge with existing cache
        merged_df = self._merge_data(cached_df, new_df)
        
        # Save updated cache
        self._save_cached_data(symbol, merged_df)
        
        return self._filter_date_range(merged_df, from_date, to_date)
    
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
        buffer_start = analysis_start - timedelta(days=self.INDICATOR_BUFFER_DAYS + 50)
        return self.fetch_ohlcv(symbol, buffer_start, analysis_end)
    
    def get_trading_days(self, symbol: str) -> list[datetime]:
        print("get_trading_days : Symbol", symbol)
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
