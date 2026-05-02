"""
LangGraph Trading Graph Module.

Provides:
- State schema with Pydantic models
- Agent nodes for each trading agent
- Conditional edges for routing
- Redis-backed state management
- Main trading graph
"""

from graph.state import (
    TradingState,
    AgentStatus,
    AgentTransition,
    ErrorInfo,
    DataQualityResults,
    FactorResults,
    PortfolioResults,
    RiskResults,
    ExecutionResults,
    PerformanceResults,
)
from graph.nodes import (
    DATA_GUARDIAN_NODE,
    FACTOR_ANALYST_NODE,
    PORTFOLIO_CONSTRUCTOR_NODE,
    RISK_MANAGER_NODE,
    EXECUTION_STRATEGIST_NODE,
    PERFORMANCE_ANALYST_NODE,
    HUMAN_ESCALATION_NODE,
    RETRY_NODE,
    DataGuardianNode,
    FactorAnalystNode,
    PortfolioConstructorNode,
    RiskManagerNode,
    ExecutionStrategistNode,
    PerformanceAnalystNode,
    human_escalation_node,
    retry_node,
    data_guardian_node,
    factor_analyst_node,
    portfolio_constructor_node,
    risk_manager_node,
    execution_strategist_node,
    performance_analyst_node,
)
from graph.edges import (
    route_after_data_guardian,
    route_after_factor_analyst,
    route_after_portfolio_constructor,
    route_after_risk_manager,
    route_after_execution_strategist,
)
from graph.state_manager import RedisStateManager
from graph.trading_graph import create_trading_graph

__all__ = [
    # State
    "TradingState",
    "AgentStatus",
    "AgentTransition",
    "ErrorInfo",
    "DataQualityResults",
    "FactorResults",
    "PortfolioResults",
    "RiskResults",
    "ExecutionResults",
    "PerformanceResults",
    # Nodes
    "DATA_GUARDIAN_NODE",
    "FACTOR_ANALYST_NODE",
    "PORTFOLIO_CONSTRUCTOR_NODE",
    "RISK_MANAGER_NODE",
    "EXECUTION_STRATEGIST_NODE",
    "PERFORMANCE_ANALYST_NODE",
    "HUMAN_ESCALATION_NODE",
    "RETRY_NODE",
    "DataGuardianNode",
    "FactorAnalystNode",
    "PortfolioConstructorNode",
    "RiskManagerNode",
    "ExecutionStrategistNode",
    "PerformanceAnalystNode",
    "human_escalation_node",
    "retry_node",
    "data_guardian_node",
    "factor_analyst_node",
    "portfolio_constructor_node",
    "risk_manager_node",
    "execution_strategist_node",
    "performance_analyst_node",
    # Edges
    "route_after_data_guardian",
    "route_after_factor_analyst",
    "route_after_portfolio_constructor",
    "route_after_risk_manager",
    "route_after_execution_strategist",
    # State Manager
    "RedisStateManager",
    # Graph
    "create_trading_graph",
]