"""
Factor Analysis Engine for Quantitative Trading System.

This module provides a complete factor analysis system including:
- Factor calculations (value, momentum, quality, volatility, size)
- Factor preprocessing (normalization, winsorization)
- Factor validation (IC calculation, walk-forward testing)
- Factor library with metadata
- Factor correlation analysis

Usage:
    from factors import FactorEngine, FactorLibrary
    
    # Calculate factors
    engine = FactorEngine(db_path="data/universe.db")
    factors_df = engine.calculate_all_factors(
        tickers=["AAPL", "MSFT", "GOOGL"],
        date=date(2024, 3, 31)
    )
    
    # Access factor metadata
    library = FactorLibrary()
    pe_metadata = library.get_factor_metadata("pe_ratio")
"""

from factors.calculator import (
    ValueFactors,
    MomentumFactors,
    QualityFactors,
    VolatilityFactors,
    SizeFactor,
)
from factors.preprocessing import (
    normalize_zscore,
    normalize_sector_neutral,
    winsorize,
    impute_missing_values,
    normalize_and_winsorize,
)
from factors.validation import (
    calculate_ic,
    calculate_rank_ic,
    calculate_ic_series,
    calculate_icir,
)
from factors.library import FactorLibrary, FactorMetadata
from factors.engine import FactorEngine
from factors.backtesting import (
    WalkForwardValidator,
    calculate_icir,
    calculate_factor_returns,
    run_factor_validation,
)
from factors.analysis import (
    FactorCorrelationAnalyzer,
    FactorOptimizer,
)

__all__ = [
    # Calculator
    "ValueFactors",
    "MomentumFactors",
    "QualityFactors",
    "VolatilityFactors",
    "SizeFactor",
    # Preprocessing
    "normalize_zscore",
    "normalize_sector_neutral",
    "winsorize",
    "impute_missing_values",
    "normalize_and_winsorize",
    # Validation
    "calculate_ic",
    "calculate_rank_ic",
    "calculate_ic_series",
    "calculate_icir",
    # Library
    "FactorLibrary",
    "FactorMetadata",
    # Engine
    "FactorEngine",
    # Backtesting
    "WalkForwardValidator",
    "calculate_factor_returns",
    "run_factor_validation",
    # Analysis
    "FactorCorrelationAnalyzer",
    "FactorOptimizer",
]

__version__ = "1.0.0"