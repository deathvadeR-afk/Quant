"""
Portfolio Optimization Engine for Quantitative Trading System.

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

Usage:
from optimization import PortfolioOptimizer, ConstraintBuilder

# Build optimizer with constraints
optimizer = PortfolioOptimizer()
optimizer.set_method("mean_variance")
optimizer.add_constraint("sector", {"tech": 0.25})
optimizer.add_constraint("position_size", {"min": 0.01, "max": 0.10})

# Optimize
weights = optimizer.optimize(expected_returns, covariance_matrix)
"""

from optimization.optimizer import PortfolioOptimizer, OptimizationResult
from optimization.constraints import ConstraintBuilder, SectorConstraint, PositionSizeConstraint
from optimization.risk_models import CovarianceEstimator, VaRCalculator, CVaRCalculator

__all__ = [
    "PortfolioOptimizer",
    "OptimizationResult",
    "ConstraintBuilder",
    "SectorConstraint",
    "PositionSizeConstraint",
    "CovarianceEstimator",
    "VaRCalculator",
    "CVaRCalculator",
]

__version__ = "1.0.0"