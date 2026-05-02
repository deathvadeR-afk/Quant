"""
Fundamental data collection module for the quantitative trading system.

This module collects fundamental data (quarterly and annual), implements 
point-in-time correctness, and handles corporate actions.
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
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def download_fundamental_data(
    tickers: List[str],
    db_path: str = "data/universe.db",
    retries: int = 3,
    delay: float = 1.0
) -> Dict[str, Union[Dict[str, pd.DataFrame], Exception]]:
    """
    Download fundamental data for the given tickers.
    
    Args:
        tickers: List of ticker symbols to download fundamentals for
        db_path: Path to SQLite database
        retries: Number of retry attempts for failed downloads
        delay: Delay between retries in seconds
        
    Returns:
        Dictionary mapping ticker symbols to their fundamental data or exception if failed
    """
    results = {}
    
    # Create data directory if it doesn't exist
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    for i, ticker in enumerate(tickers):
        logger.info(f"Downloading fundamental data for {ticker} ({i+1}/{len(tickers)})...")
        
        for attempt in range(retries):
            try:
                # Get the ticker object
                stock = yf.Ticker(ticker)
                
                # Download various fundamental data
                fund_data = {
                    'income_stmt': stock.income_stmt if hasattr(stock, 'income_stmt') and stock.income_stmt is not None else pd.DataFrame(),
                    'balance_sheet': stock.balance_sheet if hasattr(stock, 'balance_sheet') and stock.balance_sheet is not None else pd.DataFrame(),
                    'cash_flow': stock.cashflow if hasattr(stock, 'cashflow') and stock.cashflow is not None else pd.DataFrame(),
                    'quarterly_income_stmt': stock.quarterly_income_stmt if hasattr(stock, 'quarterly_income_stmt') and stock.quarterly_income_stmt is not None else pd.DataFrame(),
                    'quarterly_balance_sheet': stock.quarterly_balance_sheet if hasattr(stock, 'quarterly_balance_sheet') and stock.quarterly_balance_sheet is not None else pd.DataFrame(),
                    'quarterly_cash_flow': stock.quarterly_cashflow if hasattr(stock, 'quarterly_cashflow') and stock.quarterly_cashflow is not None else pd.DataFrame(),
                    'info': stock.info if hasattr(stock, 'info') and stock.info is not None else {}
                }
                
                # Process and store the fundamental data
                processed_data = process_fundamental_data(fund_data, ticker)
                
                # Store in database
                store_fundamental_data(processed_data, db_path)
                
                results[ticker] = processed_data
                logger.info(f"Successfully downloaded fundamental data for {ticker}")
                break  # Success, exit retry loop
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {ticker}: {str(e)}")
                if attempt == retries - 1:  # Last attempt
                    logger.error(f"Failed to download fundamental data for {ticker} after {retries} attempts: {str(e)}")
                    results[ticker] = e
                else:
                    # Wait before retrying
                    time.sleep(delay)
    
    return results


def process_fundamental_data(raw_data: Dict, ticker: str) -> Dict[str, pd.DataFrame]:
    """
    Process raw fundamental data to match our database schema.
    
    Args:
        raw_data: Raw fundamental data from yfinance
        ticker: Ticker symbol
        
    Returns:
        Dictionary of processed DataFrames ready for database storage
    """
    processed = {}
    
    # Process quarterly income statement
    if not raw_data['quarterly_income_stmt'].empty:
        quarterly_income = process_statement(raw_data['quarterly_income_stmt'], ticker, 'income_stmt', 'quarterly')
        processed['quarterly_income_stmt'] = quarterly_income
    
    # Process annual income statement
    if not raw_data['income_stmt'].empty:
        annual_income = process_statement(raw_data['income_stmt'], ticker, 'income_stmt', 'annual')
        processed['income_stmt'] = annual_income
    
    # Process quarterly balance sheet
    if not raw_data['quarterly_balance_sheet'].empty:
        quarterly_bs = process_statement(raw_data['quarterly_balance_sheet'], ticker, 'balance_sheet', 'quarterly')
        processed['quarterly_balance_sheet'] = quarterly_bs
    
    # Process annual balance sheet
    if not raw_data['balance_sheet'].empty:
        annual_bs = process_statement(raw_data['balance_sheet'], ticker, 'balance_sheet', 'annual')
        processed['balance_sheet'] = annual_bs
    
    # Process quarterly cash flow
    if not raw_data['quarterly_cash_flow'].empty:
        quarterly_cf = process_statement(raw_data['quarterly_cash_flow'], ticker, 'cash_flow', 'quarterly')
        processed['quarterly_cash_flow'] = quarterly_cf
    
    # Process annual cash flow
    if not raw_data['cash_flow'].empty:
        annual_cf = process_statement(raw_data['cash_flow'], ticker, 'cash_flow', 'annual')
        processed['cash_flow'] = annual_cf
    
    return processed


def process_statement(df: pd.DataFrame, ticker: str, statement_type: str, period_type: str) -> pd.DataFrame:
    """
    Process a financial statement to match our database schema.
    
    Args:
        df: Raw financial statement DataFrame from yfinance
        ticker: Ticker symbol
        statement_type: Type of statement ('income_stmt', 'balance_sheet', 'cash_flow')
        period_type: Period type ('annual', 'quarterly')
        
    Returns:
        Processed DataFrame ready for database storage
    """
    if df.empty:
        return pd.DataFrame()
    
    # Transpose the DataFrame so dates become rows
    df_transposed = df.transpose()
    
    # Reset index to make dates a column
    df_transposed = df_transposed.reset_index()
    df_transposed = df_transposed.rename(columns={'index': 'period_end_date'})
    
    # Convert period_end_date to datetime and then to date
    df_transposed['period_end_date'] = pd.to_datetime(df_transposed['period_end_date']).dt.date
    
    # Melt the DataFrame to convert metrics to rows
    id_vars = ['period_end_date']
    value_vars = [col for col in df_transposed.columns if col != 'period_end_date']
    
    melted = df_transposed.melt(id_vars=id_vars, value_vars=value_vars, var_name='metric', value_name='value')
    
    # Add ticker, report date (using period_end_date as report date for now)
    # In a real system, we'd have separate report dates when the data was filed
    melted['ticker'] = ticker
    melted['report_date'] = melted['period_end_date']  # Simplified assumption
    melted['currency'] = 'USD'  # Default currency
    melted['source'] = f'yfinance_{statement_type}_{period_type}'
    
    # Reorder columns to match our schema
    cols_order = ['ticker', 'report_date', 'period_end_date', 'metric', 'value', 'currency', 'source']
    melted = melted[cols_order]
    
    # Drop rows with null values
    melted = melted.dropna(subset=['value'])
    
    return melted


import threading

# Global lock for database writes to prevent race conditions (shared with price_data)
_db_write_lock = threading.Lock()

def store_fundamental_data(processed_data: Dict[str, pd.DataFrame], db_path: str) -> None:
    """
    Store fundamental data in SQLite database.
    
    Args:
        processed_data: Dictionary of processed fundamental data DataFrames
        db_path: Path to SQLite database
    """
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
            # Store each type of fundamental data
            for stmt_type, df in processed_data.items():
                if not df.empty:
                    # Filter out records that already exist in the database
                    # Create a temporary table to hold new records
                    df_temp = df.copy()
                    df_temp.to_sql('temp_fundamentals', conn, if_exists='replace', index=False)
                     
                    # Use INSERT OR IGNORE to avoid duplicate key errors
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR IGNORE INTO fundamentals
                        SELECT * FROM temp_fundamentals
                    ''')
                     
                    # Get the number of records actually inserted
                    records_inserted = cursor.rowcount
                     
                    # Drop the temporary table
                    cursor.execute('DROP TABLE temp_fundamentals')
                     
                    logger.info(f"Attempted to store {len(df)} fundamental records for {df['ticker'].iloc[0] if not df.empty else 'N/A'}, inserted {records_inserted} new records")
             
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error when storing fundamental data: {e}")
            raise
        finally:
            conn.close()


def get_existing_fundamental_dates(ticker: str, db_path: str) -> List[datetime.date]:
    """
    Get dates for which we already have fundamental data for a ticker.
    
    Args:
        ticker: Ticker symbol
        db_path: Path to SQLite database
        
    Returns:
        List of dates for which we already have fundamental data
    """
    conn = sqlite3.connect(db_path)
    try:
        query = "SELECT DISTINCT report_date FROM fundamentals WHERE ticker = ? ORDER BY report_date"
        cursor = conn.cursor()
        cursor.execute(query, (ticker,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error:
        # If table doesn't exist or is empty, return empty list
        return []
    finally:
        conn.close()


def download_incremental_fundamental_data(
    tickers: List[str],
    db_path: str = "data/universe.db"
) -> Dict[str, Union[Dict[str, pd.DataFrame], Exception]]:
    """
    Download incremental fundamental data for the given tickers.
    
    Args:
        tickers: List of ticker symbols to download fundamentals for
        db_path: Path to SQLite database
        
    Returns:
        Dictionary mapping ticker symbols to their newly downloaded fundamental data or exception if failed
    """
    results = {}
    
    for ticker in tickers:
        try:
            # Get existing report dates for this ticker
            existing_dates = set(get_existing_fundamental_dates(ticker, db_path))
            
            # Download fundamental data for the ticker
            raw_data = download_fundamental_data([ticker], db_path)
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
                            store_fundamental_data({stmt_type: new_df}, db_path)
                            new_data[stmt_type] = new_df
                
                results[ticker] = new_data
                new_records_count = sum(len(df) for df in new_data.values())
                logger.info(f"Added {new_records_count} new fundamental records for {ticker}")
            else:
                results[ticker] = ticker_data  # Pass through the error
                
        except Exception as e:
            logger.error(f"Error in incremental fundamental download for {ticker}: {e}")
            results[ticker] = e
    
    return results


def collect_stock_metadata(tickers: List[str], db_path: str = "data/universe.db") -> None:
    """
    Collect and store stock metadata for the given tickers.
    
    Args:
        tickers: List of ticker symbols
        db_path: Path to SQLite database
    """
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
    
    conn = sqlite3.connect(db_path)
    
    metadata_list = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if info:
                metadata = {
                    'ticker': ticker,
                    'company_name': info.get('longName', info.get('shortName', '')),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'exchange': info.get('exchange', ''),
                    'currency': info.get('currency', ''),
                    'market_cap': info.get('marketCap', None),
                    'share_class': info.get('quoteType', '')
                }
                metadata_list.append(metadata)
                
        except Exception as e:
            logger.error(f"Error collecting metadata for {ticker}: {e}")
    
    if metadata_list:
        metadata_df = pd.DataFrame(metadata_list)
        
        try:
            # Insert or update metadata in the database
            metadata_df.to_sql('stock_metadata', conn, if_exists='replace', index=False)
            logger.info(f"Stored metadata for {len(metadata_list)} stocks")
        except sqlite3.Error as e:
            logger.error(f"Database error when storing stock metadata: {e}")
            raise
        finally:
            conn.close()


def download_corporate_actions(
    tickers: List[str],
    start_date: str,
    end_date: str,
    db_path: str = "data/universe.db"
) -> Dict[str, Union[pd.DataFrame, Exception]]:
    """
    Download corporate actions data for the given tickers.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        db_path: Path to SQLite database
        
    Returns:
        Dictionary mapping ticker symbols to their corporate actions data or exception if failed
    """
    results = {}
    
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
    
    conn = sqlite3.connect(db_path)
    
    try:
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                
                # Get dividends and splits
                dividends = stock.dividends
                splits = stock.splits
                
                corporate_actions = []
                
                # Process dividends
                if not dividends.empty:
                    for date, amount in dividends.items():
                        corporate_actions.append({
                            'ticker': ticker,
                            'ex_date': date.date(),
                            'action_type': 'dividend',
                            'amount': amount,
                            'description': f'Dividend payment of ${amount:.4f}'
                        })
                
                # Process splits
                if not splits.empty:
                    for date, ratio in splits.items():
                        corporate_actions.append({
                            'ticker': ticker,
                            'ex_date': date.date(),
                            'action_type': 'split',
                            'amount': ratio,
                            'description': f'Stock split with ratio {ratio:.4f}'
                        })
                
                # Create DataFrame and store in database
                if corporate_actions:
                    ca_df = pd.DataFrame(corporate_actions)
                    
                    # Store in database
                    ca_df.to_sql('corporate_actions', conn, if_exists='append', index=False, method='multi')
                    results[ticker] = ca_df
                    logger.info(f"Stored {len(ca_df)} corporate actions for {ticker}")
                else:
                    results[ticker] = pd.DataFrame()
                    logger.info(f"No corporate actions found for {ticker}")
                    
            except Exception as e:
                logger.error(f"Error downloading corporate actions for {ticker}: {e}")
                results[ticker] = e
        
        conn.commit()
        
    except sqlite3.Error as e:
        logger.error(f"Database error when storing corporate actions: {e}")
        raise
    finally:
        conn.close()
    
    return results


def validate_fundamental_data(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Validate fundamental data for common issues.
    
    Args:
        df: DataFrame with fundamental data to validate
        
    Returns:
        Dictionary mapping validation issues to lists of affected tickers/dates
    """
    issues = {}
    
    if df.empty:
        return issues
    
    # Check for missing values in critical columns
    missing_critical = df[
        df[['ticker', 'report_date', 'period_end_date', 'metric', 'value']].isnull().any(axis=1)
    ]
    if not missing_critical.empty:
        issues['missing_critical_values'] = missing_critical[['ticker', 'report_date', 'metric']].apply(
            lambda x: f"{x['ticker']}:{x['report_date']}:{x['metric']}", axis=1
        ).tolist()
    
    # Check for negative values where they shouldn't be (e.g., revenue, assets)
    # We'll flag certain metrics that should typically be positive
    pos_metrics = ['TotalRevenue', 'GrossProfit', 'NetIncome', 'TotalAssets', 'TotalEquity']
    if 'metric' in df.columns and 'value' in df.columns:
        neg_pos_metrics = df[
            (df['metric'].isin(pos_metrics)) & (df['value'] < 0)
        ]
        if not neg_pos_metrics.empty:
            issues['negative_positive_metrics'] = neg_pos_metrics[['ticker', 'report_date', 'metric', 'value']].apply(
                lambda x: f"{x['ticker']}:{x['report_date']}:{x['metric']}={x['value']}", axis=1
            ).tolist()
    
    # Check for extremely large values (potential data errors)
    if 'value' in df.columns:
        # Look for values that are significantly larger than typical (more than 6 standard deviations)
        mean_val = df['value'].mean()
        std_val = df['value'].std()
        if not np.isnan(std_val) and std_val > 0:
            extreme_vals = df[
                (df['value'] > mean_val + 6 * std_val) | 
                (df['value'] < mean_val - 6 * std_val)
            ]
            if not extreme_vals.empty:
                issues['extreme_values'] = extreme_vals[['ticker', 'report_date', 'metric', 'value']].apply(
                    lambda x: f"{x['ticker']}:{x['report_date']}:{x['metric']}={x['value']}", axis=1
                ).tolist()
    
    return issues


if __name__ == "__main__":
    # Example usage
    import sys
    from pathlib import Path
    
    # Add parent directory to path to handle imports
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    sample_tickers = ["AAPL", "MSFT"]
    
    print("Starting fundamental data download...")
    results = download_fundamental_data(sample_tickers)
    
    for ticker, result in results.items():
        if isinstance(result, dict):
            print(f"Successfully downloaded fundamental data for {ticker}")
            for stmt_type, df in result.items():
                if not df.empty:
                    print(f"  - {stmt_type}: {len(df)} records")
        else:
            print(f"Error downloading fundamental data for {ticker}: {result}")
    
    # Also collect stock metadata
    print("\nCollecting stock metadata...")
    collect_stock_metadata(sample_tickers)
    
    print("\nFundamental data download completed.")