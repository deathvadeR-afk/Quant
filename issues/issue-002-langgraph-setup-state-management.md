# Issue 002: LangGraph Setup & State Management

**Status:** [x] Done (2026-05-03)
**Priority:** 🔴 High
**Tags:** [AFK]
**Blocked by:** 001
**Type:** Infrastructure
**Estimate:** 3-4 days
**PRD Section:** PRD Section 4.3, US-002
**Status Notes:** All audit discrepancies have been resolved. Per-node state persistence implemented, state_manager timeout fixed to 0.1s (100ms), performance validation tests added for <2h execution and <100ms state queries, streaming support tested. All 33 tests pass.

---

## Description

Set up LangGraph orchestration with Redis-backed state management for agent coordination.

## Vertical Slice Definition

This issue touches all relevant layers:

- **Orchestration Layer:** LangGraph graph topology and node definitions
- **State Layer:** Redis-backed persistent state with Pydantic models
- **Routing Layer:** Conditional edges for agent workflows
- **Persistence Layer:** State backup and recovery

## User Story

**As a** System Architect,  
**I want** LangGraph orchestration with Redis state management,  
**so that** agents can coordinate workflows and persist state across restarts.

## Acceptance Criteria

### PRD Acceptance Criteria

As per PRD US-002: "As a system architect, I want a LangGraph orchestration framework with state management so that I can coordinate agent workflows." Required criteria:

- [x] LangGraph setup with state management (evidence: [`graph/trading_graph.py`](graph/trading_graph.py))
- [x] Redis persistence (evidence: [`graph/state_manager.py`](graph/state_manager.py))
- [x] Streaming support (evidence: [`graph/trading_graph.py:49-57`](graph/trading_graph.py:49-57), [`tests/test_trading_graph.py`](tests/test_trading_graph.py) TestStreaming)
- [x] Graph execution <2h (evidence: [`tests/test_trading_graph.py`](tests/test_trading_graph.py) test_graph_execution_time)
- [x] State queries <100ms (evidence: [`graph/state_manager.py:41`](graph/state_manager.py:41), [`tests/test_trading_graph.py`](tests/test_trading_graph.py) test_state_query_performance)

### Technical Requirements

- [x] LangGraph graph topology defined with agent nodes and conditional edges
- [x] Redis state schema implemented with Pydantic models
- [x] State persists across system restarts
- [x] Agent transitions logged with timestamps and reasoning
- [x] Error recovery flows (retry, fallback, human escalation)
- [x] Graph execution < 2 hours for full daily cycle (Evidence: [`tests/test_trading_graph.py`](tests/test_trading_graph.py) test_graph_execution_time)
- [x] State queries < 100ms (Evidence: [`graph/state_manager.py:41`](graph/state_manager.py:41), [`tests/test_trading_graph.py`](tests/test_trading_graph.py) test_state_query_performance)
- [x] Streaming support for real-time updates

### Quality Requirements

- [x] **Unit Tests:**
  - Test state serialization/deserialization
  - Test graph node execution
  - Test conditional routing logic
  - Test error recovery flows

- [x] **Integration Tests:**
  - Test full graph execution with mock agents
  - Test state persistence across restarts
  - Test concurrent graph executions
  - Test Redis connection failures

- [x] **Performance:**
  - State read/write < 100ms
  - Graph execution < 2 hours for full cycle
  - Memory usage < 1GB during execution

### Documentation Requirements

- [x] Graph topology documentation
- [x] State schema documentation
- [x] Agent communication protocol
- [x] Error recovery procedures

## Implementation Plan

### Phase 1: Graph Design (Day 1)

1. Design agent node topology
2. Define conditional routing logic
3. Create state schema with Pydantic
4. Design error recovery flows

### Phase 2: State Management (Day 2)

1. Implement Redis state manager
2. Create Pydantic models for state
3. Add state versioning and audit trail
4. Implement state backup/restore

### Phase 3: Graph Implementation (Day 3)

1. Create LangGraph nodes for each agent
2. Implement conditional edges
3. Add streaming support
4. Implement error handling

### Phase 4: Integration & Testing (Day 4)

1. Test graph execution
2. Test state persistence
3. Test error recovery
4. Performance benchmarking

## Dependencies

### Required

- langgraph (graph orchestration)
- redis (state storage)
- pydantic (state models)
- issue #001 (tool wrappers)

### New Dependencies

- redis-py (Redis client)
- pydantic (data validation)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Graph complexity unmanageable | Medium | Medium | Modular design, hierarchical graphs |
| State corruption | Low | High | Atomic updates, validation, backup/restore |
| Redis unavailable | Low | High | Connection pooling, retry logic |

## Definition of Done

- [x] LangGraph topology implemented
- [x] Redis state management functional
- [x] All tests passing
- [x] Performance requirements met
- [x] Documentation complete
- [x] Demo: Full graph execution with state persistence

## Audit Findings

| Discrepancy | Classification | File Reference | Details |
|-------------|----------------|----------------|---------|
| No performance validation for <2h graph execution/<100ms state queries | HIGH | [`tests/test_trading_graph.py`](tests/test_trading_graph.py) | Missing performance benchmarks |
| State saved only at end of cycle, not per-node | MEDIUM | [`graph/trading_graph.py:284`](graph/trading_graph.py:284) | State persistence not implemented per-node |
| Missing streaming/performance tests | MEDIUM | [`tests/test_trading_graph.py`](tests/test_trading_graph.py) | No test coverage for streaming or performance requirements |

## Resolution Summary (Completed 2026-05-03)

| Discrepancy | Resolution |
|-------------|------------|
| State saved only at end of cycle | Modified [`graph/trading_graph.py`](graph/trading_graph.py) to save state after each node via `graph.stream()` |
| State manager timeout 1.0s vs PRD <100ms | Changed [`graph/state_manager.py:41`](graph/state_manager.py:41) `operation_timeout` to 0.1 (100ms) |
| No performance validation for <2h execution | Added `test_graph_execution_time()` to [`tests/test_trading_graph.py`](tests/test_trading_graph.py) |
| No performance validation for <100ms queries | Added `test_state_query_performance()` to [`tests/test_trading_graph.py`](tests/test_trading_graph.py) |
| Missing streaming/performance tests | Added `test_streaming_support()` to [`tests/test_trading_graph.py`](tests/test_trading_graph.py) |

## Next Steps

- [x] All implementation gaps resolved
- [x] Performance validation tests passing (33/33 tests)
- [x] Issue marked as [x] Done

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 2 of 12 (Depends on 001)
