"""
Return Forecasting Models Module.

This module provides ML models for forecasting returns:
- Linear Regression: Baseline interpretable model
- Random Forest: Non-linear relationships, robust to outliers
- XGBoost/LightGBM: Best-in-class for tabular data
- Ensemble: Weighted combination of all models
- Walk-forward cross-validation with purge/embargo
- Model persistence and versioning
- Feature importance tracking

Target: 20-day forward excess returns
Features: Factor values, technical indicators, fundamental ratios
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import date, datetime, timedelta
from abc import ABC, abstractmethod
import logging
import pickle
import json
import time
from pathlib import Path

# Training time thresholds
TRAINING_TIME_THRESHOLD_SECONDS = 1800  # 30 minutes (PRD requirement)
TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS = 600  # 10 minutes per single model (Quality Requirement)

logger = logging.getLogger(__name__)

# Check for optional dependencies
try:
    from sklearn.linear_model import LinearRegression as SKLinearRegression
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.model_selection import KFold
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    SKLinearRegression = None
    RandomForestRegressor = None
    GradientBoostingRegressor = None
    KFold = None
    logger.warning("sklearn not available, using numpy implementations")

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    XGBRegressor = None
    logger.warning("xgboost not available")

try:
    from lightgbm import LGBMRegressor
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    LGBMRegressor = None
    logger.warning("lightgbm not available")


class BaseModel(ABC):
    """Abstract base class for all return forecasting models."""
    
    def __init__(self, model_type: str):
        """Initialize base model.
        
        Args:
            model_type: Type identifier for the model
        """
        self.model_type = model_type
        self.is_fitted = False
        self.feature_names: Optional[List[str]] = None
        self.feature_importance_: Optional[Dict[str, float]] = None
        self.training_time_: Optional[float] = None
    
    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> 'BaseModel':
        """Fit the model to training data.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            
        Returns:
            self
        """
        pass
    
    @abstractmethod
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make predictions.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of predictions with same index as X
        """
        pass
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance values.
        
        Returns:
            Dict mapping feature names to importance values
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before getting feature importance")
        return self.feature_importance_ or {}
    
    def serialize(self) -> Dict:
        """Serialize model to dictionary.
        
        Returns:
            Dict containing model data
        """
        return {
            "model_type": self.model_type,
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names,
        }
    
    @classmethod
    def deserialize(cls, data: Dict) -> 'BaseModel':
        """Deserialize model from dictionary.
        
        Args:
            data: Dict containing model data
            
        Returns:
            Model instance
        """
        model = cls()
        model.is_fitted = data.get("is_fitted", False)
        model.feature_names = data.get("feature_names")
        return model


class LinearRegressionModel(BaseModel):
    """Linear Regression baseline model for return forecasting."""
    
    def __init__(
        self,
        fit_intercept: bool = True,
        normalize: bool = False,
        feature_names: Optional[List[str]] = None
    ):
        """Initialize Linear Regression model.
        
        Args:
            fit_intercept: Whether to fit intercept
            normalize: Whether to normalize features
            feature_names: List of feature names
        """
        super().__init__("linear_regression")
        self.fit_intercept = fit_intercept
        self.normalize = normalize
        self.feature_names = feature_names
        self.coefficients_: Optional[np.ndarray] = None
        self.intercept_: float = 0.0
        self._sklearn_model = None
        
        # Use sklearn if available
        if HAS_SKLEARN and SKLinearRegression is not None:
            # Note: normalize parameter removed in sklearn 1.0+, handle normalization manually if needed
            self._sklearn_model = SKLinearRegression(
                fit_intercept=fit_intercept
            )
    
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> 'LinearRegressionModel':
        """Fit linear regression model.
        
        Args:
            X: Feature DataFrame (n_samples, n_features)
            y: Target Series (n_samples,)
            
        Returns:
            self
        """
        if X is None:
            raise ValueError("Features (X) are required")
        if y is None:
            raise ValueError("Target (y) is required")
        
        start_time = time.time()
        
        # Store feature names
        if self.feature_names is None:
            self.feature_names = X.columns.tolist()
        
        X_array = X.values
        y_array = y.values
        
        if self._sklearn_model is not None:
            self._sklearn_model.fit(X_array, y_array)
            self.coefficients_ = self._sklearn_model.coef_
            self.intercept_ = self._sklearn_model.intercept_
        else:
            # Numpy implementation (OLS)
            if self.normalize:
                X_array = (X_array - X_array.mean(axis=0)) / (X_array.std(axis=0) + 1e-8)
            
            # Add bias term
            if self.fit_intercept:
                X_array = np.column_stack([np.ones(X_array.shape[0]), X_array])
            
            # OLS solution: beta = (X'X)^(-1) X'y
            XtX = X_array.T @ X_array
            Xty = X_array.T @ y_array
            
            try:
                beta = np.linalg.solve(XtX, Xty)
            except np.linalg.LinAlgError:
                # Use pseudoinverse if singular
                beta = np.linalg.lstsq(XtX, Xty, rcond=None)[0]
            
            if self.fit_intercept:
                self.intercept_ = beta[0]
                self.coefficients_ = beta[1:]
            else:
                self.intercept_ = 0.0
                self.coefficients_ = beta
        
        self.is_fitted = True
        self.training_time_ = time.time() - start_time
        
        # Check training time threshold
        if self.training_time_ > TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS:
            logger.warning(
                f"LinearRegression training time {self.training_time_:.2f}s exceeds "
                f"single model threshold {TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS}s"
            )
        
        # Calculate feature importance (absolute coefficients)
        if self.coefficients_ is not None:
            abs_coefs = np.abs(self.coefficients_)
            total = abs_coefs.sum()
            if total > 0:
                self.feature_importance_ = {
                    name: float(abs_coefs[i] / total)
                    for i, name in enumerate(self.feature_names)
                }
        
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make predictions.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of predictions
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        X_array = X.values
        
        if self._sklearn_model is not None:
            predictions = self._sklearn_model.predict(X_array)
        else:
            predictions = X_array @ self.coefficients_ + self.intercept_
        
        return pd.Series(predictions, index=X.index)
    
    def serialize(self) -> Dict:
        """Serialize model to dictionary."""
        data = super().serialize()
        data.update({
            "coefficients": self.coefficients_.tolist() if self.coefficients_ is not None else None,
            "intercept": float(self.intercept_),
            "fit_intercept": self.fit_intercept,
            "normalize": self.normalize,
        })
        return data
    
    @classmethod
    def deserialize(cls, data: Dict) -> 'LinearRegressionModel':
        """Deserialize model from dictionary."""
        model = cls(
            fit_intercept=data.get("fit_intercept", True),
            normalize=data.get("normalize", False),
            feature_names=data.get("feature_names")
        )
        model.is_fitted = data.get("is_fitted", False)
        model.coefficients_ = np.array(data["coefficients"]) if data.get("coefficients") else None
        model.intercept_ = data.get("intercept", 0.0)
        return model


class RandomForestModel(BaseModel):
    """Random Forest model for capturing non-linear relationships."""
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = None,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
        random_state: Optional[int] = None,
        feature_names: Optional[List[str]] = None
    ):
        """Initialize Random Forest model.
        
        Args:
            n_estimators: Number of trees
            max_depth: Maximum tree depth
            min_samples_split: Min samples to split node
            min_samples_leaf: Min samples in leaf
            random_state: Random seed
            feature_names: List of feature names
        """
        super().__init__("random_forest")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.feature_names = feature_names
        self.feature_importances_: Optional[np.ndarray] = None
        self._sklearn_model = None
        
        # Use sklearn if available
        if HAS_SKLEARN and RandomForestRegressor is not None:
            self._sklearn_model = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=min_samples_split,
                min_samples_leaf=min_samples_leaf,
                random_state=random_state
            )
    
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> 'RandomForestModel':
        """Fit Random Forest model.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            
        Returns:
            self
        """
        if X is None or y is None:
            raise ValueError("Features and target are required")
        
        start_time = time.time()
        
        if self.feature_names is None:
            self.feature_names = X.columns.tolist()
        
        if self._sklearn_model is not None:
            self._sklearn_model.fit(X.values, y.values)
        else:
            # Fallback: use GradientBoosting from sklearn or simple model
            if HAS_SKLEARN and GradientBoostingRegressor is not None:
                self._sklearn_model = GradientBoostingRegressor(
                    n_estimators=self.n_estimators,
                    max_depth=self.max_depth or 3,
                    random_state=self.random_state
                )
                self._sklearn_model.fit(X.values, y.values)
            else:
                # Last resort: use simple linear model
                self._fallback_model = LinearRegressionModel(
                    feature_names=self.feature_names
                )
                self._fallback_model.fit(X, y)
                self.is_fitted = True
                self.training_time_ = time.time() - start_time
                return self
        
        self.is_fitted = True
        self.training_time_ = time.time() - start_time
        
        # Check training time threshold
        if self.training_time_ > TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS:
            logger.warning(
                f"RandomForest training time {self.training_time_:.2f}s exceeds "
                f"single model threshold {TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS}s"
            )
        
        # Store feature importances
        if hasattr(self._sklearn_model, "feature_importances_"):
            self.feature_importances_ = self._sklearn_model.feature_importances_
            total = self.feature_importances_.sum()
            if total > 0:
                self.feature_importance_ = {
                    name: float(self.feature_importances_[i] / total)
                    for i, name in enumerate(self.feature_names)
                }
        
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make predictions.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of predictions
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        if hasattr(self, "_fallback_model"):
            return self._fallback_model.predict(X)
        
        predictions = self._sklearn_model.predict(X.values)
        return pd.Series(predictions, index=X.index)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance values."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted")
        
        if hasattr(self, "_fallback_model"):
            return self._fallback_model.get_feature_importance()
        
        if self.feature_importance_ is None and self.feature_importances_ is not None:
            total = self.feature_importances_.sum()
            if total > 0:
                self.feature_importance_ = {
                    name: float(self.feature_importances_[i] / total)
                    for i, name in enumerate(self.feature_names)
                }
        
        return self.feature_importance_ or {}


class XGBoostModel(BaseModel):
    """XGBoost/LightGBM model for best-in-class tabular performance."""
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        early_stopping_rounds: Optional[int] = None,
        random_state: Optional[int] = None,
        verbosity: int = 0,
        feature_names: Optional[List[str]] = None
    ):
        """Initialize XGBoost model.
        
        Args:
            n_estimators: Number of boosting rounds
            max_depth: Maximum tree depth
            learning_rate: Learning rate
            subsample: Subsample ratio
            colsample_bytree: Column subsample ratio
            early_stopping_rounds: Early stopping rounds
            random_state: Random seed
            verbosity: Verbosity level
            feature_names: List of feature names
        """
        super().__init__("xgboost")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.early_stopping_rounds = early_stopping_rounds
        self.random_state = random_state
        self.verbosity = verbosity
        self.feature_names = feature_names
        self.best_iteration_: Optional[int] = None
        self._model_type = None
        self._model = None
        
        # Try xgboost first, then lightgbm, then sklearn
        if HAS_XGBOOST and XGBRegressor is not None:
            self._model = XGBRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=subsample,
                colsample_bytree=colsample_bytree,
                early_stopping_rounds=early_stopping_rounds,
                random_state=random_state,
                verbosity=verbosity
            )
            self._model_type = "xgboost"
            self.model_type = "xgboost"
        elif HAS_LIGHTGBM and LGBMRegressor is not None:
            self._model = LGBMRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=subsample,
                colsample_bytree=colsample_bytree,
                random_state=random_state,
                verbose=-1 if verbosity == 0 else verbosity
            )
            self._model_type = "lightgbm"
            self.model_type = "lightgbm"
        elif HAS_SKLEARN and GradientBoostingRegressor is not None:
            self._model = GradientBoostingRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=subsample,
                random_state=random_state
            )
            self._model_type = "sklearn_gb"
            self.model_type = "gradient_boosting"
    
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        eval_set: Optional[List[Tuple[pd.DataFrame, pd.Series]]] = None,
        **kwargs
    ) -> 'XGBoostModel':
        """Fit XGBoost/LightGBM model.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            eval_set: Validation set for early stopping
            
        Returns:
            self
        """
        if X is None or y is None:
            raise ValueError("Features and target are required")
        
        if self._model is None:
            # Fallback to linear model if nothing else available
            self._fallback_model = LinearRegressionModel(feature_names=self.feature_names)
            self._fallback_model.fit(X, y)
            self.is_fitted = True
            return self
        
        start_time = time.time()
        
        if self.feature_names is None:
            self.feature_names = X.columns.tolist()
        
        eval_set_formatted = None
        if eval_set is not None:
            eval_set_formatted = [(df.values, series.values) for df, series in eval_set]
        
        if self._model_type == "xgboost":
            self._model.fit(
                X.values, y.values,
                eval_set=eval_set_formatted,
                verbose=False
            )
            if hasattr(self._model, "best_iteration"):
                self.best_iteration_ = self._model.best_iteration
        elif self._model_type == "lightgbm":
            if eval_set_formatted:
                self._model.fit(
                    X.values, y.values,
                    eval_set=eval_set_formatted,
                )
            else:
                self._model.fit(X.values, y.values)
        else:
            # sklearn GradientBoosting
            self._model.fit(X.values, y.values)
        
        self.is_fitted = True
        self.training_time_ = time.time() - start_time
        
        # Check training time threshold
        if self.training_time_ > TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS:
            logger.warning(
                f"XGBoost training time {self.training_time_:.2f}s exceeds "
                f"single model threshold {TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS}s"
            )
        
        # Store feature importance
        if hasattr(self._model, "feature_importances_"):
            importances = self._model.feature_importances_
            total = importances.sum()
            if total > 0:
                self.feature_importance_ = {
                    name: float(importances[i] / total)
                    for i, name in enumerate(self.feature_names)
                }
        
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make predictions.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of predictions
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        if hasattr(self, "_fallback_model"):
            return self._fallback_model.predict(X)
        
        predictions = self._model.predict(X.values)
        return pd.Series(predictions, index=X.index)


try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None
    logger.warning("PyTorch not available, LSTM model will use fallback")


class LSTMModel(BaseModel):
    """LSTM model for sequential time series patterns (optional per PRD Section 4.5)."""
    
    def __init__(
        self,
        hidden_dim: int = 64,
        num_layers: int = 2,
        sequence_length: int = 20,
        feature_names: Optional[List[str]] = None,
        random_state: Optional[int] = None
    ):
        """Initialize LSTM model.
        
        Args:
            hidden_dim: Hidden dimension of LSTM
            num_layers: Number of LSTM layers
            sequence_length: Length of input sequences
            feature_names: List of feature names
            random_state: Random seed
        """
        super().__init__("lstm")
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.sequence_length = sequence_length
        self.feature_names = feature_names
        self.random_state = random_state
        self._model = None
        self._device = torch.device("cuda" if torch and torch.cuda.is_available() else "cpu") if HAS_TORCH else None
        
        if HAS_TORCH and nn is not None:
            self._init_lstm_model()
        else:
            self._fallback_model = LinearRegressionModel(feature_names=feature_names)
    
    def _init_lstm_model(self):
        """Initialize PyTorch LSTM model."""
        if not HAS_TORCH or nn is None:
            return
        
        n_features = len(self.feature_names) if self.feature_names else 1
        
        class LSTMNet(nn.Module):
            def __init__(self, n_features, hidden_dim, num_layers):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=n_features,
                    hidden_size=hidden_dim,
                    num_layers=num_layers,
                    batch_first=True
                )
                self.fc = nn.Linear(hidden_dim, 1)
            
            def forward(self, x):
                lstm_out, (h_n, c_n) = self.lstm(x)
                # Use last hidden state
                out = self.fc(h_n[-1, :, :])
                return out.squeeze(-1)
        
        self._model = LSTMNet(n_features, self.hidden_dim, self.num_layers).to(self._device)
        self._optimizer = torch.optim.Adam(self._model.parameters(), lr=0.001)
        self._criterion = nn.MSELoss()
    
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> 'LSTMModel':
        """Fit LSTM model.
        
        Args:
            X: Feature DataFrame (n_samples, n_features)
            y: Target Series (n_samples,)
            
        Returns:
            self
        """
        start_time = time.time()
        
        if self.feature_names is None:
            self.feature_names = X.columns.tolist()
        
        if not HAS_TORCH or self._model is None:
            # Fallback to linear model
            self._fallback_model.fit(X, y)
            self.is_fitted = True
            self.training_time_ = time.time() - start_time
            return self
        
        # Prepare sequences
        X_seq, y_seq = self._prepare_sequences(X.values, y.values)
        
        if len(X_seq) == 0:
            logger.warning("Not enough data for LSTM sequences, using fallback")
            self._fallback_model.fit(X, y)
            self.is_fitted = True
            self.training_time_ = time.time() - start_time
            return self
        
        # Convert to tensors
        X_tensor = torch.tensor(X_seq, dtype=torch.float32).to(self._device)
        y_tensor = torch.tensor(y_seq, dtype=torch.float32).to(self._device)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        # Train
        self._model.train()
        epochs = 10
        for _ in range(epochs):
            for batch_X, batch_y in dataloader:
                self._optimizer.zero_grad()
                predictions = self._model(batch_X)
                loss = self._criterion(predictions, batch_y)
                loss.backward()
                self._optimizer.step()
        
        self.is_fitted = True
        self.training_time_ = time.time() - start_time
        
        # Check training time threshold
        if self.training_time_ > TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS:
            logger.warning(
                f"LSTM training time {self.training_time_:.2f}s exceeds "
                f"single model threshold {TRAINING_TIME_THRESHOLD_SINGLE_MODEL_SECONDS}s"
            )
        
        return self
    
    def _prepare_sequences(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequence data for LSTM.
        
        Args:
            X: Feature array (n_samples, n_features)
            y: Target array (n_samples,)
            
        Returns:
            Tuple of (X_sequences, y_sequences)
        """
        X_seq = []
        y_seq = []
        
        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i+self.sequence_length])
            y_seq.append(y[i+self.sequence_length])
        
        return np.array(X_seq), np.array(y_seq)
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make predictions with LSTM model.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of predictions
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        if hasattr(self, "_fallback_model"):
            return self._fallback_model.predict(X)
        
        if not HAS_TORCH or self._model is None:
            raise RuntimeError("PyTorch not available for LSTM prediction")
        
        self._model.eval()
        with torch.no_grad():
            X_values = X.values
            if len(X_values) < self.sequence_length:
                # Pad if not enough data
                pad_len = self.sequence_length - len(X_values)
                X_padded = np.pad(X_values, ((pad_len, 0), (0, 0)), mode='edge')
                X_seq = X_padded.reshape(1, self.sequence_length, -1)
            else:
                X_seq = X_values[-self.sequence_length:].reshape(1, self.sequence_length, -1)
            
            X_tensor = torch.tensor(X_seq, dtype=torch.float32).to(self._device)
            prediction = self._model(X_tensor).cpu().numpy()
        
        return pd.Series(prediction, index=X.index[-1:] if len(X) > 0 else X.index)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """LSTM feature importance is not directly available, return empty."""
        return {}


class EnsembleModel(BaseModel):
    """Ensemble model combining multiple base models."""
    
    def __init__(self, feature_names: Optional[List[str]] = None):
        """Initialize Ensemble model.
        
        Args:
            feature_names: List of feature names
        """
        super().__init__("ensemble")
        self.models: List[BaseModel] = []
        self.model_weights: Optional[np.ndarray] = None
        self.feature_names = feature_names
    
    def add_model(self, model: BaseModel) -> 'EnsembleModel':
        """Add a model to the ensemble.
        
        Args:
            model: BaseModel instance
            
        Returns:
            self
        """
        self.models.append(model)
        return self
    
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        use_cv_for_weights: bool = True,
        n_cv_folds: int = 5,
        **kwargs
    ) -> 'EnsembleModel':
        """Fit all models and compute weights.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            use_cv_for_weights: Whether to use CV for weight determination
            n_cv_folds: Number of CV folds for weight calculation
            
        Returns:
            self
        """
        if len(self.models) == 0:
            raise ValueError("No models in ensemble")
        
        if self.feature_names is None:
            self.feature_names = X.columns.tolist()
        
        start_time = time.time()
        
        # Fit all models
        for model in self.models:
            model.fit(X, y)
        
        # Compute weights based on CV performance
        if use_cv_for_weights and len(self.models) > 1:
            self.model_weights = self._compute_cv_weights(X, y, n_cv_folds)
        else:
            # Equal weights
            self.model_weights = np.ones(len(self.models)) / len(self.models)
        
        self.is_fitted = True
        self.training_time_ = time.time() - start_time
        
        # Check ensemble training time threshold (30min)
        if self.training_time_ > TRAINING_TIME_THRESHOLD_SECONDS:
            logger.warning(
                f"Ensemble training time {self.training_time_:.2f}s exceeds "
                f"threshold {TRAINING_TIME_THRESHOLD_SECONDS}s"
            )
        
        return self
    
    def _compute_cv_weights(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_folds: int
    ) -> np.ndarray:
        """Compute model weights using cross-validation.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            n_folds: Number of CV folds
            
        Returns:
            Array of model weights
        """
        if KFold is None:
            # Fallback to equal weights if sklearn not available
            return np.ones(len(self.models)) / len(self.models)
        
        n_models = len(self.models)
        fold_scores = np.zeros((n_folds, n_models))
        
        kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
        
        for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            for model_idx, model in enumerate(self.models):
                # Clone model for this fold
                model_copy = self._clone_model(model)
                model_copy.fit(X_train, y_train)
                predictions = model_copy.predict(X_val)
                
                # Calculate R2 score
                ss_res = ((y_val - predictions) ** 2).sum()
                ss_tot = ((y_val - y_val.mean()) ** 2).sum()
                r2 = 1 - (ss_res / (ss_tot + 1e-8))
                fold_scores[fold_idx, model_idx] = r2
        
        # Average scores across folds
        avg_scores = fold_scores.mean(axis=0)
        
        # Convert scores to weights (softmax-like)
        # Use max score to prevent overflow
        max_score = avg_scores.max()
        exp_scores = np.exp(avg_scores - max_score)
        weights = exp_scores / exp_scores.sum()
        
        return weights
    
    def _clone_model(self, model: BaseModel) -> BaseModel:
        """Clone a model instance."""
        if isinstance(model, LinearRegressionModel):
            return LinearRegressionModel(
                fit_intercept=model.fit_intercept,
                normalize=model.normalize,
                feature_names=model.feature_names
            )
        elif isinstance(model, RandomForestModel):
            return RandomForestModel(
                n_estimators=model.n_estimators,
                max_depth=model.max_depth,
                random_state=model.random_state,
                feature_names=model.feature_names
            )
        elif isinstance(model, XGBoostModel):
            return XGBoostModel(
                n_estimators=model.n_estimators,
                max_depth=model.max_depth,
                learning_rate=model.learning_rate,
                random_state=model.random_state,
                verbosity=model.verbosity,
                feature_names=model.feature_names
            )
        else:
            raise ValueError(f"Unknown model type: {type(model)}")
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make weighted ensemble predictions.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of weighted predictions
        """
        if not self.is_fitted:
            raise ValueError("Ensemble must be fitted before prediction")
        
        if self.model_weights is None:
            raise ValueError("Model weights not set")
        
        # Get predictions from all models
        predictions = np.zeros(len(X))
        
        for model, weight in zip(self.models, self.model_weights):
            pred = model.predict(X).values
            predictions += weight * pred
        
        return pd.Series(predictions, index=X.index)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get weighted average of feature importances."""
        if not self.is_fitted:
            raise ValueError("Ensemble must be fitted")
        
        combined_importance = {}
        
        for model, weight in zip(self.models, self.model_weights):
            importance = model.get_feature_importance()
            for feature, imp in importance.items():
                combined_importance[feature] = combined_importance.get(feature, 0) + weight * imp
        
        return combined_importance


class WalkForwardCV:
    """Walk-forward cross-validation with purge/embargo gaps."""
    
    def __init__(
        self,
        train_window_days: int = 252,
        test_window_days: int = 21,
        purge_gap_days: int = 5,
        embargo_days: int = 5
    ):
        """Initialize walk-forward validator.
        
        Args:
            train_window_days: Training window length in days
            test_window_days: Test window length in days
            purge_gap_days: Gap between train and test (prevents look-ahead)
            embargo_days: Embargo on last N days of training
        """
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.purge_gap_days = purge_gap_days
        self.embargo_days = embargo_days
    
    def generate_splits(
        self,
        dates: pd.DatetimeIndex
    ) -> List[Dict[str, Any]]:
        """Generate train/test splits for walk-forward validation.
        
        Args:
            dates: Sorted datetime index of available dates
            
        Returns:
            List of dicts with train_start, train_end, test_start, test_end
        """
        splits = []
        
        n_dates = len(dates)
        min_required = self.train_window_days + self.test_window_days + self.purge_gap_days
        
        if n_dates < min_required:
            logger.warning(f"Not enough dates for validation: {n_dates} < {min_required}")
            return splits
        
        # Generate splits
        for i in range(self.train_window_days, n_dates - self.test_window_days, self.test_window_days):
            train_end_idx = i
            test_start_idx = i + self.purge_gap_days
            test_end_idx = min(i + self.purge_gap_days + self.test_window_days, n_dates)
            
            # Apply embargo (shift test start forward)
            if self.embargo_days > 0:
                # Embargo applies to training data near test period
                embargo_offset = self.embargo_days
                train_end_idx = i - embargo_offset
            
            train_start_idx = max(0, train_end_idx - self.train_window_days)
            
            splits.append({
                "train_start": dates[train_start_idx],
                "train_end": dates[train_end_idx],
                "test_start": dates[test_start_idx],
                "test_end": dates[test_end_idx],
                "train_start_idx": train_start_idx,
                "train_end_idx": train_end_idx,
                "test_start_idx": test_start_idx,
                "test_end_idx": test_end_idx
            })
        
        return splits
    
    def run_validation(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame,
        model: BaseModel,
        target_horizon_days: int = 20
    ) -> Dict[str, Any]:
        """Run walk-forward validation.
        
        Args:
            factor_data: DataFrame of factor values (dates x tickers)
            return_data: DataFrame of returns (dates x tickers)
            model: Model to validate
            target_horizon_days: Forward return horizon
            
        Returns:
            Dict with validation metrics
        """
        dates = factor_data.index
        splits = list(self.generate_splits(dates))
        
        if len(splits) == 0:
            return {
                "oos_r2_mean": np.nan,
                "oos_r2_std": np.nan,
                "ic_mean": np.nan,
                "ic_std": np.nan,
                "num_splits": 0
            }
        
        oos_r2_scores = []
        oos_ic_scores = []
        
        for split in splits:
            train_start = split["train_start_idx"]
            train_end = split["train_end_idx"]
            test_start = split["test_start_idx"]
            test_end = split["test_end_idx"]
            
            # Get training data
            train_factors = factor_data.iloc[train_start:train_end]
            train_returns = return_data.iloc[train_start:train_end]
            
            # Get test data
            test_factors = factor_data.iloc[test_start:test_end]
            test_returns = return_data.iloc[test_start:test_end]
            
            if len(train_factors) < 10 or len(test_factors) < 5:
                continue
            
            # Flatten for training (cross-sectional)
            # Use last date of training window
            X_train = train_factors.iloc[-1].dropna()
            y_train = train_returns.iloc[-1].loc[X_train.index]
            
            # Align test data
            X_test = test_factors.iloc[-1].dropna()
            common_idx = X_train.index.intersection(X_test.index)
            
            if len(common_idx) < 10:
                continue
            
            X_train = X_train.loc[common_idx]
            y_train = y_train.loc[common_idx]
            X_test = X_test.loc[common_idx]
            y_test = test_returns.iloc[-1].loc[common_idx]
            
            # Train model
            try:
                model_copy = self._clone_model(model)
                model_copy.fit(pd.DataFrame(X_train), pd.Series(y_train))
                
                # Predict
                predictions = model_copy.predict(pd.DataFrame(X_test))
                
                # Calculate R2
                ss_res = ((y_test - predictions) ** 2).sum()
                ss_tot = ((y_test - y_test.mean()) ** 2).sum()
                r2 = 1 - (ss_res / (ss_tot + 1e-8))
                oos_r2_scores.append(r2)
                
                # Calculate IC
                ic = predictions.corr(pd.Series(y_test))
                if not np.isnan(ic):
                    oos_ic_scores.append(ic)
                    
            except Exception as e:
                logger.warning(f"Split validation failed: {e}")
                continue
        
        oos_r2_mean = np.mean(oos_r2_scores) if oos_r2_scores else np.nan
        return {
            "oos_r2_mean": oos_r2_mean,
            "oos_r2_std": np.std(oos_r2_scores) if oos_r2_scores else np.nan,
            "ic_mean": np.mean(oos_ic_scores) if oos_ic_scores else np.nan,
            "ic_std": np.std(oos_ic_scores) if oos_ic_scores else np.nan,
            "num_splits": len(oos_r2_scores),
            "pct_positive_r2": (np.array(oos_r2_scores) > 0).mean() if oos_r2_scores else np.nan,
            "oos_r2_meets_threshold": bool(oos_r2_mean > 0.05) if not np.isnan(oos_r2_mean) else False
        }
    
    def _clone_model(self, model: BaseModel) -> BaseModel:
        """Clone a model instance."""
        if isinstance(model, LinearRegressionModel):
            return LinearRegressionModel(
                fit_intercept=model.fit_intercept,
                normalize=model.normalize,
                feature_names=model.feature_names
            )
        elif isinstance(model, RandomForestModel):
            return RandomForestModel(
                n_estimators=model.n_estimators,
                max_depth=model.max_depth,
                random_state=model.random_state,
                feature_names=model.feature_names
            )
        elif isinstance(model, XGBoostModel):
            return XGBoostModel(
                n_estimators=model.n_estimators,
                max_depth=model.max_depth,
                learning_rate=model.learning_rate,
                random_state=model.random_state,
                verbosity=model.verbosity,
                feature_names=model.feature_names
            )
        elif isinstance(model, EnsembleModel):
            ensemble = EnsembleModel(feature_names=model.feature_names)
            for m in model.models:
                ensemble.add_model(self._clone_model(m))
            return ensemble
        else:
            raise ValueError(f"Unknown model type: {type(model)}")


class FeatureImportanceTracker:
    """Track feature importance across validation folds."""
    
    def __init__(self):
        """Initialize tracker."""
        self.importance_history: List[Dict[str, Any]] = []
    
    def add_importance(
        self,
        importance: Dict[str, float],
        fold: int,
        metadata: Optional[Dict] = None
    ) -> None:
        """Add importance values for a fold.
        
        Args:
            importance: Dict of feature importances
            fold: Fold number
            metadata: Optional additional metadata
        """
        self.importance_history.append({
            "fold": fold,
            "importance": importance,
            "metadata": metadata or {}
        })
    
    def get_average_importance(self) -> Dict[str, float]:
        """Get average importance across all folds.
        
        Returns:
            Dict of average feature importances
        """
        if not self.importance_history:
            return {}
        
        all_features = set()
        for record in self.importance_history:
            all_features.update(record["importance"].keys())
        
        avg_importance = {}
        for feature in all_features:
            values = [
                record["importance"].get(feature, 0)
                for record in self.importance_history
            ]
            avg_importance[feature] = np.mean(values)
        
        return avg_importance
    
    def get_stability_scores(self) -> Dict[str, Dict[str, float]]:
        """Calculate stability scores (CV of importance) across folds.
        
        Returns:
            Dict of feature -> {mean, std, cv} stability metrics
        """
        if not self.importance_history:
            return {}
        
        all_features = set()
        for record in self.importance_history:
            all_features.update(record["importance"].keys())
        
        stability = {}
        for feature in all_features:
            values = [
                record["importance"].get(feature, 0)
                for record in self.importance_history
            ]
            mean_val = np.mean(values)
            std_val = np.std(values)
            cv = std_val / (mean_val + 1e-8) if mean_val != 0 else np.inf
            
            stability[feature] = {
                "mean": mean_val,
                "std": std_val,
                "cv": cv
            }
        
        return stability


class ModelPersistence:
    """Model persistence and versioning utilities."""
    
    @staticmethod
    def save_model(
        model: BaseModel,
        path: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Save model to file.
        
        Args:
            model: Model to save
            path: File path
            metadata: Optional metadata dict
        """
        data = {
            "model_data": model.serialize(),
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        with open(path, "wb") as f:
            pickle.dump(data, f)
    
    @staticmethod
    def load_model(
        path: str,
        return_metadata: bool = False
    ) -> Union[BaseModel, Tuple[BaseModel, Dict]]:
        """Load model from file.
        
        Args:
            path: File path
            return_metadata: Whether to return metadata
            
        Returns:
            Model or (Model, metadata) tuple
        """
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        model_data = data["model_data"]
        metadata = data.get("metadata", {})
        
        # Reconstruct model
        model_type = model_data.get("model_type")
        
        if model_type == "linear_regression":
            model = LinearRegressionModel.deserialize(model_data)
        elif model_type == "random_forest":
            model = RandomForestModel(
                n_estimators=model_data.get("n_estimators", 100),
                random_state=model_data.get("random_state")
            )
            model.is_fitted = model_data.get("is_fitted", False)
        elif model_type == "xgboost" or model_type == "lightgbm":
            model = XGBoostModel(
                n_estimators=model_data.get("n_estimators", 100),
                random_state=model_data.get("random_state")
            )
            model.is_fitted = model_data.get("is_fitted", False)
        elif model_type == "ensemble":
            model = EnsembleModel(feature_names=model_data.get("feature_names"))
            model.is_fitted = model_data.get("is_fitted", False)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        if return_metadata:
            return model, metadata
        return model
    
    @staticmethod
    def get_version_history() -> List[Dict]:
        """Get model version history.
        
        Returns:
            List of version records
        """
        # This would typically read from a database or file
        # For now, return empty list
        return []


class ReturnForecaster:
    """Main interface for return forecasting."""
    
    def __init__(self, db_path: str = "data/universe.db"):
        """Initialize return forecaster.
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        
        # Initialize base models
        self.base_models: List[BaseModel] = [
            LinearRegressionModel(),
            RandomForestModel(n_estimators=50, random_state=42),
            XGBoostModel(n_estimators=50, random_state=42, verbosity=0)
        ]
        # Add LSTM model if PyTorch is available
        if HAS_TORCH:
            try:
                self.base_models.append(LSTMModel(random_state=42))
                logger.info("LSTM model added to base models")
            except Exception as e:
                logger.warning(f"Failed to initialize LSTM model: {e}")
        
        # Initialize ensemble
        self.ensemble = EnsembleModel()
        for model in self.base_models:
            self.ensemble.add_model(model)
        
        # Initialize validation
        self.validation = WalkForwardCV(
            train_window_days=252,
            test_window_days=21,
            purge_gap_days=5,
            embargo_days=5
        )
        
        # Feature importance tracker
        self.importance_tracker = FeatureImportanceTracker()
        
        # Model metadata
        self.model_metadata: Dict[str, Any] = {}
    
    def train_model(
        self,
        model_type: str,
        X: pd.DataFrame,
        y: pd.Series,
        **kwargs
    ) -> Dict[str, Any]:
        """Train a single model.
        
        Args:
            model_type: Type of model ('linear_regression', 'random_forest', 'xgboost')
            X: Feature DataFrame
            y: Target Series
            
        Returns:
            Dict with training results
        """
        start_time = time.time()
        
        if model_type == "linear_regression":
            model = LinearRegressionModel(feature_names=X.columns.tolist())
        elif model_type == "random_forest":
            model = RandomForestModel(
                n_estimators=kwargs.get("n_estimators", 50),
                random_state=kwargs.get("random_state", 42),
                feature_names=X.columns.tolist()
            )
        elif model_type == "xgboost":
            model = XGBoostModel(
                n_estimators=kwargs.get("n_estimators", 50),
                random_state=kwargs.get("random_state", 42),
                verbosity=kwargs.get("verbosity", 0),
                feature_names=X.columns.tolist()
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        model.fit(X, y)
        
        return {
            "status": "success",
            "model": model,
            "training_time": time.time() - start_time,
            "model_type": model_type
        }
    
    def train_ensemble(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        use_cv_for_weights: bool = True,
        n_cv_folds: int = 5
    ) -> Dict[str, Any]:
        """Train the ensemble model.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            use_cv_for_weights: Whether to use CV for weights
            n_cv_folds: Number of CV folds
            
        Returns:
            Dict with training results
        """
        start_time = time.time()
        
        self.ensemble.fit(X, y, use_cv_for_weights=use_cv_for_weights, n_cv_folds=n_cv_folds)
        
        # Track feature importance
        importance = self.ensemble.get_feature_importance()
        self.importance_tracker.add_importance(importance, fold=0)
        
        return {
            "status": "success",
            "num_models": len(self.ensemble.models),
            "weights": self.ensemble.model_weights.tolist() if self.ensemble.model_weights is not None else None,
            "training_time": time.time() - start_time,
            "feature_importance": importance
        }
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make ensemble predictions.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of predictions
        """
        return self.ensemble.predict(X)
    
    def validate_out_of_sample(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_cv_folds: int = 5
    ) -> Dict[str, Any]:
        """Validate ensemble out-of-sample using walk-forward validation.
        
        Args:
            X: Feature DataFrame (should have datetime index for walk-forward)
            y: Target Series (should have datetime index matching X)
            n_cv_folds: Number of CV folds (unused if walk-forward is used)
            
        Returns:
            Dict with validation metrics including R² > 0.05 threshold check
        """
        # Use walk-forward validation if X has datetime index
        if isinstance(X.index, pd.DatetimeIndex) and isinstance(y.index, pd.DatetimeIndex):
            # Prepare factor_data and return_data as DataFrames with datetime index
            factor_data = X.copy()
            return_data = pd.DataFrame(y).T if y.ndim == 1 else y.copy()
            # Align return data to match factor data shape
            return_data = return_data.reindex(factor_data.index, method='ffill')
            
            results = self.validation.run_validation(
                factor_data=factor_data,
                return_data=return_data,
                model=self.ensemble,
                target_horizon_days=20
            )
            # Add threshold check
            results["oos_r2_meets_threshold"] = bool(results.get("oos_r2_mean", np.nan) > 0.05) if not np.isnan(results.get("oos_r2_mean", np.nan)) else False
            return results
        else:
            # Fallback to standard CV if no datetime index
            if KFold is None:
                raise RuntimeError("sklearn required for cross-validation")
            
            kf = KFold(n_splits=n_cv_folds, shuffle=True, random_state=42)
            
            oos_r2_scores = []
            oos_ic_scores = []
            
            for train_idx, val_idx in kf.split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                # Train ensemble on this fold
                ensemble = EnsembleModel()
                for model in self.base_models:
                    model_copy = self._clone_model(model)
                    ensemble.add_model(model_copy)
                
                ensemble.fit(X_train, y_train, use_cv_for_weights=True, n_cv_folds=3)
                
                # Predict
                predictions = ensemble.predict(X_val)
                
                # Calculate R2
                ss_res = ((y_val - predictions) ** 2).sum()
                ss_tot = ((y_val - y_val.mean()) ** 2).sum()
                r2 = 1 - (ss_res / (ss_tot + 1e-8))
                oos_r2_scores.append(r2)
                
                # Calculate IC
                ic = predictions.corr(y_val)
                if not np.isnan(ic):
                    oos_ic_scores.append(ic)
            
            oos_r2_mean = np.mean(oos_r2_scores) if oos_r2_scores else np.nan
            return {
                "oos_r2_mean": oos_r2_mean,
                "oos_r2_std": np.std(oos_r2_scores) if oos_r2_scores else np.nan,
                "ic_mean": np.mean(oos_ic_scores) if oos_ic_scores else np.nan,
                "ic_std": np.std(oos_ic_scores) if oos_ic_scores else np.nan,
                "num_splits": n_cv_folds,
                "pct_positive_r2": (np.array(oos_r2_scores) > 0).mean() if oos_r2_scores else np.nan,
                "oos_r2_meets_threshold": bool(oos_r2_mean > 0.05) if not np.isnan(oos_r2_mean) else False
            }
    
    def forecast_for_date(
        self,
        factor_data: pd.DataFrame,
        target_date: date
    ) -> pd.Series:
        """Generate forecasts for a specific date.
        
        Args:
            factor_data: DataFrame of factor values
            target_date: Target date for forecast
            
        Returns:
            Series of forecasts indexed by ticker
        """
        if not self.ensemble.is_fitted:
            raise ValueError("Ensemble must be trained before forecasting")
        
        # Get factors for target date
        target_ts = pd.Timestamp(target_date)
        
        # Check if index is datetime-like
        dates = factor_data.index
        try:
            # Try to convert first element to timestamp
            first_idx = dates[0]
            pd.Timestamp(first_idx)
            is_datetime_index = True
        except (ValueError, TypeError):
            is_datetime_index = False
        
        if is_datetime_index:
            if target_ts in factor_data.index:
                X = factor_data.loc[target_ts]
            else:
                # Find closest date
                date_diffs = []
                for d in dates:
                    d_ts = pd.Timestamp(d) if not isinstance(d, pd.Timestamp) else d
                    date_diffs.append(np.abs((d_ts - target_ts).days))
                closest_idx = np.argmin(date_diffs)
                X = factor_data.iloc[closest_idx]
            # Make predictions (single row)
            predictions = self.ensemble.predict(pd.DataFrame(X).T)
        else:
            # Non-datetime index (e.g., ticker strings) - use entire DataFrame
            predictions = self.ensemble.predict(factor_data)
        
        return predictions
    
    def _clone_model(self, model: BaseModel) -> BaseModel:
        """Clone a model instance."""
        if isinstance(model, LinearRegressionModel):
            return LinearRegressionModel(
                fit_intercept=model.fit_intercept,
                normalize=model.normalize,
                feature_names=model.feature_names
            )
        elif isinstance(model, RandomForestModel):
            return RandomForestModel(
                n_estimators=model.n_estimators,
                max_depth=model.max_depth,
                random_state=model.random_state,
                feature_names=model.feature_names
            )
        elif isinstance(model, XGBoostModel):
            return XGBoostModel(
                n_estimators=model.n_estimators,
                max_depth=model.max_depth,
                learning_rate=model.learning_rate,
                random_state=model.random_state,
                verbosity=model.verbosity,
                feature_names=model.feature_names
            )
        else:
            raise ValueError(f"Unknown model type: {type(model)}")