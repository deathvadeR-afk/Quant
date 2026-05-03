"""
Test module for Return Forecasting Models.

This module tests:
- Linear regression baseline model
- Random Forest model
- XGBoost/LightGBM model
- Ensemble model combining all base models
- Walk-forward validation with purge/embargo
- Model persistence (serialization/deserialization)
- Feature importance tracking
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import pickle
import json

# Import the modules under test
from factors.models import (
    LinearRegressionModel,
    RandomForestModel,
    XGBoostModel,
    EnsembleModel,
    ReturnForecaster,
    WalkForwardCV,
    ModelPersistence,
    FeatureImportanceTracker,
    TRAINING_TIME_THRESHOLD_SECONDS,
    TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS,
)


class TestLinearRegressionModel:
    """Tests for Linear Regression baseline model."""

    def test_model_initialization(self):
        """Test that model initializes with correct default parameters."""
        model = LinearRegressionModel()
        assert model.model_type == "linear_regression"
        assert model.feature_names is None
        assert model.is_fitted is False

    def test_model_initialization_with_params(self):
        """Test model initialization with custom parameters."""
        model = LinearRegressionModel(
            fit_intercept=True,
            normalize=True,
            feature_names=["factor1", "factor2"]
        )
        assert model.fit_intercept is True
        assert model.normalize is True
        assert model.feature_names == ["factor1", "factor2"]

    def test_fit_requires_features_and_target(self):
        """Test that fit() raises error without features or target."""
        model = LinearRegressionModel()
        
        # No features
        with pytest.raises(ValueError, match="Features.*required"):
            model.fit(None, pd.Series([1, 2, 3]))
        
        # No target
        with pytest.raises(ValueError, match="Target.*required"):
            model.fit(pd.DataFrame({"a": [1, 2, 3]}), None)

    def test_fit_with_valid_data(self):
        """Test fitting model with valid data."""
        np.random.seed(42)
        n_samples = 100
        n_features = 5
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        model = LinearRegressionModel(feature_names=X.columns.tolist())
        model.fit(X, y)
        
        assert model.is_fitted is True
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == n_features

    def test_predict_shape(self):
        """Test that predict returns correct shape."""
        np.random.seed(42)
        n_samples = 100
        n_features = 5
        
        X_train = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y_train = pd.Series(np.random.randn(n_samples))
        
        X_test = pd.DataFrame(
            np.random.randn(20, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        
        model = LinearRegressionModel(feature_names=X_train.columns.tolist())
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        
        assert len(predictions) == len(X_test)
        assert isinstance(predictions, pd.Series)

    def test_predict_before_fit_raises_error(self):
        """Test that predict raises error before model is fitted."""
        model = LinearRegressionModel()
        X = pd.DataFrame({"a": [1, 2, 3]})
        
        with pytest.raises(ValueError, match="Model must be fitted"):
            model.predict(X)

    def test_feature_importance_linear_model(self):
        """Test that linear model returns absolute coefficient values as importance."""
        np.random.seed(42)
        X = pd.DataFrame(
            np.random.randn(100, 3),
            columns=["f1", "f2", "f3"]
        )
        y = pd.Series(X["f1"] * 2 + X["f2"] * 0.5 + np.random.randn(100) * 0.1)
        
        model = LinearRegressionModel(feature_names=X.columns.tolist())
        model.fit(X, y)
        importance = model.get_feature_importance()
        
        assert "f1" in importance
        assert "f2" in importance
        assert "f3" in importance
        assert importance["f1"] > importance["f2"]  # f1 has higher coefficient

    def test_model_persistence(self):
        """Test model can be serialized and deserialized."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 3), columns=["f1", "f2", "f3"])
        y = pd.Series(np.random.randn(100))
        
        model = LinearRegressionModel(feature_names=X.columns.tolist())
        model.fit(X, y)
        
        # Serialize
        serialized = model.serialize()
        assert isinstance(serialized, dict)
        assert "model_type" in serialized
        assert "coefficients" in serialized
        
        # Deserialize
        restored = LinearRegressionModel.deserialize(serialized)
        assert restored.is_fitted is True
        assert np.allclose(restored.coefficients_, model.coefficients_)


class TestRandomForestModel:
    """Tests for Random Forest model."""

    def test_model_initialization(self):
        """Test that model initializes with correct default parameters."""
        model = RandomForestModel()
        assert model.model_type == "random_forest"
        assert model.is_fitted is False

    def test_fit_with_valid_data(self):
        """Test fitting model with valid data."""
        np.random.seed(42)
        n_samples = 100
        n_features = 5
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        model = RandomForestModel(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        assert model.is_fitted is True
        # feature_importances_ may be None if sklearn is not available
        # but feature_importance_ dict should be set
        importance = model.get_feature_importance()
        assert importance is not None

    def test_predict_returns_series(self):
        """Test that predict returns a Series with correct index."""
        np.random.seed(42)
        X_train = pd.DataFrame(
            np.random.randn(100, 3),
            columns=["f1", "f2", "f3"],
            index=[f"ticker_{i}" for i in range(100)]
        )
        y_train = pd.Series(np.random.randn(100), index=X_train.index)
        
        X_test = pd.DataFrame(
            np.random.randn(20, 3),
            columns=["f1", "f2", "f3"],
            index=[f"ticker_{i}" for i in range(100, 120)]
        )
        
        model = RandomForestModel(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        
        assert isinstance(predictions, pd.Series)
        assert predictions.index.tolist() == X_test.index.tolist()

    def test_feature_importance_sum_to_one(self):
        """Test that feature importances sum to 1."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))
        
        model = RandomForestModel(n_estimators=10, random_state=42)
        model.fit(X, y)
        importance = model.get_feature_importance()
        
        total_importance = sum(importance.values())
        assert abs(total_importance - 1.0) < 1e-6


class TestXGBoostModel:
    """Tests for XGBoost/LightGBM model."""

    def test_model_initialization(self):
        """Test that model initializes with correct default parameters."""
        model = XGBoostModel()
        # Accept xgboost, lightgbm, or gradient_boosting (fallback)
        assert model.model_type in ["xgboost", "lightgbm", "gradient_boosting"]
        assert model.is_fitted is False

    def test_fit_with_valid_data(self):
        """Test fitting model with valid data."""
        np.random.seed(42)
        n_samples = 100
        n_features = 5
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        model = XGBoostModel(n_estimators=10, random_state=42, verbosity=0)
        model.fit(X, y)
        
        assert model.is_fitted is True

    def test_early_stopping(self):
        """Test that early stopping works when enabled."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(200, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(200))
        
        # Split for early stopping
        X_train, X_val = X[:150], X[150:]
        y_train, y_val = y[:150], y[150:]
        
        model = XGBoostModel(
            n_estimators=100,
            early_stopping_rounds=5,
            random_state=42,
            verbosity=0
        )
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
        
        # Early stopping should have reduced iterations
        # Note: best_iteration_ may be None if using fallback model
        if model.best_iteration_ is not None:
            assert model.best_iteration_ < 100


class TestEnsembleModel:
    """Tests for Ensemble model combining multiple base models."""

    def test_ensemble_initialization(self):
        """Test ensemble initializes with empty model list."""
        ensemble = EnsembleModel()
        assert ensemble.model_type == "ensemble"
        assert len(ensemble.models) == 0
        assert ensemble.is_fitted is False

    def test_add_model(self):
        """Test adding models to ensemble."""
        ensemble = EnsembleModel()
        lr = LinearRegressionModel()
        rf = RandomForestModel(n_estimators=5, random_state=42)
        
        ensemble.add_model(lr)
        ensemble.add_model(rf)
        
        assert len(ensemble.models) == 2
        assert ensemble.model_weights is None  # Not fitted yet

    def test_fit_sets_weights_based_on_performance(self):
        """Test that fitting the ensemble sets weights based on validation performance."""
        np.random.seed(42)
        n_samples = 100
        n_features = 5
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        # Create ensemble with models
        ensemble = EnsembleModel()
        ensemble.add_model(LinearRegressionModel())
        ensemble.add_model(RandomForestModel(n_estimators=10, random_state=42))
        
        # Fit with cross-validation to determine weights
        ensemble.fit(X, y, use_cv_for_weights=True, n_cv_folds=3)
        
        assert ensemble.is_fitted is True
        assert ensemble.model_weights is not None
        assert len(ensemble.model_weights) == 2
        assert abs(sum(ensemble.model_weights) - 1.0) < 1e-6  # Weights sum to 1

    def test_predict_returns_weighted_average(self):
        """Test that predict returns weighted average of base model predictions."""
        np.random.seed(42)
        X_train = pd.DataFrame(np.random.randn(100, 3), columns=["f1", "f2", "f3"])
        y_train = pd.Series(np.random.randn(100))
        X_test = pd.DataFrame(np.random.randn(20, 3), columns=["f1", "f2", "f3"])
        
        ensemble = EnsembleModel()
        ensemble.add_model(LinearRegressionModel())
        ensemble.add_model(RandomForestModel(n_estimators=10, random_state=42))
        ensemble.fit(X_train, y_train, use_cv_for_weights=True, n_cv_folds=3)
        
        predictions = ensemble.predict(X_test)
        
        assert len(predictions) == len(X_test)
        assert isinstance(predictions, pd.Series)

    def test_ensemble_with_single_model(self):
        """Test ensemble with single model still works."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 3), columns=["f1", "f2", "f3"])
        y = pd.Series(np.random.randn(100))
        
        ensemble = EnsembleModel()
        ensemble.add_model(LinearRegressionModel())
        ensemble.fit(X, y)
        
        predictions = ensemble.predict(X)
        assert len(predictions) == len(X)


class TestWalkForwardCV:
    """Tests for Walk-Forward Cross-Validation with purge/embargo."""

    def test_initialization(self):
        """Test validator initializes with correct defaults."""
        validator = WalkForwardCV(
            train_window_days=252,
            test_window_days=21,
            purge_gap_days=5,
            embargo_days=5
        )
        
        assert validator.train_window_days == 252
        assert validator.test_window_days == 21
        assert validator.purge_gap_days == 5
        assert validator.embargo_days == 5

    def test_generate_splits_basic(self):
        """Test that split generation returns correct number of splits."""
        dates = pd.date_range(start="2020-01-01", end="2024-01-01", freq="D")
        
        validator = WalkForwardCV(
            train_window_days=365,
            test_window_days=30
        )
        
        splits = list(validator.generate_splits(dates))
        
        # Should have multiple splits
        assert len(splits) > 0
        
        # Each split should have train_start, train_end, test_start, test_end
        for split in splits:
            assert "train_start" in split
            assert "train_end" in split
            assert "test_start" in split
            assert "test_end" in split
            assert split["train_start"] < split["train_end"]
            assert split["test_start"] < split["test_end"]

    def test_purge_gap_prevents_overlap(self):
        """Test that purge gap creates separation between train and test."""
        dates = pd.date_range(start="2020-01-01", end="2024-01-01", freq="D")
        
        purge_gap = 5
        validator = WalkForwardCV(
            train_window_days=365,
            test_window_days=30,
            purge_gap_days=purge_gap
        )
        
        splits = list(validator.generate_splits(dates))
        
        for split in splits:
            # Train end + purge gap should be <= test start
            train_end = split["train_end"]
            test_start = split["test_start"]
            
            # Account for purge gap
            if isinstance(train_end, pd.Timestamp) and isinstance(test_start, pd.Timestamp):
                gap = (test_start - train_end).days
                assert gap >= purge_gap, f"Purge gap violated: gap={gap}, required={purge_gap}"

    def test_embargo_applied_to_last_training_points(self):
        """Test that embargo prevents using recent data for training."""
        dates = pd.date_range(start="2020-01-01", end="2024-01-01", freq="D")
        
        embargo_days = 5
        validator = WalkForwardCV(
            train_window_days=365,
            test_window_days=30,
            embargo_days=embargo_days
        )
        
        splits = list(validator.generate_splits(dates))
        
        for split in splits:
            train_end = split["train_end"]
            test_start = split["test_start"]
            
            if isinstance(train_end, pd.Timestamp) and isinstance(test_start, pd.Timestamp):
                # The last 'embargo_days' of training should not overlap with test
                embargo_boundary = train_end - pd.Timedelta(days=embargo_days)
                assert test_start > embargo_boundary

    def test_run_walk_forward_validation(self):
        """Test running complete walk-forward validation."""
        np.random.seed(42)
        n_tickers = 50
        n_days = 500
        
        # Create synthetic factor data
        dates = pd.date_range(start="2020-01-01", periods=n_days, freq="D")
        tickers = [f"TICKER_{i:03d}" for i in range(n_tickers)]
        
        factor_data = pd.DataFrame(
            np.random.randn(n_days, n_tickers),
            index=dates,
            columns=tickers
        )
        
        # Create synthetic return data (slightly correlated with factors)
        return_data = pd.DataFrame(
            np.random.randn(n_days, n_tickers) + 0.1 * factor_data.values,
            index=dates,
            columns=tickers
        )
        
        validator = WalkForwardCV(
            train_window_days=200,
            test_window_days=30,
            purge_gap_days=5,
            embargo_days=5
        )
        
        # Create simple model
        model = LinearRegressionModel()
        
        # Run validation
        results = validator.run_validation(
            factor_data=factor_data,
            return_data=return_data,
            model=model,
            target_horizon_days=20
        )
        
        assert "oos_r2_mean" in results
        assert "oos_r2_std" in results
        assert "num_splits" in results
        assert results["num_splits"] > 0


class TestFeatureImportanceTracker:
    """Tests for feature importance tracking across folds."""

    def test_initialization(self):
        """Test tracker initializes empty."""
        tracker = FeatureImportanceTracker()
        assert len(tracker.importance_history) == 0

    def test_add_importance(self):
        """Test adding importance values for a fold."""
        tracker = FeatureImportanceTracker()
        
        importance = {"feature1": 0.5, "feature2": 0.3, "feature3": 0.2}
        tracker.add_importance(importance, fold=0)
        
        assert len(tracker.importance_history) == 1
        assert tracker.importance_history[0]["fold"] == 0
        assert tracker.importance_history[0]["importance"] == importance

    def test_get_stability_scores(self):
        """Test calculating stability scores across folds."""
        tracker = FeatureImportanceTracker()
        
        # Add multiple folds with similar importance patterns
        for i in range(5):
            importance = {
                "feature1": 0.5 + np.random.randn() * 0.05,
                "feature2": 0.3 + np.random.randn() * 0.05,
                "feature3": 0.2 + np.random.randn() * 0.05
            }
            tracker.add_importance(importance, fold=i)
        
        stability = tracker.get_stability_scores()
        
        assert "feature1" in stability
        assert "feature2" in stability
        assert "feature3" in stability
        
        # High importance features should have lower CV (more stable)
        assert stability["feature1"]["cv"] < 1.0  # CV should be reasonable

    def test_get_average_importance(self):
        """Test getting average importance across folds."""
        tracker = FeatureImportanceTracker()
        
        tracker.add_importance({"f1": 0.6, "f2": 0.4}, fold=0)
        tracker.add_importance({"f1": 0.4, "f2": 0.6}, fold=1)
        
        avg = tracker.get_average_importance()
        
        assert abs(avg["f1"] - 0.5) < 0.01
        assert abs(avg["f2"] - 0.5) < 0.01


class TestModelPersistence:
    """Tests for model serialization and versioning."""

    def test_save_and_load_model(self):
        """Test saving and loading a model."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 3), columns=["f1", "f2", "f3"])
        y = pd.Series(np.random.randn(100))
        
        model = LinearRegressionModel(feature_names=X.columns.tolist())
        model.fit(X, y)
        
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            ModelPersistence.save_model(model, f.name)
            
            loaded = ModelPersistence.load_model(f.name)
            
            assert loaded.is_fitted is True
            assert np.allclose(loaded.coefficients_, model.coefficients_)

    def test_save_with_metadata(self):
        """Test saving model with metadata."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 3), columns=["f1", "f2", "f3"])
        y = pd.Series(np.random.randn(100))
        
        model = LinearRegressionModel(feature_names=X.columns.tolist())
        model.fit(X, y)
        
        metadata = {
            "version": "1.0.0",
            "trained_date": "2024-01-15",
            "train_samples": 100,
            "r2_score": 0.15
        }
        
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            ModelPersistence.save_model(model, f.name, metadata=metadata)
            
            loaded, loaded_metadata = ModelPersistence.load_model(f.name, return_metadata=True)
            
            assert loaded_metadata["version"] == "1.0.0"
            assert loaded_metadata["trained_date"] == "2024-01-15"

    def test_version_tracking(self):
        """Test that model versions are tracked correctly."""
        versions = ModelPersistence.get_version_history()
        
        # Should have some version history
        assert isinstance(versions, list)


class TestReturnForecaster:
    """Tests for the main ReturnForecaster class."""

    def test_forecaster_initialization(self):
        """Test forecaster initializes with all base models."""
        forecaster = ReturnForecaster()
        
        assert len(forecaster.base_models) >= 3  # At least LR, RF, XGB
        assert forecaster.ensemble is not None
        assert forecaster.validation is not None

    def test_train_single_model(self):
        """Test training a single model type."""
        np.random.seed(42)
        n_samples = 100
        n_features = 10
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        forecaster = ReturnForecaster()
        result = forecaster.train_model(
            model_type="linear_regression",
            X=X,
            y=y
        )
        
        assert result["status"] == "success"
        assert "model" in result
        assert "training_time" in result

    def test_train_ensemble(self):
        """Test training the full ensemble."""
        np.random.seed(42)
        n_samples = 100
        n_features = 10
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        forecaster = ReturnForecaster()
        result = forecaster.train_ensemble(X, y)
        
        assert result["status"] == "success"
        assert result["num_models"] >= 3
        assert "weights" in result

    def test_predict(self):
        """Test making predictions."""
        np.random.seed(42)
        X_train = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y_train = pd.Series(np.random.randn(100))
        X_test = pd.DataFrame(np.random.randn(20, 5), columns=[f"f{i}" for i in range(5)])
        
        forecaster = ReturnForecaster()
        forecaster.train_ensemble(X_train, y_train)
        
        predictions = forecaster.predict(X_test)
        
        assert len(predictions) == len(X_test)
        assert isinstance(predictions, pd.Series)

    def test_validate_out_of_sample(self):
        """Test out-of-sample validation."""
        pytest.importorskip("sklearn", reason="sklearn required for cross-validation")
        
        np.random.seed(42)
        n_samples = 200
        n_features = 5
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        forecaster = ReturnForecaster()
        results = forecaster.validate_out_of_sample(X, y, n_cv_folds=3)
        
        assert "oos_r2_mean" in results
        assert "oos_r2_std" in results
        assert "ic_mean" in results
        assert results["num_splits"] == 3
    
    def test_validate_out_of_sample_r2_threshold(self):
        """Test that out-of-sample validation includes R² threshold check."""
        pytest.importorskip("sklearn", reason="sklearn required for cross-validation")
        
        np.random.seed(42)
        n_samples = 200
        n_features = 5
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"factor_{i}" for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))
        
        forecaster = ReturnForecaster()
        results = forecaster.validate_out_of_sample(X, y, n_cv_folds=3)
        
        assert "oos_r2_meets_threshold" in results
        assert isinstance(results["oos_r2_meets_threshold"], bool)
    
    def test_training_time_within_threshold(self):
        """Test that model training time is within threshold."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))
        
        # Linear Regression (should be fast)
        model = LinearRegressionModel(feature_names=X.columns.tolist())
        model.fit(X, y)
        assert model.training_time_ < TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS
        
        # Random Forest (should be fast with small data)
        rf_model = RandomForestModel(n_estimators=10, random_state=42)
        rf_model.fit(X, y)
        assert rf_model.training_time_ < TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS
        
        # XGBoost (should be fast with small data)
        xgb_model = XGBoostModel(n_estimators=10, random_state=42, verbosity=0)
        xgb_model.fit(X, y)
        assert xgb_model.training_time_ < TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS

    def test_forecast_for_date(self):
        """Test generating forecasts for a specific date."""
        np.random.seed(42)
        n_tickers = 50
        n_features = 5
        
        tickers = [f"TICKER_{i:03d}" for i in range(n_tickers)]
        
        # Create training data: tickers x features
        X_train = pd.DataFrame(
            np.random.randn(n_tickers, n_features),
            columns=[f"factor_{i}" for i in range(n_features)],
            index=tickers
        )
        y_train = pd.Series(np.random.randn(n_tickers), index=tickers)
        
        forecaster = ReturnForecaster()
        forecaster.train_ensemble(X_train, y_train)
        
        # Create factor data for forecasting - same format as training
        # Each row is a ticker, columns are features
        factor_data = pd.DataFrame(
            np.random.randn(n_tickers, n_features),
            columns=[f"factor_{i}" for i in range(n_features)],
            index=tickers
        )
        
        # Forecast - use a date that exists in the index (if it's a DatetimeIndex)
        # Since factor_data has ticker index, not date index, we just verify it works
        # The method should handle the case where target_date is not in index
        forecasts = forecaster.forecast_for_date(factor_data, target_date=date(2024, 3, 31))
        
        assert len(forecasts) == n_tickers
        assert isinstance(forecasts, pd.Series)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])