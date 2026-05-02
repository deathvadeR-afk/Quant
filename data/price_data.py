"""
Price data downloader module for the quantitative trading system.

This module downloads OHLCV data with error handling, handles delisted stocks,
adjusts for splits and dividends, and stores data in SQLite with proper indexing.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import logging
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import warnings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def download_price_data(
    tickers: List[str], 
    start_date: str, 
    end_date: str,
    db_path: str = "data/universe.db",
    retries: int = 3,
    delay: float = 1.0
) -> Dict[str, Union[pd.DataFrame, Exception]]:
    """
    Download OHLCV data with error handling.
    
    Handles delisted stocks (yfinance returns NaN), adjusts for splits and dividends,
    and stores in SQLite with proper indexing.
    
    Args:
        tickers: List of ticker symbols to download
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        db_path: Path to SQLite database
        retries: Number of retry attempts for failed downloads
        delay: Delay between retries in seconds
        
    Returns:
        Dictionary mapping ticker symbols to their price data or exception if failed
    """
    results = {}
    
    # Create data directory if it doesn't exist
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    for i, ticker in enumerate(tickers):
        logger.info(f"Downloading price data for {ticker} ({i+1}/{len(tickers)})...")
        
        # Retry mechanism for failed downloads
        for attempt in range(retries):
            try:
                # Download data using yfinance
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date, auto_adjust=False)
                
                # Check if data is empty (likely delisted stock)
                if hist.empty:
                    logger.warning(f"No price data found for {ticker}. Likely delisted.")
                    results[ticker] = pd.DataFrame()  # Return empty DataFrame for delisted stocks
                    break
                
                # Process the data to match our schema
                processed_data = process_price_data(hist, ticker)
                
                # Store in database
                store_price_data(processed_data, db_path)
                
                results[ticker] = processed_data
                logger.info(f"Successfully downloaded {len(processed_data)} records for {ticker}")
                break  # Success, exit retry loop
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {ticker}: {str(e)}")
                if attempt == retries - 1:  # Last attempt
                    logger.error(f"Failed to download data for {ticker} after {retries} attempts: {str(e)}")
                    results[ticker] = e
                else:
                    # Wait before retrying
                    import time
                    time.sleep(delay)
    
    return results


def process_price_data(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Process raw yfinance data to match our database schema.
    
    Args:
        df: Raw DataFrame from yfinance
        ticker: Ticker symbol
        
    Returns:
        Processed DataFrame ready for database storage
    """
    # Reset index to make date a column
    df = df.reset_index()
    
    # Rename columns to match our schema
    df = df.rename(columns={
        'Date': 'date',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Adj Close': 'adj_close',
        'Volume': 'volume'
    })
    
    # Add ticker column
    df['ticker'] = ticker
    
    # Ensure date is in the right format
    df['date'] = pd.to_datetime(df['date']).dt.date
    
    # Select only the columns we need
    df = df[['ticker', 'date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']]
    
    # Convert dtypes appropriately - use float64 for consistency
    # Int64 can cause issues with NaN in calculations
    df = df.astype({
        'ticker': 'string',
        'open': 'float64',
        'high': 'float64',
        'low': 'float64',
        'close': 'float64',
        'adj_close': 'float64',
        'volume': 'float64'  # Use float64 for consistency with NaN handling
    })
    
    return df


import threading

# Global lock for database writes to prevent race conditions
_db_write_lock = threading.Lock()

def store_price_data(df: pd.DataFrame, db_path: str) -> None:
    """
    Store price data in SQLite database.
    
    Args:
        df: DataFrame with price data
        db_path: Path to SQLite database
    """
    if df.empty:
        return  # Nothing to store
         
    # Create database schema if it doesn't exist
    try:
        from data.db_schema import create_database_schema
    except ImportError:
        # Handle the case when run from the data directory
        import sys
        from pathlib import Path
        # Add parent directory to path
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.db_schema import create_database_schema
    create_database_schema(db_path)
     
    # Use lock to prevent race conditions in multi-threaded agent system
    with _db_write_lock:
        # Connect to database
        conn = sqlite3.connect(db_path)
         
        try:
            # Filter out records that already exist in the database
            if not df.empty:
                # Create a temporary table to hold new records
                df_temp = df.copy()
                df_temp.to_sql('temp_prices', conn, if_exists='replace', index=False)
                 
                # Use INSERT OR IGNORE to avoid duplicate key errors
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO prices
                    SELECT * FROM temp_prices
                ''')
                 
                # Get the number of records actually inserted
                records_inserted = cursor.rowcount
                 
                # Drop the temporary table
                cursor.execute('DROP TABLE temp_prices')
                 
                logger.info(f"Attempted to store {len(df)} records for {df['ticker'].iloc[0]}, inserted {records_inserted} new records")
             
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error when storing price data: {e}")
            raise
        finally:
            conn.close()


def get_existing_price_dates(ticker: str, db_path: str) -> List[datetime.date]:
    """
    Get dates for which we already have price data for a ticker.
    
    Args:
        ticker: Ticker symbol
        db_path: Path to SQLite database
        
    Returns:
        List of dates for which we already have data
    """
    conn = sqlite3.connect(db_path)
    try:
        query = "SELECT DISTINCT date FROM prices WHERE ticker = ? ORDER BY date"
        cursor = conn.cursor()
        cursor.execute(query, (ticker,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error:
        # If table doesn't exist or is empty, return empty list
        return []
    finally:
        conn.close()


def download_incremental_price_data(
    tickers: List[str], 
    end_date: str,
    lookback_days: int = 365,
    db_path: str = "data/universe.db"
) -> Dict[str, Union[pd.DataFrame, Exception]]:
    """
    Download incremental price data for the given period.
    
    Args:
        tickers: List of ticker symbols to download
        end_date: End date in 'YYYY-MM-DD' format
        lookback_days: Number of days to look back for updates
        db_path: Path to SQLite database
        
    Returns:
        Dictionary mapping ticker symbols to their newly downloaded price data or exception if failed
    """
    # Calculate start date based on lookback
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_dt = end_dt - timedelta(days=lookback_days)
    start_date = start_dt.strftime('%Y-%m-%d')
    
    results = {}
    
    for ticker in tickers:
        try:
            # Get existing dates for this ticker
            existing_dates = set(get_existing_price_dates(ticker, db_path))
            
            # Download data for the period
            full_data = download_price_data([ticker], start_date, end_date, db_path)
            
            # Filter out dates we already have
            ticker_data = full_data[ticker]
            if isinstance(ticker_data, pd.DataFrame) and not ticker_data.empty:
                new_data = ticker_data[~ticker_data['date'].isin(existing_dates)]
                
                # Store only new data
                if not new_data.empty:
                    store_price_data(new_data, db_path)
                    results[ticker] = new_data
                    logger.info(f"Added {len(new_data)} new records for {ticker}")
                else:
                    results[ticker] = pd.DataFrame()  # No new data
                    logger.info(f"No new data for {ticker}")
            else:
                results[ticker] = ticker_data  # Pass through the result (could be empty df or error)
                
        except Exception as e:
            logger.error(f"Error in incremental download for {ticker}: {e}")
            results[ticker] = e
    
    return results


def validate_price_data(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Validate price data for common issues.
    
    Args:
        df: DataFrame with price data to validate
        
    Returns:
        Dictionary mapping validation issues to lists of affected tickers/dates
    """
    issues = {}
    
    if df.empty:
        return issues
    
    # Check for missing values
    missing_values = df[df.isnull().any(axis=1)]
    if not missing_values.empty:
        issues['missing_values'] = missing_values[['ticker', 'date']].apply(
            lambda x: f"{x['ticker']}:{x['date']}", axis=1
        ).tolist()
    
    # Check for negative prices or volumes
    negative_check_cols = ['open', 'high', 'low', 'close', 'adj_close']
    for col in negative_check_cols:
        if col in df.columns:
            negative_vals = df[df[col] < 0]
            if not negative_vals.empty:
                if 'negative_values' not in issues:
                    issues['negative_values'] = []
                issues['negative_values'].extend(
                    negative_vals[['ticker', 'date']].apply(
                        lambda x: f"{x['ticker']}:{x['date']} ({col}={x[col]})", axis=1
                    ).tolist()
                )
    
    # Check for volume < 0
    if 'volume' in df.columns:
        negative_volume = df[df['volume'] < 0]
        if not negative_volume.empty:
            if 'negative_values' not in issues:
                issues['negative_values'] = []
            issues['negative_values'].extend(
                negative_volume[['ticker', 'date']].apply(
                    lambda x: f"{x['ticker']}:{x['date']} (volume={x['volume']})", axis=1
                ).tolist()
            )
    
    # Check for OHLC inconsistencies (e.g., low > high)
    if all(col in df.columns for col in ['high', 'low']):
        invalid_ohlc = df[df['low'] > df['high']]
        if not invalid_ohlc.empty:
            issues['invalid_ohlc'] = invalid_ohlc[['ticker', 'date']].apply(
                lambda x: f"{x['ticker']}:{x['date']} (low>{x['high']})", axis=1
            ).tolist()
    
    return issues


if __name__ == "__main__":
    # Example usage
    # Download some sample data
    import sys
    from pathlib import Path
    
    # Add parent directory to path to handle imports
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    sample_tickers = ["AAPL", "MSFT", "GOOGL"]
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    print("Starting price data download...")
    results = download_price_data(sample_tickers, start_date, end_date)
    
    for ticker, result in results.items():
        if isinstance(result, pd.DataFrame):
            if not result.empty:
                print(f"Successfully downloaded {len(result)} records for {ticker}")
            else:
                print(f"No data available for {ticker}")
        else:
            print(f"Error downloading {ticker}: {result}")
    
    print("Price data download completed.")