# Issue 011: Performance Analyst Agent

**Status:** [ ] Pending  
**Priority:** 🟡 Medium  
**Tags:** [AFK]  
**Blocked by:** 008  
**Type:** Agent  
**Estimate:** 2-3 days  
**Completed:**  
**PRD Section:** PRD Section 4.12, US-012  
**Status Notes:** No implementation files exist; only `agents/data_guardian.py` is present in the agents/ directory.

---

## Description

Create agent that analyzes performance and generates natural language reports.

## Vertical Slice Definition

This issue touches all relevant layers:

- **Analysis Layer:** P&L attribution
- **Benchmark Layer:** Performance comparison
- **Drift Layer:** Strategy drift detection
- **Reporting Layer:** Natural language report generation

## User Story

**As a** Fund Manager,  
**I want** the Performance Analyst agent to generate daily reports,  
**so that** I understand P&L drivers and strategy drift.

## Acceptance Criteria

### PRD Acceptance Criteria

As per PRD US-012: "As a Fund Manager, I can receive daily performance reports from the Performance Analyst agent so that I understand P&L drivers and strategy drift." Required criteria:

- Daily P&L attribution (factor, stock, timing)
- Benchmark comparison (SPY, equal-weight)
- Strategy drift detection
- Natural language report generation via Gemma 4
- Attribution explains 95%+ of daily P&L
- Reports generated < 5 minutes
- Historical performance tracking

### Technical Requirements

- [ ] Daily P&L attribution (factor, stock, timing) (Evidence: No implementation exists yet)
- [ ] Benchmark comparison (SPY, equal-weight) (Evidence: No implementation exists yet)
- [ ] Strategy drift detection (Evidence: No implementation exists yet)
- [ ] Natural language report generation via Gemma 4 (Evidence: No implementation exists yet)
- [ ] Attribution explains 95%+ of daily P&L (Evidence: No implementation exists yet)
- [ ] Reports generated < 5 minutes (Evidence: No implementation exists yet)
- [ ] Historical performance tracking (Evidence: No implementation exists yet)
- [ ] State management via Redis (issue #002) (Evidence: No implementation exists yet)

### Quality Requirements

- [ ] **Unit Tests:**
  - Test attribution calculations
  - Test drift detection
  - Test report generation
  - Test state updates

- [ ] **Integration Tests:**
  - End-to-end: Portfolio → Analysis → Report
  - Test in LangGraph workflow

- [ ] **Performance:**
  - Report generation < 5 minutes
  - Memory usage < 1GB
  - LLM latency < 30 seconds

### Documentation Requirements

- Attribution methodology
- Drift detection criteria
- Report interpretation guide

## Implementation Plan

### Phase1: Agent Framework (Day 1)

1. Create agent class with LangGraph node
2. Implement state management (Redis)
3. Define message schemas

### Phase2: Attribution & Analysis (Day 2)

1. Implement P&L attribution
2. Add benchmark comparison
3. Implement drift detection

### Phase3: LLM Reporting (Day 3)

1. Integrate Gemma 4 via NVIDIA NIM
2. Create report generation
3. Add historical tracking

## Dependencies

### Required

- Portfolio Constructor Agent (issue #008)
- LangGraph (issue #002)
- Redis (issue #002)

### New Dependencies

- nvidia-nim (Gemma 4)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Inaccurate attribution | Low | Medium | Multiple attribution methods, cross-validation |
| LLM hallucination | Medium | Medium | Ground in actual data |

## Definition of Done

- [ ] P&L attribution functional
- [ ] Benchmark comparison operational
- [ ] Drift detection working
- [ ] Reports generated via Gemma 4
- [ ] Attribution explains 95%+ of P&L
- [ ] Reports < 5 minutes
- [ ] State management via Redis
- [ ] All tests passing
- [ ] Performance requirements met
- [ ] Documentation complete
- [ ] Demo: Agent generates daily performance report

## Audit Findings

| Discrepancy | Classification | File Reference | Details |
|-------------|----------------|----------------|---------|
| No code implementation exists | HIGH | `agents/` directory | Only `agents/data_guardian.py` exists; no Performance Analyst Agent code found |

## Next Steps

1. Create `agents/performance_analyst.py` with LangGraph node integration
2. Implement P&L attribution and benchmark comparison logic
3. Add Gemma 4 LLM integration for natural language report generation
4. Implement strategy drift detection and historical performance tracking
5. Add unit and integration tests per PRD requirements
6. Validate report generation latency < 5 minutes and 95%+ P&L attribution accuracy

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 11 of 12 (Depends on 008)
