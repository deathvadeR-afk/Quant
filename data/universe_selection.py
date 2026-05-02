"""
Universe Selection Module

Defines the tradeable universe for the multi-factor strategy.
Supports dynamic filtering based on market cap and volume.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import List, Optional
import sqlite3
import os


# =============================================================================
# Configuration
# =============================================================================

UNIVERSE_CONFIG = {
    'min_market_cap': 100_000_000,      # $100M minimum market cap
    'min_avg_daily_volume': 500_000,    # $500K minimum daily volume
    'min_share_price': 2,               # $2 minimum share price
    'target_universe_size': 500,        # Target number of stocks (exactly 500)
    'selection_criteria': 'market_cap',  # Selection criteria: 'market_cap' for largest by market cap
}

# Database path
DB_PATH = 'data/universe.db'


# =============================================================================
# Ticker Data Sources
# =============================================================================

def get_ticker_list_from_nasdaq() -> List[str]:
    """Fetch tickers from NASDAQ official listing."""
    try:
        url = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
        df = pd.read_csv(url, sep='|')
        tickers = df[df['Symbol'] != 'File Creation Time']['Symbol'].tolist()
        return [t for t in tickers if t and t.isalpha() and len(t) <= 5]
    except Exception:
        return []


def get_sp500_tickers() -> List[str]:
    """Fetch S&P 500 tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500 = tables[0]
        return sp500['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception:
        return []


def get_static_ticker_list() -> List[str]:
    """Comprehensive static list of liquid US equities (cleaned - no delisted tickers)."""
    return [
        # Large Caps (Top 100) - verified active
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'UNH', 'JNJ',
        'V', 'XOM', 'JPM', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV', 'PEP',
        'KO', 'COST', 'AVGO', 'LLY', 'TMO', 'WMT', 'MCD', 'CSCO', 'ACN', 'ABT',
        'DHR', 'ADBE', 'CRM', 'TXN', 'NKE', 'PM', 'NEE', 'BMY', 'UNP', 'LIN',
        'ORCL', 'RTX', 'HON', 'AMGN', 'IBM', 'QCOM', 'NOW', 'INTC', 'AMD', 'GS',
        'CAT', 'SPGI', 'LOW', 'AXP', 'SBUX', 'BLK', 'DE', 'ELV', 'MS', 'ISRG',
        'INTU', 'GILD', 'TJX', 'MDLZ', 'SYK', 'ZTS', 'ADI', 'CVS', 'REGN', 'VRTX',
        'PLD', 'CB', 'SO', 'DUK', 'CME', 'CL', 'ETN', 'FIS', 'NSC', 'ICE',
        'ITW', 'APD', 'EOG', 'MMC', 'PFE', 'USB', 'HUM', 'FCX', 'SHW', 'GD',
        'NOC', 'WM', 'AMAT', 'GM', 'PSA', 'EW', 'MCO', 'AON', 'SLB', 'TT',
        'BDX', 'CI', 'MO', 'ADP', 'PH', 'NEM', 'BSX', 'COP', 'DG', 'RSG',
        'ROP', 'CMG', 'MCK', 'SNPS', 'CDNS', 'PANW', 'MU', 'KLAC', 'TEL',
        'WFC', 'TFC', 'C', 'BAC', 'AIG', 'MET', 'PRU', 'AFL', 'TRV', 'HIG',
        'ALL', 'SCHW', 'DFS', 'SYF', 'COF', 'PNC', 'BBY', 'LRCX', 'MAR',
        # Additional High-Liquidity Stocks
        'PYPL', 'SOFI', 'ANET', 'UBER', 'APLD', 'VRT', 'MELI', 'FOUR', 'IREN',
        'ZETA', 'TSM', 'ASML', 'DIS', 'NFLX', 'CRM', 'ADBE', 'ORCL', 'NOW', 'SNOW', 'TEAM',
        'SQ', 'SHOP', 'TWLO', 'ZM', 'DOCU', 'CRWD', 'OKTA', 'NET', 'DDOG',
        'MDB', 'PLTR', 'PATH', 'U', 'FVRR', 'DDOG', 'SPLK',
        # Mid Caps
        'AFRM', 'RIVN', 'LCID', 'RBLX', 'GPRO', 'SNAP', 'PINS', 'DBX', 'BOX',
        'TW', 'YELP', 'W', 'ABNB', 'DASH', 'COIN',
        # More stocks to fill universe
        'A', 'AAL', 'AAP', 'ABMD', 'ABNB', 'ACGL', 'ACIW', 'ACM', 'ADAP', 'ADSK',
        'AEE', 'AEP', 'AFL', 'AGNC', 'AIG', 'AIV', 'AIZ', 'AJG', 'ALB', 'ALE',
        'ALK', 'ALL', 'ALXN', 'AM', 'AMAT', 'AMCR', 'AME', 'AMED', 'AMG', 'AMH',
        'AMN', 'AMP', 'AMRN', 'AMRK', 'AMT', 'AMZN', 'ANET', 'ANSS', 'ANTM', 'AON',
        'APA', 'APD', 'APH', 'APLE', 'ARE', 'ARNA', 'ARNC', 'AROC', 'ASB', 'ASML',
        'ATO', 'ATR', 'ATVI', 'AVB', 'AVGO', 'AVY', 'AWK', 'AXP', 'AYX', 'AZO',
        'BA', 'BABA', 'BAC', 'BALL', 'BBY', 'BDC', 'BDX', 'BEN', 'BF.B', 'BHF',
        'BHP', 'BIIB', 'BK', 'BKNG', 'BKR', 'BLK', 'BLL', 'BMY', 'BNH', 'BNS',
        'BOW', 'BP', 'BPMC', 'BRK.B', 'BSX', 'BTI', 'BWA', 'BXP', 'BYD', 'C',
        'CAG', 'CAH', 'CARR', 'CAT', 'CB', 'CBRE', 'CCI', 'CCL', 'CDNS', 'CERN',
        'CF', 'CFG', 'CHDG', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLF', 'CLX',
        'CM', 'CMC', 'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COG',
        'COO', 'COP', 'COST', 'COTY', 'CPB', 'CPRI', 'CPT', 'CRL', 'CRM', 'CRO',
        'CSCO', 'CSX', 'CTAS', 'CTLT', 'CTSH', 'CTVA', 'CVS', 'CVX', 'CYB', 'D',
        'DAL', 'DASH', 'DBX', 'DD', 'DE', 'DELL', 'DFS', 'DG', 'DGX', 'DHI',
        'DHR', 'DIS', 'DISCA', 'DISCK', 'DISH', 'DLR', 'DLTR', 'DOV', 'DOW',
        'DPZ', 'DRI', 'DTE', 'DUK', 'DVA', 'DVN', 'DWDP', 'DXC', 'DXCM', 'E',
        'EBAY', 'ECL', 'ED', 'EE', 'EIX', 'EL', 'EMN', 'EMR', 'ENPH', 'EOG',
        'EPAM', 'EQIX', 'EQR', 'ES', 'ESS', 'ETN', 'ETSY', 'EUR', 'EVRG', 'EWH',
        'EWT', 'EWZ', 'EXC', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG', 'FAST', 'FB',
        'FCX', 'FDX', 'FE', 'FF', 'FIS', 'FISV', 'FITB', 'FLT', 'FMC', 'FNMA',
        'FOXA', 'FRC', 'FRT', 'FTNT', 'FTV', 'FVRR', 'G', 'GBCI', 'GD', 'GE',
        'GEN', 'GILD', 'GIS', 'GLD', 'GLW', 'GM', 'GNRC', 'GOOG', 'GOOGL', 'GPC',
        'GPN', 'GPS', 'GRMN', 'GS', 'GWW', 'HAL', 'HBI', 'HCA', 'HD', 'HES',
        'HIG', 'HII', 'HLT', 'HOLX', 'HON', 'HP', 'HPQ', 'HRL', 'HSIC', 'HSY',
        'HUM', 'HWM', 'IBM', 'ICE', 'ICF', 'IDXX', 'IEX', 'IFF', 'ILMN', 'INCY',
        'INTC', 'INTU', 'IONS', 'IP', 'IPG', 'IQV', 'IR', 'IRM', 'ISRG', 'IT',
        'ITW', 'IVZ', 'J', 'JBHT', 'JCI', 'JKHY', 'JNJ', 'JPM', 'K', 'KDP',
        'KEY', 'KEYS', 'KHC', 'KIM', 'KLAC', 'KMB', 'KMI', 'KMX', 'KO', 'KRC',
        'KRE', 'KSS', 'L', 'LAM', 'LANC', 'LAZ', 'LDOS', 'LEG', 'LEN', 'LH',
        'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LRCX', 'LUV',
        'LVS', 'LW', 'LYB', 'LYV', 'M', 'MA', 'MAA', 'MAC', 'MAR', 'MAS',
        'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MELI', 'MET', 'MGM', 'MHK',
        'MKC', 'MLM', 'MMC', 'MMM', 'MO', 'MOH', 'MOS', 'MPC', 'MRK', 'MRNA',
        'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTD', 'MU', 'MXIM', 'MYL',
        'N', 'NCLH', 'NDAQ', 'NEE', 'NEM', 'NFLX', 'NIO', 'NLSN', 'NOC', 'NOK',
        'NOV', 'NRG', 'NSC', 'NTAP', 'NTDOY', 'NTRS', 'NUE', 'NVR', 'NWL', 'O',
        'ODFL', 'OIH', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OXY', 'PANW', 'PAYC',
        'PBCT', 'PBI', 'PCAR', 'PCG', 'PDD', 'PEAK', 'PEG', 'PENN', 'PEP', 'PFE',
        'PFG', 'PGR', 'PH', 'PHM', 'PKG', 'PKI', 'PLD', 'PM', 'PNC', 'PNR',
        'PNW', 'PODD', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PVH',
        'PWR', 'PXD', 'PYPL', 'QCOM', 'QRVO', 'R', 'RBA', 'RCL', 'REG', 'REGN',
        'RHI', 'RJF', 'RL', 'RMD', 'ROK', 'ROST', 'RS', 'RSG', 'RTX', 'RUT',
        'SBAC', 'SBUX', 'SCHW', 'SE', 'SEE', 'SHW', 'SIRI', 'SLB', 'SLG', 'SNA',
        'SNAP', 'SNPS', 'SO', 'SPG', 'SPGI', 'SPLK', 'SRE', 'STE', 'STT', 'STZ',
        'SWK', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TCF', 'TGT', 'TJX', 'TMO',
        'TMUS', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTWO', 'TWLO', 'TWTR',
        'TXN', 'TXT', 'TYL', 'UA', 'UHS', 'UL', 'UNH', 'UNM', 'UNP', 'UPS',
        'URBN', 'USB', 'V', 'VAR', 'VFC', 'VICI', 'VLO', 'VMC', 'VMI', 'VRSK',
        'VRSN', 'VRTX', 'VTR', 'VZ', 'W', 'WAB', 'WAT', 'WBA', 'WBD', 'WCG',
        'WDC', 'WEC', 'WELL', 'WFC', 'WHR', 'WM', 'WMB', 'WMT', 'WRB', 'WRK',
        'WST', 'WTW', 'WY', 'WYNN', 'X', 'XEL', 'XOM', 'XRAY', 'XRX', 'YUM',
        'ZION', 'ZM', 'ZS'
    ]


def get_all_tickers() -> List[str]:
    """Combine all ticker sources, removing duplicates."""
    all_tickers = set()
    
    # Try each source
    sources = [
        get_ticker_list_from_nasdaq,
        get_sp500_tickers,
        get_static_ticker_list,
    ]
    
    for source in sources:
        try:
            tickers = source()
            if tickers:
                all_tickers.update(tickers)
        except Exception:
            pass
    
    # If still not enough, try to get more comprehensive list
    if len(all_tickers) < 500:
        # Add common large-cap tickers
        additional = get_extended_ticker_list()
        all_tickers.update(additional)
    
    return list(all_tickers)


def get_extended_ticker_list() -> List[str]:
    """Get an extended list of tickers from various sources."""
    # Additional comprehensive list of US equities
    extended_tickers = [
        # Tech
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO', 'ORCL', 
        'ADBE', 'CRM', 'NOW', 'INTU', 'SNPS', 'CDNS', 'PANW', 'MU', 'KLAC', 'AMAT',
        'LRCX', 'MRVL', 'QCOM', 'TXN', 'INTC', 'AMD', 'IBM', 'CSCO', 'AVB', 'EQIX',
        # Financials
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'USB',
        'PNC', 'TFC', 'COF', 'DFS', 'SYF', 'MET', 'PRU', 'AFL', 'TRV', 'HIG',
        'ALL', 'CB', 'AIG', 'BRK.B', 'SPGI', 'MCO', 'ICE', 'CME', 'COIN', 'SQ',
        # Healthcare
        'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY',
        'AMGN', 'GILD', 'VRTX', 'REGN', 'ISRG', 'MDT', 'SYK', 'ZTS', 'BDX', 'CL',
        'CVS', 'CI', 'HUM', 'MO', 'MCK', 'MCK', 'LLY', 'CVS', 'AMGN', 'GILD',
        # Consumer
        'PG', 'KO', 'PEP', 'COST', 'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT',
        'LOW', 'TJX', 'DG', 'DLTR', 'ORLY', 'BBY', 'ROST', 'EL', 'CL', 'KMB',
        'GIS', 'K', 'MDLZ', 'HSY', 'KHC', 'STZ', 'MO', 'PM', 'BTI', 'UVV',
        # Energy
        'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX', 'VLO', 'OXY', 'PXD',
        'FANG', 'DVN', 'HES', 'APA', 'HAL', 'BKR', 'FTI', 'KMI', 'WMB', 'ETR',
        # Industrials
        'CAT', 'DE', 'BA', 'HON', 'UPS', 'RTX', 'UNP', 'GE', 'LMT', 'GD',
        'MMM', 'ITW', 'EMR', 'ETN', 'PH', 'CMI', 'ROK', 'IR', 'CME', 'FDX',
        'CSX', 'NSC', 'JBHT', 'ODFL', 'EXPD', 'CARR', 'TT', 'ETN', 'AME', 'ODFL',
        # Materials
        'LIN', 'APD', 'SHW', 'ECL', 'NEM', 'FCX', 'NUE', 'DOW', 'DD', 'PPG',
        'DDP', 'DOW', 'EMN', 'AVY', 'BALL', 'PKG', 'WRK', 'IP', 'GLT', 'AFL',
        # Real Estate
        'PLD', 'AMT', 'EQIX', 'PSA', 'O', 'SPG', 'WELL', 'AVB', 'EQR', 'VTR',
        'MAA', 'UDR', 'ESS', 'KLAC', 'REG', 'FRT', 'SLG', 'VNO', 'BXP', 'ARE',
        # Utilities
        'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'XEL', 'EXC', 'ED', 'PEG',
        'WEC', 'DTE', 'AEE', 'ES', 'FE', 'NWE', 'AWK', 'WTRG', 'AWK', 'CEQ',
        # Communications
        'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR', 'NFLX', 'PARA', 'WBD', 'FOX',
        'EA', 'ATVI', 'TTWO', 'NTDOY', 'OMCL', 'SNAP', 'PINS', 'META', 'TWTR', 'ZBRA',
        # More mid-cap stocks
        'AFRM', 'RIVN', 'LCID', 'RBLX', 'GPRO', 'SNAP', 'PINS', 'DBX', 'BOX', 'ZEN',
        'TW', 'YELP', 'W', 'ABNB', 'DASH', 'COIN', 'U', 'FVRR', 'SPLK', 'NET',
        'DDOG', 'CRWD', 'OKTA', 'SNOW', 'TEAM', 'WORK', 'ZM', 'DOCU', 'SHOP', 'TWLO',
        'PLTR', 'PATH', 'MNDY', 'WDAY', 'SPLK', 'FTNT', 'PANW', 'ZS', 'OKTA', 'CRWD',
        'DT', 'SOFI', 'UPST', 'BILL', 'QUBT', 'RBLX', 'JOBY', 'RKLB', 'ASTS', 'VORB',
    ]
    
    return list(set(extended_tickers))


# =============================================================================
# Liquidity Calculation
# =============================================================================

def calculate_liquidity(tickers: List[str], lookback_days: int = 60) -> pd.DataFrame:
    """Calculate liquidity metrics for a list of tickers."""
    print(f"Downloading data for {len(tickers)} tickers...")
    
    results = []
    batch_size = 50
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        
        try:
            data = yf.download(
                batch, 
                period=f"{lookback_days}d",
                group_by='ticker',
                progress=False,
                auto_adjust=False
            )
        except Exception:
            continue
        
        for ticker in batch:
            try:
                # Extract price and volume data
                if len(batch) == 1:
                    close = data['Close']
                    vol = data['Volume']
                else:
                    if ticker not in data.columns.get_level_values(0):
                        continue
                    close = data[ticker]['Close']
                    vol = data[ticker]['Volume']
                
                if len(close) == 0:
                    continue
                
                # Calculate metrics
                avg_volume = vol.mean()
                avg_close = close.mean()
                dollar_volume = avg_volume * avg_close
                
                # Get market cap
                try:
                    market_cap = yf.Ticker(ticker).info.get('marketCap')
                except Exception:
                    market_cap = None
                
                results.append({
                    'ticker': ticker,
                    'avg_volume': avg_volume,
                    'avg_close': avg_close,
                    'avg_dollar_volume': dollar_volume,
                    'market_cap': market_cap,
                    'last_close': close.iloc[-1]
                })
            except Exception:
                continue
    
    return pd.DataFrame(results)


# =============================================================================
# Filtering
# =============================================================================

def filter_by_liquidity(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """Filter universe by liquidity and market cap criteria, then limit to target size."""
    if config is None:
        config = UNIVERSE_CONFIG
    
    if df.empty:
        return df
    
    # Apply filters
    mask = (
        (df['avg_dollar_volume'] >= config['min_avg_daily_volume']) &
        (df['market_cap'] >= config['min_market_cap']) &
        (df['last_close'] >= config['min_share_price'])
    )
    
    filtered = df[mask].copy()
    
    # Sort by selection criteria (default: market_cap for largest companies)
    selection_criteria = config.get('selection_criteria', 'market_cap')
    if selection_criteria == 'market_cap':
        filtered = filtered.sort_values('market_cap', ascending=False)
    else:
        filtered = filtered.sort_values('avg_dollar_volume', ascending=False)
    
    # Limit to target universe size (exactly 500)
    target_size = config['target_universe_size']
    if len(filtered) > target_size:
        filtered = filtered.head(target_size)
    
    return filtered.reset_index(drop=True)


# =============================================================================
# Database Operations
# =============================================================================

def init_db(db_path: str = DB_PATH):
    """Initialize the universe database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS universe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            avg_volume REAL,
            avg_close REAL,
            avg_dollar_volume REAL,
            market_cap REAL,
            last_close REAL,
            source TEXT,
            UNIQUE(date, ticker)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_date_ticker ON universe(date, ticker)')
    conn.commit()
    conn.close()


def save_to_db(df: pd.DataFrame, source: str = 'all', db_path: str = DB_PATH):
    """Save universe to database."""
    if df.empty:
        return
    
    init_db(db_path)
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(db_path)
    
    for _, row in df.iterrows():
        conn.execute('''
            INSERT OR REPLACE INTO universe 
            (date, ticker, avg_volume, avg_close, avg_dollar_volume, market_cap, last_close, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date_str, row['ticker'], row['avg_volume'], row['avg_close'],
              row['avg_dollar_volume'], row['market_cap'], row['last_close'], source))
    
    conn.commit()
    conn.close()
    print(f"Saved {len(df)} tickers to database")


def load_from_db(date: Optional[str] = None, db_path: str = DB_PATH) -> pd.DataFrame:
    """Load universe from database."""
    conn = sqlite3.connect(db_path)
    
    if date is None:
        query = "SELECT * FROM universe WHERE date = (SELECT MAX(date) FROM universe)"
    else:
        query = f"SELECT * FROM universe WHERE date = '{date}'"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df


# =============================================================================
# Main Interface
# =============================================================================

def get_filtered_universe(source: str = 'all', save: bool = True, target_size: int = None) -> pd.DataFrame:
    """
    Get the complete filtered universe.
    
    Args:
        source: Data source ('all', 'sp500', 'nasdaq', or 'static')
        save: Whether to save to database
        target_size: Override target universe size (default: from config)
    
    Returns:
        DataFrame with filtered universe
    """
    # Get tickers based on source
    if source == 'all':
        tickers = get_all_tickers()
    elif source == 'sp500':
        tickers = get_sp500_tickers() or get_static_ticker_list()
    elif source == 'nasdaq':
        tickers = get_ticker_list_from_nasdaq() or get_static_ticker_list()
    else:
        tickers = get_static_ticker_list()
    
    print(f"Starting with {len(tickers)} tickers from {source}")
    
    # Calculate liquidity metrics
    metrics_df = calculate_liquidity(tickers)
    print(f"Got metrics for {len(metrics_df)} tickers")
    
    # Override config if target_size is specified
    config = UNIVERSE_CONFIG.copy()
    if target_size is not None:
        config['target_universe_size'] = target_size
    
    # Filter universe
    universe_df = filter_by_liquidity(metrics_df, config)
    print(f"Filtered universe: {len(universe_df)} stocks")
    
    # Ensure exactly 500 companies
    if len(universe_df) < 500:
        print(f"Warning: Only {len(universe_df)} stocks meet criteria. Trying to expand universe...")
        # Try to get more tickers and re-process
        expanded_tickers = get_static_ticker_list() + get_sp500_tickers()
        additional_tickers = [t for t in expanded_tickers if t not in tickers]
        
        if additional_tickers:
            print(f"Trying {len(additional_tickers)} additional tickers...")
            additional_metrics = calculate_liquidity(additional_tickers[:500])  # Limit to avoid too many API calls
            
            if not additional_metrics.empty:
                # Combine with existing
                combined = pd.concat([metrics_df, additional_metrics], ignore_index=True)
                combined = combined.drop_duplicates(subset=['ticker'], keep='first')
                universe_df = filter_by_liquidity(combined, config)
                print(f"Expanded universe: {len(universe_df)} stocks")
    
    # Add timestamp
    universe_df['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Save to database
    if save:
        save_to_db(universe_df, source)
    
    return universe_df


def select_top_n_by_market_cap(tickers: List[str], n: int = 500) -> pd.DataFrame:
    """
    Select top N companies by market capitalization from a list of tickers.
    
    This function fetches market cap data for the provided tickers and returns
    the top N companies sorted by market cap.
    
    Args:
        tickers: List of ticker symbols to evaluate
        n: Number of companies to select (default: 500)
    
    Returns:
        DataFrame with top N companies sorted by market cap
    """
    print(f"Selecting top {n} companies by market cap from {len(tickers)} tickers...")
    
    # Calculate liquidity metrics which includes market cap
    metrics_df = calculate_liquidity(tickers)
    
    if metrics_df.empty:
        print("No metrics retrieved. Returning empty DataFrame.")
        return pd.DataFrame()
    
    # Sort by market cap (descending) and take top N
    metrics_df = metrics_df.sort_values('market_cap', ascending=False)
    
    # Filter out companies with no market cap
    metrics_df = metrics_df[metrics_df['market_cap'].notna()]
    
    # Take top N
    top_n = metrics_df.head(n).copy()
    
    print(f"Selected {len(top_n)} companies by market cap")
    return top_n.reset_index(drop=True)


def ensure_exact_universe_size(target_size: int = 500, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    Ensure the universe in the database has exactly the target number of companies.
    
    If the current universe has more than target_size, truncate to target_size.
    If less than target_size, try to add more companies by market cap.
    
    Args:
        target_size: Target number of companies (default: 500)
        db_path: Path to the database
    
    Returns:
        DataFrame with exactly target_size companies
    """
    # Load current universe
    current_universe = load_from_db(db_path=db_path)
    
    if current_universe.empty:
        print("No universe found in database. Building new universe...")
        return get_filtered_universe(save=True)
    
    current_size = len(current_universe)
    
    if current_size == target_size:
        print(f"Universe already has exactly {target_size} companies")
        return current_universe
    
    if current_size > target_size:
        print(f"Universe has {current_size} companies. Truncating to {target_size}...")
        # Sort by market cap and take top target_size
        current_universe = current_universe.sort_values('market_cap', ascending=False)
        current_universe = current_universe.head(target_size)
        save_to_db(current_universe)
        return current_universe.reset_index(drop=True)
    
    # current_size < target_size - need to add more
    print(f"Universe has only {current_size} companies. Adding more to reach {target_size}...")
    
    # Get more tickers to try
    additional_tickers = get_static_ticker_list() + get_sp500_tickers()
    existing_tickers = set(current_universe['ticker'].tolist())
    new_tickers = [t for t in additional_tickers if t not in existing_tickers]
    
    if new_tickers:
        # Get metrics for new tickers
        additional_metrics = calculate_liquidity(new_tickers[:1000])  # Limit to avoid too many API calls
        
        if not additional_metrics.empty:
            # Combine with existing
            combined = pd.concat([current_universe, additional_metrics], ignore_index=True)
            combined = combined.drop_duplicates(subset=['ticker'], keep='first')
            
            # Sort by market cap and take top target_size
            combined = combined.sort_values('market_cap', ascending=False)
            combined = combined.head(target_size)
            
            save_to_db(combined)
            print(f"Universe expanded to {len(combined)} companies")
            return combined.reset_index(drop=True)
    
    print(f"Could only achieve {len(current_universe)} companies")
    return current_universe


def main():
    """Main function to run universe selection."""
    print("=" * 60)
    print("Universe Selection - Task 1.1")
    print("=" * 60)
    
    universe = get_filtered_universe(source='all', save=True)
    
    print("\nUniverse Summary:")
    print(f"  Total stocks: {len(universe)}")
    print(f"  Avg daily volume: ${universe['avg_dollar_volume'].mean():,.0f}")
    print(f"  Total market cap: ${universe['market_cap'].sum():,.0f}")
    
    print("\nTop 10 by dollar volume:")
    print(universe[['ticker', 'avg_dollar_volume', 'market_cap']].head(10).to_string(index=False))
    
    return universe


if __name__ == "__main__":
    main()
