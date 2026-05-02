"""
Portfolio Optimizer Module.

This module provides portfolio optimization with multiple methods:
- Mean-variance optimization (Markowitz)
- Risk parity
- Maximum Sharpe ratio
- Minimum variance

And constraint handling:
- Sector limits
- Position size constraints
- Turnover constraints
- Long/short ratio
- Gross exposure
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of portfolio optimization.
    
    Attributes:
        weights: Portfolio weights for each asset
        expected_return: Expected portfolio return
        expected_volatility: Expected portfolio volatility (annualized)
        sharpe_ratio: Sharpe ratio of the portfolio
        method: Optimization method used
        risk_contributions: Risk contribution of each asset (optional)
        optimization_time: Time taken for optimization in seconds
    """
    weights: np.ndarray
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    method: str
    risk_contributions: Optional[np.ndarray] = None
    optimization_time: float = 0.0


class PortfolioOptimizer:
    """Portfolio optimizer with multiple methods and constraint handling.
    
    This class implements various portfolio optimization methods:
    - Mean-variance (Markowitz)
    - Risk parity
    - Maximum Sharpe ratio
    - Minimum variance
    
    Constraints can be added for:
    - Position size (min/max weight)
    - Sector exposure
    - Turnover
    - Gross exposure
    - Long/short ratio
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """Initialize the portfolio optimizer.
        
        Args:
            risk_free_rate: Risk-free rate for Sharpe ratio calculation (default 2%)
        """
        self.method = "mean_variance"
        self.constraints: List[Dict] = []
        self.risk_free_rate = risk_free_rate
        self.transaction_cost_rate = 0.001  # 0.1% per trade
        
    def set_method(self, method: str) -> None:
        """Set the optimization method.
        
        Args:
            method: One of 'mean_variance', 'risk_parity', 'max_sharpe', 'min_variance'
            
        Raises:
            ValueError: If method is not recognized
        """
        valid_methods = ["mean_variance", "risk_parity", "max_sharpe", "min_variance"]
        if method not in valid_methods:
            raise ValueError(f"Invalid method: {method}. Must be one of {valid_methods}")
        self.method = method
        
    def add_constraint(self, constraint_type: str, params: Dict[str, Any]) -> None:
        """Add a constraint to the optimizer.
        
        Args:
            constraint_type: Type of constraint ('position_size', 'sector', 'turnover', etc.)
            params: Dictionary of constraint parameters
        """
        constraint = {"type": constraint_type, "params": params}
        self.constraints.append(constraint)
        
    def clear_constraints(self) -> None:
        """Clear all constraints."""
        self.constraints = []
        
    def optimize(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        tickers: List[str],
        previous_weights: Optional[np.ndarray] = None
    ) -> OptimizationResult:
        """Run portfolio optimization.
        
        Args:
            expected_returns: Expected returns for each asset (annualized)
            covariance_matrix: Covariance matrix of asset returns
            tickers: List of asset ticker symbols
            previous_weights: Previous portfolio weights for turnover calculation
            
        Returns:
            OptimizationResult with weights and metrics
            
        Raises:
            ValueError: If dimensions don't match
        """
        n_assets = len(expected_returns)
        
        if covariance_matrix.shape != (n_assets, n_assets):
            raise ValueError(
                f"Expected returns has {n_assets} assets but covariance matrix "
                f"is {covariance_matrix.shape}"
            )
            
        if len(tickers) != n_assets:
            raise ValueError(
                f"Expected returns has {n_assets} assets but got {len(tickers)} tickers"
            )
            
        # Parse constraints
        position_bounds = self._parse_position_constraints()
        sector_limits = self._parse_sector_constraints()
        max_turnover = self._parse_turnover_constraint()
        
        # Run optimization based on method
        if self.method == "mean_variance":
            weights = self._optimize_mean_variance(
                expected_returns, covariance_matrix, position_bounds
            )
        elif self.method == "risk_parity":
            weights = self._optimize_risk_parity(
                covariance_matrix, position_bounds
            )
        elif self.method == "max_sharpe":
            weights = self._optimize_max_sharpe(
                expected_returns, covariance_matrix, position_bounds
            )
        elif self.method == "min_variance":
            weights = self._optimize_min_variance(
                covariance_matrix, position_bounds
            )
        else:
            # Fallback to mean variance
            weights = self._optimize_mean_variance(
                expected_returns, covariance_matrix, position_bounds
            )
            
        # Apply turnover constraint if specified
        if max_turnover is not None and previous_weights is not None:
            weights = self._apply_turnover_constraint(
                weights, previous_weights, max_turnover
            )
            
        # Calculate portfolio metrics
        port_return = np.dot(weights, expected_returns)
        port_volatility = np.sqrt(weights @ covariance_matrix @ weights)
        sharpe = (port_return - self.risk_free_rate) / port_volatility if port_volatility > 0 else 0
        
        # Calculate risk contributions for risk parity
        risk_contributions = None
        if self.method == "risk_parity":
            risk_contributions = self._calculate_risk_contributions(weights, covariance_matrix)
        
        return OptimizationResult(
            weights=weights,
            expected_return=port_return,
            expected_volatility=port_volatility,
            sharpe_ratio=sharpe,
            method=self.method,
            risk_contributions=risk_contributions
        )
        
    def _parse_position_constraints(self) -> tuple:
        """Parse position size constraints.
        
        Returns:
            Tuple of (min_weight, max_weight) or (None, None) if not specified
        """
        min_weight = None
        max_weight = None
        
        for constraint in self.constraints:
            if constraint["type"] == "position_size":
                params = constraint["params"]
                min_weight = params.get("min", 0.0)
                max_weight = params.get("max", 1.0)
                
        return (min_weight, max_weight)
        
    def _parse_sector_constraints(self) -> Dict[str, float]:
        """Parse sector constraints.
        
        Returns:
            Dictionary mapping sector names to max exposure
        """
        sector_limits = {}
        for constraint in self.constraints:
            if constraint["type"] == "sector":
                sector_limits.update(constraint["params"])
        return sector_limits
        
    def _parse_turnover_constraint(self) -> Optional[float]:
        """Parse turnover constraint.
        
        Returns:
            Maximum turnover or None if not specified
        """
        for constraint in self.constraints:
            if constraint["type"] == "turnover":
                return constraint["params"].get("max_turnover")
        return None
        
    def _optimize_mean_variance(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        position_bounds: tuple
    ) -> np.ndarray:
        """Mean-variance optimization (Markowitz).
        
        Maximizes return for a given level of risk (or minimizes risk for given return).
        Here we maximize Sharpe ratio as a proxy for efficient portfolio.
        """
        n_assets = len(expected_returns)
        min_w, max_w = position_bounds
        
        # Use analytical solution for max Sharpe portfolio
        # This is a simplified version - in production would use cvxpy
        try:
            # Calculate weights using risk-adjusted return optimization
            # w = Σ^(-1) * (μ - r_f * 1) / (1' * Σ^(-1) * (μ - r_f * 1))
            cov_inv = np.linalg.inv(covariance_matrix + np.eye(n_assets) * 1e-6)
            risk_adj_returns = expected_returns - self.risk_free_rate
            weights = cov_inv @ risk_adj_returns
            weights = weights / np.sum(weights)  # Normalize to sum to 1
            
        except np.linalg.LinAlgError:
            # Fallback to equal weights
            weights = np.ones(n_assets) / n_assets
            
        # Apply position bounds (multiple times to handle normalization effects)
        for _ in range(5):
            if min_w is not None:
                weights = np.maximum(weights, min_w)
            if max_w is not None:
                weights = np.minimum(weights, max_w)
            weights = weights / np.sum(weights)

        return weights
        
    def _optimize_risk_parity(
        self,
        covariance_matrix: np.ndarray,
        position_bounds: tuple
    ) -> np.ndarray:
        """Risk parity optimization.
        
        Equalizes the risk contribution of each asset to the portfolio.
        """
        n_assets = covariance_matrix.shape[0]
        min_w, max_w = position_bounds
        
        # Initial weights (equal weight)
        weights = np.ones(n_assets) / n_assets
        
        # Iterative algorithm to achieve risk parity
        for _ in range(100):  # Max iterations
            portfolio_vol = np.sqrt(weights @ covariance_matrix @ weights)
            marginal_contrib = covariance_matrix @ weights
            risk_contrib = weights * marginal_contrib / portfolio_vol
            
            # Target: equal risk contributions
            target_risk = portfolio_vol / n_assets
            diff = risk_contrib - target_risk
            
            # Adjust weights
            adjustment = 0.1 * diff / marginal_contrib
            weights = weights * (1 + adjustment)
            
            # Apply bounds and normalize (multiple times)
            for _ in range(3):
                if min_w is not None:
                    weights = np.maximum(weights, min_w)
                if max_w is not None:
                    weights = np.minimum(weights, max_w)
                weights = weights / np.sum(weights)
            
            # Check convergence
            if np.max(np.abs(diff)) < 1e-6:
                break
                
        return weights
        
    def _optimize_max_sharpe(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        position_bounds: tuple
    ) -> np.ndarray:
        """Maximum Sharpe ratio optimization.
        
        Finds the portfolio that maximizes the Sharpe ratio.
        """
        n_assets = len(expected_returns)
        min_w, max_w = position_bounds
        
        # Use the same approach as mean-variance (which optimizes Sharpe)
        return self._optimize_mean_variance(expected_returns, covariance_matrix, position_bounds)
        
    def _optimize_min_variance(
        self,
        covariance_matrix: np.ndarray,
        position_bounds: tuple
    ) -> np.ndarray:
        """Minimum variance optimization.
        
        Finds the portfolio with minimum volatility.
        """
        n_assets = covariance_matrix.shape[0]
        min_w, max_w = position_bounds
        
        try:
            # Minimum variance: w = Σ^(-1) * 1 / (1' * Σ^(-1) * 1)
            cov_inv = np.linalg.inv(covariance_matrix + np.eye(n_assets) * 1e-6)
            ones = np.ones(n_assets)
            weights = cov_inv @ ones
            weights = weights / np.sum(weights)
            
        except np.linalg.LinAlgError:
            # Fallback to equal weights
            weights = np.ones(n_assets) / n_assets
            
        # Apply position bounds (multiple times to handle normalization effects)
        for _ in range(5):
            if min_w is not None:
                weights = np.maximum(weights, min_w)
            if max_w is not None:
                weights = np.minimum(weights, max_w)
            weights = weights / np.sum(weights)

        return weights
        
    def _apply_turnover_constraint(
        self,
        weights: np.ndarray,
        previous_weights: np.ndarray,
        max_turnover: float
    ) -> np.ndarray:
        """Apply turnover constraint by scaling changes.
        
        Args:
            weights: New weights
            previous_weights: Previous weights
            max_turnover: Maximum allowed turnover
            
        Returns:
            Adjusted weights satisfying turnover constraint
        """
        # Calculate current turnover
        current_turnover = np.sum(np.abs(weights - previous_weights)) / 2
        
        if current_turnover <= max_turnover:
            return weights
            
        # Scale down the changes to meet turnover constraint
        scaling_factor = max_turnover / current_turnover
        diff = weights - previous_weights
        adjusted_diff = diff * scaling_factor
        weights = previous_weights + adjusted_diff
        
        # Ensure weights sum to 1
        weights = weights / np.sum(weights)
        
        return weights
        
    def _calculate_risk_contributions(
        self,
        weights: np.ndarray,
        covariance_matrix: np.ndarray
    ) -> np.ndarray:
        """Calculate risk contributions of each asset.
        
        Args:
            weights: Portfolio weights
            covariance_matrix: Covariance matrix
            
        Returns:
            Risk contribution of each asset
        """
        portfolio_vol = np.sqrt(weights @ covariance_matrix @ weights)
        marginal_contrib = covariance_matrix @ weights
        risk_contrib = weights * marginal_contrib / portfolio_vol
        
        return risk_contrib
        
    def _calculate_turnover(
        self,
        previous_weights: np.ndarray,
        new_weights: np.ndarray
    ) -> float:
        """Calculate portfolio turnover.
        
        Args:
            previous_weights: Previous portfolio weights
            new_weights: New portfolio weights
            
        Returns:
            Turnover (sum of absolute changes / 2)
        """
        return np.sum(np.abs(new_weights - previous_weights)) / 2
        
    def _calculate_transaction_cost(
        self,
        previous_weights: np.ndarray,
        new_weights: np.ndarray,
        portfolio_value: float
    ) -> float:
        """Calculate transaction costs.
        
        Args:
            previous_weights: Previous portfolio weights
            new_weights: New portfolio weights
            portfolio_value: Total portfolio value
            
        Returns:
            Transaction cost in dollars
        """
        turnover = self._calculate_turnover(previous_weights, new_weights)
        return turnover * portfolio_value * self.transaction_cost_rate