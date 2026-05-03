# Issue 009: Risk Manager Agent

**Status:** [ ] Pending  
**Priority:** 🟡 Medium  
**Tags:** [AFK]  
**Blocked by:** 008  
**Type:** Agent  
**Estimate:** 3-4 days  
**Completed:**  
**PRD Section:** PRD Section 4.10, US-010  
**Status Notes:** No implementation files exist; only `agents/data_guardian.py` is present in the agents/ directory.

---

## Description

Create agent that monitors risk in real-time and enforces circuit breakers.

## Vertical Slice Definition

This issue touches all relevant layers:

- **Monitoring Layer:** Real-time risk metric tracking
- **Circuit Breaker Layer:** Automatic position limits
- **Analysis Layer:** Stress testing and scenario analysis
- **Alerting Layer:** Notification system

## User Story

**As a** Risk Manager,  
**I want** the Risk Manager agent to monitor exposures,  
**so that** I receive immediate alerts when risk thresholds are breached.

## Acceptance Criteria

### PRD Acceptance Criteria

As per PRD US-010: "As a Risk Manager, I can rely on the Risk Manager agent to monitor exposures so that I receive immediate alerts when risk thresholds are breached." Required criteria:

- Monitors 20+ risk metrics in real-time
- Circuit breakers trigger < 100ms
- Calculates VaR (95%, 99%) and CVaR
- Stress tests: 2008, 2020, 2022 scenarios
- Correlation breakdown detection
- Position and exposure limit enforcement
- Zero false-negative alerts in testing

### Technical Requirements

- [ ] Monitors 20+ risk metrics in real-time (Evidence: No implementation exists yet)
- [ ] Circuit breakers trigger < 100ms (Evidence: No implementation exists yet)
- [ ] Calculates VaR (95%, 99%) and CVaR (Evidence: No implementation exists yet)
- [ ] Stress tests: 2008, 2020, 2022 scenarios (Evidence: No implementation exists yet)
- [ ] Correlation breakdown detection (Evidence: No implementation exists yet)
- [ ] Position and exposure limit enforcement (Evidence: No implementation exists yet)
- [ ] Zero false-negative alerts in testing (Evidence: No implementation exists yet)
- [ ] State management via Redis (issue #002) (Evidence: No implementation exists yet)

### Quality Requirements

- [ ] **Unit Tests:**
  - Test risk metric calculations
  - Test circuit breaker logic
  - Test stress test scenarios
  - Test alert delivery

- [ ] **Integration Tests:**
  - End-to-end: Portfolio → Risk monitoring → Alerts
  - Test circuit breaker triggers
  - Test in LangGraph workflow

- [ ] **Performance:**
  - Risk calculations < 1 second
  - Circuit breaker trigger < 100ms
  - Memory usage < 1GB

### Documentation Requirements

- Risk metric definitions
- Circuit breaker configuration
- Stress test scenarios
- Alert response procedures

## Implementation Plan

### Phase1: Agent Framework (Day 1)

1. Create agent class with LangGraph node
2. Implement state management (Redis)
3. Define message schemas

### Phase2: Risk Metrics (Day 2)

1. Implement VaR and CVaR calculations
2. Add correlation monitoring
3. Implement exposure tracking

### Phase3: Circuit Breakers (Day 3)

1. Implement circuit breaker logic
2. Add position limit enforcement
3. Configure alert thresholds

### Phase4: Stress Testing & Integration (Day 4)

1. Implement stress test scenarios
2. Add alert delivery system
3. Performance optimization

## Dependencies

### Required

- Portfolio Constructor Agent (issue #008)
- LangGraph (issue #002)
- Redis (issue #002)

### New Dependencies

- scipy (statistical calculations)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| False circuit breaker triggers | Medium | High | Multi-factor confirmation, graduated response, human override |
| Risk model failure | Low | High | Model diversity, fallback to simpler models |

## Definition of Done

- [ ] Risk metrics monitored in real-time
- [ ] Circuit breakers functional (< 100ms)
- [ ] Stress tests operational
- [ ] Zero false-negative alerts
- [ ] State management via Redis
- [ ] All tests passing
- [ ] Performance requirements met
- [ ] Documentation complete
- [ ] Demo: Agent triggers circuit breaker on risk breach

## Audit Findings

| Discrepancy | Classification | File Reference | Details |
|-------------|----------------|----------------|---------|
| No code implementation exists | HIGH | `agents/` directory | Only `agents/data_guardian.py` exists; no Risk Manager Agent code found |

## Next Steps

1. Create `agents/risk_manager.py` with LangGraph node integration
2. Implement core risk metrics (VaR, CVaR, correlation monitoring)
3. Add circuit breaker logic and position limit enforcement
4. Implement stress test scenarios for 2008, 2020, 2022
5. Add unit and integration tests per PRD requirements
6. Validate circuit breaker trigger latency < 100ms and zero false-negative alerts

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 9 of 12 (Depends on 008)
