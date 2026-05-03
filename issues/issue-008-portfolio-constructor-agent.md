# Issue 008: Portfolio Constructor Agent

**Status:** [ ] Pending  
**Priority:** 🟡 Medium  
**Tags:** [AFK]  
**Blocked by:** 004, 005, 007  
**Type:** Agent  
**Estimate:** 4-5 days  
**Completed:**  
**PRD Section:** PRD Section 4.9, US-009  
**Status Notes:** No implementation files exist; only `agents/data_guardian.py` is present in the agents/ directory.

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

### PRD Acceptance Criteria

As per PRD US-009: "As a Portfolio Manager, I can use the Portfolio Constructor agent to build optimal portfolios so that I maximize risk-adjusted returns within constraints." Required criteria:

- Integrates return forecasts from ML models
- Runs optimization with user-specified constraints
- Generates allocation reports with explanations
- Scenario analysis (bull/bear/base cases)
- Turnover and cost optimization
- Portfolios optimized < 60 seconds
- Backtested max drawdown < 10%

### Technical Requirements

- [ ] Integrates return forecasts from ML models (issue #004) (Evidence: No implementation exists yet)
- [ ] Runs optimization with user-specified constraints (Evidence: No implementation exists yet)
- [ ] Generates allocation reports with explanations (Gemma 4) (Evidence: No implementation exists yet)
- [ ] Scenario analysis (bull/bear/base cases) (Evidence: No implementation exists yet)
- [ ] Turnover and cost optimization (Evidence: No implementation exists yet)
- [ ] Portfolios optimized < 60 seconds (Evidence: No implementation exists yet)
- [ ] Backtested max drawdown < 10% (Evidence: No implementation exists yet)
- [ ] State management via Redis (issue #002) (Evidence: No implementation exists yet)

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

### Phase1: Agent Framework (Day 1)

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

## Audit Findings

| Discrepancy | Classification | File Reference | Details |
|-------------|----------------|----------------|---------|
| No code implementation exists | HIGH | `agents/` directory | Only `agents/data_guardian.py` exists; no Portfolio Constructor Agent code found |

## Next Steps

1. Create `agents/portfolio_constructor.py` with LangGraph node integration
2. Integrate with Portfolio Optimization Engine (issue #005) and Return Forecasting Models (issue #004)
3. Add Gemma 4 LLM integration for allocation report generation
4. Implement scenario analysis and cost/turnover optimization logic
5. Add unit and integration tests per PRD requirements
6. Validate optimization latency < 60 seconds and max drawdown < 10%

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 8 of 12 (Depends on 004, 005, 007)
