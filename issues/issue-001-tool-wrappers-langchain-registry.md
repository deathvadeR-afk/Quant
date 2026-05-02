# Issue 001: Tool Wrappers & LangChain Registry
**Status:** [x] DONE
**Priority:** 🔴 High
**Tags:** [AFK]
**Blocked by:** None
**Type:** Infrastructure
**Estimate:** 2-3 days
**Completed:** 2026-04-26

---

## Description

Create thin LangChain tool wrappers around existing data modules. Existing production code remains untouched - only thin wrapper layers are added.

## Vertical Slice Definition

This issue touches all relevant layers:
- **Integration Layer:** LangChain tool wrappers around existing modules
- **Existing Code Layer:** data_quality, universe_selection, price_data, fundamental_data (UNCHANGED)
- **Registry Layer:** Central tool registry for agent access
- **Documentation Layer:** Tool descriptions optimized for LLM consumption

## User Story

**As a** Quant Engineer,  
**I want** to wrap existing data modules as LangChain tools,  
**so that** agents can access production data without modifying existing code.

## Acceptance Criteria

### Technical Requirements

- [ ] `DataQualityTool` wraps `run_full_data_quality_check()` - returns structured quality metrics
- [ ] `UniverseSelectionTool` wraps `get_all_tickers()`, `select_universe()` - returns universe DataFrame as JSON
- [ ] `PriceDataTool` wraps `download_price_data()`, `get_existing_price_dates()` - returns price data
- [ ] `FundamentalDataTool` wraps `download_fundamental_data()` - returns fundamental data
- [ ] `PortfolioQueryTool` wraps `get_selected_tickers()`, `get_portfolio_exposure()` - returns portfolio state
- [ ] All tools return JSON-serializable outputs with clear schemas
- [ ] Tool descriptions optimized for LLM consumption (clear, concise, include input/output specs)
- [ ] Tool execution timeout: 30 seconds with configurable timeout per tool
- [ ] Error handling with graceful degradation (return error message, not crash)

### Quality Requirements

- [ ] **Unit Tests:**
  - Test each tool wrapper matches direct function call output
  - Test timeout handling
  - Test error handling for invalid inputs
  - Test JSON serialization

- [ ] **Integration Tests:**
  - Test tool invocation through LangChain
  - Test tool from agent context
  - Test concurrent tool execution

- [ ] **Performance:**
  - Tool execution < 5 seconds for typical queries
  - Memory usage < 500MB per tool invocation
  - Support concurrent execution of 5+ tools

### Documentation Requirements

- Tool reference documentation (inputs, outputs, examples)
- Integration guide for adding new tools
- LLM prompt templates for tool usage

## Implementation Plan

### Phase 1: Tool Wrapper Design (Day 1)
1. Define common tool interface
2. Design JSON output schemas for each tool
3. Create error handling strategy
4. Define timeout configuration

### Phase 2: Implement Core Tools (Day 1-2)
1. `DataQualityTool` - wraps data_quality module
2. `PriceDataTool` - wraps price_data module
3. `FundamentalDataTool` - wraps fundamental_data module

### Phase 3: Implement Query Tools (Day 2)
1. `UniverseSelectionTool` - wraps universe_selection module
2. `PortfolioQueryTool` - wraps db_schema query functions

### Phase 4: Registry & Integration (Day 3)
1. Create tool registry for easy agent access
2. Add LangChain integration
3. Implement timeout and error handling
4. Test all tools

### Phase 5: Testing & Documentation (Day 3)
1. Unit tests for each tool
2. Integration tests
3. Performance benchmarking
4. Documentation

## Dependencies

### Required
- langchain (tool base classes)
- Existing data modules (unchanged)

### New Dependencies
- langchain-core (tool interface)

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Tool execution too slow | Medium | Medium | Add timeouts, implement caching for expensive queries |
| LLM can't understand tool outputs | Low | Medium | Format as structured JSON, add clear descriptions |
| Breaking existing code | Very Low | High | Zero changes to existing modules, wrappers only |

## Definition of Done

- [ ] All 5 tools implemented and tested
- [ ] Tools integrated with LangChain
- [ ] Tool registry created
- [ ] All tests passing
- [ ] Performance requirements met
- [ ] Documentation complete
- [ ] Demo: Agent can invoke tools successfully

---

**Created:** 2026-04-25  
**Owner:** AI Assistant  
**Priority Order:** 1 of 12 (First to implement)