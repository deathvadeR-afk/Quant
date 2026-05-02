# Grill Me Session: Agentic AI Multi-Factor Trading System

## Session Overview
**Date:** 2026-04-25  
**Feature:** Multi-Factor Equity Long/Short Strategy with Agentic AI  
**Status:** Phase 1 - Design Alignment Complete

## Objective
Build a production-grade agentic trading system that leverages existing data infrastructure through LangChain tool wrappers, uses 6 specialized AI agents orchestrated by LangGraph, and integrates NVIDIA Gemma 4 LLM for intelligent decision-making. The system combines institutional-quality factor analysis, ML-based return forecasting, and portfolio optimization with autonomous agent coordination.

---

## Key Design Questions & Recommendations

### Q1: What is the overall system architecture?
**Recommended Answer:** Multi-layer agentic architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestration                   │
│         (Graph-based agent coordination, Redis state)        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │  Data   │ │ Factor  │ │Portfolio│ │  Risk   │ │Execution│
   │ Guardian│ │ Analyst │ │Constructor│ │ Manager │ │Strategist│
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
        │          │          │          │          │
        └──────────┴──────────┼──────────┴──────────┘
                              ▼
                    ┌─────────────────┐
                    │Performance Analyst│
                    └─────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │  Tool   │          │   ML    │          │  LLM    │
   │Registry │          │ Models  │          │ (Gemma4)│
   │(Wrapped │          │(Return  │          │         │
   │Existing)│          │Forecast)│          │         │
   └─────────┘          └─────────┘          └─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │  Data   │          │  Factor │          │Portfolio│
   │ Pipeline│          │ Engine  │          │   Opt   │
   │(Existing)│         │ (New)   │          │ (New)   │
   └─────────┘          └─────────┘          └─────────┘
```

**Rationale:** Agentic architecture provides autonomous decision-making, natural language interaction, and modular extensibility. LangGraph enables complex workflows with conditional routing and error recovery.

**Dependencies:** LangChain, LangGraph, Redis, NVIDIA NIM API access.

---

### Q2: How do we leverage existing infrastructure without rebuilding?
**Recommended Answer:** Create thin LangChain tool wrappers around existing modules:

**Existing Modules → Tool Wrappers:**
- `data_quality.py` → `DataQualityTool` (wraps `run_full_data_quality_check()`)
- `universe_selection.py` → `UniverseSelectionTool` (wraps `get_all_tickers()`, `select_universe()`)
- `price_data.py` → `PriceDataTool` (wraps `download_price_data()`, `get_existing_price_dates()`)
- `fundamental_data.py` → `FundamentalDataTool` (wraps `download_fundamental_data()`)
- `db_schema.py` → `PortfolioQueryTool` (wraps `get_selected_tickers()`, `get_portfolio_exposure()`)

**Implementation:**
```python
from langchain.tools import BaseTool

class DataQualityTool(BaseTool):
    name = "data_quality_check"
    description = "Run full data quality validation on price/fundamental data"
    
    def _run(self, tickers: List[str]):
        from data.data_quality import run_full_data_quality_check
        return run_full_data_quality_check(tickers)
```

**Rationale:** Existing code is production-grade (34K+ test lines). Wrappers take 1-2 days vs. weeks of rebuilding. Maintains backward compatibility.

**Dependencies:** langchain, existing data modules.

---

### Q3: What are the 6 specialized agents and their responsibilities?
**Recommended Answer:**

**1. Data Guardian Agent (Week 7)**
- Monitors data quality in real-time
- Wraps `DataQualityManager` with LLM-enhanced reporting
- Detects anomalies using Isolation Forest
- Generates natural language quality reports via Gemma 4
- Suggests remediation actions

**2. Factor Analyst Agent (Week 8)**
- Calculates and validates 20+ factors (value, momentum, quality, volatility, size)
- Generates factor hypotheses using LLM reasoning
- Backtests factors with IC > 0.05 threshold
- Ranks factors by predictive power
- Produces research reports

**3. Portfolio Constructor Agent (Week 9)**
- Integrates return forecasting models (linear, RF, XGBoost, LSTM)
- Runs portfolio optimization (mean-variance, risk parity, max Sharpe)
- Handles constraints (sector, position size, turnover)
- Generates allocation reports with explanations

**4. Risk Manager Agent (Week 10)**
- Monitors 20+ risk metrics in real-time
- Implements circuit breakers (trigger < 100ms)
- Calculates VaR, CVaR, factor exposures
- Runs stress tests (2008, 2020, 2022 scenarios)
- Enforces position and exposure limits

**5. Execution Strategist Agent (Week 11)**
- Predicts market impact
- Implements optimal order slicing (VWAP, TWAP)
- Seeks liquidity
- Simulates paper trading
- Achieves 20% better execution costs than VWAP baseline

**6. Performance Analyst Agent (Week 11)**
- Performs daily P&L attribution
- Compares to benchmarks
- Detects strategy drift
- Generates natural language performance reports
- Explains 95%+ of daily P&L

**Rationale:** Specialized agents provide modularity, expertise, and parallel processing. Each agent can be developed, tested, and deployed independently.

**Dependencies:** All agents depend on Tool Registry and LLM integration.

---

### Q4: How does LangGraph orchestration work?
**Recommended Answer:** Graph topology with conditional routing:

```
Start → Data Guardian → [Check Quality]
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
         [Quality OK]            [Quality Issues]
              │                       │
              ▼                       ▼
        Factor Analyst ←────── Data Guardian
              │              (Remediation Loop)
              ▼
        [Factors Validated]
              │
              ▼
        Portfolio Constructor
              │
              ▼
        [Portfolio Built]
              │
              ▼
        Risk Manager
              │
        ┌─────┴─────┐
        ▼           ▼
   [Risk OK]   [Risk Breach]
        │           │
        ▼           ▼
   Execution   Portfolio Constructor
   Strategist   (Re-optimization)
        │
        ▼
   Performance Analyst
        │
        ▼
       End
```

**State Management:** Redis-backed persistent state
- Agent outputs, decisions, and reasoning logged
- State persists across system restarts
- Audit trail for compliance

**Rationale:** Graph-based routing enables complex workflows, error recovery, and conditional logic. Redis provides fast, persistent state.

**Dependencies:** langgraph, redis, pydantic (state schema).

---

### Q5: What is the role of NVIDIA Gemma 4 LLM?
**Recommended Answer:** LLM serves as the "brain" for reasoning and communication:

**Agent Reasoning:**
- Data Guardian: "The price data for AAPL shows a 15% spike. This could be a split or a data error. Let me check corporate actions..."
- Factor Analyst: "Value factors have IC = 0.08 this month, exceeding the 0.05 threshold. I recommend increasing value exposure."
- Portfolio Constructor: "Given the risk constraints, I'll use risk parity instead of mean-variance to reduce concentration."

**Report Generation:**
- Natural language quality reports
- Factor research summaries
- Portfolio allocation explanations
- Risk assessment narratives
- Performance commentaries

**Hypothesis Generation:**
- LLM suggests new factor combinations
- Proposes regime-dependent strategies
- Identifies market anomalies

**Rationale:** Gemma 4 via NVIDIA NIM provides fast, cost-effective inference. Natural language makes the system accessible to non-technical users.

**Dependencies:** NVIDIA NIM API, langchain-nvidia-ai-endpoints.

---

### Q6: What new engines need to be built?
**Recommended Answer:** Three critical engines:

**Factor Analysis Engine (Weeks 3-4):**
- 20+ factors: P/E, P/B, EV/EBITDA, momentum (1M/3M/6M/12M), ROE, ROA, volatility, beta, size
- Factor normalization and winsorization
- Factor correlation analysis
- IC calculation and backtesting
- Factor library with metadata

**Portfolio Optimization Engine (Weeks 5-6):**
- Return forecasting: Linear regression, Random Forest, XGBoost, LSTM
- Optimization methods: Mean-variance, risk parity, max Sharpe, min variance
- Risk models: Ledoit-Wolf covariance, VaR, CVaR, factor risk
- Transaction cost modeling
- Constraint handling

**Return Forecasting Models (Weeks 5-6):**
- Ensemble of linear, tree-based, and neural models
- Walk-forward validation
- Feature engineering from factor analysis
- R² > 0.05 out-of-sample target

**Rationale:** These engines are the core value-add. Existing infrastructure handles data; new engines handle intelligence.

**Dependencies:** scikit-learn, xgboost, lightgbm, cvxpy, pytorch (for LSTM).

---

### Q7: How do we avoid lookahead bias and overfitting?
**Recommended Answer:** Strict temporal discipline:

**Data Handling:**
- Point-in-time correctness: Use reporting dates, not period dates
- If Q2 earnings released Aug 15, don't use before Aug 15
- Feature lag: All features use t-1 data to predict t

**Validation:**
- Walk-forward cross-validation with purge gaps
- Out-of-sample testing (minimum 12 months)
- Multiple testing correction for factor discovery
- Economic rationale requirement for all factors

**Monitoring:**
- Real-time IC tracking
- Performance decay detection
- Feature drift monitoring (KS tests)
- Automatic retraining triggers

**Rationale:** Financial data is noisy with low signal-to-noise ratio. Strict validation prevents false discoveries.

**Dependencies:** Custom CV splitters, statistical tests.

---

### Q8: What is the minimal viable product (MVP) scope?
**Recommended Answer:** Phase 1-2 deliverables (Weeks 1-6):

**Must-Have:**
- ✅ Tool wrappers for existing data modules (Week 1)
- ✅ LangGraph setup with 2 agents (Data Guardian, Factor Analyst) (Week 2)
- ✅ Factor Analysis Engine with 10+ validated factors (Weeks 3-4)
- ✅ Return forecasting model (single XGBoost) (Week 5)
- ✅ Portfolio optimization (mean-variance) (Week 6)
- ✅ Backtesting framework with IC and Sharpe metrics

**Nice-to-Have (Phase 3+):**
- All 6 agents operational
- LSTM return forecasting
- Risk parity optimization
- Real-time execution simulation
- Advanced LLM reasoning

**Dependencies:** Core engines, agent infrastructure.

---

## Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture** | Agentic AI with LangGraph | Autonomous, modular, extensible |
| **Existing Code** | Thin LangChain tool wrappers | Preserve investment, quick integration |
| **LLM** | NVIDIA Gemma 4 via NIM | Fast, cost-effective, proven |
| **State Management** | Redis | Fast, persistent, scalable |
| **Factor Engine** | 20+ validated factors | Institutional standard |
| **Optimization** | cvxpy with multiple methods | Robust, constraint-aware |
| **Forecasting** | Ensemble (linear, RF, XGBoost, LSTM) | Capture linear and non-linear patterns |
| **Validation** | Walk-forward CV with purge gaps | Prevent lookahead bias |
| **MVP Scope** | 2 agents + core engines | Deliver value quickly, iterate |

---

## Open Questions for User

1. **Risk tolerance:** What maximum drawdown is acceptable? (REVISED plan targets < 10%)
2. **Rebalancing frequency:** Monthly, weekly, or daily? (REVISED plan suggests monthly)
3. **LLM budget:** What is the monthly NVIDIA NIM budget? (Affects inference frequency)
4. **Asset classes:** US equities only, or include crypto/forex? (REVISED plan: US equities)
5. **Live trading:** Paper trading only, or gradual live rollout? (REVISED plan: Paper first)

---

## Next Steps

**If aligned, proceed to:**
- Phase 2: Write detailed PRD with user stories and acceptance criteria
- Phase 3: Break into vertical slice issues (tool wrappers → agents → orchestration)
- Phase 4: Implement using TDD (test-driven development)

**Estimated Timeline:**
- MVP (2 agents + engines): 6 weeks
- Full system (6 agents): 24 weeks

---

**Session Status:** ✅ Design aligned (pending user confirmation)  
**Last Updated:** 2026-04-25