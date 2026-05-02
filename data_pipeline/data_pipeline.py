"""
Main data pipeline module for the quantitative trading system.

This module orchestrates the entire data collection pipeline:
1. Creates database schema
2. Selects exactly 500 companies by market cap
3. Downloads price data with error handling for all 500 companies
4. Downloads fundamental data for all 500 companies
5. Updates data incrementally
6. Validates data quality
7. Provides summary reports
"""

import sys
from pathlib import Path
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import pandas as pd
import time

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

TARGET_UNIVERSE_SIZE = 500  # Exactly 500 companies
DEFAULT_START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')  # 5 years back
DEFAULT_END_DATE = datetime.now().strftime('%Y-%m-%d')
DB_PATH = "data/universe.db"


# =============================================================================
# Database Initialization
# =============================================================================

def initialize_database(db_path: str = DB_PATH):
    """
    Initialize the database with required schema.
    
    Args:
        db_path: Path to SQLite database
    """
    logger.info(f"Initializing database at {db_path}")
    
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
    
    logger.info("Database initialized successfully")


# =============================================================================
# Universe Selection
# =============================================================================

def select_universe(
    target_size: int = TARGET_UNIVERSE_SIZE,
    db_path: str = DB_PATH,
    save_to_db: bool = True
) -> pd.DataFrame:
    """
    Select exactly 500 companies by market capitalization.
    
    Args:
        target_size: Target number of companies (default: 500)
        db_path: Path to SQLite database
        save_to_db: Whether to save to the selected_universe table
    
    Returns:
        DataFrame with exactly target_size companies
    """
    logger.info(f"Selecting top {target_size} companies by market capitalization...")
    
    try:
        from data.universe_selection import (
            get_all_tickers, 
            calculate_liquidity, 
            filter_by_liquidity,
            UNIVERSE_CONFIG,
            get_static_ticker_list,
            get_sp500_tickers
        )
    except ImportError:
        # Handle import from parent directory
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.universe_selection import (
            get_all_tickers, 
            calculate_liquidity, 
            filter_by_liquidity,
            UNIVERSE_CONFIG,
            get_static_ticker_list,
            get_sp500_tickers
        )
    
    # Get comprehensive ticker list
    tickers = get_all_tickers()
    if len(tickers) < target_size:
        # Add more tickers from static list and S&P 500
        additional = get_static_ticker_list() + get_sp500_tickers()
        tickers = list(set(tickers + additional))
    
    logger.info(f"Starting with {len(tickers)} tickers for universe selection...")
    
    # Calculate liquidity metrics (includes market cap)
    metrics_df = calculate_liquidity(tickers)
    logger.info(f"Retrieved metrics for {len(metrics_df)} tickers")
    
    if metrics_df.empty:
        logger.error("No metrics retrieved. Cannot build universe.")
        return pd.DataFrame()
    
    # Filter and sort by market cap
    config = UNIVERSE_CONFIG.copy()
    config['target_universe_size'] = target_size
    config['selection_criteria'] = 'market_cap'
    
    universe_df = filter_by_liquidity(metrics_df, config)
    logger.info(f"Filtered universe: {len(universe_df)} stocks")
    
    # Ensure we have exactly target_size companies
    if len(universe_df) < target_size:
        logger.warning(f"Only {len(universe_df)} stocks meet criteria. Attempting to expand...")
        # Try to get more tickers
        additional_tickers = get_static_ticker_list()[:500]
        existing = set(universe_df['ticker'].tolist())
        new_tickers = [t for t in additional_tickers if t not in existing]
        
        if new_tickers:
            additional_metrics = calculate_liquidity(new_tickers)
            if not additional_metrics.empty:
                combined = pd.concat([metrics_df, additional_metrics], ignore_index=True)
                combined = combined.drop_duplicates(subset=['ticker'], keep='first')
                universe_df = filter_by_liquidity(combined, config)
                logger.info(f"Expanded to {len(universe_df)} stocks")
    
    # Limit to exactly target_size
    if len(universe_df) > target_size:
        universe_df = universe_df.head(target_size)
    
    # Add selection rank
    universe_df['selection_rank'] = range(1, len(universe_df) + 1)
    
    logger.info(f"Selected {len(universe_df)} companies by market cap")
    
    # Save to database
    if save_to_db:
        try:
            from data.db_schema import save_selected_universe
            save_selected_universe(universe_df, db_path)
            logger.info("Saved selected universe to database")
        except Exception as e:
            logger.error(f"Failed to save universe to database: {e}")
    
    return universe_df


def get_universe_from_db(db_path: str = DB_PATH) -> List[str]:
    """
    Get the list of ticker symbols from the selected universe in the database.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        List of ticker symbols (exactly 500 if available)
    """
    try:
        from data.db_schema import get_selected_tickers
        tickers = get_selected_tickers(db_path)
        return tickers if tickers else []
    except ImportError:
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.db_schema import get_selected_tickers
        tickers = get_selected_tickers(db_path)
        return tickers if tickers else []
    except Exception as e:
        logger.error(f"Database error getting universe: {e}")
        return []


# =============================================================================
# Price Data Download
# =============================================================================

def download_price_data_for_universe(
    tickers: List[str], 
    start_date: str, 
    end_date: str,
    db_path: str = DB_PATH,
    batch_size: int = 50,
    retry_failed: bool = True
) -> Dict[str, any]:
    """
    Download price data for the given universe of tickers with progress tracking.
    
    Args:
        tickers: List of ticker symbols to download
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        db_path: Path to SQLite database
        batch_size: Number of tickers to process in each batch
        retry_failed: Whether to retry failed downloads
    
    Returns:
        Dictionary with results and statistics
    """
    logger.info(f"Starting price data download for {len(tickers)} tickers: {start_date} to {end_date}")
    
    try:
        from data.price_data import download_price_data
    except ImportError:
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.price_data import download_price_data
    
    results = {}
    successful = 0
    failed = 0
    failed_tickers = []
    
    # Process in batches
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, len(tickers))
        batch = tickers[batch_start:batch_end]
        
        logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} tickers)...")
        
        try:
            batch_results = download_price_data(batch, start_date, end_date, db_path)
            
            for ticker, result in batch_results.items():
                if isinstance(result, Exception):
                    logger.error(f"Failed to download price data for {ticker}: {result}")
                    failed += 1
                    failed_tickers.append(ticker)
                    results[ticker] = {'status': 'failed', 'error': str(result)}
                elif hasattr(result, '__len__') and len(result) > 0:
                    logger.info(f"Downloaded {len(result)} price records for {ticker}")
                    successful += 1
                    results[ticker] = {'status': 'success', 'records': len(result)}
                    
                    # Update data status in database
                    try:
                        from data.db_schema import update_company_data_status
                        update_company_data_status(ticker, db_path, price_complete=True)
                    except:
                        pass
                else:
                    logger.warning(f"No data available for {ticker}")
                    successful += 1  # Count as success even if no data
                    results[ticker] = {'status': 'no_data', 'records': 0}
        
        except Exception as e:
            logger.error(f"Batch {batch_num + 1} failed: {e}")
        
        # Small delay between batches to avoid rate limiting
        time.sleep(1)
    
    # Retry failed tickers if enabled
    if retry_failed and failed_tickers:
        logger.info(f"Retrying {len(failed_tickers)} failed tickers...")
        retry_results = download_price_data(failed_tickers, start_date, end_date, db_path)
        
        for ticker, result in retry_results.items():
            if isinstance(result, Exception):
                logger.error(f"Retry failed for {ticker}: {result}")
            elif hasattr(result, '__len__') and len(result) > 0:
                logger.info(f"Retry successful: {len(result)} records for {ticker}")
                successful += 1
                failed -= 1
                results[ticker] = {'status': 'success', 'records': len(result), 'retry': True}
                
                # Update data status in database
                try:
                    from data.db_schema import update_company_data_status
                    update_company_data_status(ticker, db_path, price_complete=True)
                except:
                    pass
    
    logger.info(f"Price data download completed. Successful: {successful}, Failed: {failed}")
    
    return {
        'total': len(tickers),
        'successful': successful,
        'failed': failed,
        'results': results
    }


# =============================================================================
# Fundamental Data Download
# =============================================================================

def download_fundamental_data_for_universe(
    tickers: List[str],
    db_path: str = DB_PATH,
    batch_size: int = 20,
    retry_failed: bool = True
) -> Dict[str, any]:
    """
    Download fundamental data for the given universe of tickers with progress tracking.
    
    Args:
        tickers: List of ticker symbols to download fundamentals for
        db_path: Path to SQLite database
        batch_size: Number of tickers to process in each batch
        retry_failed: Whether to retry failed downloads
    
    Returns:
        Dictionary with results and statistics
    """
    logger.info(f"Starting fundamental data download for {len(tickers)} tickers")
    
    try:
        from data.fundamental_data import download_fundamental_data, collect_stock_metadata
    except ImportError:
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.fundamental_data import download_fundamental_data, collect_stock_metadata
    
    results = {}
    successful = 0
    failed = 0
    failed_tickers = []
    
    # Process in batches (smaller batch size for fundamentals due to API limits)
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, len(tickers))
        batch = tickers[batch_start:batch_end]
        
        logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} tickers)...")
        
        try:
            batch_results = download_fundamental_data(batch, db_path)
            
            for ticker, result in batch_results.items():
                if isinstance(result, Exception):
                    logger.error(f"Failed to download fundamental data for {ticker}: {result}")
                    failed += 1
                    failed_tickers.append(ticker)
                    results[ticker] = {'status': 'failed', 'error': str(result)}
                else:
                    logger.info(f"Downloaded fundamental data for {ticker}")
                    successful += 1
                    results[ticker] = {'status': 'success'}
                    
                    # Update data status in database
                    try:
                        from data.db_schema import update_company_data_status
                        update_company_data_status(ticker, db_path, fundamental_complete=True)
                    except:
                        pass
        
        except Exception as e:
            logger.error(f"Batch {batch_num + 1} failed: {e}")
        
        # Delay between batches to avoid rate limiting
        time.sleep(2)
    
    # Retry failed tickers if enabled
    if retry_failed and failed_tickers:
        logger.info(f"Retrying {len(failed_tickers)} failed tickers...")
        
        for ticker in failed_tickers:
            try:
                retry_result = download_fundamental_data([ticker], db_path)
                if ticker in retry_result and not isinstance(retry_result[ticker], Exception):
                    logger.info(f"Retry successful for {ticker}")
                    successful += 1
                    failed -= 1
                    results[ticker] = {'status': 'success', 'retry': True}
                    
                    # Update data status in database
                    try:
                        from data.db_schema import update_company_data_status
                        update_company_data_status(ticker, db_path, fundamental_complete=True)
                    except:
                        pass
            except Exception as e:
                logger.error(f"Retry failed for {ticker}: {e}")
    
    # Collect stock metadata
    logger.info("Collecting stock metadata...")
    try:
        collect_stock_metadata(tickers, db_path)
        logger.info("Stock metadata collection completed")
    except Exception as e:
        logger.error(f"Metadata collection failed: {e}")
    
    logger.info(f"Fundamental data download completed. Successful: {successful}, Failed: {failed}")
    
    return {
        'total': len(tickers),
        'successful': successful,
        'failed': failed,
        'results': results
    }


# =============================================================================
# Incremental Update
# =============================================================================

def run_incremental_update(
    tickers: List[str],
    db_path: str = DB_PATH,
    update_prices: bool = True,
    update_fundamentals: bool = True,
    update_corporate_actions: bool = True,
    update_metadata: bool = True
):
    """
    Run incremental update for the given tickers.
    
    Args:
        tickers: List of ticker symbols to update
        db_path: Path to SQLite database
        update_prices: Whether to update price data
        update_fundamentals: Whether to update fundamental data
        update_corporate_actions: Whether to update corporate actions
        update_metadata: Whether to update stock metadata
    """
    logger.info(f"Starting incremental update for {len(tickers)} tickers")
    
    try:
        from data.incremental_update import run_incremental_update as run_inc_update
    except ImportError:
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.incremental_update import run_incremental_update as run_inc_update
    
    results = run_inc_update(
        tickers,
        db_path,
        update_prices,
        update_fundamentals,
        update_corporate_actions,
        update_metadata
    )
    
    logger.info("Incremental update completed")
    return results


# =============================================================================
# Data Validation
# =============================================================================

def validate_data_quality(
    tickers: List[str],
    db_path: str = DB_PATH
):
    """
    Validate the quality of collected data.
    
    Args:
        tickers: List of ticker symbols to validate
        db_path: Path to SQLite database
    """
    logger.info(f"Starting data quality validation for {len(tickers)} tickers")
    
    try:
        from data.data_quality import run_data_validation_pipeline
    except ImportError:
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.data_quality import run_data_validation_pipeline
    
    results = run_data_validation_pipeline(tickers, db_path)
    
    quality_report = results['quality_report']
    summary = quality_report['summary']
    
    logger.info("Data Quality Report Summary:")
    logger.info(f"  - Total tickers analyzed: {summary['total_tickers']}")
    logger.info(f"  - Price data available: {summary['price_data_available']}")
    logger.info(f"  - Fundamental data available: {summary['fundamental_data_available']}")
    logger.info(f"  - Total price records: {summary['total_price_records']}")
    logger.info(f"  - Total fundamental records: {summary['total_fundamental_records']}")
    logger.info(f"  - Spikes detected: {summary['spikes_found']}")
    logger.info(f"  - Gaps detected: {summary['gaps_found']}")
    
    logger.info("Data quality validation completed")


# =============================================================================
# Summary Report
# =============================================================================

def generate_summary_report(db_path: str = DB_PATH) -> Dict:
    """
    Generate a summary report showing the status of the universe.
    
    Args:
        db_path: Path to SQLite database
    
    Returns:
        Dictionary with summary statistics
    """
    logger.info("Generating summary report...")
    
    try:
        from data.db_schema import get_universe_data_status, get_selected_universe
    except ImportError:
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.db_schema import get_universe_data_status, get_selected_universe
    
    # Get universe status
    status = get_universe_data_status(db_path)
    
    # Get universe details
    universe_df = get_selected_universe(db_path)
    
    # Get price data count
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count unique tickers with price data
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM prices")
    price_tickers = cursor.fetchone()[0]
    
    # Count total price records
    cursor.execute("SELECT COUNT(*) FROM prices")
    price_records = cursor.fetchone()[0]
    
    # Count unique tickers with fundamental data
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM fundamentals")
    fundamental_tickers = cursor.fetchone()[0]
    
    # Count total fundamental records
    cursor.execute("SELECT COUNT(*) FROM fundamentals")
    fundamental_records = cursor.fetchone()[0]
    
    conn.close()
    
    report = {
        'total_companies_in_universe': len(universe_df),
        'companies_with_price_data': price_tickers,
        'companies_with_fundamental_data': fundamental_tickers,
        'total_price_records': price_records,
        'total_fundamental_records': fundamental_records,
        'universe_status': status,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info("=" * 60)
    logger.info("SUMMARY REPORT")
    logger.info("=" * 60)
    logger.info(f"Total companies in universe: {report['total_companies_in_universe']}")
    logger.info(f"Companies with price data: {report['companies_with_price_data']}")
    logger.info(f"Companies with fundamental data: {report['companies_with_fundamental_data']}")
    logger.info(f"Total price records: {report['total_price_records']}")
    logger.info(f"Total fundamental records: {report['total_fundamental_records']}")
    logger.info(f"Universe complete: {status['complete']}/{status['total']}")
    logger.info(f"Price data complete: {status['price_complete']}/{status['total']}")
    logger.info(f"Fundamental data complete: {status['fundamental_complete']}/{status['total']}")
    logger.info("=" * 60)
    
    return report


# =============================================================================
# Complete Pipeline
# =============================================================================

def run_complete_pipeline(
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    db_path: str = DB_PATH,
    target_size: int = TARGET_UNIVERSE_SIZE,
    validate_data: bool = True
):
    """
    Run the complete data pipeline: initialize, select universe, download, update, validate.
    
    Args:
        start_date: Start date for initial download ('YYYY-MM-DD')
        end_date: End date for initial download ('YYYY-MM-DD')
        db_path: Path to SQLite database
        target_size: Target number of companies (default: 500)
        validate_data: Whether to run data validation
    """
    logger.info("=" * 60)
    logger.info("STARTING COMPLETE DATA PIPELINE FOR 500 COMPANIES")
    logger.info("=" * 60)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Target universe size: {target_size}")
    
    try:
        # 1. Initialize database
        initialize_database(db_path)
        
        # 2. Select exactly 500 companies by market cap
        universe_df = select_universe(target_size=target_size, db_path=db_path)
        
        if universe_df.empty:
            logger.error("Failed to select universe. Exiting.")
            return
        
        tickers = universe_df['ticker'].tolist()
        logger.info(f"Selected {len(tickers)} companies for processing")
        
        # 3. Download initial price data
        logger.info("Step 1/3: Downloading price data...")
        price_results = download_price_data_for_universe(tickers, start_date, end_date, db_path)
        
        # 4. Download fundamental data
        logger.info("Step 2/3: Downloading fundamental data...")
        fundamental_results = download_fundamental_data_for_universe(tickers, db_path)
        
        # 5. Run incremental update to catch any recent data
        logger.info("Step 3/3: Running incremental update...")
        run_incremental_update(tickers, db_path)
        
        # 6. Validate data quality
        if validate_data:
            validate_data_quality(tickers, db_path)
        
        # 7. Generate summary report
        report = generate_summary_report(db_path)
        
        logger.info("=" * 60)
        logger.info("DATA PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return report
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        logger.exception("Full traceback:")
        raise


def verify_universe(db_path: str = DB_PATH) -> Dict:
    """
    Verify that the database contains exactly 500 companies with complete data.
    
    Args:
        db_path: Path to SQLite database
    
    Returns:
        Dictionary with verification results
    """
    logger.info("Verifying universe...")
    
    try:
        from data.db_schema import get_selected_universe, get_universe_data_status
    except ImportError:
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from data.db_schema import get_selected_universe, get_universe_data_status
    
    # Get universe
    universe_df = get_selected_universe(db_path)
    status = get_universe_data_status(db_path)
    
    # Verify counts
    has_exactly_500 = len(universe_df) == 500
    all_price_complete = status['price_complete'] == 500
    all_fundamental_complete = status['fundamental_complete'] == 500
    all_complete = status['complete'] == 500
    
    verification = {
        'has_exactly_500_companies': has_exactly_500,
        'actual_company_count': len(universe_df),
        'target_count': 500,
        'all_price_data_complete': all_price_complete,
        'all_fundamental_data_complete': all_fundamental_complete,
        'all_data_complete': all_complete,
        'status': status
    }
    
    logger.info("=" * 60)
    logger.info("VERIFICATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Has exactly 500 companies: {has_exactly_500} ({len(universe_df)}/500)")
    logger.info(f"All price data complete: {all_price_complete} ({status['price_complete']}/500)")
    logger.info(f"All fundamental data complete: {all_fundamental_complete} ({status['fundamental_complete']}/500)")
    logger.info(f"All data complete: {all_complete} ({status['complete']}/500)")
    logger.info("=" * 60)
    
    return verification


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """
    Main entry point for the data pipeline.
    """
    parser = argparse.ArgumentParser(description='Quantitative Trading Data Pipeline for 500 Companies')
    parser.add_argument('--start-date', type=str, default=DEFAULT_START_DATE,
                        help='Start date for initial download (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=DEFAULT_END_DATE,
                        help='End date for initial download (YYYY-MM-DD)')
    parser.add_argument('--db-path', type=str, default=DB_PATH,
                        help='Path to SQLite database (default: data/universe.db)')
    parser.add_argument('--target-size', type=int, default=TARGET_UNIVERSE_SIZE,
                        help='Target number of companies (default: 500)')
    parser.add_argument('--no-validate', action='store_true',
                        help='Skip data validation step')
    parser.add_argument('--verify-only', action='store_true',
                        help='Only verify the universe without downloading')
    parser.add_argument('--select-only', action='store_true',
                        help='Only select universe without downloading data')
    
    args = parser.parse_args()
    
    if args.verify_only:
        # Only verify the universe
        verification = verify_universe(args.db_path)
        return
    
    if args.select_only:
        # Only select universe
        initialize_database(args.db_path)
        universe_df = select_universe(target_size=args.target_size, db_path=args.db_path)
        print(f"Selected {len(universe_df)} companies")
        return
    
    # Run complete pipeline
    run_complete_pipeline(
        start_date=args.start_date,
        end_date=args.end_date,
        db_path=args.db_path,
        target_size=args.target_size,
        validate_data=not args.no_validate
    )


if __name__ == "__main__":
    main()
