# Issue 003: Factor Analysis Engine
**Status:** [x] Done
**Priority:** 🔴 High
**Tags:** [AFK]
**Blocked by:** 001
**Type:** Feature
**Estimate:** 4-5 days
**Completed:** 2026-04-26

---

## Description

Calculate and validate 20+ factors across value, momentum, quality, volatility, and size categories for portfolio construction.

## Vertical Slice Definition

This issue touches all relevant layers:
- **Data Layer:** Reads from existing price/fundamental data (via tools)
- **Calculation Layer:** Factor computation engine
- **Validation Layer:** IC calculation and walk-forward backtesting
- **Storage Layer:** Factor values and metadata

## User Story

**As a** Quant Analyst,  
**I want** to calculate and validate 20+ predictive factors,  
**so that** I can identify signals for portfolio construction.

## Acceptance Criteria

### Technical Requirements

- [ ] **Value Factors:** P/E, P/B, EV/EBITDA, dividend yield, price/FCF
- [ ] **Momentum Factors:** 1M, 3M, 6M, 12M returns, RSI(14), MACD histogram
- [ ] **Quality Factors:** ROE, ROA, profit margin, debt/equity, earnings stability
- [ ] **Volatility Factors:** 20d historical vol, beta (vs SPY), max drawdown
- [ ] **Size Factor:** Market cap percentile within universe
- [ ] All factors normalized (sector-neutral z-scores) and winsorized (1st/99th)
- [ ] Factor IC calculated with walk-forward validation
- [ ] 5+ factors achieve IC > 0.05 out-of-sample
- [ ] Factor backtesting < 5 minutes per factor
- [ ] Factor library with metadata (category, calculation, frequency)

### Quality Requirements

- [ ] **Unit Tests:**
  - Test factor calculations against manual examples
  - Test normalization and winsorization
  - Test IC calculation
  - Test missing data handling

- [ ] **Integration Tests:**
  - End-to-end: Data → Factors → IC calculation
  - Test with subset of stocks before full 500
  - Test factor stability across time periods

- [ ] **Performance:**
  - Factor calculation < 5 minutes for 20 factors × 500 stocks
  - Memory usage < 2GB
  - IC calculation < 1 minute

### Documentation Requirements

- Factor dictionary (name, category, formula, interpretation)
- Calculation methodology document
- IC and backtesting results report

## Implementation Plan

### Phase 1: Factor Calculations (Days 1-2)
1. Implement value factors (P/E, P/B, EV/EBITDA, etc.)
2. Implement momentum factors (returns, RSI, MACD)
3. Implement quality factors (ROE, ROA, margins)
4. Implement volatility factors (volatility, beta, drawdown)
5. Implement size factor (market cap percentile)

### Phase 2: Preprocessing (Day 3)
1. Sector-neutral z-score normalization
2. Winsorization at 1st/99th percentiles
3. Missing value imputation (sector median)
4. Point-in-time correctness

### Phase 3: Validation (Day 4)
1. Information Coefficient (IC) calculation
2. Walk-forward validation framework
3. ICIR (IC Information Ratio) for stability
4. Factor correlation analysis

### Phase 4: Library & Integration (Day 5)
1. Create factor library with metadata
2. Integrate with existing data pipeline (via tools)
3. Performance optimization
4. Documentation and reporting

## Dependencies

### Required
- Existing data modules (accessed via tools from issue #001)
- pandas, numpy (already in requirements)

### New Dependencies
- scipy (statistical tests)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Factors not predictive | Medium | High | Test multiple variations, economic rationale, out-of-sample validation |
| Computational expense | Medium | Medium | Vectorized operations, parallel processing |
| Lookahead bias | Low | Critical | Strict temporal separation, point-in-time data |

## Definition of Done

- [ ] 20+ factors calculated and validated
- [ ] 5+ factors with IC > 0.05
- [ ] All tests passing
- [ ] Performance requirements met
- [ ] Documentation complete
- [ ] Demo: Factor library accessible to agents

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 3 of 12 (Depends on 001)