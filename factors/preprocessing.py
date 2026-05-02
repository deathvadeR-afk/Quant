"""
Factor Preprocessing Module.

This module provides preprocessing functions for factor data:
- Z-score normalization
- Sector-neutral z-score normalization
- Winsorization at specified percentiles
- Missing value imputation

All functions are designed to be vectorized for performance.
"""

import pandas as pd
import numpy as np
from typing import Optional, Union


def normalize_zscore(factors: pd.Series) -> pd.Series:
    """
    Apply z-score normalization to factors.
    
    Args:
        factors: Series with ticker index and factor values
        
    Returns:
        Series with normalized factor values (mean=0, std=1)
    """
    if factors.empty or factors.std() == 0:
        return factors
    
    return (factors - factors.mean()) / factors.std()


def normalize_sector_neutral(
    factors: pd.Series, 
    sectors: pd.Series
) -> pd.Series:
    """
    Apply sector-neutral z-score normalization.
    
    Each factor is normalized within its sector, then combined.
    
    Args:
        factors: Series with ticker index and factor values
        sectors: Series with ticker index and sector values
        
    Returns:
        Series with sector-neutral normalized factor values
    """
    # Align factors and sectors
    common_idx = factors.index.intersection(sectors.index)
    if len(common_idx) == 0:
        return factors
    
    factors_aligned = factors.loc[common_idx]
    sectors_aligned = sectors.loc[common_idx]
    
    # Calculate sector means and standard deviations
    result = pd.Series(index=common_idx, dtype=float)
    
    for sector in sectors_aligned.unique():
        if pd.isna(sector):
            continue
        
        sector_mask = sectors_aligned == sector
        sector_factors = factors_aligned[sector_mask]
        
        if len(sector_factors) == 0:
            continue
        
        sector_mean = sector_factors.mean()
        sector_std = sector_factors.std()
        
        if sector_std > 0:
            result[sector_mask] = (sector_factors - sector_mean) / sector_std
        else:
            result[sector_mask] = 0
    
    return result


def winsorize(
    factors: pd.Series, 
    lower_percentile: float = 0.01, 
    upper_percentile: float = 0.99
) -> pd.Series:
    """
    Winsorize factors at specified percentiles.
    
    Clips extreme values to the percentile boundaries.
    
    Args:
        factors: Series with ticker index and factor values
        lower_percentile: Lower percentile for winsorization (default 0.01)
        upper_percentile: Upper percentile for winsorization (default 0.99)
        
    Returns:
        Series with winsorized factor values
    """
    if factors.empty:
        return factors
    
    lower_bound = factors.quantile(lower_percentile)
    upper_bound = factors.quantile(upper_percentile)
    
    return factors.clip(lower=lower_bound, upper=upper_bound)


def impute_missing_values(
    factors: pd.Series, 
    sectors: pd.Series,
    method: str = 'sector_median'
) -> pd.Series:
    """
    Impute missing values in factor data.
    
    Args:
        factors: Series with ticker index and factor values
        sectors: Series with ticker index and sector values
        method: Imputation method ('sector_median', 'global_median', 'zero')
        
    Returns:
        Series with imputed factor values
    """
    result = factors.copy()
    
    if method == 'sector_median':
        # Align factors and sectors
        common_idx = factors.index.intersection(sectors.index)
        
        for idx in common_idx:
            if pd.isna(result[idx]):
                sector = sectors[idx]
                if pd.isna(sector):
                    # Use global median if sector is unknown
                    result[idx] = factors.median()
                else:
                    # Use sector median
                    sector_mask = sectors == sector
                    sector_factors = factors[sector_mask]
                    sector_median = sector_factors.median()
                    result[idx] = sector_median if not pd.isna(sector_median) else factors.median()
    
    elif method == 'global_median':
        median_value = factors.median()
        result = result.fillna(median_value)
    
    elif method == 'zero':
        result = result.fillna(0)
    
    return result


def normalize_and_winsorize(
    factors: pd.Series,
    sectors: Optional[pd.Series] = None,
    winsorize_lower: float = 0.01,
    winsorize_upper: float = 0.99
) -> pd.Series:
    """
    Apply full preprocessing pipeline: normalization and winsorization.
    
    Args:
        factors: Series with ticker index and factor values
        sectors: Optional series with ticker index and sector values
        winsorize_lower: Lower percentile for winsorization
        winsorize_upper: Upper percentile for winsorization
        
    Returns:
        Series with preprocessed factor values
    """
    # First winsorize
    result = winsorize(factors, winsorize_lower, winsorize_upper)
    
    # Then normalize
    if sectors is not None:
        result = normalize_sector_neutral(result, sectors)
    else:
        result = normalize_zscore(result)
    
    return result