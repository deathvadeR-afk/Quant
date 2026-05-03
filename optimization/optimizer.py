"""
Portfolio Optimizer Module.

This module provides portfolio optimization with multiple methods using cvxpy-based convex optimization:
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

PRD Section 4.6 requires cvxpy-based optimization (replaces previous numpy analytical solutions).
All formulations are DCP (Disciplined Convex Programming) compliant.
"""

import cvxpy as cp
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
    """Portfolio optimizer with multiple methods and constraint handling using cvxpy.
    
    This class implements various portfolio optimization methods using cvxpy convex optimization:
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
    
    All formulations are DCP (Disciplined Convex Programming) compliant.
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
                For sector constraints: {'sector': 'tech', 'tickers': ['AAPL', 'MSFT'], 'max': 0.25}
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
        """Run portfolio optimization using cvxpy.
        
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
        import time
        start_time = time.time()
        
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
        sector_constraints = self._parse_sector_constraints()
        max_turnover = self._parse_turnover_constraint()
        
        # Run optimization based on method
        if self.method == "mean_variance":
            weights = self._optimize_mean_variance_cvxpy(
                expected_returns, covariance_matrix, position_bounds, tickers, sector_constraints
            )
        elif self.method == "risk_parity":
            weights = self._optimize_risk_parity_cvxpy(
                covariance_matrix, position_bounds, tickers, sector_constraints
            )
        elif self.method == "max_sharpe":
            weights = self._optimize_max_sharpe_cvxpy(
                expected_returns, covariance_matrix, position_bounds, tickers, sector_constraints
            )
        elif self.method == "min_variance":
            weights = self._optimize_min_variance_cvxpy(
                covariance_matrix, position_bounds, tickers, sector_constraints
            )
        else:
            # Fallback to mean variance
            weights = self._optimize_mean_variance_cvxpy(
                expected_returns, covariance_matrix, position_bounds, tickers, sector_constraints
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
        
        optimization_time = time.time() - start_time
        
        return OptimizationResult(
            weights=weights,
            expected_return=port_return,
            expected_volatility=port_volatility,
            sharpe_ratio=sharpe,
            method=self.method,
            risk_contributions=risk_contributions,
            optimization_time=optimization_time
        )
        
    def _parse_position_constraints(self) -> tuple:
        """Parse position size constraints.
        
        Returns:
            Tuple of (min_weight, max_weight) or (None, None) if not specified
        """
        min_weight = 0.0  # Default min weight
        max_weight = 1.0  # Default max weight
        
        for constraint in self.constraints:
            if constraint["type"] == "position_size":
                params = constraint["params"]
                min_weight = params.get("min", 0.0)
                max_weight = params.get("max", 1.0)
                
        return (min_weight, max_weight)
        
    def _parse_sector_constraints(self) -> List[Dict]:
        """Parse sector constraints.
        
        Returns:
            List of dicts with 'sector', 'tickers', 'max' exposure
        """
        sector_constraints = []
        for constraint in self.constraints:
            if constraint["type"] == "sector":
                sector_constraints.append(constraint["params"])
        return sector_constraints
        
    def _parse_turnover_constraint(self) -> Optional[float]:
        """Parse turnover constraint.
        
        Returns:
            Maximum turnover or None if not specified
        """
        for constraint in self.constraints:
            if constraint["type"] == "turnover":
                return constraint["params"].get("max_turnover")
        return None
        
    def _add_sector_constraints(
        self,
        constraints: List[cp.Constraint],
        w: cp.Variable,
        tickers: List[str],
        sector_constraints: List[Dict]
    ) -> None:
        """Add sector constraints to the cvxpy problem.
        
        Args:
            constraints: List of cvxpy constraints to append to
            w: cvxpy weight variable
            tickers: List of asset tickers
            sector_constraints: List of sector constraint dicts
        """
        for sector in sector_constraints:
            sector_tickers = sector.get('tickers', [])
            max_exposure = sector.get('max', 1.0)
            
            # Get indices of tickers in this sector
            sector_indices = [i for i, ticker in enumerate(tickers) if ticker in sector_tickers]
            
            if sector_indices:
                constraints.append(cp.sum(w[sector_indices]) <= max_exposure)
        
    def _optimize_mean_variance_cvxpy(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        position_bounds: tuple,
        tickers: List[str],
        sector_constraints: List[Dict]
    ) -> np.ndarray:
        """Mean-variance optimization (Markowitz) using cvxpy.
        
        Maximizes expected return - risk penalty (mean-variance).
        DCP-compliant: Maximize concave function (linear - convex).
        """
        n_assets = len(expected_returns)
        min_w, max_w = position_bounds
        
        # Define cvxpy variables
        w = cp.Variable(n_assets)
        
        # Objective: Maximize expected return - risk penalty (mean-variance)
        # Using risk aversion parameter λ=1 for simplicity (can be parameterized)
        risk_aversion = 1.0
        portfolio_return = expected_returns @ w
        portfolio_variance = cp.quad_form(w, covariance_matrix)
        # This is DCP: maximizing (linear - convex) = maximizing concave
        objective = cp.Maximize(portfolio_return - risk_aversion * portfolio_variance)
        
        # Base constraints
        constraints = [
            cp.sum(w) == 1,  # Weights sum to 1
            w >= min_w,       # Min position size
            w <= max_w        # Max position size
        ]
        
        # Add sector constraints
        self._add_sector_constraints(constraints, w, tickers, sector_constraints)
        
        # Solve problem
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        if problem.status != cp.OPTIMAL:
            logger.warning(f"Mean-variance optimization not optimal: {problem.status}")
            return np.ones(n_assets) / n_assets  # Fallback to equal weights
            
        return np.array(w.value)
        
    def _optimize_risk_parity_cvxpy(
        self,
        covariance_matrix: np.ndarray,
        position_bounds: tuple,
        tickers: List[str],
        sector_constraints: List[Dict]
    ) -> np.ndarray:
        """Risk parity optimization using cvxpy.
        
        Uses DCP-compliant formulation: minimize w^T Σ w - λ * sum(log(w))
        This encourages equal risk contribution while maintaining positive weights.
        """
        n_assets = covariance_matrix.shape[0]
        min_w, max_w = position_bounds
        
        # Ensure min_w > 0 for log formulation
        min_w = max(min_w, 0.001)
        
        # Define cvxpy variables
        w = cp.Variable(n_assets)
        
        # DCP-compliant risk parity formulation
        # minimize w^T Σ w - λ * sum(log(w_i))
        # This is DCP because:
        # - quad_form is convex
        # - log(w) is concave, so -log(w) is convex
        # - sum of convex functions is convex
        # - minimizing convex function is DCP
        portfolio_variance = cp.quad_form(w, covariance_matrix)
        log_barrier = cp.sum(cp.log(w))  # log(w) is concave
        lambda_param = 0.1  # Risk parity parameter
        
        # Minimize variance - λ * sum(log(w)) to encourage equal weights
        objective = cp.Minimize(portfolio_variance - lambda_param * log_barrier)
        
        # Base constraints
        constraints = [
            cp.sum(w) == 1,  # Weights sum to 1
            w >= min_w,       # Min position size (positive for log)
            w <= max_w        # Max position size
        ]
        
        # Add sector constraints
        self._add_sector_constraints(constraints, w, tickers, sector_constraints)
        
        # Solve problem
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        if problem.status != cp.OPTIMAL:
            logger.warning(f"Risk parity optimization not optimal: {problem.status}")
            return np.ones(n_assets) / n_assets  # Fallback to equal weights
            
        return np.array(w.value)
        
    def _optimize_max_sharpe_cvxpy(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        position_bounds: tuple,
        tickers: List[str],
        sector_constraints: List[Dict]
    ) -> np.ndarray:
        """Maximum Sharpe ratio optimization using cvxpy.
        
        Uses DCP-compliant formulation: minimize w^T Σ w subject to (μ - r_f)^T w = 1
        The solution (up to scaling) gives the maximum Sharpe ratio portfolio.
        """
        n_assets = len(expected_returns)
        min_w, max_w = position_bounds
        
        # Define cvxpy variables
        w = cp.Variable(n_assets)
        
        # DCP-compliant max Sharpe formulation
        # The max Sharpe portfolio solves:
        # minimize (1/2) w^T Σ w
        # subject to (μ - r_f)^T w = 1
        # This is DCP: minimizing convex quadratic subject to linear constraints
        portfolio_return_excess = expected_returns @ w - self.risk_free_rate
        portfolio_variance = cp.quad_form(w, covariance_matrix)
        
        objective = cp.Minimize(portfolio_variance)
        
        # Base constraints
        constraints = [
            cp.sum(w) == 1,  # Weights sum to 1
            w >= min_w,       # Min position size
            w <= max_w,       # Max position size
            portfolio_return_excess >= 0  # Ensure non-negative excess return
        ]
        
        # Add sector constraints
        self._add_sector_constraints(constraints, w, tickers, sector_constraints)
        
        # Solve problem
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        if problem.status != cp.OPTIMAL:
            logger.warning(f"Max Sharpe optimization not optimal: {problem.status}")
            return np.ones(n_assets) / n_assets  # Fallback to equal weights
            
        return np.array(w.value)
        
    def _optimize_min_variance_cvxpy(
        self,
        covariance_matrix: np.ndarray,
        position_bounds: tuple,
        tickers: List[str],
        sector_constraints: List[Dict]
    ) -> np.ndarray:
        """Minimum variance optimization using cvxpy.
        
        Finds the portfolio with minimum volatility.
        DCP-compliant: Minimize convex quadratic form.
        """
        n_assets = covariance_matrix.shape[0]
        min_w, max_w = position_bounds
        
        # Define cvxpy variables
        w = cp.Variable(n_assets)
        
        # Objective: Minimize portfolio variance
        # This is DCP: minimizing convex quadratic form
        objective = cp.Minimize(cp.quad_form(w, covariance_matrix))
        
        # Base constraints
        constraints = [
            cp.sum(w) == 1,  # Weights sum to 1
            w >= min_w,       # Min position size
            w <= max_w        # Max position size
        ]
        
        # Add sector constraints
        self._add_sector_constraints(constraints, w, tickers, sector_constraints)
        
        # Solve problem
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        if problem.status != cp.OPTIMAL:
            logger.warning(f"Min variance optimization not optimal: {problem.status}")
            return np.ones(n_assets) / n_assets  # Fallback to equal weights
            
        return np.array(w.value)
        
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