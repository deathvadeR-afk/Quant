"""
Factor Analysis Module.

This module provides analysis tools for factor research:
- Factor correlation matrix calculation
- High correlation pair detection
- Factor redundancy analysis
- Multi-factor combination optimization

These tools help identify which factors provide unique information
and which are redundant (highly correlated with others).
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


class FactorCorrelationAnalyzer:
    """
    Analyzer for factor correlations and redundancy.
    
    This class provides tools to:
    - Calculate factor correlation matrices
    - Identify highly correlated factor pairs
    - Analyze factor redundancy
    - Suggest factor combinations
    """
    
    def __init__(self, correlation_threshold: float = 0.9):
        """
        Initialize the correlation analyzer.
        
        Args:
            correlation_threshold: Threshold for considering factors highly correlated
        """
        self.correlation_threshold = correlation_threshold
    
    def calculate_correlation_matrix(
        self, 
        factors_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate factor correlation matrix.
        
        Args:
            factors_df: DataFrame with factor values (columns are factors)
            
        Returns:
            Correlation matrix as DataFrame
        """
        # Get factor columns
        factor_columns = [col for col in factors_df.columns if col not in ['ticker', 'date', 'sector']]
        
        if len(factor_columns) < 2:
            return pd.DataFrame()
        
        # Calculate correlation matrix
        factor_data = factors_df[factor_columns]
        corr_matrix = factor_data.corr()
        
        return corr_matrix
    
    def find_high_correlation_pairs(
        self, 
        factors_df: pd.DataFrame,
        threshold: Optional[float] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Find pairs of highly correlated factors.
        
        Args:
            factors_df: DataFrame with factor values
            threshold: Correlation threshold (uses default if not provided)
            
        Returns:
            List of tuples (factor1, factor2, correlation)
        """
        if threshold is None:
            threshold = self.correlation_threshold
        
        corr_matrix = self.calculate_correlation_matrix(factors_df)
        
        if corr_matrix.empty:
            return []
        
        # Find pairs with high correlation
        high_corr_pairs = []
        
        for i, factor1 in enumerate(corr_matrix.columns):
            for factor2 in corr_matrix.columns[i+1:]:
                corr = corr_matrix.loc[factor1, factor2]
                if abs(corr) >= threshold:
                    high_corr_pairs.append((factor1, factor2, corr))
        
        # Sort by absolute correlation
        high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        
        return high_corr_pairs
    
    def get_uncorrelated_factors(
        self,
        factors_df: pd.DataFrame,
        max_correlation: float = 0.5
    ) -> List[str]:
        """
        Get a subset of factors with low mutual correlation.
        
        This is useful for building a factor portfolio with
        minimal redundancy.
        
        Args:
            factors_df: DataFrame with factor values
            max_correlation: Maximum allowed correlation between any two factors
            
        Returns:
            List of factor names with low mutual correlation
        """
        corr_matrix = self.calculate_correlation_matrix(factors_df)
        
        if corr_matrix.empty:
            return []
        
        factor_columns = list(corr_matrix.columns)
        selected = []
        
        for factor in factor_columns:
            # Check if this factor is correlated with any already selected
            is_correlated = False
            for selected_factor in selected:
                if abs(corr_matrix.loc[factor, selected_factor]) > max_correlation:
                    is_correlated = True
                    break
            
            if not is_correlated:
                selected.append(factor)
        
        return selected
    
    def calculate_factor_decay(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame,
        max_lag: int = 20
    ) -> Dict[str, Dict]:
        """
        Calculate how factor predictive power decays over time.
        
        Args:
            factor_data: DataFrame with factor values indexed by date
            return_data: DataFrame with return values indexed by date
            max_lag: Maximum lag to test
            
        Returns:
            Dict mapping factor names to decay statistics
        """
        from factors.validation import calculate_ic
        
        results = {}
        factor_columns = [col for col in factor_data.columns if col not in ['ticker', 'date', 'sector']]
        
        for factor in factor_columns:
            decay_stats = {
                'ic_at_lag_0': np.nan,
                'ic_at_lag_5': np.nan,
                'ic_at_lag_10': np.nan,
                'optimal_lag': 0,
                'optimal_ic': np.nan
            }
            
            best_ic = -np.inf
            best_lag = 0
            
            for lag in range(max_lag + 1):
                if lag == 0:
                    ic = calculate_ic(factor_data[factor], return_data[factor])
                else:
                    # Shift returns backward
                    ic = calculate_ic(factor_data[factor][:-lag], return_data[factor][lag:])
                
                if not np.isnan(ic) and abs(ic) > abs(best_ic):
                    best_ic = ic
                    best_lag = lag
                
                if lag == 0:
                    decay_stats['ic_at_lag_0'] = ic
                elif lag == 5:
                    decay_stats['ic_at_lag_5'] = ic
                elif lag == 10:
                    decay_stats['ic_at_lag_10'] = ic
            
            decay_stats['optimal_lag'] = best_lag
            decay_stats['optimal_ic'] = best_ic
            
            results[factor] = decay_stats
        
        return results


class FactorOptimizer:
    """
    Optimizer for factor combination and weighting.
    
    This class provides tools to:
    - Optimize factor weights to maximize IC
    - Find optimal factor combinations
    - Backtest factor strategies
    """
    
    def __init__(self):
        """Initialize the factor optimizer."""
        pass
    
    def optimize_factor_weights(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.Series,
        method: str = 'ic_weighted'
    ) -> Dict[str, float]:
        """
        Optimize factor weights to maximize predictive power.
        
        Args:
            factor_data: DataFrame with factor values
            return_data: Series with forward returns
            method: Weighting method ('ic_weighted', 'equal', 'optimized')
            
        Returns:
            Dict mapping factor names to weights
        """
        from factors.validation import calculate_ic
        
        factor_columns = [col for col in factor_data.columns if col not in ['ticker', 'date', 'sector']]
        
        if len(factor_columns) == 0:
            return {}
        
        if method == 'equal':
            # Equal weights
            weight = 1.0 / len(factor_columns)
            return {f: weight for f in factor_columns}
        
        elif method == 'ic_weighted':
            # Weight by IC
            weights = {}
            total_ic = 0
            
            for factor in factor_columns:
                ic = calculate_ic(factor_data[factor], return_data)
                if not np.isnan(ic) and ic > 0:
                    weights[factor] = ic
                    total_ic += ic
                else:
                    weights[factor] = 0
            
            # Normalize weights
            if total_ic > 0:
                weights = {f: w / total_ic for f, w in weights.items()}
            
            return weights
        
        else:
            # Default to equal weights
            weight = 1.0 / len(factor_columns)
            return {f: weight for f in factor_columns}
    
    def create_composite_factor(
        self,
        factor_data: pd.DataFrame,
        weights: Optional[Dict[str, float]] = None
    ) -> pd.Series:
        """
        Create a composite factor from multiple factors.
        
        Args:
            factor_data: DataFrame with factor values
            weights: Optional dict of factor weights
            
        Returns:
            Series with composite factor values
        """
        if weights is None:
            # Use equal weights
            factor_columns = [col for col in factor_data.columns if col not in ['ticker', 'date', 'sector']]
            weights = {f: 1.0 / len(factor_columns) for f in factor_columns}
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {f: w / total_weight for f, w in weights.items()}
        
        # Calculate composite
        composite = pd.Series(0, index=factor_data.index)
        
        for factor, weight in weights.items():
            if factor in factor_data.columns:
                composite += factor_data[factor] * weight
        
        return composite