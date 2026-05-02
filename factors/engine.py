"""
Factor Engine Module.

This module provides the main FactorEngine class that orchestrates
factor calculation, preprocessing, and validation for the entire
factor analysis pipeline.

The engine:
1. Calculates all factors from price and fundamental data
2. Applies normalization and winsorization
3. Validates factors using IC calculation
4. Stores results for later use by portfolio construction
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import date, datetime
import sqlite3
import logging

from factors.calculator import (
    ValueFactors, MomentumFactors, QualityFactors, 
    VolatilityFactors, SizeFactor
)
from factors.preprocessing import normalize_and_winsorize
from factors.validation import calculate_ic
from factors.library import FactorLibrary

logger = logging.getLogger(__name__)


class FactorEngine:
    """
    Main engine for factor calculation and validation.
    
    This class orchestrates the entire factor analysis pipeline:
    - Data retrieval from database
    - Factor calculation
    - Preprocessing (normalization, winsorization)
    - IC validation
    - Result storage
    """
    
    def __init__(self, db_path: str = "data/universe.db"):
        """
        Initialize the factor engine.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        
        # Initialize factor calculators
        self.value_factors = ValueFactors()
        self.momentum_factors = MomentumFactors()
        self.quality_factors = QualityFactors()
        self.volatility_factors = VolatilityFactors()
        self.size_factor = SizeFactor()
        
        # Initialize factor library
        self.library = FactorLibrary()
    
    def calculate_all_factors(
        self,
        tickers: List[str],
        date: date,
        normalize: bool = True,
        winsorize_lower: float = 0.01,
        winsorize_upper: float = 0.99
    ) -> pd.DataFrame:
        """
        Calculate all factors for a universe of stocks.
        
        Args:
            tickers: List of ticker symbols
            date: Date for factor calculation
            normalize: Whether to normalize factors
            winsorize_lower: Lower percentile for winsorization
            winsorize_upper: Upper percentile for winsorization
            
        Returns:
            DataFrame with columns [ticker, date, factor1, factor2, ...]
        """
        logger.info(f"Calculating factors for {len(tickers)} stocks on {date}")
        
        # Get price and fundamental data
        price_data = self._get_price_data(tickers, date)
        fundamental_data = self._get_fundamental_data(tickers, date)
        
        # Calculate all factors
        factors = {}
        
        # Value factors
        try:
            pe = self.value_factors.calculate_pe_ratio(fundamental_data)
            for ticker in tickers:
                if ticker in pe.index:
                    factors.setdefault(ticker, {})['pe_ratio'] = pe[ticker]
        except Exception as e:
            logger.warning(f"Error calculating P/E: {e}")
        
        try:
            pb = self.value_factors.calculate_pb_ratio(fundamental_data)
            for ticker in tickers:
                if ticker in pb.index:
                    factors.setdefault(ticker, {})['pb_ratio'] = pb[ticker]
        except Exception as e:
            logger.warning(f"Error calculating P/B: {e}")
        
        # Momentum factors
        try:
            mom_1m = self.momentum_factors.calculate_cumulative_return(price_data, 21)
            for ticker in tickers:
                if ticker in mom_1m.index:
                    factors.setdefault(ticker, {})['momentum_1m'] = mom_1m[ticker]
        except Exception as e:
            logger.warning(f"Error calculating 1M momentum: {e}")
        
        try:
            mom_3m = self.momentum_factors.calculate_cumulative_return(price_data, 63)
            for ticker in tickers:
                if ticker in mom_3m.index:
                    factors.setdefault(ticker, {})['momentum_3m'] = mom_3m[ticker]
        except Exception as e:
            logger.warning(f"Error calculating 3M momentum: {e}")
        
        try:
            rsi = self.momentum_factors.calculate_rsi(price_data, 14)
            for ticker in tickers:
                if ticker in rsi.index:
                    factors.setdefault(ticker, {})['rsi_14'] = rsi[ticker]
        except Exception as e:
            logger.warning(f"Error calculating RSI: {e}")
        
        try:
            macd = self.momentum_factors.calculate_macd(price_data)
            for ticker in tickers:
                if ticker in macd.index:
                    factors.setdefault(ticker, {})['macd_histogram'] = macd[ticker]
        except Exception as e:
            logger.warning(f"Error calculating MACD: {e}")
        
        # Quality factors
        try:
            roe = self.quality_factors.calculate_roe(fundamental_data)
            for ticker in tickers:
                if ticker in roe.index:
                    factors.setdefault(ticker, {})['roe'] = roe[ticker]
        except Exception as e:
            logger.warning(f"Error calculating ROE: {e}")
        
        try:
            roa = self.quality_factors.calculate_roa(fundamental_data)
            for ticker in tickers:
                if ticker in roa.index:
                    factors.setdefault(ticker, {})['roa'] = roa[ticker]
        except Exception as e:
            logger.warning(f"Error calculating ROA: {e}")
        
        try:
            de = self.quality_factors.calculate_debt_equity(fundamental_data)
            for ticker in tickers:
                if ticker in de.index:
                    factors.setdefault(ticker, {})['debt_equity'] = de[ticker]
        except Exception as e:
            logger.warning(f"Error calculating D/E: {e}")
        
        # Volatility factors
        try:
            vol = self.volatility_factors.calculate_historical_volatility(price_data, 20)
            for ticker in tickers:
                if ticker in vol.index:
                    factors.setdefault(ticker, {})['historical_volatility_20d'] = vol[ticker]
        except Exception as e:
            logger.warning(f"Error calculating volatility: {e}")
        
        try:
            beta = self.volatility_factors.calculate_beta(price_data, price_data)
            for ticker in tickers:
                if ticker in beta.index:
                    factors.setdefault(ticker, {})['beta'] = beta[ticker]
        except Exception as e:
            logger.warning(f"Error calculating beta: {e}")
        
        try:
            mdd = self.volatility_factors.calculate_max_drawdown(price_data)
            for ticker in tickers:
                if ticker in mdd.index:
                    factors.setdefault(ticker, {})['max_drawdown'] = mdd[ticker]
        except Exception as e:
            logger.warning(f"Error calculating max drawdown: {e}")
        
        # Size factor
        try:
            size = self.size_factor.calculate_market_cap_percentile(fundamental_data)
            for ticker in tickers:
                if ticker in size.index:
                    factors.setdefault(ticker, {})['market_cap_percentile'] = size[ticker]
        except Exception as e:
            logger.warning(f"Error calculating size: {e}")
        
        # Convert to DataFrame
        result_data = []
        for ticker, ticker_factors in factors.items():
            row = {'ticker': ticker, 'date': date}
            row.update(ticker_factors)
            result_data.append(row)
        
        if not result_data:
            return pd.DataFrame(columns=['ticker', 'date'])
        
        df = pd.DataFrame(result_data)
        
        # Apply normalization if requested
        if normalize and len(df) > 1:
            factor_columns = [col for col in df.columns if col not in ['ticker', 'date', 'sector']]
            for col in factor_columns:
                if col in df.columns:
                    df[col] = normalize_and_winsorize(
                        df[col],
                        winsorize_lower=winsorize_lower,
                        winsorize_upper=winsorize_upper
                    )
        
        logger.info(f"Calculated {len(df.columns) - 2} factors for {len(df)} stocks")
        
        return df
    
    def _get_price_data(
        self, 
        tickers: List[str], 
        date: date
    ) -> pd.DataFrame:
        """
        Get price data from database.
        
        Args:
            tickers: List of ticker symbols
            date: Date for data retrieval
            
        Returns:
            DataFrame with price data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get data for the past year for momentum calculations
            start_date = pd.Timestamp(date) - pd.Timedelta(days=400)
            end_date = pd.Timestamp(date)
            
            query = """
                SELECT ticker, date, open, high, low, close, adj_close, volume
                FROM prices
                WHERE ticker IN ({})
                AND date >= ?
                AND date <= ?
                ORDER BY ticker, date
            """.format(','.join('?' * len(tickers)))
            
            df = pd.read_sql_query(
                query, 
                conn, 
                params=[*tickers, start_date, end_date]
            )
            
            conn.close()
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except Exception as e:
            logger.warning(f"Error retrieving price data: {e}")
            return pd.DataFrame()
    
    def _get_fundamental_data(
        self, 
        tickers: List[str], 
        date: date
    ) -> pd.DataFrame:
        """
        Get fundamental data from database.
        
        Args:
            tickers: List of ticker symbols
            date: Date for data retrieval
            
        Returns:
            DataFrame with fundamental data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
                SELECT ticker, report_date, metric, value
                FROM fundamentals
                WHERE ticker IN ({})
                ORDER BY ticker, report_date
            """.format(','.join('?' * len(tickers)))
            
            df = pd.read_sql_query(query, conn, params=tickers)
            
            conn.close()
            
            if not df.empty:
                df['report_date'] = pd.to_datetime(df['report_date'])
            
            return df
            
        except Exception as e:
            logger.warning(f"Error retrieving fundamental data: {e}")
            return pd.DataFrame()
    
    def validate_factors(
        self,
        factors_df: pd.DataFrame,
        forward_returns: pd.Series,
        ic_threshold: float = 0.05
    ) -> Dict:
        """
        Validate factors using IC calculation.
        
        Args:
            factors_df: DataFrame with factor values
            forward_returns: Series with forward returns indexed by ticker
            ic_threshold: Minimum IC for factor to be considered valid
            
        Returns:
            Dict with IC scores and validation results
        """
        results = {}
        
        factor_columns = [col for col in factors_df.columns if col not in ['ticker', 'date', 'sector']]
        
        for factor in factor_columns:
            if factor not in factors_df.columns:
                continue
            
            # Get the most recent factor values
            factor_values = factors_df.groupby('ticker')[factor].last()
            
            # Calculate IC
            ic = calculate_ic(factor_values, forward_returns)
            
            results[factor] = {
                'ic': ic,
                'valid': ic > ic_threshold if not np.isnan(ic) else False
            }
        
        return results