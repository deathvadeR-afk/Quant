# Issue 008: Portfolio Constructor Agent
**Status:** [ ] Pending  
**Priority:** 🟡 Medium  
**Tags:** [AFK]  
**Blocked by:** 004, 005, 007  
**Type:** Agent  
**Estimate:** 4-5 days

---

## Description

Create agent that constructs optimal portfolios using ML return forecasts and optimization engine.

## Vertical Slice Definition

This issue touches all relevant layers:
- **Forecast Layer:** Return forecasts from ML models (via tools)
- **Optimization Layer:** Portfolio optimization engine (issue #005)
- **Constraint Layer:** User-specified constraints
- **Reporting Layer:** Allocation reports with LLM explanations

## User Story

**As a** Portfolio Manager,  
**I want** the Portfolio Constructor agent to build optimal portfolios,  
**so that** I maximize risk-adjusted returns within constraints.

## Acceptance Criteria

### Technical Requirements

- [ ] Integrates return forecasts from ML models (issue #004)
- [ ] Runs optimization with user-specified constraints
- [ ] Generates allocation reports with explanations (Gemma 4)
- [ ] Scenario analysis (bull/bear/base cases)
- [ ] Turnover and cost optimization
- [ ] Portfolios optimized < 60 seconds
- [ ] Backtested max drawdown < 10%
- [ ] State management via Redis (issue #002)

### Quality Requirements

- [ ] **Unit Tests:**
  - Test optimization integration
  - Test constraint handling
  - Test report generation
  - Test state updates

- [ ] **Integration Tests:**
  - End-to-end: Forecasts → Optimization → Portfolio
  - Test with various constraints
  - Test in LangGraph workflow

- [ ] **Performance:**
  - Optimization < 60 seconds
  - Memory usage < 2GB
  - Report generation < 2 minutes

### Documentation Requirements

- Agent configuration guide
- Constraint specification guide
- Report interpretation guide

## Implementation Plan

### Phase 1: Agent Framework (Day 1)
1. Create agent class with LangGraph node
2. Implement state management (Redis)
3. Define message schemas

### Phase 2: Optimization Integration (Days 1-2)
1. Integrate Portfolio Optimization Engine (issue #005)
2. Integrate Return Forecasting Models (issue #004)
3. Add constraint handling

### Phase 3: LLM & Reporting (Day 3)
1. Integrate Gemma 4 via NVIDIA NIM
2. Create allocation report generation
3. Implement scenario analysis
4. Add cost/turnover optimization

### Phase 4: Testing & Documentation (Day 4-5)
1. Unit and integration tests
2. Performance benchmarking
3. Documentation

## Dependencies

### Required
- Return Forecasting Models (issue #004)
- Portfolio Optimization Engine (issue #005)
- Factor Analyst Agent (issue #007)
- LangGraph (issue #002)
- Redis (issue #002)

### New Dependencies
- nvidia-nim (Gemma 4)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Poor portfolio performance | Medium | High | Multiple optimization methods, ensemble portfolios, conservative constraints |
| Constraint violations | Low | Medium | Hard constraints in optimizer, post-optimization validation |

## Definition of Done

- [ ] Agent constructs optimal portfolios
- [ ] Constraints properly handled
- [ ] Reports generated via Gemma 4
- [ ] Optimization < 60 seconds
- [ ] Max drawdown < 10% in backtests
- [ ] State management via Redis
- [ ] All tests passing
- [ ] Performance requirements met
- [ ] Documentation complete
- [ ] Demo: Agent produces optimized portfolio with report

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 8 of 12 (Depends on 004, 005, 007)