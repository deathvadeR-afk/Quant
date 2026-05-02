"""
Test module for Portfolio Optimization Engine.

This module tests:
- Mean-variance optimization (Markowitz)
- Risk parity optimization
- Maximum Sharpe ratio optimization
- Minimum variance optimization
- Constraint handling (sector, position size, turnover)
- Transaction cost modeling
- Risk models (covariance, VaR, CVaR)

Run with: pytest optimization/test_optimizer.py -v

TDD Phase: RED (write failing tests first)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

# Import the modules under test
from optimization import (
    PortfolioOptimizer,
    OptimizationResult,
    ConstraintBuilder,
    SectorConstraint,
    PositionSizeConstraint,
    CovarianceEstimator,
    VaRCalculator,
    CVaRCalculator,
)


class TestPortfolioOptimizer:
    """Tests for PortfolioOptimizer class."""

    @pytest.fixture
    def sample_returns(self):
        """Sample expected returns for 5 assets."""
        return np.array([0.05, 0.08, 0.06, 0.04, 0.07])

    @pytest.fixture
    def sample_covariance(self):
        """Sample covariance matrix for 5 assets."""
        return np.array([
            [0.0100, 0.0030, 0.0025, 0.0015, 0.0020],
            [0.0030, 0.0160, 0.0035, 0.0020, 0.0025],
            [0.0025, 0.0035, 0.0120, 0.0025, 0.0030],
            [0.0015, 0.0020, 0.0025, 0.0080, 0.0015],
            [0.0020, 0.0025, 0.0030, 0.0015, 0.0140],
        ])

    @pytest.fixture
    def sample_tickers(self):
        """Sample ticker symbols."""
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

    def test_optimizer_initialization(self):
        """Test that optimizer initializes with correct defaults."""
        optimizer = PortfolioOptimizer()
        assert optimizer.method == "mean_variance"
        assert optimizer.constraints == []
        assert optimizer.transaction_cost_rate == 0.001  # 0.1%

    def test_set_optimization_method(self):
        """Test setting different optimization methods."""
        optimizer = PortfolioOptimizer()
        
        optimizer.set_method("mean_variance")
        assert optimizer.method == "mean_variance"
        
        optimizer.set_method("risk_parity")
        assert optimizer.method == "risk_parity"
        
        optimizer.set_method("max_sharpe")
        assert optimizer.method == "max_sharpe"
        
        optimizer.set_method("min_variance")
        assert optimizer.method == "min_variance"

    def test_mean_variance_optimization(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test mean-variance (Markowitz) optimization."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        
        assert isinstance(result, OptimizationResult)
        assert len(result.weights) == 5
        assert abs(sum(result.weights) - 1.0) < 0.001  # Weights sum to 1
        assert all(w >= -0.5 for w in result.weights)  # No extreme short positions
        assert result.expected_return is not None
        assert result.expected_volatility is not None
        assert result.sharpe_ratio is not None

    def test_risk_parity_optimization(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test risk parity optimization."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("risk_parity")
        
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        
        assert isinstance(result, OptimizationResult)
        assert len(result.weights) == 5
        assert abs(sum(result.weights) - 1.0) < 0.001
        
        # Risk parity should have more equal risk contributions
        # Check that no single asset dominates risk
        risk_contributions = result.risk_contributions
        if risk_contributions is not None:
            max_risk_share = max(risk_contributions)
            min_risk_share = min(risk_contributions)
            # In risk parity, risk contributions should be roughly equal
            # Allow some tolerance for numerical optimization
            assert max_risk_share < 0.4  # No asset > 40% of portfolio risk

    def test_max_sharpe_optimization(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test maximum Sharpe ratio optimization."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("max_sharpe")
        
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        
        assert isinstance(result, OptimizationResult)
        assert len(result.weights) == 5
        assert abs(sum(result.weights) - 1.0) < 0.001
        assert result.sharpe_ratio is not None
        # Max Sharpe should have positive Sharpe ratio for positive returns
        assert result.sharpe_ratio >= 0

    def test_min_variance_optimization(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test minimum variance optimization."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("min_variance")
        
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        
        assert isinstance(result, OptimizationResult)
        assert len(result.weights) == 5
        assert abs(sum(result.weights) - 1.0) < 0.001
        # Min variance should have lower volatility than equal weight
        equal_weight = np.ones(5) / 5
        equal_weight_vol = np.sqrt(equal_weight @ sample_covariance @ equal_weight)
        assert result.expected_volatility <= equal_weight_vol * 1.1  # Allow 10% tolerance

    def test_optimization_with_position_constraints(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test optimization with position size constraints."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        optimizer.add_constraint("position_size", {"min": 0.05, "max": 0.30})
        
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        
        assert isinstance(result, OptimizationResult)
        assert all(w >= 0.05 - 0.001 for w in result.weights)
        assert all(w <= 0.30 + 0.001 for w in result.weights)

    def test_optimization_with_sector_constraints(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test optimization with sector constraints.
        
        Note: This test verifies the constraint is accepted without error.
        Full sector constraint enforcement requires sector mapping data.
        """
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        # Add sector constraint - optimizer should accept it without error
        optimizer.add_constraint("sector", {"tech": 0.50})
        
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        
        assert isinstance(result, OptimizationResult)
        # Weights should still sum to 1
        assert abs(sum(result.weights) - 1.0) < 0.001

    def test_optimization_with_turnover_constraint(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test optimization with turnover constraint."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        # Previous weights (equal weight)
        previous_weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        optimizer.add_constraint("turnover", {"max_turnover": 0.20})
        
        result = optimizer.optimize(
            sample_returns, sample_covariance, sample_tickers,
            previous_weights=previous_weights
        )
        
        assert isinstance(result, OptimizationResult)
        # Calculate turnover
        turnover = np.sum(np.abs(result.weights - previous_weights)) / 2
        assert turnover <= 0.20 + 0.001

    def test_optimization_time_requirement(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test that optimization completes within 30 seconds."""
        import time
        
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        
        start_time = time.time()
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 30, f"Optimization took {elapsed_time:.2f} seconds"
        assert isinstance(result, OptimizationResult)

    def test_optimization_handles_empty_constraints(
        self, sample_returns, sample_covariance, sample_tickers
    ):
        """Test optimization with no constraints."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        # No constraints added
        
        result = optimizer.optimize(sample_returns, sample_covariance, sample_tickers)
        
        assert isinstance(result, OptimizationResult)
        assert len(result.weights) == 5
        assert abs(sum(result.weights) - 1.0) < 0.001


class TestOptimizationResult:
    """Tests for OptimizationResult dataclass."""

    def test_result_creation(self):
        """Test creating an OptimizationResult."""
        weights = np.array([0.2, 0.3, 0.2, 0.15, 0.15])
        result = OptimizationResult(
            weights=weights,
            expected_return=0.06,
            expected_volatility=0.12,
            sharpe_ratio=0.5,
            method="mean_variance",
        )
        
        assert np.array_equal(result.weights, weights)
        assert result.expected_return == 0.06
        assert result.expected_volatility == 0.12
        assert result.sharpe_ratio == 0.5
        assert result.method == "mean_variance"

    def test_result_with_risk_contributions(self):
        """Test result with risk contributions."""
        weights = np.array([0.2, 0.3, 0.2, 0.15, 0.15])
        risk_contributions = np.array([0.25, 0.30, 0.20, 0.12, 0.13])
        
        result = OptimizationResult(
            weights=weights,
            expected_return=0.06,
            expected_volatility=0.12,
            sharpe_ratio=0.5,
            method="risk_parity",
            risk_contributions=risk_contributions,
        )
        
        assert np.array_equal(result.risk_contributions, risk_contributions)
        # Risk contributions should sum to 1 (as fractions of total risk)
        assert abs(sum(risk_contributions) - 1.0) < 0.001


class TestConstraintBuilder:
    """Tests for ConstraintBuilder class."""

    def test_builder_initialization(self):
        """Test ConstraintBuilder initializes correctly."""
        builder = ConstraintBuilder()
        assert builder.constraints == []

    def test_add_sector_constraint(self):
        """Test adding sector constraints."""
        builder = ConstraintBuilder()
        builder.add_sector_limit("tech", 0.25)
        builder.add_sector_limit("healthcare", 0.30)
        
        assert len(builder.constraints) == 2
        assert any(c.sector_name == "tech" for c in builder.constraints)
        assert any(c.sector_name == "healthcare" for c in builder.constraints)

    def test_add_position_size_constraint(self):
        """Test adding position size constraints."""
        builder = ConstraintBuilder()
        builder.add_position_size(min_weight=0.01, max_weight=0.10)
        
        assert len(builder.constraints) == 1
        constraint = builder.constraints[0]
        assert constraint.min_weight == 0.01
        assert constraint.max_weight == 0.10

    def test_add_turnover_constraint(self):
        """Test adding turnover constraints."""
        builder = ConstraintBuilder()
        builder.add_turnover_limit(max_turnover=0.20)
        
        assert len(builder.constraints) == 1
        assert builder.constraints[0].max_turnover == 0.20

    def test_add_gross_exposure_constraint(self):
        """Test adding gross exposure constraints."""
        builder = ConstraintBuilder()
        builder.add_gross_exposure_limit(max_exposure=2.0)
        
        assert len(builder.constraints) == 1
        assert builder.constraints[0].max_exposure == 2.0

    def test_add_long_short_ratio_constraint(self):
        """Test adding long/short ratio constraints."""
        builder = ConstraintBuilder()
        builder.add_long_short_ratio(max_ratio=1.3)  # 130/30
        
        assert len(builder.constraints) == 1
        assert builder.constraints[0].max_ratio == 1.3

    def test_clear_constraints(self):
        """Test clearing all constraints."""
        builder = ConstraintBuilder()
        builder.add_position_size(min_weight=0.01, max_weight=0.10)
        builder.add_sector_limit("tech", 0.25)
        
        builder.clear()
        assert len(builder.constraints) == 0

    def test_build_returns_constraint_list(self):
        """Test that build returns the constraint list."""
        builder = ConstraintBuilder()
        builder.add_position_size(min_weight=0.01, max_weight=0.10)
        
        constraints = builder.build()
        assert len(constraints) == 1
        assert constraints[0].min_weight == 0.01


class TestCovarianceEstimator:
    """Tests for CovarianceEstimator class."""

    @pytest.fixture
    def sample_price_data(self):
        """Sample price data for covariance estimation."""
        np.random.seed(42)
        dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="B")
        n_days = len(dates)
        
        # Generate correlated returns
        corr_matrix = np.array([
            [1.0, 0.7, 0.5],
            [0.7, 1.0, 0.6],
            [0.5, 0.6, 1.0],
        ])
        volatilities = np.array([0.15, 0.20, 0.18])
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix
        
        # Generate returns from multivariate normal
        mean_returns = np.zeros(3)
        returns = np.random.multivariate_normal(mean_returns, cov_matrix, n_days)
        
        # Convert to prices
        prices = 100 * np.exp(np.cumsum(returns, axis=0))
        prices = np.vstack([np.full(3, 100), prices])  # Add starting prices
        
        df = pd.DataFrame(
            prices,
            index=dates.insert(0, dates[0] - pd.Timedelta(days=1)),
            columns=["AAPL", "MSFT", "GOOGL"]
        )
        return df

    def test_sample_covariance(self, sample_price_data):
        """Test sample covariance estimation."""
        estimator = CovarianceEstimator(method="sample")
        cov_matrix = estimator.estimate(sample_price_data)
        
        assert cov_matrix.shape == (3, 3)
        assert np.allclose(cov_matrix, cov_matrix.T)  # Symmetric
        assert np.all(np.diag(cov_matrix) > 0)  # Positive variances

    def test_ledoit_wolf_covariance(self, sample_price_data):
        """Test Ledoit-Wolf shrinkage covariance estimation."""
        estimator = CovarianceEstimator(method="ledoit_wolf")
        cov_matrix = estimator.estimate(sample_price_data)
        
        assert cov_matrix.shape == (3, 3)
        assert np.allclose(cov_matrix, cov_matrix.T)  # Symmetric
        assert np.all(np.diag(cov_matrix) > 0)  # Positive variances

    def test_covariance_is_positive_definite(self, sample_price_data):
        """Test that covariance matrix is positive definite."""
        estimator = CovarianceEstimator(method="ledoit_wolf")
        cov_matrix = estimator.estimate(sample_price_data)
        
        # Check eigenvalues are positive
        eigenvalues = np.linalg.eigvalsh(cov_matrix)
        assert all(eigenvalues > 0), "Covariance matrix should be positive definite"


class TestVaRCalculator:
    """Tests for VaR (Value at Risk) calculator."""

    @pytest.fixture
    def sample_portfolio_values(self):
        """Sample portfolio values for VaR calculation."""
        np.random.seed(42)
        # Simulate 252 days of portfolio values
        initial_value = 1000000
        daily_returns = np.random.normal(0.0005, 0.01, 252)
        values = initial_value * np.exp(np.cumsum(daily_returns))
        return values

    def test_var_calculation_95(self, sample_portfolio_values):
        """Test VaR calculation at 95% confidence."""
        calculator = VaRCalculator(confidence_level=0.95)
        var_95 = calculator.calculate(sample_portfolio_values)
        
        assert var_95 > 0
        assert var_95 < sample_portfolio_values[-1] * 0.1  # Should be < 10% of portfolio

    def test_var_calculation_99(self, sample_portfolio_values):
        """Test VaR calculation at 99% confidence."""
        calculator = VaRCalculator(confidence_level=0.99)
        var_99 = calculator.calculate(sample_portfolio_values)
        
        # 99% VaR should be larger than 95% VaR
        calculator_95 = VaRCalculator(confidence_level=0.95)
        var_95 = calculator_95.calculate(sample_portfolio_values)
        
        assert var_99 >= var_95

    def test_var_with_different_confidence_levels(self, sample_portfolio_values):
        """Test VaR with various confidence levels."""
        for confidence in [0.90, 0.95, 0.99]:
            calculator = VaRCalculator(confidence_level=confidence)
            var = calculator.calculate(sample_portfolio_values)
            assert var > 0


class TestCVaRCalculator:
    """Tests for CVaR (Conditional Value at Risk) calculator."""

    @pytest.fixture
    def sample_portfolio_values(self):
        """Sample portfolio values for CVaR calculation."""
        np.random.seed(42)
        initial_value = 1000000
        daily_returns = np.random.normal(0.0005, 0.01, 252)
        values = initial_value * np.exp(np.cumsum(daily_returns))
        return values

    def test_cvar_calculation_95(self, sample_portfolio_values):
        """Test CVaR calculation at 95% confidence."""
        calculator = CVaRCalculator(confidence_level=0.95)
        cvar_95 = calculator.calculate(sample_portfolio_values)
        
        assert cvar_95 > 0
        # CVaR should be >= VaR (it's the average of worse cases)
        var_calculator = VaRCalculator(confidence_level=0.95)
        var_95 = var_calculator.calculate(sample_portfolio_values)
        assert cvar_95 >= var_95

    def test_cvar_calculation_99(self, sample_portfolio_values):
        """Test CVaR calculation at 99% confidence."""
        calculator = CVaRCalculator(confidence_level=0.99)
        cvar_99 = calculator.calculate(sample_portfolio_values)
        
        # 99% CVaR should be larger than 95% CVaR
        calculator_95 = CVaRCalculator(confidence_level=0.95)
        cvar_95 = calculator_95.calculate(sample_portfolio_values)
        
        assert cvar_99 >= cvar_95

    def test_cvar_greater_than_var(self, sample_portfolio_values):
        """Test that CVaR is always >= VaR."""
        for confidence in [0.90, 0.95, 0.99]:
            var_calc = VaRCalculator(confidence_level=confidence)
            cvar_calc = CVaRCalculator(confidence_level=confidence)
            
            var = var_calc.calculate(sample_portfolio_values)
            cvar = cvar_calc.calculate(sample_portfolio_values)
            
            assert cvar >= var


class TestTransactionCostModeling:
    """Tests for transaction cost modeling."""

    def test_calculate_turnover(self):
        """Test turnover calculation."""
        previous_weights = np.array([0.2, 0.3, 0.2, 0.15, 0.15])
        new_weights = np.array([0.25, 0.25, 0.20, 0.15, 0.15])
        
        optimizer = PortfolioOptimizer()
        turnover = optimizer._calculate_turnover(previous_weights, new_weights)
        
        # Turnover = sum of absolute changes / 2
        expected_turnover = np.sum(np.abs(new_weights - previous_weights)) / 2
        assert abs(turnover - expected_turnover) < 0.0001

    def test_transaction_cost_calculation(self):
        """Test transaction cost calculation."""
        previous_weights = np.array([0.2, 0.3, 0.2, 0.15, 0.15])
        new_weights = np.array([0.25, 0.25, 0.20, 0.15, 0.15])
        portfolio_value = 1000000
        
        optimizer = PortfolioOptimizer()
        optimizer.transaction_cost_rate = 0.001  # 0.1%
        
        cost = optimizer._calculate_transaction_cost(
            previous_weights, new_weights, portfolio_value
        )
        
        expected_turnover = np.sum(np.abs(new_weights - previous_weights)) / 2
        expected_cost = expected_turnover * portfolio_value * 0.001
        assert abs(cost - expected_cost) < 0.01


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_optimization_with_negative_returns(self):
        """Test optimization with negative expected returns."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        
        negative_returns = np.array([-0.05, -0.03, -0.02, -0.04, -0.01])
        covariance = np.eye(5) * 0.01
        tickers = ["A", "B", "C", "D", "E"]
        
        result = optimizer.optimize(negative_returns, covariance, tickers)
        
        assert isinstance(result, OptimizationResult)
        assert len(result.weights) == 5

    def test_optimization_with_high_correlation(self):
        """Test optimization with highly correlated assets."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("mean_variance")
        
        returns = np.array([0.05, 0.06, 0.07, 0.08, 0.09])
        # High correlation matrix
        covariance = np.array([
            [0.0100, 0.0095, 0.0090, 0.0085, 0.0080],
            [0.0095, 0.0100, 0.0095, 0.0090, 0.0085],
            [0.0090, 0.0095, 0.0100, 0.0095, 0.0090],
            [0.0085, 0.0090, 0.0095, 0.0100, 0.0095],
            [0.0080, 0.0085, 0.0090, 0.0095, 0.0100],
        ])
        tickers = ["A", "B", "C", "D", "E"]
        
        result = optimizer.optimize(returns, covariance, tickers)
        
        assert isinstance(result, OptimizationResult)
        assert abs(sum(result.weights) - 1.0) < 0.001

    def test_optimization_with_zero_returns(self):
        """Test optimization with zero expected returns."""
        optimizer = PortfolioOptimizer()
        optimizer.set_method("min_variance")  # Use min variance when returns are zero
        
        zero_returns = np.zeros(5)
        covariance = np.eye(5) * 0.01
        tickers = ["A", "B", "C", "D", "E"]
        
        result = optimizer.optimize(zero_returns, covariance, tickers)
        
        assert isinstance(result, OptimizationResult)
        # Min variance should still produce valid weights
        assert abs(sum(result.weights) - 1.0) < 0.001

    def test_invalid_optimization_method(self):
        """Test that invalid method raises error."""
        optimizer = PortfolioOptimizer()
        
        with pytest.raises(ValueError):
            optimizer.set_method("invalid_method")

    def test_mismatched_dimensions(self):
        """Test optimization with mismatched return/covariance dimensions."""
        optimizer = PortfolioOptimizer()
        
        returns = np.array([0.05, 0.06, 0.07])  # 3 assets
        covariance = np.eye(5) * 0.01  # 5x5 matrix
        tickers = ["A", "B", "C", "D", "E"]
        
        with pytest.raises(ValueError):
            optimizer.optimize(returns, covariance, tickers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])