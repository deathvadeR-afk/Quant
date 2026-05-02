"""
Risk Models Module for Portfolio Optimization.

This module provides risk calculation tools:
- CovarianceEstimator: Sample and Ledoit-Wolf covariance estimation
- VaRCalculator: Value at Risk calculation
- CVaRCalculator: Conditional Value at Risk calculation
"""

import numpy as np
import pandas as pd
from typing import Optional, Union
from dataclasses import dataclass


class CovarianceEstimator:
    """Estimates covariance matrices using various methods.
    
    Supported methods:
    - sample: Sample covariance matrix
    - ledoit_wolf: Ledoit-Wolf shrinkage estimator
    """
    
    def __init__(self, method: str = "sample"):
        """Initialize the covariance estimator.
        
        Args:
            method: Estimation method ('sample' or 'ledoit_wolf')
        """
        self.method = method
        
    def estimate(self, prices: pd.DataFrame) -> np.ndarray:
        """Estimate covariance matrix from price data.
        
        Args:
            prices: DataFrame of prices (rows=dates, columns=assets)
            
        Returns:
            Covariance matrix as numpy array
        """
        # Calculate returns
        returns = prices.pct_change().dropna()
        
        if self.method == "sample":
            return self._sample_covariance(returns)
        elif self.method == "ledoit_wolf":
            return self._ledoit_wolf_covariance(returns)
        else:
            return self._sample_covariance(returns)
            
    def _sample_covariance(self, returns: pd.DataFrame) -> np.ndarray:
        """Calculate sample covariance matrix.
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            Sample covariance matrix
        """
        return np.cov(returns.values, rowvar=False)
        
    def _ledoit_wolf_covariance(self, returns: pd.DataFrame) -> np.ndarray:
        """Calculate Ledoit-Wolf shrinkage covariance estimator.
        
        The Ledoit-Wolf estimator provides a regularized covariance matrix
        that is always positive definite, addressing the instability of
        the sample covariance matrix when the number of observations is
        small relative to the number of assets.
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            Shrunk covariance matrix
        """
        n_samples, n_assets = returns.shape
        
        # Sample covariance
        sample_cov = np.cov(returns.values, rowvar=False)
        
        # Target (identity matrix scaled by average variance)
        mean_variance = np.trace(sample_cov) / n_assets
        target = np.eye(n_assets) * mean_variance
        
        # Calculate optimal shrinkage intensity
        # Using Ledoit-Wolf formula
        X = returns.values - returns.mean().values
        S = np.dot(X.T, X) / n_samples  # Sample covariance (alternative calculation)
        
        # Sum of squared off-diagonal elements of sample covariance
        sum_sq_off_diag = np.sum(sample_cov**2) - np.sum(np.diag(sample_cov)**2)
        
        # Sum of squared off-diagonal elements of X'X/n
        sum_sq_X = np.sum(S**2) - np.sum(np.diag(S)**2)
        
        # Sum of squared differences between sample and target
        delta = np.sum((sample_cov - target)**2)
        
        # Calculate mu
        mu = np.sum(np.diag(sample_cov)) * mean_variance - mean_variance**2 * n_assets
        
        # Calculate gamma
        gamma = np.sum((target - S)**2)
        
        # Calculate kappa
        kappa = (sum_sq_X - sum_sq_off_diag) / (n_samples * (mean_variance**2 * n_assets - mu))
        
        # Calculate shrinkage intensity
        if delta == 0:
            shrinkage = 1.0
        else:
            shrinkage = max(0, min(1, (n_samples * mu + gamma) / (n_samples * (mu + delta))))
        
        # Apply shrinkage
        shrunk_cov = shrinkage * target + (1 - shrinkage) * sample_cov
        
        # Ensure positive definiteness
        shrunk_cov = self._make_positive_definite(shrunk_cov)
        
        return shrunk_cov
        
    def _make_positive_definite(self, matrix: np.ndarray, epsilon: float = 1e-6) -> np.ndarray:
        """Make matrix positive definite by adding small diagonal perturbation.
        
        Args:
            matrix: Input matrix
            epsilon: Small value to add to diagonal
            
        Returns:
            Positive definite matrix
        """
        n = matrix.shape[0]
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        
        # Check if any eigenvalues are negative or very small
        if np.any(eigenvalues <= epsilon):
            # Add small perturbation to negative eigenvalues
            eigenvalues = np.maximum(eigenvalues, epsilon)
            matrix = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
            
        return matrix


@dataclass
class VaRCalculator:
    """Value at Risk (VaR) calculator.
    
    VaR represents the maximum loss at a given confidence level over a time horizon.
    
    Attributes:
        confidence_level: Confidence level (e.g., 0.95 for 95%)
    """
    confidence_level: float = 0.95
    
    def calculate(
        self,
        portfolio_values: Union[np.ndarray, pd.Series],
        method: str = "historical"
    ) -> float:
        """Calculate Value at Risk.
        
        Args:
            portfolio_values: Historical portfolio values
            method: Calculation method ('historical', 'parametric')
            
        Returns:
            VaR as a positive number (loss)
        """
        if isinstance(portfolio_values, pd.Series):
            values = portfolio_values.values
        else:
            values = np.array(portfolio_values)
            
        if method == "historical":
            return self._historical_var(values)
        elif method == "parametric":
            return self._parametric_var(values)
        else:
            return self._historical_var(values)
            
    def _historical_var(self, values: np.ndarray) -> float:
        """Calculate historical VaR.
        
        Args:
            values: Portfolio values
            
        Returns:
            Historical VaR
        """
        # Calculate daily returns
        returns = np.diff(values) / values[:-1]
        
        # VaR is the negative of the percentile (loss is positive)
        percentile = (1 - self.confidence_level) * 100
        var = -np.percentile(returns, percentile)
        
        # Convert to dollar amount (assuming final value as reference)
        dollar_var = var * values[-1]
        
        return dollar_var
        
    def _parametric_var(self, values: np.ndarray) -> float:
        """Calculate parametric VaR assuming normal distribution.
        
        Args:
            values: Portfolio values
            
        Returns:
            Parametric VaR
        """
        # Calculate daily returns
        returns = np.diff(values) / values[:-1]
        
        # Calculate mean and standard deviation
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Z-score for confidence level
        from scipy import stats
        z = stats.norm.ppf(1 - self.confidence_level)
        
        # VaR assuming normal distribution
        var = -(mu + z * sigma)
        
        # Convert to dollar amount
        dollar_var = var * values[-1]
        
        return max(0, dollar_var)


@dataclass
class CVaRCalculator:
    """Conditional Value at Risk (CVaR) calculator.
    
    CVaR (also known as Expected Shortfall) represents the expected loss
    given that the loss exceeds VaR.
    
    Attributes:
        confidence_level: Confidence level (e.g., 0.95 for 95%)
    """
    confidence_level: float = 0.95
    
    def calculate(
        self,
        portfolio_values: Union[np.ndarray, pd.Series],
        method: str = "historical"
    ) -> float:
        """Calculate Conditional Value at Risk.
        
        Args:
            portfolio_values: Historical portfolio values
            method: Calculation method ('historical', 'parametric')
            
        Returns:
            CVaR as a positive number (expected loss in tail)
        """
        if isinstance(portfolio_values, pd.Series):
            values = portfolio_values.values
        else:
            values = np.array(portfolio_values)
            
        if method == "historical":
            return self._historical_cvar(values)
        elif method == "parametric":
            return self._parametric_cvar(values)
        else:
            return self._historical_cvar(values)
            
    def _historical_cvar(self, values: np.ndarray) -> float:
        """Calculate historical CVaR.
        
        CVaR is the average of all losses beyond VaR.
        
        Args:
            values: Portfolio values
            
        Returns:
            Historical CVaR
        """
        # Calculate daily returns
        returns = np.diff(values) / values[:-1]
        
        # Find the VaR threshold
        percentile = (1 - self.confidence_level) * 100
        var_threshold = np.percentile(returns, percentile)
        
        # CVaR is the average of returns below VaR threshold
        tail_returns = returns[returns <= var_threshold]
        
        if len(tail_returns) == 0:
            return 0.0
            
        cvar = -np.mean(tail_returns)
        
        # Convert to dollar amount
        dollar_cvar = cvar * values[-1]
        
        return dollar_cvar
        
    def _parametric_cvar(self, values: np.ndarray) -> float:
        """Calculate parametric CVaR assuming normal distribution.
        
        For normal distribution, CVaR has a closed-form solution.
        
        Args:
            values: Portfolio values
            
        Returns:
            Parametric CVaR
        """
        # Calculate daily returns
        returns = np.diff(values) / values[:-1]
        
        # Calculate mean and standard deviation
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Z-score for confidence level
        from scipy import stats
        z = stats.norm.ppf(1 - self.confidence_level)
        
        # CVaR for normal distribution
        # CVaR = -(mu - sigma * exp(-z^2/2) / (sqrt(2*pi) * (1-confidence)))
        # Simplified: CVaR = -(mu + sigma * phi(z) / (1 - confidence))
        # where phi is the standard normal PDF
        
        phi_z = stats.norm.pdf(z)
        cvar = -(mu + sigma * phi_z / (1 - self.confidence_level))
        
        # Convert to dollar amount
        dollar_cvar = cvar * values[-1]
        
        return max(0, dollar_cvar)


def calculate_portfolio_risk_metrics(
    weights: np.ndarray,
    covariance_matrix: np.ndarray,
    portfolio_values: Optional[np.ndarray] = None,
    confidence_levels: tuple = (0.95, 0.99)
) -> dict:
    """Calculate comprehensive risk metrics for a portfolio.
    
    Args:
        weights: Portfolio weights
        covariance_matrix: Covariance matrix of returns
        portfolio_values: Historical portfolio values (optional)
        confidence_levels: Tuple of confidence levels for VaR/CVaR
        
    Returns:
        Dictionary of risk metrics
    """
    metrics = {}
    
    # Portfolio volatility
    portfolio_variance = weights @ covariance_matrix @ weights
    metrics["volatility"] = np.sqrt(portfolio_variance)
    metrics["variance"] = portfolio_variance
    
    # Individual asset volatilities
    asset_volatilities = np.sqrt(np.diag(covariance_matrix))
    metrics["asset_volatilities"] = asset_volatilities
    
    # Diversification ratio (weighted avg vol / portfolio vol)
    weighted_avg_vol = np.sum(weights * asset_volatilities)
    if portfolio_variance > 0:
        metrics["diversification_ratio"] = weighted_avg_vol / np.sqrt(portfolio_variance)
    else:
        metrics["diversification_ratio"] = 1.0
        
    # VaR and CVaR if portfolio values provided
    if portfolio_values is not None:
        for cl in confidence_levels:
            var_calc = VaRCalculator(confidence_level=cl)
            cvar_calc = CVaRCalculator(confidence_level=cl)
            
            metrics[f"var_{int(cl*100)}"] = var_calc.calculate(portfolio_values)
            metrics[f"cvar_{int(cl*100)}"] = cvar_calc.calculate(portfolio_values)
            
    return metrics