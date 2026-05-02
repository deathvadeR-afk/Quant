"""
Unit Tests for Data Quality Module.

This test suite covers:
- DataQualityConfig configuration
- Missing value detection and handling
- Duplicate detection and handling
- Outlier detection with multiple methods
- Data consistency validation
- Invalid entry detection
- DataQualityManager integration
- Pipeline integration functions
- Edge cases and error handling

Author: Quant Team
Version: 1.0.0
"""

import unittest
import pandas as pd
import numpy as np
import sqlite3
import os
import tempfile
import json
from datetime import datetime, timedelta
from typing import List, Dict

# Import the data quality module
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from data.data_quality import (
    # Enums
    HandlingStrategy,
    OutlierMethod,
    DataType,
    
    # Config and Data Classes
    DataQualityConfig,
    DataQualityIssue,
    DataQualityMetrics,
    
    # Handlers
    MissingValueHandler,
    DuplicateHandler,
    OutlierHandler,
    ConsistencyValidator,
    InvalidEntryDetector,
    
    # Main Manager
    DataQualityManager,
    
    # Pipeline Functions
    validate_price_data,
    validate_fundamental_data,
    run_full_data_quality_check,
    
    # Legacy Functions
    detect_price_spikes,
    detect_volume_anomalies,
    check_data_gaps,
    validate_price_data_completeness,
    validate_data_consistency,
    run_data_validation_pipeline,
)


class TestDataQualityConfig(unittest.TestCase):
    """Test cases for DataQualityConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DataQualityConfig()
        
        self.assertEqual(config.max_missing_price_pct, 0.05)
        self.assertEqual(config.zscore_threshold, 5.0)
        self.assertEqual(config.iqr_multiplier, 1.5)
        self.assertEqual(config.outlier_method, OutlierMethod.ZSCORE)
        self.assertEqual(config.missing_strategy, HandlingStrategy.FORWARD_FILL)
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = DataQualityConfig(
            max_missing_price_pct=0.10,
            zscore_threshold=3.0,
            missing_strategy=HandlingStrategy.INTERPOLATE,
            outlier_method=OutlierMethod.IQR
        )
        
        self.assertEqual(config.max_missing_price_pct, 0.10)
        self.assertEqual(config.zscore_threshold, 3.0)
        self.assertEqual(config.missing_strategy, HandlingStrategy.INTERPOLATE)
        self.assertEqual(config.outlier_method, OutlierMethod.IQR)
    
    def test_config_to_dict(self):
        """Test configuration serialization to dictionary."""
        config = DataQualityConfig()
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertIn('max_missing_price_pct', config_dict)
        self.assertIn('zscore_threshold', config_dict)
        self.assertEqual(config_dict['missing_strategy'], 'forward_fill')
    
    def test_config_from_dict(self):
        """Test configuration deserialization from dictionary."""
        config_dict = {
            'max_missing_price_pct': 0.15,
            'zscore_threshold': 4.0,
            'missing_strategy': 'interpolate',
            'outlier_method': 'iqr'
        }
        
        config = DataQualityConfig.from_dict(config_dict)
        
        self.assertEqual(config.max_missing_price_pct, 0.15)
        self.assertEqual(config.zscore_threshold, 4.0)
        self.assertEqual(config.missing_strategy, HandlingStrategy.INTERPOLATE)
        self.assertEqual(config.outlier_method, OutlierMethod.IQR)


class TestMissingValueHandler(unittest.TestCase):
    """Test cases for MissingValueHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DataQualityConfig()
        self.handler = MissingValueHandler(self.config)
        
        # Create sample data with missing values
        self.df_with_missing = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL', 'AAPL', 'MSFT', 'MSFT'],
            'date': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-01', '2023-01-02'],
            'close': [150.0, np.nan, 152.0, 280.0, np.nan],
            'volume': [1000000, 1100000, np.nan, 900000, 950000]
        })
    
    def test_detect_missing(self):
        """Test missing value detection."""
        missing_info = self.handler.detect_missing(self.df_with_missing)
        
        self.assertTrue(missing_info['close'].sum() == 2)
        self.assertTrue(missing_info['volume'].sum() == 1)
    
    def test_get_missing_summary(self):
        """Test missing value summary."""
        summary = self.handler.get_missing_summary(self.df_with_missing)
        
        self.assertIn('close', summary.index)
        self.assertIn('volume', summary.index)
        self.assertEqual(summary.loc['close', 'missing'], 2)
        self.assertEqual(summary.loc['volume', 'missing'], 1)
    
    def test_handle_missing_forward_fill(self):
        """Test forward fill strategy."""
        df, issues = self.handler.handle_missing(
            self.df_with_missing.copy(),
            ['close'],
            strategy=HandlingStrategy.FORWARD_FILL
        )
        
        # Check that missing values were filled
        self.assertFalse(df['close'].isna().any())
        self.assertEqual(df.loc[1, 'close'], 150.0)  # Forward filled from 2023-01-01
    
    def test_handle_missing_backward_fill(self):
        """Test backward fill strategy."""
        df, issues = self.handler.handle_missing(
            self.df_with_missing.copy(),
            ['close'],
            strategy=HandlingStrategy.BACKWARD_FILL
        )
        
        # Check that missing values were filled
        self.assertFalse(df['close'].isna().any())
        self.assertEqual(df.loc[1, 'close'], 152.0)  # Backward filled from 2023-01-03
    
    def test_handle_missing_interpolate(self):
        """Test linear interpolation strategy."""
        df, issues = self.handler.handle_missing(
            self.df_with_missing.copy(),
            ['close'],
            strategy=HandlingStrategy.INTERPOLATE
        )
        
        # Check that missing values were interpolated
        self.assertFalse(df['close'].isna().any())
        # Should be interpolated between 150 and 152
        self.assertAlmostEqual(df.loc[1, 'close'], 151.0, places=1)
    
    def test_handle_missing_impute_mean(self):
        """Test mean imputation strategy."""
        df, issues = self.handler.handle_missing(
            self.df_with_missing.copy(),
            ['close'],
            strategy=HandlingStrategy.IMPUTE_MEAN
        )
        
        # Check that missing values were imputed with mean
        self.assertFalse(df['close'].isna().any())
        # Mean of [150, 152] = 151
        self.assertEqual(df.loc[1, 'close'], 151.0)
        self.assertEqual(df.loc[4, 'close'], 151.0)
    
    def test_handle_missing_impute_median(self):
        """Test median imputation strategy."""
        df, issues = self.handler.handle_missing(
            self.df_with_missing.copy(),
            ['close'],
            strategy=HandlingStrategy.IMPUTE_MEDIAN
        )
        
        # Check that missing values were imputed with median
        self.assertFalse(df['close'].isna().any())
        # Median of [150, 152] = 151
        self.assertEqual(df.loc[1, 'close'], 151.0)
    
    def test_handle_missing_remove(self):
        """Test remove strategy."""
        original_len = len(self.df_with_missing)
        df, issues = self.handler.handle_missing(
            self.df_with_missing.copy(),
            ['close'],
            strategy=HandlingStrategy.REMOVE
        )
        
        # Should have removed rows with missing close values
        self.assertEqual(len(df), original_len - 2)
        self.assertFalse(df['close'].isna().any())
    
    def test_handle_missing_flag(self):
        """Test flag strategy."""
        df, issues = self.handler.handle_missing(
            self.df_with_missing.copy(),
            ['close'],
            strategy=HandlingStrategy.FLAG
        )
        
        # Should have created flag columns
        self.assertIn('close_missing', df.columns)
        self.assertEqual(df['close_missing'].sum(), 2)


class TestDuplicateHandler(unittest.TestCase):
    """Test cases for DuplicateHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DataQualityConfig()
        self.handler = DuplicateHandler(self.config)
        
        # Create sample data with duplicates
        self.df_with_duplicates = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL', 'AAPL', 'MSFT', 'MSFT'],
            'date': ['2023-01-01', '2023-01-01', '2023-01-02', '2023-01-01', '2023-01-01'],
            'close': [150.0, 150.0, 152.0, 280.0, 280.0]
        })
        
        self.df_no_duplicates = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'date': ['2023-01-01', '2023-01-01'],
            'close': [150.0, 280.0]
        })
    
    def test_detect_duplicates(self):
        """Test duplicate detection."""
        duplicates = self.handler.detect_duplicates(
            self.df_with_duplicates,
            subset=['ticker', 'date']
        )
        
        # Should find 2 duplicate rows (AAPL 2023-01-01 and MSFT 2023-01-01)
        self.assertEqual(len(duplicates), 2)
    
    def test_get_duplicate_summary(self):
        """Test duplicate summary."""
        summary = self.handler.get_duplicate_summary(
            self.df_with_duplicates,
            subset=['ticker', 'date']
        )
        
        self.assertEqual(summary['total_duplicates'], 2)
        self.assertGreater(summary['duplicate_pct'], 0)
    
    def test_detect_no_duplicates(self):
        """Test detection when there are no duplicates."""
        duplicates = self.handler.detect_duplicates(
            self.df_no_duplicates,
            subset=['ticker', 'date']
        )
        
        self.assertEqual(len(duplicates), 0)
    
    def test_handle_duplicates_remove(self):
        """Test remove strategy for duplicates."""
        df, issues = self.handler.handle_duplicates(
            self.df_with_duplicates.copy(),
            subset=['ticker', 'date'],
            strategy=HandlingStrategy.REMOVE
        )
        
        # Should have removed duplicates
        self.assertEqual(len(df), 3)  # 5 - 2 duplicates
    
    def test_handle_duplicates_flag(self):
        """Test flag strategy for duplicates."""
        df, issues = self.handler.handle_duplicates(
            self.df_with_duplicates.copy(),
            subset=['ticker', 'date'],
            strategy=HandlingStrategy.FLAG
        )
        
        # Should have created duplicate flag column
        self.assertIn('_is_duplicate', df.columns)
        self.assertEqual(df['_is_duplicate'].sum(), 2)


class TestOutlierHandler(unittest.TestCase):
    """Test cases for OutlierHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DataQualityConfig(zscore_threshold=2.0)
        self.handler = OutlierHandler(self.config)
        
        # Create sample data with outliers
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 100)
        outliers = np.array([200, 250, 300])  # Clear outliers
        self.data_with_outliers = np.concatenate([normal_data, outliers])
        
        self.series_with_outliers = pd.Series(self.data_with_outliers)
        self.series_normal = pd.Series(np.random.normal(100, 10, 100))
    
    def test_detect_zscore_outliers(self):
        """Test Z-score outlier detection."""
        outliers = self.handler.detect_zscore_outliers(self.series_with_outliers)
        
        # Should detect the 3 obvious outliers
        self.assertEqual(outliers.sum(), 3)
    
    def test_detect_iqr_outliers(self):
        """Test IQR outlier detection."""
        outliers = self.handler.detect_iqr_outliers(
            self.series_with_outliers,
            multiplier=1.5
        )
        
        # Should detect outliers using IQR method
        self.assertGreater(outliers.sum(), 0)
    
    def test_detect_modified_zscore_outliers(self):
        """Test modified Z-score outlier detection."""
        outliers = self.handler.detect_modified_zscore_outliers(self.series_with_outliers)
        
        # Should detect outliers using modified Z-score
        self.assertGreater(outliers.sum(), 0)
    
    def test_detect_percentile_outliers(self):
        """Test percentile outlier detection."""
        outliers = self.handler.detect_percentile_outliers(
            self.series_with_outliers,
            lower=1.0,
            upper=99.0
        )
        
        # Should detect outliers using percentile method
        self.assertGreater(outliers.sum(), 0)
    
    def test_no_outliers_normal_data(self):
        """Test that normal data has no outliers."""
        outliers = self.handler.detect_zscore_outliers(self.series_normal)
        
        # Should have few or no outliers
        self.assertLess(outliers.sum(), 5)
    
    def test_handle_outliers_flag(self):
        """Test flag strategy for outliers."""
        df = pd.DataFrame({'value': self.data_with_outliers})
        
        df_cleaned, issues = self.handler.handle_outliers(
            df,
            'value',
            method=OutlierMethod.ZSCORE,
            strategy=HandlingStrategy.FLAG
        )
        
        self.assertIn('value_is_outlier', df_cleaned.columns)
        self.assertEqual(len(issues), 2)  # Detection + flagging
    
    def test_handle_outliers_winsorize(self):
        """Test winsorize strategy for outliers."""
        df = pd.DataFrame({'value': self.data_with_outliers})
        
        df_cleaned, issues = self.handler.handle_outliers(
            df,
            'value',
            method=OutlierMethod.ZSCORE,
            strategy=HandlingStrategy.WINSORIZE
        )
        
        # Values should be capped at percentile thresholds
        self.assertLessEqual(df_cleaned['value'].max(), df['value'].quantile(0.99))
    
    def test_handle_outliers_remove(self):
        """Test remove strategy for outliers."""
        df = pd.DataFrame({'value': self.data_with_outliers})
        original_len = len(df)
        
        df_cleaned, issues = self.handler.handle_outliers(
            df,
            'value',
            method=OutlierMethod.ZSCORE,
            strategy=HandlingStrategy.REMOVE
        )
        
        # Should have removed outlier rows
        self.assertLess(len(df_cleaned), original_len)


class TestConsistencyValidator(unittest.TestCase):
    """Test cases for ConsistencyValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DataQualityConfig()
        self.validator = ConsistencyValidator(self.config)
        
        # Create sample data with consistency issues
        self.df_with_issues = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL', 'MSFT'],
            'date': ['2023-01-01', '2023-01-02', '2023-01-01'],
            'open': [150, 155, 280],
            'high': [145, 160, 290],  # Lower than open - issue!
            'low': [148, 152, 275],
            'close': [152, 158, 285],
            'volume': [-100, 1000000, 900000]  # Negative volume - issue!
        })
        
        self.df_clean = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'date': ['2023-01-01', '2023-01-01'],
            'open': [150, 280],
            'high': [155, 290],
            'low': [148, 275],
            'close': [152, 285],
            'volume': [1000000, 900000]
        })
    
    def test_check_ohlc_consistency(self):
        """Test OHLC consistency check."""
        issues = self.validator.check_ohlc_consistency(self.df_with_issues)
        
        # Should find the high < open issue
        self.assertGreater(len(issues), 0)
    
    def test_check_ohlc_clean_data(self):
        """Test OHLC check with clean data."""
        issues = self.validator.check_ohlc_consistency(self.df_clean)
        
        self.assertEqual(len(issues), 0)
    
    def test_check_volume_validity(self):
        """Test volume validity check."""
        issues = self.validator.check_volume_validity(self.df_with_issues)
        
        # Should find negative volume
        self.assertGreater(len(issues), 0)
    
    def test_check_volume_clean(self):
        """Test volume check with clean data."""
        issues = self.validator.check_volume_validity(self.df_clean)
        
        self.assertEqual(len(issues), 0)
    
    def test_check_price_range(self):
        """Test price range check."""
        # Create data with out-of-range prices
        df_extreme = pd.DataFrame({
            'close': [0.0001, 150, 2000000]  # Too low and too high
        })
        
        issues = self.validator.check_price_range(df_extreme)
        
        # Should find extreme values
        self.assertGreater(len(issues), 0)
    
    def test_check_price_continuity(self):
        """Test price continuity check."""
        # Create data with gaps
        df_with_gaps = pd.DataFrame({
            'ticker': ['AAPL'] * 5,
            'date': ['2023-01-01', '2023-01-02', '2023-01-08', '2023-01-09', '2023-01-10']
        })
        
        gaps = self.validator.check_price_continuity(df_with_gaps, max_gap_days=3)
        
        # Should find gap from 2023-01-02 to 2023-01-08
        self.assertGreater(len(gaps), 0)
    
    def test_check_all_consistency(self):
        """Test full consistency check."""
        issues_dict, issues_list = self.validator.check_all_consistency(self.df_with_issues)
        
        # Should find multiple types of issues
        self.assertIn('ohlc_inconsistency', issues_dict)
        self.assertIn('invalid_volume', issues_dict)


class TestInvalidEntryDetector(unittest.TestCase):
    """Test cases for InvalidEntryDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DataQualityConfig()
        self.detector = InvalidEntryDetector(self.config)
        
        # Create data with invalid entries
        self.df_with_invalid = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOG'],
            'date': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'open': [150, -10, 280],  # Negative price
            'high': [155, 160, 290],
            'low': [148, 152, 275],
            'close': [152, 0, 285],  # Zero and negative
            'volume': [1000000, -500, 900000]  # Negative volume
        })
    
    def test_detect_invalid_prices(self):
        """Test invalid price detection."""
        issues = self.detector.detect_invalid_prices(self.df_with_invalid)
        
        # Should find negative and zero prices
        self.assertGreater(len(issues), 0)
    
    def test_detect_invalid_volume(self):
        """Test invalid volume detection."""
        issues = self.detector.detect_invalid_volume(self.df_with_invalid)
        
        # Should find negative volume
        self.assertGreater(len(issues), 0)
    
    def test_detect_all_invalid(self):
        """Test full invalid entry detection."""
        issues_dict, issues_list = self.detector.detect_all_invalid(self.df_with_invalid)
        
        self.assertIn('invalid_prices', issues_dict)
        self.assertIn('invalid_volume', issues_dict)


class TestDataQualityManager(unittest.TestCase):
    """Test cases for DataQualityManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DataQualityConfig(
            zscore_threshold=2.0,
            missing_strategy=HandlingStrategy.INTERPOLATE
        )
        self.manager = DataQualityManager(self.config)
        
        # Create sample data with multiple issues
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        
        # Generate price data with some outliers
        prices = 100 + np.random.randn(50).cumsum()
        prices[25] = 200  # Outlier
        prices[30] = 50   # Outlier
        
        self.df_with_issues = pd.DataFrame({
            'ticker': ['AAPL'] * 50,
            'date': dates,
            'open': prices + np.random.randn(50),
            'high': prices + np.abs(np.random.randn(50)) + 5,
            'low': prices - np.abs(np.random.randn(50)) - 5,
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 50)
        })
        
        # Add missing values
        self.df_with_issues.loc[10, 'close'] = np.nan
        self.df_with_issues.loc[20, 'close'] = np.nan
        
        # Add duplicate
        self.df_with_issues = pd.concat([
            self.df_with_issues,
            self.df_with_issues.iloc[[5]]
        ], ignore_index=True)
    
    def test_validate(self):
        """Test validation."""
        df, metrics, issues = self.manager.validate(
            self.df_with_issues,
            DataType.PRICE
        )
        
        # Should detect issues
        self.assertGreater(metrics.missing_values, 0)
        self.assertGreater(metrics.duplicates, 0)
        self.assertGreater(metrics.outliers, 0)
        self.assertLess(metrics.quality_score, 100)
    
    def test_clean(self):
        """Test cleaning."""
        df, issues = self.manager.clean(
            self.df_with_issues.copy(),
            DataType.PRICE
        )
        
        # Should have cleaned data
        self.assertGreater(len(issues), 0)
    
    def test_quality_score_calculation(self):
        """Test quality score calculation."""
        df, metrics, issues = self.manager.validate(
            self.df_with_issues,
            DataType.PRICE
        )
        
        # Quality score should be between 0 and 100
        self.assertGreaterEqual(metrics.quality_score, 0)
        self.assertLessEqual(metrics.quality_score, 100)
    
    def test_get_quality_report(self):
        """Test quality report generation."""
        self.manager.validate(self.df_with_issues, DataType.PRICE)
        report = self.manager.get_quality_report()
        
        self.assertIn('metrics', report)
        self.assertIn('issues', report)
        self.assertIn('config', report)
        self.assertIn('timestamp', report)
    
    def test_validate_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        df_empty = pd.DataFrame()
        
        df, metrics, issues = self.manager.validate(df_empty, DataType.PRICE)
        
        self.assertEqual(metrics.total_records, 0)
        self.assertEqual(metrics.quality_score, 100.0)


class TestPipelineFunctions(unittest.TestCase):
    """Test cases for pipeline integration functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create database schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fundamentals (
                ticker TEXT,
                report_date TEXT,
                period_end_date TEXT,
                metric TEXT,
                value REAL,
                PRIMARY KEY (ticker, report_date, metric)
            )
        """)
        
        # Insert test data
        test_prices = [
            ('AAPL', '2023-01-01', 150, 155, 148, 152, 152, 1000000),
            ('AAPL', '2023-01-02', 152, 157, 150, 155, 155, 1100000),
            ('MSFT', '2023-01-01', 280, 285, 275, 282, 282, 900000),
        ]
        
        cursor.executemany(
            "INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            test_prices
        )
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up temporary database."""
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def test_validate_price_data_function(self):
        """Test validate_price_data function."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL'],
            'date': ['2023-01-01', '2023-01-02'],
            'close': [150, np.nan],
            'volume': [1000000, 1100000]
        })
        
        df_validated, metrics, issues = validate_price_data(
            df,
            clean=True
        )
        
        # Should handle missing value
        self.assertFalse(df_validated['close'].isna().any())
    
    def test_validate_fundamental_data_function(self):
        """Test validate_fundamental_data function."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL'],
            'report_date': ['2023-01-01', '2023-01-02'],
            'value': [150.0, np.nan]
        })
        
        df_validated, metrics, issues = validate_fundamental_data(
            df,
            clean=True
        )
        
        # Should validate fundamental data
        self.assertIsNotNone(metrics)


class TestLegacyFunctions(unittest.TestCase):
    """Test cases for legacy compatibility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample price data
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = 100 + np.random.randn(100).cumsum()
        prices[50] = prices[49] * 1.5  # Create spike
        
        self.df = pd.DataFrame({
            'ticker': ['AAPL'] * 100,
            'date': dates,
            'open': prices + np.random.randn(100),
            'high': prices + np.abs(np.random.randn(100)) + 5,
            'low': prices - np.abs(np.random.randn(100)) - 5,
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100)
        })
    
    def test_detect_price_spikes(self):
        """Test legacy detect_price_spikes function."""
        spikes = detect_price_spikes(self.df, z_threshold=3.0)
        
        # Should detect at least one spike
        self.assertIsInstance(spikes, pd.DataFrame)
    
    def test_detect_volume_anomalies(self):
        """Test legacy detect_volume_anomalies function."""
        anomalies = detect_volume_anomalies(self.df, z_threshold=5.0)
        
        # Should return DataFrame
        self.assertIsInstance(anomalies, pd.DataFrame)
    
    def test_check_data_gaps(self):
        """Test legacy check_data_gaps function."""
        # Create data with gaps
        df_gaps = pd.DataFrame({
            'ticker': ['AAPL'] * 5,
            'date': ['2023-01-01', '2023-01-02', '2023-01-05', '2023-01-06', '2023-01-10']
        })
        
        gaps = check_data_gaps(df_gaps)
        
        # Should detect gaps
        self.assertIsInstance(gaps, list)
    
    def test_validate_price_data_completeness(self):
        """Test legacy validate_price_data_completeness function."""
        result = validate_price_data_completeness(self.df)
        
        self.assertIn('valid', result)
        self.assertIn('issues', result)
    
    def test_validate_data_consistency(self):
        """Test legacy validate_data_consistency function."""
        # Create data with consistency issues
        df_issues = pd.DataFrame({
            'ticker': ['AAPL'],
            'date': ['2023-01-01'],
            'open': [150],
            'high': [145],  # Lower than open - issue
            'low': [155],    # Higher than open - issue
            'close': [148]
        })
        
        result = validate_data_consistency(df_issues)
        
        # Should detect inconsistencies
        self.assertIsInstance(result, dict)


class TestEdgeCases(unittest.TestCase):
    """Test cases for edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DataQualityConfig()
        self.manager = DataQualityManager(self.config)
    
    def test_all_columns_missing(self):
        """Test handling when all values in a column are missing."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'close': [np.nan, np.nan]
        })
        
        df, metrics, issues = self.manager.validate(df, DataType.PRICE)
        
        # Should handle gracefully
        self.assertEqual(metrics.missing_values, 2)
    
    def test_single_row_dataframe(self):
        """Test handling single row DataFrame."""
        df = pd.DataFrame({
            'ticker': ['AAPL'],
            'date': ['2023-01-01'],
            'close': [150.0]
        })
        
        df, metrics, issues = self.manager.validate(df, DataType.PRICE)
        
        self.assertEqual(metrics.total_records, 1)
    
    def test_no_numeric_columns(self):
        """Test handling DataFrame with no numeric columns."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'date': ['2023-01-01', '2023-01-02']
        })
        
        df, metrics, issues = self.manager.validate(df, DataType.PRICE)
        
        # Should handle gracefully
        self.assertEqual(metrics.total_records, 2)
    
    def test_constant_values(self):
        """Test handling constant value series (zero std)."""
        df = pd.DataFrame({
            'value': [100, 100, 100, 100, 100]
        })
        
        handler = OutlierHandler(self.config)
        outliers = handler.detect_zscore_outliers(df['value'])
        
        # Should not flag constant values as outliers
        self.assertEqual(outliers.sum(), 0)
    
    def test_extreme_outliers(self):
        """Test handling extreme outliers."""
        df = pd.DataFrame({
            'value': [1, 2, 3, 4, 5, 1e10]  # Extreme outlier
        })
        
        handler = OutlierHandler(self.config)
        outliers = handler.detect_zscore_outliers(df['value'])
        
        # Should detect the extreme outlier
        self.assertEqual(outliers.sum(), 1)


class TestIntegrationWithPipeline(unittest.TestCase):
    """Integration tests with existing data pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            )
        """)
        
        # Insert test data
        test_data = [
            ('AAPL', '2023-01-01', 150, 155, 148, 152, 152, 1000000),
            ('AAPL', '2023-01-02', 152, 157, 150, 155, 155, 1100000),
            ('AAPL', '2023-01-03', 155, 160, 153, 158, 158, 1050000),
            ('MSFT', '2023-01-01', 280, 285, 275, 282, 282, 900000),
            ('MSFT', '2023-01-02', 282, 288, 280, 285, 285, 950000),
        ]
        
        cursor.executemany(
            "INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            test_data
        )
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up."""
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def test_run_data_validation_pipeline(self):
        """Test run_data_validation_pipeline function."""
        result = run_data_validation_pipeline(
            tickers=['AAPL', 'MSFT'],
            db_path=self.db_path
        )
        
        # Should return validation results
        self.assertIsNotNone(result)


# Run tests if executed directly
if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDataQualityConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestMissingValueHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestDuplicateHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestOutlierHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestConsistencyValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestInvalidEntryDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestDataQualityManager))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestLegacyFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationWithPipeline))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
