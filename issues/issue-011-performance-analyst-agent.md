# Issue 011: Performance Analyst Agent
**Status:** [ ] Pending  
**Priority:** 🟡 Medium  
**Tags:** [AFK]  
**Blocked by:** 008  
**Type:** Agent  
**Estimate:** 2-3 days

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

### Technical Requirements

- [ ] Daily P&L attribution (factor, stock, timing)
- [ ] Benchmark comparison (SPY, equal-weight)
- [ ] Strategy drift detection
- [ ] Natural language report generation via Gemma 4
- [ ] Attribution explains 95%+ of daily P&L
- [ ] Reports generated < 5 minutes
- [ ] Historical performance tracking
- [ ] State management via Redis (issue #002)

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

### Phase 1: Agent Framework (Day 1)
1. Create agent class with LangGraph node
2. Implement state management (Redis)
3. Define message schemas

### Phase 2: Attribution & Analysis (Day 2)
1. Implement P&L attribution
2. Add benchmark comparison
3. Implement drift detection

### Phase 3: LLM Reporting (Day 3)
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

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 11 of 12 (Depends on 008)