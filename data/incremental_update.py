"""
Incremental update system for the quantitative trading data pipeline.

This module implements an incremental update system that only downloads 
and stores new data since the last update, rather than re-downloading everything.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import logging
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IncrementalDataUpdater:
    """
    Class to handle incremental updates for price and fundamental data.
    """
    
    def __init__(self, db_path: str = "data/universe.db"):
        """
        Initialize the incremental updater.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.metadata_path = Path(db_path).parent / "pipeline_metadata.json"
        
        # Create database schema if it doesn't exist
        try:
            from data.db_schema import create_database_schema
        except ImportError:
            # Handle the case when run from the data directory
            import sys
            from pathlib import Path as LocalPath
            # Add parent directory to path
            parent_dir = LocalPath(__file__).parent.parent
            sys.path.insert(0, str(parent_dir))
            from data.db_schema import create_database_schema
        create_database_schema(self.db_path)
        
        # Initialize metadata
        self._init_metadata()
    
    def _init_metadata(self):
        """Initialize or load pipeline metadata."""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "last_update": {},
                "download_stats": {}
            }
    
    def save_metadata(self):
        """Save pipeline metadata to file."""
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def get_last_update_date(self, ticker: str, data_type: str) -> Optional[datetime.date]:
        """
        Get the last update date for a specific ticker and data type.
        
        Args:
            ticker: Ticker symbol
            data_type: Type of data ('price', 'fundamental', 'corporate_action')
            
        Returns:
            Last update date or None if not found
        """
        key = f"{ticker}_{data_type}"
        if key in self.metadata["last_update"]:
            date_str = self.metadata["last_update"][key]
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        return None
    
    def set_last_update_date(self, ticker: str, data_type: str, date: datetime.date):
        """
        Set the last update date for a specific ticker and data type.
        
        Args:
            ticker: Ticker symbol
            data_type: Type of data ('price', 'fundamental', 'corporate_action')
            date: Update date
        """
        key = f"{ticker}_{data_type}"
        self.metadata["last_update"][key] = date.strftime("%Y-%m-%d")
        self.save_metadata()
    
    def get_existing_price_dates(self, ticker: str) -> List[datetime.date]:
        """
        Get dates for which we already have price data for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            List of dates for which we already have price data
        """
        conn = sqlite3.connect(self.db_path)
        try:
            query = "SELECT DISTINCT date FROM prices WHERE ticker = ? ORDER BY date"
            cursor = conn.cursor()
            cursor.execute(query, (ticker,))
            rows = cursor.fetchall()
            return [datetime.strptime(row[0], "%Y-%m-%d").date() if isinstance(row[0], str) else row[0] for row in rows]
        except sqlite3.Error:
            # If table doesn't exist or is empty, return empty list
            return []
        finally:
            conn.close()
    
    def get_existing_fundamental_dates(self, ticker: str) -> List[datetime.date]:
        """
        Get dates for which we already have fundamental data for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            List of dates for which we already have fundamental data
        """
        conn = sqlite3.connect(self.db_path)
        try:
            query = "SELECT DISTINCT report_date FROM fundamentals WHERE ticker = ? ORDER BY report_date"
            cursor = conn.cursor()
            cursor.execute(query, (ticker,))
            rows = cursor.fetchall()
            return [datetime.strptime(row[0], "%Y-%m-%d").date() if isinstance(row[0], str) else row[0] for row in rows]
        except sqlite3.Error:
            # If table doesn't exist or is empty, return empty list
            return []
        finally:
            conn.close()
    
    def update_price_data(self, 
                         tickers: List[str], 
                         end_date: Optional[str] = None,
                         lookback_days: int = 30,
                         max_workers: int = 5) -> Dict[str, Union[pd.DataFrame, Exception]]:
        """
        Incrementally update price data for the given tickers.
        
        Args:
            tickers: List of ticker symbols to update
            end_date: End date in 'YYYY-MM-DD' format (defaults to today)
            lookback_days: Number of days to look back for updates
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary mapping ticker symbols to their newly downloaded price data or exception if failed
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=lookback_days)
        start_date = start_dt.strftime('%Y-%m-%d')
        
        results = {}
        
        # Import the price data functions
        from data.price_data import download_price_data, process_price_data, store_price_data
        
        for ticker in tickers:
            try:
                # Get existing dates for this ticker
                existing_dates = set(self.get_existing_price_dates(ticker))
                
                # Determine start date based on last update
                last_update = self.get_last_update_date(ticker, 'price')
                if last_update:
                    # Start from the day after the last update
                    incremental_start = last_update + timedelta(days=1)
                    start_date = max(datetime.strptime(start_date, '%Y-%m-%d').date(), incremental_start).strftime('%Y-%m-%d')
                
                # Download data for the period
                full_data_result = download_price_data([ticker], start_date, end_date, self.db_path)
                
                # Process the result
                ticker_data = full_data_result[ticker]
                if isinstance(ticker_data, pd.DataFrame) and not ticker_data.empty:
                    # Filter out dates we already have
                    new_data = ticker_data[~ticker_data['date'].isin(existing_dates)]
                    
                    # Store only new data
                    if not new_data.empty:
                        store_price_data(new_data, self.db_path)
                        results[ticker] = new_data
                        
                        # Update last update date
                        latest_date = new_data['date'].max()
                        self.set_last_update_date(ticker, 'price', latest_date)
                        
                        logger.info(f"Added {len(new_data)} new price records for {ticker}, latest date: {latest_date}")
                    else:
                        results[ticker] = pd.DataFrame()  # No new data
                        logger.info(f"No new price data for {ticker}")
                else:
                    results[ticker] = ticker_data  # Pass through the result (could be empty df or error)
                
            except Exception as e:
                logger.error(f"Error in incremental price update for {ticker}: {e}")
                results[ticker] = e
        
        return results
    
    def update_fundamental_data(self, 
                               tickers: List[str],
                               max_workers: int = 2) -> Dict[str, Union[Dict[str, pd.DataFrame], Exception]]:
        """
        Incrementally update fundamental data for the given tickers.
        
        Args:
            tickers: List of ticker symbols to update
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary mapping ticker symbols to their newly downloaded fundamental data or exception if failed
        """
        results = {}
        
        # Import the fundamental data functions
        from data.fundamental_data import download_fundamental_data, store_fundamental_data
        
        for ticker in tickers:
            try:
                # Get existing report dates for this ticker
                existing_dates = set(self.get_existing_fundamental_dates(ticker))
                
                # Download fundamental data for the ticker
                raw_data = download_fundamental_data([ticker], self.db_path)
                ticker_data = raw_data[ticker]
                
                if isinstance(ticker_data, dict):
                    # Process to keep only new data
                    new_data = {}
                    for stmt_type, df in ticker_data.items():
                        if not df.empty:
                            # Filter out dates we already have
                            new_df = df[~df['report_date'].isin(existing_dates)]
                            
                            if not new_df.empty:
                                # Store only new data
                                store_fundamental_data({stmt_type: new_df}, self.db_path)
                                new_data[stmt_type] = new_df
                    
                    results[ticker] = new_data
                    new_records_count = sum(len(df) for df in new_data.values())
                    
                    if new_records_count > 0:
                        # Update last update date to today
                        today = datetime.now().date()
                        self.set_last_update_date(ticker, 'fundamental', today)
                        logger.info(f"Added {new_records_count} new fundamental records for {ticker}")
                    else:
                        logger.info(f"No new fundamental data for {ticker}")
                else:
                    results[ticker] = ticker_data  # Pass through the error
                    
            except Exception as e:
                logger.error(f"Error in incremental fundamental update for {ticker}: {e}")
                results[ticker] = e
        
        return results
    
    def update_corporate_actions(self, 
                                 tickers: List[str],
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> Dict[str, Union[pd.DataFrame, Exception]]:
        """
        Incrementally update corporate actions data for the given tickers.
        
        Args:
            tickers: List of ticker symbols to update
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Dictionary mapping ticker symbols to their newly downloaded corporate actions data or exception if failed
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            # Default to 90 days back to catch recent corporate actions
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=90)
            start_date = start_dt.strftime('%Y-%m-%d')
        
        results = {}
        
        # Import the corporate actions function
        from data.fundamental_data import download_corporate_actions
        
        for ticker in tickers:
            try:
                # Download corporate actions
                ca_results = download_corporate_actions([ticker], start_date, end_date, self.db_path)
                ticker_ca = ca_results[ticker]
                
                if isinstance(ticker_ca, pd.DataFrame):
                    # Update last update date
                    today = datetime.now().date()
                    self.set_last_update_date(ticker, 'corporate_action', today)
                    
                    results[ticker] = ticker_ca
                    logger.info(f"Updated corporate actions for {ticker}: {len(ticker_ca)} records")
                else:
                    results[ticker] = ticker_ca  # Pass through the error
                    
            except Exception as e:
                logger.error(f"Error in incremental corporate actions update for {ticker}: {e}")
                results[ticker] = e
        
        return results
    
    def update_stock_metadata(self, tickers: List[str]):
        """
        Update stock metadata for the given tickers.
        
        Args:
            tickers: List of ticker symbols to update
        """
        from data.fundamental_data import collect_stock_metadata
        collect_stock_metadata(tickers, self.db_path)
        
        # Update last update date for all tickers
        today = datetime.now().date()
        for ticker in tickers:
            self.set_last_update_date(ticker, 'metadata', today)
        
        logger.info(f"Updated metadata for {len(tickers)} tickers")
    
    def run_full_update(self, 
                       tickers: List[str], 
                       update_prices: bool = True,
                       update_fundamentals: bool = True,
                       update_corporate_actions: bool = True,
                       update_metadata: bool = True,
                       end_date: Optional[str] = None) -> Dict[str, Dict]:
        """
        Run a full incremental update for all data types.
        
        Args:
            tickers: List of ticker symbols to update
            update_prices: Whether to update price data
            update_fundamentals: Whether to update fundamental data
            update_corporate_actions: Whether to update corporate actions
            update_metadata: Whether to update stock metadata
            end_date: End date for updates
            
        Returns:
            Dictionary with results for each data type
        """
        results = {
            'prices': {},
            'fundamentals': {},
            'corporate_actions': {},
            'metadata_updated': False
        }
        
        # Update price data
        if update_prices:
            logger.info("Starting price data update...")
            results['prices'] = self.update_price_data(tickers, end_date=end_date)
        
        # Update fundamental data
        if update_fundamentals:
            logger.info("Starting fundamental data update...")
            results['fundamentals'] = self.update_fundamental_data(tickers)
        
        # Update corporate actions
        if update_corporate_actions:
            logger.info("Starting corporate actions update...")
            results['corporate_actions'] = self.update_corporate_actions(tickers, end_date=end_date)
        
        # Update metadata
        if update_metadata:
            logger.info("Starting metadata update...")
            self.update_stock_metadata(tickers)
            results['metadata_updated'] = True
        
        logger.info("Full incremental update completed")
        return results


def run_incremental_update(tickers: List[str], 
                          db_path: str = "data/universe.db",
                          update_prices: bool = True,
                          update_fundamentals: bool = True,
                          update_corporate_actions: bool = True,
                          update_metadata: bool = True,
                          end_date: Optional[str] = None) -> Dict[str, Dict]:
    """
    Convenience function to run incremental updates.
    
    Args:
        tickers: List of ticker symbols to update
        db_path: Path to SQLite database
        update_prices: Whether to update price data
        update_fundamentals: Whether to update fundamental data
        update_corporate_actions: Whether to update corporate actions
        update_metadata: Whether to update stock metadata
        end_date: End date for updates
        
    Returns:
        Dictionary with results for each data type
    """
    updater = IncrementalDataUpdater(db_path)
    return updater.run_full_update(
        tickers, 
        update_prices, 
        update_fundamentals, 
        update_corporate_actions, 
        update_metadata, 
        end_date
    )


if __name__ == "__main__":
    # Example usage
    sample_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    
    print("Starting incremental data update...")
    
    # Initialize the updater
    updater = IncrementalDataUpdater()
    
    # Run a full update
    results = updater.run_full_update(
        tickers=sample_tickers,
        update_prices=True,
        update_fundamentals=True,
        update_corporate_actions=True,
        update_metadata=True
    )
    
    # Print summary
    print("\nUpdate Summary:")
    
    # Count price updates
    price_updates = 0
    for ticker, data in results['prices'].items():
        if isinstance(data, pd.DataFrame):
            price_updates += len(data)
    print(f"- Price records added: {price_updates}")
    
    # Count fundamental updates
    fundamental_updates = 0
    for ticker, data_dict in results['fundamentals'].items():
        if isinstance(data_dict, dict):
            for stmt_type, df in data_dict.items():
                if isinstance(df, pd.DataFrame):
                    fundamental_updates += len(df)
    print(f"- Fundamental records added: {fundamental_updates}")
    
    # Count corporate action updates
    ca_updates = 0
    for ticker, data in results['corporate_actions'].items():
        if isinstance(data, pd.DataFrame):
            ca_updates += len(data)
    print(f"- Corporate action records added: {ca_updates}")
    
    print("- Metadata updated" if results['metadata_updated'] else "- Metadata not updated")
    
    print("\nIncremental data update completed.")