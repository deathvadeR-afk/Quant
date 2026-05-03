"""
Database schema for the quantitative trading system.

This module defines the SQLite database schema for storing:
1. Price data (OHLCV)
2. Fundamental data (financial statements, ratios)
3. Selected universe (500 companies)
"""

import sqlite3
from typing import Optional, List, Dict, Any
import pandas as pd


def create_database_schema(db_path: str) -> None:
    """
    Create the database tables for price and fundamental data.
    
    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create prices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)
    
    # Create fundamentals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT NOT NULL,
            report_date DATE NOT NULL,  -- Date when the data was reported
            period_end_date DATE NOT NULL,  -- Period the data represents (e.g., Q2 2023)
            metric TEXT NOT NULL,  -- Name of the metric (e.g., 'revenue', 'eps')
            value REAL,  -- Value of the metric
            currency TEXT,  -- Currency of the value
            source TEXT,  -- Source of the data
            PRIMARY KEY (ticker, report_date, metric)
        )
    """)
    
    # Create stock metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_metadata (
            ticker TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            industry TEXT,
            exchange TEXT,
            currency TEXT,
            market_cap REAL,
            share_class TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create selected_universe table for tracking the 500 selected companies
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS selected_universe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            company_name TEXT,
            sector TEXT,
            industry TEXT,
            market_cap REAL,
            selection_rank INTEGER,
            selection_date DATE NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_status TEXT DEFAULT 'pending',
            price_data_complete INTEGER DEFAULT 0,
            fundamental_data_complete INTEGER DEFAULT 0,
            last_updated TIMESTAMP
        )
    """)
    
    # Create corporate_actions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corporate_actions (
            ticker TEXT NOT NULL,
            ex_date DATE NOT NULL,  -- Date when the action takes effect
            action_type TEXT NOT NULL,  -- 'dividend', 'split', 'delisting'
            amount REAL,  -- For dividends or split ratio
            description TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, ex_date, action_type)
        )
    """)
    
    # Create indexes for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker_date ON fundamentals(ticker, report_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamentals_metric ON fundamentals(metric)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_corporate_actions_date ON corporate_actions(ex_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_selected_universe_ticker ON selected_universe(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_selected_universe_rank ON selected_universe(selection_rank)")
    
    conn.commit()
    conn.close()


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Get a connection to the database with row factory configured.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        Database connection with row factory set to return dict-like objects
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn


def save_selected_universe(df: pd.DataFrame, db_path: str) -> None:
    """
    Save the selected 500 companies to the selected_universe table.
    
    Args:
        df: DataFrame with columns: ticker, company_name, sector, industry, market_cap
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the selection date
    from datetime import datetime
    selection_date = datetime.now().strftime('%Y-%m-%d')
    
    # Clear existing universe and insert new one
    cursor.execute("DELETE FROM selected_universe")
    
    for rank, row in df.iterrows():
        cursor.execute("""
            INSERT INTO selected_universe 
            (ticker, company_name, sector, industry, market_cap, selection_rank, selection_date, data_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get('ticker', ''),
            row.get('company_name', row.get('ticker', '')),
            row.get('sector', ''),
            row.get('industry', ''),
            row.get('market_cap', None),
            rank + 1,  # 1-based ranking
            selection_date,
            'pending'
        ))
    
    conn.commit()
    conn.close()
    print(f"Saved {len(df)} companies to selected_universe table")


def get_selected_universe(db_path: str) -> pd.DataFrame:
    """
    Get the selected universe of companies from the database.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        DataFrame with the selected universe
    """
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM selected_universe ORDER BY selection_rank"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_selected_tickers(db_path: str) -> List[str]:
    """
    Get the list of ticker symbols for the selected universe.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        List of ticker symbols
    """
    conn = sqlite3.connect(db_path)
    query = "SELECT ticker FROM selected_universe ORDER BY selection_rank"
    cursor = conn.cursor()
    cursor.execute(query)
    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tickers


def update_company_data_status(
    ticker: str, 
    db_path: str,
    price_complete: bool = None,
    fundamental_complete: bool = None
) -> None:
    """
    Update the data status for a company in the selected universe.
    
    Args:
        ticker: Ticker symbol
        db_path: Path to the SQLite database file
        price_complete: Whether price data is complete
        fundamental_complete: Whether fundamental data is complete
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    updates = []
    if price_complete is not None:
        updates.append(f"price_data_complete = {1 if price_complete else 0}")
    if fundamental_complete is not None:
        updates.append(f"fundamental_data_complete = {1 if fundamental_complete else 0}")
    
    if updates:
        from datetime import datetime
        updates.append(f"last_updated = '{datetime.now().isoformat()}'")
        
        # Check if all data is complete
        if price_complete and fundamental_complete:
            updates.append("data_status = 'complete'")
        elif price_complete or fundamental_complete:
            updates.append("data_status = 'in_progress'")
        
        query = f"UPDATE selected_universe SET {', '.join(updates)} WHERE ticker = ?"
        cursor.execute(query, (ticker,))
        conn.commit()
    
    conn.close()


def get_universe_data_status(db_path: str) -> Dict:
    """
    Get the data download status for the entire universe.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        Dictionary with status counts
    """
    conn = sqlite3.connect(db_path)
    query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN data_status = 'complete' THEN 1 ELSE 0 END) as complete,
            SUM(CASE WHEN data_status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN data_status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN price_data_complete = 1 THEN 1 ELSE 0 END) as price_complete,
            SUM(CASE WHEN fundamental_data_complete = 1 THEN 1 ELSE 0 END) as fundamental_complete
        FROM selected_universe
    """
    cursor = conn.cursor()
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    
    return {
        'total': row[0] or 0,
        'complete': row[1] or 0,
        'in_progress': row[2] or 0,
        'pending': row[3] or 0,
        'price_complete': row[4] or 0,
        'fundamental_complete': row[5] or 0
    }


def get_portfolio_exposure(db_path: str) -> Dict[str, Any]:
    """
    Get portfolio sector and industry exposure breakdown.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        Dictionary with sector_exposure (list of sector records) and top_industries (list of industry records)
    """
    conn = sqlite3.connect(db_path)
    try:
        # Query sector exposure
        sector_query = """
            SELECT sector, COUNT(*) as count,
                   SUM(market_cap) as total_market_cap
            FROM selected_universe
            WHERE sector IS NOT NULL
            GROUP BY sector
            ORDER BY total_market_cap DESC
        """
        sector_df = pd.read_sql_query(sector_query, conn)
        
        # Query top 20 industries by count
        industry_query = """
            SELECT industry, COUNT(*) as count
            FROM selected_universe
            WHERE industry IS NOT NULL
            GROUP BY industry
            ORDER BY count DESC
            LIMIT 20
        """
        industry_df = pd.read_sql_query(industry_query, conn)
        
        return {
            "sector_exposure": sector_df.to_dict(orient="records") if not sector_df.empty else [],
            "top_industries": industry_df.to_dict(orient="records") if not industry_df.empty else [],
        }
    except Exception as e:
        return {"error": str(e), "sector_exposure": [], "top_industries": []}
    finally:
        conn.close()


if __name__ == "__main__":
    # Create the database schema in the default location
    import os
    from pathlib import Path
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    db_path = data_dir / "universe.db"
    create_database_schema(str(db_path))
    print(f"Database schema created at {db_path}")