"""
Tests for Factor Analysis Engine.

These tests verify that the factor calculation engine correctly:
- Calculates value, momentum, quality, volatility, and size factors
- Normalizes factors using sector-neutral z-scores
- Winsorizes at 1st/99th percentiles
- Calculates Information Coefficient (IC) for validation
- Handles missing data gracefully

Run with: pytest factors/test_factors.py -v

TDD Phase: RED (write failing tests first)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import tempfile


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_price_data():
    """Create sample price data for testing factor calculations."""
    dates = pd.date_range(start='2024-01-01', end='2024-03-31', freq='D')
    
    data = []
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    
    for ticker in tickers:
        # Create realistic price series with trend
        base_price = 100 if ticker != 'AAPL' else 180
        for i, d in enumerate(dates):
            # Add some randomness and trend
            np.random.seed(hash(ticker + str(i)) % 2**32)
            price = base_price * (1 + 0.001 * i) * (1 + np.random.randn() * 0.02)
            data.append({
                'ticker': ticker,
                'date': d,
                'open': price * 0.99,
                'high': price * 1.02,
                'low': price * 0.98,
                'close': price,
                'adj_close': price,
                'volume': int(1000000 * (1 + np.random.rand()))
            })
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_fundamental_data():
    """Create sample fundamental data for testing factor calculations."""
    data = []
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    
    # Common financial metrics
    fundamentals = {
        'AAPL': {'pe': 28.5, 'pb': 45.0, 'roe': 0.45, 'roa': 0.18, 'debt_equity': 1.5, 'market_cap': 2800e9},
        'MSFT': {'pe': 35.0, 'pb': 12.0, 'roe': 0.38, 'roa': 0.15, 'debt_equity': 0.8, 'market_cap': 3100e9},
        'GOOGL': {'pe': 25.0, 'pb': 6.0, 'roe': 0.25, 'roa': 0.12, 'debt_equity': 0.3, 'market_cap': 1900e9},
        'AMZN': {'pe': 60.0, 'pb': 8.0, 'roe': 0.15, 'roa': 0.06, 'debt_equity': 0.9, 'market_cap': 1800e9},
        'META': {'pe': 30.0, 'pb': 8.0, 'roe': 0.28, 'roa': 0.12, 'debt_equity': 0.4, 'market_cap': 1200e9},
    }
    
    for ticker in tickers:
        fund = fundamentals[ticker]
        data.append({
            'ticker': ticker,
            'report_date': date(2024, 3, 31),
            'metric': 'pe_ratio',
            'value': fund['pe']
        })
        data.append({
            'ticker': ticker,
            'report_date': date(2024, 3, 31),
            'metric': 'pb_ratio',
            'value': fund['pb']
        })
        data.append({
            'ticker': ticker,
            'report_date': date(2024, 3, 31),
            'metric': 'roe',
            'value': fund['roe']
        })
        data.append({
            'ticker': ticker,
            'report_date': date(2024, 3, 31),
            'metric': 'roa',
            'value': fund['roa']
        })
        data.append({
            'ticker': ticker,
            'report_date': date(2024, 3, 31),
            'metric': 'debt_equity',
            'value': fund['debt_equity']
        })
        data.append({
            'ticker': ticker,
            'report_date': date(2024, 3, 31),
            'metric': 'market_cap',
            'value': fund['market_cap']
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    conn = sqlite3.connect(temp_file.name)
    
    # Create schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT NOT NULL,
            report_date DATE NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            PRIMARY KEY (ticker, report_date, metric)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_metadata (
            ticker TEXT PRIMARY KEY,
            sector TEXT,
            industry TEXT,
            market_cap REAL
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield temp_file.name
    
    import os
    os.unlink(temp_file.name)


# =============================================================================
# TDD Phase 1: Test Factor Calculations (RED - failing tests first)
# =============================================================================

class TestValueFactors:
    """Test value factor calculations."""
    
    def test_pe_ratio_calculation(self, sample_fundamental_data):
        """Test P/E ratio is calculated correctly."""
        from factors.calculator import ValueFactors
        
        # Create factor calculator
        calc = ValueFactors()
        
        # Calculate P/E for AAPL
        pe_values = calc.calculate_pe_ratio(sample_fundamental_data)
        
        assert 'AAPL' in pe_values.index
        assert pe_values['AAPL'] == pytest.approx(28.5, rel=0.01)
    
    def test_pb_ratio_calculation(self, sample_fundamental_data):
        """Test P/B ratio is calculated correctly."""
        from factors.calculator import ValueFactors
        
        calc = ValueFactors()
        pb_values = calc.calculate_pb_ratio(sample_fundamental_data)
        
        assert 'AAPL' in pb_values.index
        assert pb_values['AAPL'] == pytest.approx(45.0, rel=0.01)
    
    def test_ev_ebitda_calculation(self, sample_fundamental_data):
        """Test EV/EBITDA ratio calculation."""
        from factors.calculator import ValueFactors
        
        calc = ValueFactors()
        
        # Add enterprise_value and ebitda to the fundamental data
        test_data = sample_fundamental_data.copy()
        new_rows = [
            {'ticker': 'AAPL', 'report_date': date(2024, 3, 31), 'metric': 'enterprise_value', 'value': 3000e9},
            {'ticker': 'AAPL', 'report_date': date(2024, 3, 31), 'metric': 'ebitda', 'value': 120e9},
            {'ticker': 'MSFT', 'report_date': date(2024, 3, 31), 'metric': 'enterprise_value', 'value': 2500e9},
            {'ticker': 'MSFT', 'report_date': date(2024, 3, 31), 'metric': 'ebitda', 'value': 100e9},
        ]
        test_data = pd.concat([test_data, pd.DataFrame(new_rows)], ignore_index=True)
        
        ev_ebitda = calc.calculate_ev_ebitda(test_data)
        assert ev_ebitda['AAPL'] == pytest.approx(25.0, rel=0.1)


class TestMomentumFactors:
    """Test momentum factor calculations."""
    
    def test_1m_return_calculation(self, sample_price_data):
        """Test 1-month return calculation."""
        from factors.calculator import MomentumFactors
        
        calc = MomentumFactors()
        
        # Calculate 1-month return for AAPL
        returns = calc.calculate_cumulative_return(sample_price_data, window_days=21)
        
        assert 'AAPL' in returns.index
        assert isinstance(returns['AAPL'], float)
        # Return should be positive due to upward trend
        assert returns['AAPL'] > 0
    
    def test_3m_return_calculation(self, sample_price_data):
        """Test 3-month return calculation."""
        from factors.calculator import MomentumFactors
        
        calc = MomentumFactors()
        returns = calc.calculate_cumulative_return(sample_price_data, window_days=63)
        
        assert 'AAPL' in returns.index
        assert isinstance(returns['AAPL'], float)
    
    def test_rsi_calculation(self, sample_price_data):
        """Test RSI(14) calculation."""
        from factors.calculator import MomentumFactors
        
        calc = MomentumFactors()
        rsi = calc.calculate_rsi(sample_price_data, window=14)
        
        assert 'AAPL' in rsi.index
        assert 0 <= rsi['AAPL'] <= 100
    
    def test_macd_calculation(self, sample_price_data):
        """Test MACD histogram calculation."""
        from factors.calculator import MomentumFactors
        
        calc = MomentumFactors()
        macd = calc.calculate_macd(sample_price_data)
        
        assert 'AAPL' in macd.index
        assert isinstance(macd['AAPL'], float)


class TestQualityFactors:
    """Test quality factor calculations."""
    
    def test_roe_calculation(self, sample_fundamental_data):
        """Test ROE calculation."""
        from factors.calculator import QualityFactors
        
        calc = QualityFactors()
        roe = calc.calculate_roe(sample_fundamental_data)
        
        assert 'AAPL' in roe.index
        assert roe['AAPL'] == pytest.approx(0.45, rel=0.01)
    
    def test_roa_calculation(self, sample_fundamental_data):
        """Test ROA calculation."""
        from factors.calculator import QualityFactors
        
        calc = QualityFactors()
        roa = calc.calculate_roa(sample_fundamental_data)
        
        assert 'AAPL' in roa.index
        assert roa['AAPL'] == pytest.approx(0.18, rel=0.01)
    
    def test_debt_equity_calculation(self, sample_fundamental_data):
        """Test debt/equity calculation."""
        from factors.calculator import QualityFactors
        
        calc = QualityFactors()
        de = calc.calculate_debt_equity(sample_fundamental_data)
        
        assert 'AAPL' in de.index
        assert de['AAPL'] == pytest.approx(1.5, rel=0.01)


class TestVolatilityFactors:
    """Test volatility factor calculations."""
    
    def test_historical_volatility_calculation(self, sample_price_data):
        """Test 20-day historical volatility calculation."""
        from factors.calculator import VolatilityFactors
        
        calc = VolatilityFactors()
        vol = calc.calculate_historical_volatility(sample_price_data, window_days=20)
        
        assert 'AAPL' in vol.index
        assert vol['AAPL'] > 0
        assert vol['AAPL'] < 1  # Volatility should be less than 100%
    
    def test_beta_calculation(self, sample_price_data):
        """Test beta calculation against market (SPY)."""
        from factors.calculator import VolatilityFactors
        
        calc = VolatilityFactors()
        
        # Create mock market data
        market_data = sample_price_data.copy()
        market_data['ticker'] = 'SPY'
        
        beta = calc.calculate_beta(sample_price_data, market_data)
        
        assert 'AAPL' in beta.index
        assert isinstance(beta['AAPL'], float)


class TestSizeFactor:
    """Test size factor calculation."""
    
    def test_market_cap_percentile_calculation(self, sample_fundamental_data):
        """Test market cap percentile calculation."""
        from factors.calculator import SizeFactor
        
        calc = SizeFactor()
        size = calc.calculate_market_cap_percentile(sample_fundamental_data)
        
        assert 'AAPL' in size.index
        assert 0 <= size['AAPL'] <= 1
        # AAPL has the largest market cap, should be at 100th percentile
        assert size['AAPL'] >= 0.8


# =============================================================================
# TDD Phase 2: Test Normalization and Winsorization (RED)
# =============================================================================

class TestNormalization:
    """Test factor normalization."""
    
    def test_zscore_normalization(self):
        """Test z-score normalization."""
        from factors.preprocessing import normalize_zscore
        
        # Create sample factor values
        factors = pd.Series({'AAPL': 100, 'MSFT': 200, 'GOOGL': 150})
        
        normalized = normalize_zscore(factors)
        
        # Mean should be 0, std should be 1
        assert normalized.mean() == pytest.approx(0, abs=1e-10)
        assert normalized.std() == pytest.approx(1, rel=0.01)
    
    def test_sector_neutral_zscore(self):
        """Test sector-neutral z-score normalization."""
        from factors.preprocessing import normalize_sector_neutral
        
        # Create sample data with sector information
        factors = pd.Series({'AAPL': 100, 'MSFT': 200, 'GOOGL': 150})
        sectors = pd.Series({'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech'})
        
        normalized = normalize_sector_neutral(factors, sectors)
        
        # Within-sector mean should be 0
        assert normalized.mean() == pytest.approx(0, abs=1e-10)


class TestWinsorization:
    """Test winsorization."""
    
    def test_winsorize_1st_99th_percentile(self):
        """Test winsorization at 1st and 99th percentiles."""
        from factors.preprocessing import winsorize
        
        # Create data with outliers
        factors = pd.Series({
            'AAPL': 100, 'MSFT': 200, 'GOOGL': 150,
            'OUTLIER_LOW': -1000, 'OUTLIER_HIGH': 1000
        })
        
        winsorized = winsorize(factors, lower_percentile=0.01, upper_percentile=0.99)
        
        # Outliers should be clipped to be less extreme
        # The exact values depend on the percentile calculation
        assert abs(winsorized['OUTLIER_LOW']) < abs(factors['OUTLIER_LOW'])
        assert abs(winsorized['OUTLIER_HIGH']) < abs(factors['OUTLIER_HIGH'])


# =============================================================================
# TDD Phase 3: Test IC Calculation (RED)
# =============================================================================

class TestICCalculation:
    """Test Information Coefficient calculation."""
    
    def test_ic_calculation(self):
        """Test IC calculation between factors and forward returns."""
        from factors.validation import calculate_ic
        
        # Create sample factor values and forward returns
        factors = pd.Series({'AAPL': 0.5, 'MSFT': 0.3, 'GOOGL': 0.7, 'AMZN': 0.4, 'META': 0.6})
        returns = pd.Series({'AAPL': 0.05, 'MSFT': 0.03, 'GOOGL': 0.08, 'AMZN': 0.02, 'META': 0.07})
        
        ic = calculate_ic(factors, returns)
        
        # IC should be between -1 and 1
        assert -1 <= ic <= 1
        # For positively correlated data, IC should be positive
        assert ic > 0
    
    def test_ic_with_missing_data(self):
        """Test IC calculation handles missing data."""
        from factors.validation import calculate_ic
        
        factors = pd.Series({'AAPL': 0.5, 'MSFT': 0.3, 'GOOGL': 0.7, 'AMZN': np.nan})
        returns = pd.Series({'AAPL': 0.05, 'MSFT': 0.03, 'GOOGL': 0.08, 'AMZN': 0.02})
        
        ic = calculate_ic(factors, returns)
        
        # Should still calculate IC, ignoring NaN
        assert -1 <= ic <= 1
    
    def test_rank_ic_calculation(self):
        """Test Rank IC (Spearman correlation) calculation."""
        from factors.validation import calculate_rank_ic
        
        factors = pd.Series({'AAPL': 0.5, 'MSFT': 0.3, 'GOOGL': 0.7, 'AMZN': 0.4, 'META': 0.6})
        returns = pd.Series({'AAPL': 0.05, 'MSFT': 0.03, 'GOOGL': 0.08, 'AMZN': 0.02, 'META': 0.07})
        
        rank_ic = calculate_rank_ic(factors, returns)
        
        assert -1 <= rank_ic <= 1


# =============================================================================
# TDD Phase 4: Test Missing Data Handling (RED)
# =============================================================================

class TestMissingDataHandling:
    """Test missing data handling."""
    
    def test_missing_value_imputation_sector_median(self):
        """Test sector median imputation for missing values."""
        from factors.preprocessing import impute_missing_values
        
        factors = pd.Series({'AAPL': 0.5, 'MSFT': 0.3, 'GOOGL': np.nan, 'AMZN': 0.4})
        sectors = pd.Series({'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'AMZN': 'Retail'})
        
        imputed = impute_missing_values(factors, sectors, method='sector_median')
        
        # GOOGL should be imputed with Tech sector median (0.4)
        assert not np.isnan(imputed['GOOGL'])
        assert imputed['GOOGL'] == pytest.approx(0.4, rel=0.01)
    
    def test_missing_factor_returns_nan(self):
        """Test that missing factors return NaN, not zeros."""
        from factors.calculator import ValueFactors
        
        calc = ValueFactors()
        
        # Create data with missing P/E for one ticker
        factors = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'report_date': [date(2024, 3, 31), date(2024, 3, 31)],
            'metric': ['pe_ratio', 'pe_ratio'],
            'value': [28.5, np.nan]
        })
        
        pe_values = calc.calculate_pe_ratio(factors)
        
        assert np.isnan(pe_values['MSFT'])


# =============================================================================
# TDD Phase 5: Test Factor Library (RED)
# =============================================================================

class TestFactorLibrary:
    """Test factor library and metadata."""
    
    def test_factor_library_contains_all_factors(self):
        """Test that factor library contains all 20+ required factors."""
        from factors.library import FactorLibrary
        
        library = FactorLibrary()
        
        # Check all required factor categories
        assert len(library.get_factors_by_category('value')) >= 5
        assert len(library.get_factors_by_category('momentum')) >= 6
        assert len(library.get_factors_by_category('quality')) >= 5
        assert len(library.get_factors_by_category('volatility')) >= 3
        assert len(library.get_factors_by_category('size')) >= 1
        
        # Total should be 20+
        total_factors = len(library.list_all_factors())
        assert total_factors >= 20
    
    def test_factor_metadata(self):
        """Test factor metadata is properly stored."""
        from factors.library import FactorLibrary
        
        library = FactorLibrary()
        
        pe_metadata = library.get_factor_metadata('pe_ratio')
        
        assert pe_metadata is not None
        assert pe_metadata['category'] == 'value'
        assert 'description' in pe_metadata
        assert 'formula' in pe_metadata
    
    def test_factor_calculation_frequency(self):
        """Test factor calculation frequency is defined."""
        from factors.library import FactorLibrary
        
        library = FactorLibrary()
        
        pe_metadata = library.get_factor_metadata('pe_ratio')
        
        assert 'calculation_frequency' in pe_metadata
        assert pe_metadata['calculation_frequency'] in ['daily', 'weekly', 'monthly', 'quarterly']


# =============================================================================
# TDD Phase 6: Test Integration (RED)
# =============================================================================

class TestFactorEngineIntegration:
    """Test end-to-end factor calculation."""
    
    def test_calculate_all_factors_for_universe(self, sample_price_data, sample_fundamental_data, temp_db):
        """Test calculating all factors for a universe of stocks."""
        from factors.engine import FactorEngine
        
        engine = FactorEngine(db_path=temp_db)
        
        # Mock the data retrieval methods to return our sample data
        with patch.object(engine, '_get_price_data', return_value=sample_price_data):
            with patch.object(engine, '_get_fundamental_data', return_value=sample_fundamental_data):
                # Calculate all factors
                factors_df = engine.calculate_all_factors(
                    tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
                    date=date(2024, 3, 31)
                )
        
        # Should have factors for all tickers
        assert len(factors_df) == 5
        
        # Should have multiple factor columns
        factor_columns = [col for col in factors_df.columns if col not in ['ticker', 'date', 'sector']]
        assert len(factor_columns) >= 5  # At least 5 factors calculated
    
    def test_factor_pipeline_normalization(self, sample_price_data, sample_fundamental_data, temp_db):
        """Test that factor pipeline includes normalization."""
        from factors.engine import FactorEngine
        
        engine = FactorEngine(db_path=temp_db)
        
        # Mock the data retrieval methods to return our sample data
        with patch.object(engine, '_get_price_data', return_value=sample_price_data):
            with patch.object(engine, '_get_fundamental_data', return_value=sample_fundamental_data):
                factors_df = engine.calculate_all_factors(
                    tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
                    date=date(2024, 3, 31),
                    normalize=True
                )
        
        # After normalization, factor means should be close to 0
        factor_columns = [col for col in factors_df.columns if col not in ['ticker', 'date', 'sector']]
        for col in factor_columns[:3]:  # Check first 3 factors
            assert factors_df[col].mean() == pytest.approx(0, abs=0.1)


# =============================================================================
# TDD Phase 7: Test Performance Requirements (RED)
# =============================================================================

class TestPerformanceRequirements:
    """Test performance requirements."""
    
    def test_factor_calculation_performance(self, sample_price_data, sample_fundamental_data, temp_db):
        """Test factor calculation meets performance requirements."""
        from factors.engine import FactorEngine
        import time
        
        engine = FactorEngine(db_path=temp_db)
        
        # Create larger dataset for performance testing
        tickers = [f'STOCK_{i}' for i in range(50)]
        
        # Create larger sample data
        large_price_data = sample_price_data.copy()
        large_fundamental_data = sample_fundamental_data.copy()
        
        start_time = time.time()
        with patch.object(engine, '_get_price_data', return_value=large_price_data):
            with patch.object(engine, '_get_fundamental_data', return_value=large_fundamental_data):
                factors_df = engine.calculate_all_factors(
                    tickers=tickers,
                    date=date(2024, 3, 31)
                )
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (5 minutes for 20 factors x 500 stocks)
        # For 50 stocks, should be < 30 seconds
        assert elapsed < 30, f"Factor calculation took {elapsed:.2f}s, expected < 30s"
    
    def test_ic_calculation_performance(self):
        """Test IC calculation meets performance requirements."""
        from factors.validation import calculate_ic
        import time
        
        # Create larger dataset
        factors = pd.Series(np.random.randn(500))
        returns = pd.Series(np.random.randn(500))
        
        start_time = time.time()
        ic = calculate_ic(factors, returns)
        elapsed = time.time() - start_time
        
        # IC calculation should be < 1 second for 500 stocks
        assert elapsed < 1, f"IC calculation took {elapsed:.2f}s, expected < 1s"


# =============================================================================
# TDD Phase 8: Test Backtesting Framework (RED)
# =============================================================================

class TestBacktestingFramework:
    """Test factor backtesting framework."""
    
    def test_walk_forward_validation(self, temp_db):
        """Test walk-forward validation framework."""
        from factors.backtesting import WalkForwardValidator
        
        validator = WalkForwardValidator(db_path=temp_db)
        
        # Create sample historical data (use 'ME' instead of deprecated 'M')
        dates = pd.date_range(start='2023-01-01', end='2024-03-31', freq='ME')
        
        # Mock factor and return data
        factor_data = {d: pd.Series(np.random.randn(50)) for d in dates}
        return_data = {d: pd.Series(np.random.randn(50)) for d in dates}
        
        results = validator.run_walk_forward(
            factor_data=factor_data,
            return_data=return_data,
            train_window_days=365,
            test_window_days=30
        )
        
        assert 'ic_mean' in results
        assert 'ic_std' in results
        assert results['ic_mean'] is not None
    
    def test_icir_calculation(self):
        """Test IC Information Ratio (ICIR) calculation."""
        from factors.backtesting import calculate_icir
        
        # Create sample IC time series
        ic_series = pd.Series([0.05, 0.08, 0.03, 0.10, 0.06, 0.04, 0.09, 0.07])
        
        icir = calculate_icir(ic_series)
        
        # ICIR should be IC_mean / IC_std
        assert icir > 0
        assert isinstance(icir, float)


# =============================================================================
# TDD Phase 9: Test Factor Correlation Analysis (RED)
# =============================================================================

class TestFactorCorrelation:
    """Test factor correlation analysis."""
    
    def test_factor_correlation_matrix(self, temp_db):
        """Test factor correlation matrix calculation."""
        from factors.analysis import FactorCorrelationAnalyzer
        
        analyzer = FactorCorrelationAnalyzer()
        
        # Create sample factor data
        factors_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'] * 10,
            'date': pd.date_range('2024-01-01', periods=50, freq='W-FRI'),
            'pe_ratio': np.random.randn(50),
            'pb_ratio': np.random.randn(50),
            'roe': np.random.randn(50),
            'momentum_1m': np.random.randn(50),
        })
        
        corr_matrix = analyzer.calculate_correlation_matrix(factors_df)
        
        assert corr_matrix.shape[0] == corr_matrix.shape[1]
        assert 'pe_ratio' in corr_matrix.index
        assert 'pb_ratio' in corr_matrix.columns
    
    def test_high_correlation_detection(self, temp_db):
        """Test detection of highly correlated factors."""
        from factors.analysis import FactorCorrelationAnalyzer
        
        analyzer = FactorCorrelationAnalyzer()
        
        # Create factor data with known high correlation
        np.random.seed(42)
        base_factor = np.random.randn(50)
        factors_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'] * 10,
            'date': pd.date_range('2024-01-01', periods=50, freq='W-FRI'),
            'factor_a': base_factor,
            'factor_b': base_factor * 0.95 + np.random.randn(50) * 0.1,  # Highly correlated with factor_a
        })
        
        high_corr_pairs = analyzer.find_high_correlation_pairs(factors_df, threshold=0.7)
        
        # Should detect the high correlation
        assert len(high_corr_pairs) > 0