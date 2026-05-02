"""
Factor Validation Module.

This module provides validation functions for factor analysis:
- Information Coefficient (IC) calculation
- Rank IC (Spearman correlation) calculation
- IC-based factor ranking

All functions are designed to be vectorized for performance.
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Optional, Union, Tuple


def calculate_ic(
    factors: pd.Series, 
    returns: pd.Series,
    method: str = 'pearson'
) -> float:
    """
    Calculate Information Coefficient (IC) between factors and returns.
    
    IC measures the correlation between factor values and forward returns.
    
    Args:
        factors: Series with ticker index and factor values
        returns: Series with ticker index and forward return values
        method: Correlation method ('pearson' or 'spearman')
        
    Returns:
        IC value between -1 and 1
    """
    # Align indices
    common_idx = factors.index.intersection(returns.index)
    if len(common_idx) < 2:
        return np.nan
    
    factors_aligned = factors.loc[common_idx].dropna()
    returns_aligned = returns.loc[common_idx].dropna()
    
    # Re-align after dropping NaN
    common_idx = factors_aligned.index.intersection(returns_aligned.index)
    if len(common_idx) < 2:
        return np.nan
    
    factors_aligned = factors_aligned.loc[common_idx]
    returns_aligned = returns_aligned.loc[common_idx]
    
    if method == 'pearson':
        correlation = factors_aligned.corr(returns_aligned)
    elif method == 'spearman':
        correlation, _ = stats.spearmanr(factors_aligned, returns_aligned)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return float(correlation) if not np.isnan(correlation) else np.nan


def calculate_rank_ic(
    factors: pd.Series, 
    returns: pd.Series
) -> float:
    """
    Calculate Rank IC (Spearman correlation) between factors and returns.
    
    Rank IC is more robust to outliers and non-linear relationships.
    
    Args:
        factors: Series with ticker index and factor values
        returns: Series with ticker index and forward return values
        
    Returns:
        Rank IC value between -1 and 1
    """
    return calculate_ic(factors, returns, method='spearman')


def calculate_ic_series(
    factor_data: dict, 
    return_data: dict
) -> pd.Series:
    """
    Calculate IC time series for walk-forward validation.
    
    Args:
        factor_data: Dict mapping dates to factor Series
        return_data: Dict mapping dates to return Series
        
    Returns:
        Series of IC values indexed by date
    """
    ic_series = {}
    
    common_dates = set(factor_data.keys()).intersection(return_data.keys())
    
    for date in sorted(common_dates):
        ic = calculate_ic(factor_data[date], return_data[date])
        if not np.isnan(ic):
            ic_series[date] = ic
    
    return pd.Series(ic_series)


def calculate_icir(ic_series: pd.Series) -> float:
    """
    Calculate IC Information Ratio (ICIR).
    
    ICIR = IC_mean / IC_std
    
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


def calculate_decay_ic(
    factors: pd.Series, 
    returns: pd.Series,
    max_lag: int = 5
) -> Tuple[float, int]:
    """
    Calculate IC with optimal lag adjustment.
    
    Finds the lag that maximizes IC, useful when factor predictive
    power is delayed.
    
    Args:
        factors: Series with ticker index and factor values
        returns: Series with ticker index and forward return values
        max_lag: Maximum lag to consider
        
    Returns:
        Tuple of (optimal_ic, optimal_lag)
    """
    best_ic = -np.inf
    best_lag = 0
    
    for lag in range(max_lag + 1):
        if lag == 0:
            ic = calculate_ic(factors, returns)
        else:
            # Shift returns backward (factor predicts future returns)
            ic = calculate_ic(factors[:-lag], returns[lag:])
        
        if not np.isnan(ic) and abs(ic) > abs(best_ic):
            best_ic = ic
            best_lag = lag
    
    return best_ic, best_lag


def calculate_factor_pvalues(
    factors: pd.Series, 
    returns: pd.Series,
    method: str = 'pearson'
) -> dict:
    """
    Calculate p-values for factor-return correlations.
    
    Args:
        factors: Series with ticker index and factor values
        returns: Series with ticker index and forward return values
        method: Correlation method ('pearson' or 'spearman')
        
    Returns:
        Dict with 'ic', 'pvalue', and 'significant' keys
    """
    # Align indices
    common_idx = factors.index.intersection(returns.index)
    if len(common_idx) < 3:
        return {'ic': np.nan, 'pvalue': np.nan, 'significant': False}
    
    factors_aligned = factors.loc[common_idx].dropna()
    returns_aligned = returns.loc[common_idx].dropna()
    
    common_idx = factors_aligned.index.intersection(returns_aligned.index)
    if len(common_idx) < 3:
        return {'ic': np.nan, 'pvalue': np.nan, 'significant': False}
    
    factors_aligned = factors_aligned.loc[common_idx]
    returns_aligned = returns_aligned.loc[common_idx]
    
    if method == 'pearson':
        ic, pvalue = stats.pearsonr(factors_aligned, returns_aligned)
    else:
        ic, pvalue = stats.spearmanr(factors_aligned, returns_aligned)
    
    return {
        'ic': float(ic) if not np.isnan(ic) else np.nan,
        'pvalue': float(pvalue) if not np.isnan(pvalue) else np.nan,
        'significant': pvalue < 0.05 if not np.isnan(pvalue) else False
    }