# Issue 004: Return Forecasting Models
**Status:** [ ] Pending  
**Priority:** 🔴 High  
**Tags:** [AFK]  
**Blocked by:** 003  
**Type:** ML  
**Estimate:** 4-5 days

---

## Description

Train ensemble return forecasting models using factor features to predict 20-day forward excess returns.

## Vertical Slice Definition

This issue touches all relevant layers:
- **Data Layer:** Factor features from Factor Analysis Engine (via tools)
- **Model Layer:** Multiple ML models (linear, RF, XGBoost, LSTM)
- **Validation Layer:** Walk-forward cross-validation with purge/embargo
- **Ensemble Layer:** Model combination and weighting

## User Story

**As a** Data Scientist,  
**I want** to train return forecasting models,  
**so that** the portfolio optimizer has accurate expected returns.

## Acceptance Criteria

### Technical Requirements

- [ ] **Linear Regression:** Baseline with factor features, interpretable
- [ ] **Random Forest:** Captures non-linear interactions, robust to outliers
- [ ] **XGBoost/LightGBM:** Best-in-class for tabular data
- [ ] **LSTM (optional):** Time series patterns, sequential modeling
- [ ] **Ensemble:** Weighted combination of all models
- [ ] **Target:** 20-day forward excess return (vs risk-free rate)
- [ ] **Features:** Factor values, technical indicators, fundamental ratios, cross-sectional ranks
- [ ] **Validation:** Walk-forward CV with 5-day purge gap, 5-day embargo
- [ ] **Performance:** R² > 0.05 out-of-sample
- [ ] **Feature Importance:** Tracked and stable across folds
- [ ] **Training Time:** < 30 minutes for full history
- [ ] **Model Persistence:** Serialization and versioning

### Quality Requirements

- [ ] **Unit Tests:**
  - Test model training convergence
  - Test prediction shape and range
  - Test feature importance calculation
  - Test model serialization/deserialization

- [ ] **Integration Tests:**
  - End-to-end: Factors → Model training → Predictions
  - Test walk-forward validation splits
  - Test ensemble weighting
  - Test with holdout data

- [ ] **Performance:**
  - Single model training < 10 minutes
  - Full ensemble training < 30 minutes
  - Prediction for 500 stocks < 1 minute
  - Memory usage < 4GB during training

### Documentation Requirements

- Model architecture documentation
- Feature importance report
- Validation results (R², IC, RMSE)
- Hyperparameter configurations
- Model versioning scheme

## Implementation Plan

### Phase 1: Baseline Models (Days 1-2)
1. Implement linear regression baseline
2. Implement Random Forest
3. Feature engineering and preprocessing
4. Train/test split (temporal)

### Phase 2: Advanced Models (Days 2-3)
1. Implement XGBoost/LightGBM
2. Hyperparameter tuning (grid search or Bayesian optimization)
3. Optional: LSTM implementation
4. Feature selection

### Phase 3: Validation Framework (Day 4)
1. Implement walk-forward cross-validation
2. Add purge gap and embargo
3. Calculate R², IC, RMSE
4. Feature importance analysis

### Phase 4: Ensemble & Persistence (Day 5)
1. Create ensemble framework
2. Implement model weighting (based on validation performance)
3. Add model serialization (joblib/pickle)
4. Version tracking
5. Integration tests

## Dependencies

### Required
- Factor features (from issue #003)
- pandas, numpy, scikit-learn (already in requirements)

### New Dependencies
- xgboost or lightgbm (gradient boosting)
- torch (optional, for LSTM)
- optuna (optional, for hyperparameter tuning)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Poor forecast accuracy | Medium | High | Ensemble methods, feature engineering, regime detection, fallback to equal weight |
| Overfitting | Medium | High | Walk-forward validation, regularization, out-of-sample testing |
| Training too slow | Low | Medium | Feature selection, dimensionality reduction, incremental training |

## Definition of Done

- [ ] All models trained and validated
- [ ] R² > 0.05 out-of-sample achieved
- [ ] Feature importance stable across folds
- [ ] Models serialized and versioned
- [ ] All tests passing
- [ ] Performance requirements met
- [ ] Documentation complete
- [ ] Demo: Can generate return forecasts for current date

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 4 of 12 (Depends on 003)