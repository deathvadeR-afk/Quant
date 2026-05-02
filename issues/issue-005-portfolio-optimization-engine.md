# Issue 005: Portfolio Optimization Engine
**Title Mismatch Note:** Filename says "interpretability-monitoring" but content is "Portfolio Optimization Engine" - this issue implements the optimization engine per PRD and Kanban board.
**Status:** [ ] Pending  
**Priority:** 🔴 High  
**Tags:** [AFK]  
**Blocked by:** 004  
**Type:** Optimization  
**Estimate:** 3-4 days

---

## Description

Implement portfolio optimization with multiple methods (mean-variance, risk parity, max Sharpe) and constraint handling.

## Vertical Slice Definition

This issue touches all relevant layers:
- **Forecast Layer:** Return forecasts from ML models (via tools)
- **Optimization Layer:** cvxpy-based optimization engine
- **Risk Layer:** Risk models and constraint handling
- **Cost Layer:** Transaction cost modeling

## User Story

**As a** Portfolio Manager,  
**I want** to optimize portfolios with multiple methods,  
**so that** I can balance return and risk according to preferences.

## Acceptance Criteria

### Technical Requirements

- [ ] **Mean-Variance Optimization:** Maximize return for given risk (Markowitz)
- [ ] **Risk Parity:** Equal risk contribution from assets
- [ ] **Maximum Sharpe:** Maximize Sharpe ratio
- [ ] **Minimum Variance:** Minimize portfolio volatility
- [ ] **Constraint Handling:**
  - Sector limits (e.g., tech ≤ 25%)
  - Position size (e.g., 1% ≤ weight ≤ 10%)
  - Turnover (e.g., ≤ 20% per rebalance)
  - Long/short ratio (e.g., 130/30)
  - Gross exposure (e.g., ≤ 200%)
- [ ] **Transaction Costs:** 0.1% per trade (configurable)
- [ ] **Optimization Time:** < 30 seconds
- [ ] **Constraint Satisfaction:** All hard constraints satisfied
- [ ] **Risk Models:**
  - Sample covariance matrix
  - Ledoit-Wolf shrinkage
  - Factor risk model (optional)
  - VaR and CVaR calculations

### Quality Requirements

- [ ] **Unit Tests:**
  - Test optimization convergence
  - Test constraint satisfaction
  - Test objective function values
  - Test risk model calculations

- [ ] **Integration Tests:**
  - End-to-end: Forecasts → Optimization → Portfolio weights
  - Test with various constraint combinations
  - Test backtest integration

- [ ] **Performance:**
  - Optimization < 30 seconds for 500 stocks
  - Memory usage < 2GB
  - Backtest 10 years of data < 5 minutes

### Documentation Requirements

- Optimization methodology document
- Constraint specification guide
- Risk model documentation
- Backtesting results report

## Implementation Plan

### Phase 1: Mean-Variance Optimization (Day 1)
1. Implement Markowitz mean-variance
2. Add efficient frontier calculation
3. Test with various risk targets

### Phase 2: Additional Methods (Day 2)
1. Implement risk parity (equal risk contribution)
2. Implement maximum Sharpe ratio
3. Implement minimum variance

### Phase 3: Constraints & Costs (Day 3)
1. Add sector constraints
2. Add position size constraints
3. Add turnover constraints
4. Implement transaction cost modeling

### Phase 4: Risk Models & Integration (Day 4)
1. Implement covariance estimation (Ledoit-Wolf)
2. Add VaR and CVaR calculations
3. Integrate with return forecasts (via tools)
4. Performance optimization

## Dependencies

### Required
- Return forecasts (from issue #004, accessed via tools)
- cvxpy (optimization)
- numpy, pandas (already in requirements)

### New Dependencies
- cvxpy (convex optimization)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Optimization instability | Medium | High | Regularization, robust optimization, constraint relaxation |
| Poor out-of-sample performance | Medium | High | Conservative constraints, ensemble methods, walk-forward validation |
| Constraint conflicts | Low | Medium | Constraint prioritization, penalty methods |

## Definition of Done

- [ ] All optimization methods implemented
- [ ] Constraints properly handled
- [ ] Risk models functional
- [ ] Optimization < 30 seconds
- [ ] Backtested Sharpe > 1.2
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Demo: Can optimize portfolio with custom constraints

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 5 of 12 (Depends on 004)