"""
LangGraph Nodes for Trading Agents.

Defines node functions for each agent in the trading workflow:
- Data Guardian: Data quality validation
- Factor Analyst: Factor research and ranking
- Portfolio Constructor: Portfolio optimization
- Risk Manager: Risk assessment and circuit breakers
- Execution Strategist: Order execution planning
- Performance Analyst: Performance attribution
- Human Escalation: Handle unrecoverable errors
- Retry: Handle recoverable errors
"""

from datetime import datetime
from typing import Any, Dict, Optional, Callable
import logging

from graph.state import (
    TradingState,
    AgentStatus,
    AgentTransition,
    DataQualityResults,
    FactorResults,
    PortfolioResults,
    RiskResults,
    ExecutionResults,
    PerformanceResults,
)

logger = logging.getLogger(__name__)

# Node name constants
DATA_GUARDIAN_NODE = "data_guardian"
FACTOR_ANALYST_NODE = "factor_analyst"
PORTFOLIO_CONSTRUCTOR_NODE = "portfolio_constructor"
RISK_MANAGER_NODE = "risk_manager"
EXECUTION_STRATEGIST_NODE = "execution_strategist"
PERFORMANCE_ANALYST_NODE = "performance_analyst"
HUMAN_ESCALATION_NODE = "human_escalation"
RETRY_NODE = "retry"

# Type aliases for node functions
DataGuardianNode = Callable[[TradingState], TradingState]
FactorAnalystNode = Callable[[TradingState], TradingState]
PortfolioConstructorNode = Callable[[TradingState], TradingState]
RiskManagerNode = Callable[[TradingState], TradingState]
ExecutionStrategistNode = Callable[[TradingState], TradingState]
PerformanceAnalystNode = Callable[[TradingState], TradingState]


def _create_transition(
    state: TradingState,
    to_agent: str,
    reasoning: str,
    status: AgentStatus = AgentStatus.COMPLETED,
) -> AgentTransition:
    """Create a new transition record."""
    return AgentTransition(
        from_agent=state.current_agent,
        to_agent=to_agent,
        timestamp=datetime.now(),
        reasoning=reasoning,
        status=status,
    )


def _update_state_with_transition(
    state: TradingState,
    new_agent: str,
    new_status: AgentStatus,
    reasoning: str,
) -> TradingState:
    """Update state with new agent, status, and transition record."""
    transition = _create_transition(state, new_agent, reasoning, new_status)
    
    # Create new state with updated fields
    new_state = state.model_copy(deep=True)
    new_state.current_agent = new_agent
    new_state.agent_status = new_status
    new_state.transitions = state.transitions + [transition]
    
    return new_state


def data_guardian_node(state: TradingState) -> TradingState:
    """
    Data Guardian node - validates data quality.
    
    Executes data quality checks and updates state with results.
    """
    logger.info(f"Executing Data Guardian node for date {state.date}")
    
    # Update status to running
    new_state = state.model_copy(deep=True)
    new_state.agent_status = AgentStatus.RUNNING
    
    try:
        # Import here to avoid circular imports
        from tools.registry import get_default_registry
        
        # Get the data quality tool
        registry = get_default_registry()
        tool = registry.get_tool("data_quality")
        
        if tool is None:
            raise ValueError("Data quality tool not found")
        
        # Execute the tool
        result = tool.invoke({"date": state.date})
        
        if result.get("success"):
            data = result.get("data", {})
            quality_score = data.get("quality_score", 0.0)
            issues = data.get("issues", [])
            
            # Determine if quality passes threshold
            passes = quality_score >= 0.8
            
            data_quality_results = DataQualityResults(
                quality_score=quality_score,
                issues=issues,
                passes=passes,
                details=data,
            )
            
            new_state.data_quality_results = data_quality_results
            new_state.agent_status = AgentStatus.COMPLETED
            
            reasoning = f"Data quality check completed. Score: {quality_score:.2f}, Passes: {passes}"
            logger.info(reasoning)
        else:
            raise ValueError(f"Data quality check failed: {result.get('error')}")
    
    except Exception as e:
        logger.error(f"Data Guardian error: {e}")
        new_state.agent_status = AgentStatus.ERROR
        from graph.state import ErrorInfo
        new_state.errors = state.errors + [
            ErrorInfo(
                agent=DATA_GUARDIAN_NODE,
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(),
                recoverable=True,
            )
        ]
    
    return new_state


def factor_analyst_node(state: TradingState) -> TradingState:
    """
    Factor Analyst node - performs factor research.
    
    Analyzes factors and ranks them by performance.
    """
    logger.info(f"Executing Factor Analyst node for date {state.date}")
    
    new_state = state.model_copy(deep=True)
    new_state.agent_status = AgentStatus.RUNNING
    
    try:
        # For now, return mock results
        # In full implementation, this would run factor analysis
        factor_results = FactorResults(
            top_factors=["momentum_1m", "value_pe", "quality_roe"],
            factor_scores={
                "momentum_1m": 0.65,
                "momentum_3m": 0.58,
                "value_pe": 0.62,
                "value_pb": 0.55,
                "quality_roe": 0.60,
            },
            ic_scores={
                "momentum_1m": 0.08,
                "momentum_3m": 0.05,
                "value_pe": 0.07,
                "value_pb": 0.04,
                "quality_roe": 0.06,
            },
        )
        
        new_state.factor_results = factor_results
        new_state.agent_status = AgentStatus.COMPLETED
        
        reasoning = f"Factor analysis completed. Top factors: {', '.join(factor_results.top_factors)}"
        logger.info(reasoning)
    
    except Exception as e:
        logger.error(f"Factor Analyst error: {e}")
        new_state.agent_status = AgentStatus.ERROR
        from graph.state import ErrorInfo
        new_state.errors = state.errors + [
            ErrorInfo(
                agent=FACTOR_ANALYST_NODE,
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(),
                recoverable=True,
            )
        ]
    
    return new_state


def portfolio_constructor_node(state: TradingState) -> TradingState:
    """
    Portfolio Constructor node - builds optimized portfolio.
    
    Uses factor signals to construct portfolio with optimization.
    """
    logger.info(f"Executing Portfolio Constructor node for date {state.date}")
    
    new_state = state.model_copy(deep=True)
    new_state.agent_status = AgentStatus.RUNNING
    
    try:
        # For now, return mock results
        # In full implementation, this would run portfolio optimization
        portfolio_results = PortfolioResults(
            allocations={
                "AAPL": 0.15,
                "MSFT": 0.12,
                "GOOGL": 0.10,
                "AMZN": 0.08,
                "NVDA": 0.07,
            },
            expected_return=0.12,
            expected_risk=0.18,
            sharpe_ratio=0.67,
            constraints_satisfied=True,
        )
        
        new_state.portfolio_results = portfolio_results
        new_state.agent_status = AgentStatus.COMPLETED
        
        reasoning = f"Portfolio construction completed. {len(portfolio_results.allocations)} positions, Sharpe: {portfolio_results.sharpe_ratio:.2f}"
        logger.info(reasoning)
    
    except Exception as e:
        logger.error(f"Portfolio Constructor error: {e}")
        new_state.agent_status = AgentStatus.ERROR
        from graph.state import ErrorInfo
        new_state.errors = state.errors + [
            ErrorInfo(
                agent=PORTFOLIO_CONSTRUCTOR_NODE,
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(),
                recoverable=True,
            )
        ]
    
    return new_state


def risk_manager_node(state: TradingState) -> TradingState:
    """
    Risk Manager node - assesses and manages risk.
    
    Checks risk metrics and triggers circuit breakers if needed.
    """
    logger.info(f"Executing Risk Manager node for date {state.date}")
    
    new_state = state.model_copy(deep=True)
    new_state.agent_status = AgentStatus.RUNNING
    
    try:
        # For now, return mock results
        # In full implementation, this would run risk models
        risk_results = RiskResults(
            acceptable=True,
            circuit_breaker_triggered=False,
            risk_metrics={
                "var_95": 0.02,
                "cvar_95": 0.03,
                "max_drawdown": 0.05,
                "leverage": 1.2,
            },
            violations=[],
        )
        
        new_state.risk_results = risk_results
        new_state.agent_status = AgentStatus.COMPLETED
        
        reasoning = f"Risk assessment completed. Acceptable: {risk_results.acceptable}, Circuit breaker: {risk_results.circuit_breaker_triggered}"
        logger.info(reasoning)
    
    except Exception as e:
        logger.error(f"Risk Manager error: {e}")
        new_state.agent_status = AgentStatus.ERROR
        from graph.state import ErrorInfo
        new_state.errors = state.errors + [
            ErrorInfo(
                agent=RISK_MANAGER_NODE,
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(),
                recoverable=True,
            )
        ]
    
    return new_state


def execution_strategist_node(state: TradingState) -> TradingState:
    """
    Execution Strategist node - plans order execution.
    
    Creates execution plan with order sizing and timing.
    """
    logger.info(f"Executing Execution Strategist node for date {state.date}")
    
    new_state = state.model_copy(deep=True)
    new_state.agent_status = AgentStatus.RUNNING
    
    try:
        # For now, return mock results
        # In full implementation, this would create execution plans
        execution_results = ExecutionResults(
            orders=[
                {"ticker": "AAPL", "shares": 100, "side": "BUY", "method": "VWAP"},
                {"ticker": "MSFT", "shares": 80, "side": "BUY", "method": "VWAP"},
            ],
            expected_cost=0.001,
            fill_probabilities={"AAPL": 0.95, "MSFT": 0.93},
        )
        
        new_state.execution_results = execution_results
        new_state.agent_status = AgentStatus.COMPLETED
        
        reasoning = f"Execution plan created. {len(execution_results.orders)} orders, expected cost: {execution_results.expected_cost:.4f}"
        logger.info(reasoning)
    
    except Exception as e:
        logger.error(f"Execution Strategist error: {e}")
        new_state.agent_status = AgentStatus.ERROR
        from graph.state import ErrorInfo
        new_state.errors = state.errors + [
            ErrorInfo(
                agent=EXECUTION_STRATEGIST_NODE,
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(),
                recoverable=True,
            )
        ]
    
    return new_state


def performance_analyst_node(state: TradingState) -> TradingState:
    """
    Performance Analyst node - analyzes trading performance.
    
    Calculates P&L attribution and performance metrics.
    """
    logger.info(f"Executing Performance Analyst node for date {state.date}")
    
    new_state = state.model_copy(deep=True)
    new_state.agent_status = AgentStatus.RUNNING
    
    try:
        # For now, return mock results
        # In full implementation, this would calculate performance
        performance_results = PerformanceResults(
            pnl=0.015,
            benchmark_return=0.012,
            alpha=0.003,
            tracking_error=0.02,
            attribution={
                "momentum": 0.008,
                "value": 0.004,
                "quality": 0.003,
            },
        )
        
        new_state.performance_results = performance_results
        new_state.agent_status = AgentStatus.COMPLETED
        
        reasoning = f"Performance analysis completed. P&L: {performance_results.pnl:.4f}, Alpha: {performance_results.alpha:.4f}"
        logger.info(reasoning)
    
    except Exception as e:
        logger.error(f"Performance Analyst error: {e}")
        new_state.agent_status = AgentStatus.ERROR
        from graph.state import ErrorInfo
        new_state.errors = state.errors + [
            ErrorInfo(
                agent=PERFORMANCE_ANALYST_NODE,
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(),
                recoverable=True,
            )
        ]
    
    return new_state


def human_escalation_node(state: TradingState) -> TradingState:
    """
    Human Escalation node - handles unrecoverable errors.
    
    Sets state to waiting for human intervention.
    """
    logger.warning(f"Human escalation triggered for {state.current_agent}")
    
    new_state = state.model_copy(deep=True)
    new_state.current_agent = HUMAN_ESCALATION_NODE
    new_state.agent_status = AgentStatus.WAITING_HUMAN
    
    return new_state


def retry_node(state: TradingState) -> TradingState:
    """
    Retry node - handles recoverable errors.
    
    Retries the failed agent with exponential backoff.
    """
    logger.info(f"Retry node triggered for {state.current_agent}")
    
    new_state = state.model_copy(deep=True)
    new_state.agent_status = AgentStatus.RETRYING
    
    # The actual retry logic would be handled by the graph edges
    # This node just updates the status
    
    return new_state