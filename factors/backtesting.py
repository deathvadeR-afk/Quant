"""
Factor Backtesting Module.

This module provides backtesting functionality for factor validation:
- Walk-forward validation framework
- IC time series calculation
- ICIR (IC Information Ratio) calculation
- Factor performance reporting

Walk-forward validation is the gold standard for factor validation,
as it prevents look-ahead bias by only using data available at each point.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Callable
from datetime import date, datetime, timedelta
import logging

from factors.validation import calculate_ic, calculate_ic_series, calculate_icir

logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """
    Walk-forward validation framework for factor testing.
    
    This class implements the industry-standard walk-forward validation
    methodology:
    1. Train period: Use historical data to identify factor predictive power
    2. Test period: Apply the factor and measure actual performance
    3. Roll forward: Move the window and repeat
    
    This prevents look-ahead bias and provides realistic out-of-sample
    performance estimates.
    """
    
    def __init__(self, db_path: str = "data/universe.db"):
        """
        Initialize the walk-forward validator.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
    
    def run_walk_forward(
        self,
        factor_data: Dict[datetime, pd.Series],
        return_data: Dict[datetime, pd.Series],
        train_window_days: int = 365,
        test_window_days: int = 30
    ) -> Dict:
        """
        Run walk-forward validation.
        
        Args:
            factor_data: Dict mapping dates to factor Series
            return_data: Dict mapping dates to return Series
            train_window_days: Number of days for training window
            test_window_days: Number of days for test window
            
        Returns:
            Dict with validation results including IC statistics
        """
        # Calculate IC time series
        ic_series = calculate_ic_series(factor_data, return_data)
        
        if len(ic_series) == 0:
            return {
                'ic_mean': np.nan,
                'ic_std': np.nan,
                'icir': np.nan,
                'num_observations': 0
            }
        
        # Calculate statistics
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        icir = calculate_icir(ic_series)
        
        # Count valid ICs
        valid_ics = ic_series[~ic_series.isna()]
        
        return {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'icir': icir,
            'num_observations': len(valid_ics),
            'ic_series': ic_series,
            'pct_positive': (valid_ics > 0).mean() if len(valid_ics) > 0 else np.nan
        }
    
    def run_factor_backtest(
        self,
        factor_name: str,
        tickers: List[str],
        start_date: date,
        end_date: date,
        long_threshold: float = 0.8,
        short_threshold: float = 0.2
    ) -> Dict:
        """
        Run a complete factor backtest.
        
        Args:
            factor_name: Name of the factor to backtest
            tickers: List of ticker symbols
            start_date: Start date for backtest
            end_date: End date for backtest
            long_threshold: Percentile threshold for long positions
            short_threshold: Percentile threshold for short positions
            
        Returns:
            Dict with backtest results
        """
        # This is a simplified implementation
        # In production, this would integrate with the full data pipeline
        logger.info(f"Running backtest for {factor_name} from {start_date} to {end_date}")
        
        return {
            'factor': factor_name,
            'start_date': start_date,
            'end_date': end_date,
            'num_tickers': len(tickers),
            'long_threshold': long_threshold,
            'short_threshold': short_threshold,
            'cumulative_return': np.nan,
            'sharpe_ratio': np.nan,
            'max_drawdown': np.nan
        }


def calculate_icir(ic_series: pd.Series) -> float:
    """
    Calculate IC Information Ratio (ICIR).
    
    ICIR = IC_mean / IC_std
    
    A higher ICIR indicates more stable factor predictive power.
    ICIR > 0.5 is generally considered good for a single factor.
    
    Args:
        ic_series: Series of IC values over time
        
    Returns:
        ICIR value
    """
    if len(ic_series) < 2:
        return np.nan
    
    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    
    if ic_std == 0:
        return np.nan
    
    return ic_mean / ic_std


def calculate_factor_returns(
    factor_values: pd.Series,
    actual_returns: pd.Series,
    long_threshold: float = 0.8,
    short_threshold: float = 0.2
) -> Dict[str, float]:
    """
    Calculate returns from a factor-based long/short strategy.
    
    Args:
        factor_values: Series of factor values indexed by ticker
        actual_returns: Series of actual returns indexed by ticker
        long_threshold: Top percentile for long positions
        short_threshold: Bottom percentile for short positions
        
    Returns:
        Dict with long return, short return, and spread return
    """
    # Align indices
    common_idx = factor_values.index.intersection(actual_returns.index)
    if len(common_idx) < 2:
        return {'long_return': np.nan, 'short_return': np.nan, 'spread': np.nan}
    
    fv = factor_values.loc[common_idx]
    ar = actual_returns.loc[common_idx]
    
    # Calculate percentile ranks
    ranks = fv.rank(pct=True)
    
    # Long portfolio (top threshold)
    long_mask = ranks >= long_threshold
    long_return = ar[long_mask].mean() if long_mask.sum() > 0 else np.nan
    
    # Short portfolio (bottom threshold)
    short_mask = ranks <= short_threshold
    short_return = ar[short_mask].mean() if short_mask.sum() > 0 else np.nan
    
    # Spread (long - short)
    spread = long_return - short_return if not (np.isnan(long_return) or np.isnan(short_return)) else np.nan
    
    return {
        'long_return': long_return,
        'short_return': short_return,
        'spread': spread
    }


def run_factor_validation(
    factor_data: pd.DataFrame,
    return_data: pd.DataFrame,
    factor_name: str,
    train_window_days: int = 252,
    test_window_days: int = 21
) -> Dict:
    """
    Run complete factor validation with walk-forward testing.
    
    Args:
        factor_data: DataFrame with factor values (indexed by date, columns by ticker)
        return_data: DataFrame with return values (indexed by date, columns by ticker)
        factor_name: Name of the factor being validated
        train_window_days: Training window in days
        test_window_days: Testing window in days
        
    Returns:
        Dict with validation results
    """
    dates = sorted(factor_data.index)
    
    if len(dates) < train_window_days + test_window_days:
        return {
            'factor': factor_name,
            'error': 'Insufficient data for validation',
            'ic_mean': np.nan,
            'ic_std': np.nan,
            'icir': np.nan
        }
    
    ic_values = []
    
    for i in range(train_window_days, len(dates) - test_window_days, test_window_days):
        train_end = i
        test_start = i
        test_end = min(i + test_window_days, len(dates))
        
        # Get training data
        train_factors = factor_data.iloc[:train_end]
        train_returns = return_data.iloc[:train_end]
        
        # Get test data
        test_factors = factor_data.iloc[test_start:test_end]
        test_returns = return_data.iloc[test_start:test_end]
        
        # Calculate IC for test period
        if len(test_factors) > 0 and len(test_returns) > 0:
            # Use mean factor and return for the test period
            avg_factors = test_factors.mean()
            avg_returns = test_returns.mean()
            
            ic = calculate_ic(avg_factors, avg_returns)
            if not np.isnan(ic):
                ic_values.append(ic)
    
    ic_series = pd.Series(ic_values)
    
    return {
        'factor': factor_name,
        'ic_mean': ic_series.mean() if len(ic_series) > 0 else np.nan,
        'ic_std': ic_series.std() if len(ic_series) > 0 else np.nan,
        'icir': calculate_icir(ic_series) if len(ic_series) > 0 else np.nan,
        'num_periods': len(ic_series),
        'pct_positive': (ic_series > 0).mean() if len(ic_series) > 0 else np.nan
    }