"""
LangGraph Conditional Edges for Agent Routing.

Defines routing functions that determine which node to execute next
based on the current state.
"""

from typing import Literal
import logging

from graph.state import TradingState, AgentStatus

logger = logging.getLogger(__name__)


def route_after_data_guardian(state: TradingState) -> Literal["factor_analyst", "human_escalation", "retry"]:
    """
    Route after Data Guardian execution.
    
    Routes to:
    - factor_analyst: If data quality passed
    - human_escalation: If data quality failed and not recoverable
    - retry: If data quality failed but recoverable
    """
    if state.agent_status == AgentStatus.ERROR:
        # Check if error is recoverable
        if state.errors and state.errors[-1].recoverable:
            logger.info("Data Guardian error recoverable, routing to retry")
            return "retry"
        else:
            logger.warning("Data Guardian error not recoverable, routing to human escalation")
            return "human_escalation"
    
    if state.data_quality_results is None:
        logger.warning("No data quality results, routing to human escalation")
        return "human_escalation"
    
    if state.data_quality_results.passes:
        logger.info("Data quality passed, routing to factor analyst")
        return "factor_analyst"
    else:
        logger.warning("Data quality failed, routing to human escalation")
        return "human_escalation"


def route_after_factor_analyst(state: TradingState) -> Literal["portfolio_constructor", "human_escalation", "retry"]:
    """
    Route after Factor Analyst execution.
    
    Routes to:
    - portfolio_constructor: If factor analysis succeeded
    - human_escalation: If factor analysis failed and not recoverable
    - retry: If factor analysis failed but recoverable
    """
    if state.agent_status == AgentStatus.ERROR:
        if state.errors and state.errors[-1].recoverable:
            logger.info("Factor Analyst error recoverable, routing to retry")
            return "retry"
        else:
            logger.warning("Factor Analyst error not recoverable, routing to human escalation")
            return "human_escalation"
    
    if state.factor_results is None:
        logger.warning("No factor results, routing to human escalation")
        return "human_escalation"
    
    logger.info("Factor analysis completed, routing to portfolio constructor")
    return "portfolio_constructor"


def route_after_portfolio_constructor(state: TradingState) -> Literal["risk_manager", "human_escalation", "retry"]:
    """
    Route after Portfolio Constructor execution.
    
    Routes to:
    - risk_manager: If portfolio construction succeeded
    - human_escalation: If portfolio construction failed and not recoverable
    - retry: If portfolio construction failed but recoverable
    """
    if state.agent_status == AgentStatus.ERROR:
        if state.errors and state.errors[-1].recoverable:
            logger.info("Portfolio Constructor error recoverable, routing to retry")
            return "retry"
        else:
            logger.warning("Portfolio Constructor error not recoverable, routing to human escalation")
            return "human_escalation"
    
    if state.portfolio_results is None:
        logger.warning("No portfolio results, routing to human escalation")
        return "human_escalation"
    
    if not state.portfolio_results.constraints_satisfied:
        logger.warning("Portfolio constraints not satisfied, routing to human escalation")
        return "human_escalation"
    
    logger.info("Portfolio construction completed, routing to risk manager")
    return "risk_manager"


def route_after_risk_manager(state: TradingState) -> Literal["execution_strategist", "human_escalation", "retry"]:
    """
    Route after Risk Manager execution.
    
    Routes to:
    - execution_strategist: If risk is acceptable
    - human_escalation: If circuit breaker triggered or risk not acceptable
    - retry: If risk check failed but recoverable
    """
    if state.agent_status == AgentStatus.ERROR:
        if state.errors and state.errors[-1].recoverable:
            logger.info("Risk Manager error recoverable, routing to retry")
            return "retry"
        else:
            logger.warning("Risk Manager error not recoverable, routing to human escalation")
            return "human_escalation"
    
    if state.risk_results is None:
        logger.warning("No risk results, routing to human escalation")
        return "human_escalation"
    
    if state.risk_results.circuit_breaker_triggered:
        logger.warning("Circuit breaker triggered, routing to human escalation")
        return "human_escalation"
    
    if not state.risk_results.acceptable:
        logger.warning("Risk not acceptable, routing to human escalation")
        return "human_escalation"
    
    logger.info("Risk assessment passed, routing to execution strategist")
    return "execution_strategist"


def route_after_execution_strategist(state: TradingState) -> Literal["performance_analyst", "human_escalation", "retry"]:
    """
    Route after Execution Strategist execution.
    
    Routes to:
    - performance_analyst: If execution planning succeeded
    - human_escalation: If execution planning failed and not recoverable
    - retry: If execution planning failed but recoverable
    """
    if state.agent_status == AgentStatus.ERROR:
        if state.errors and state.errors[-1].recoverable:
            logger.info("Execution Strategist error recoverable, routing to retry")
            return "retry"
        else:
            logger.warning("Execution Strategist error not recoverable, routing to human escalation")
            return "human_escalation"
    
    if state.execution_results is None:
        logger.warning("No execution results, routing to human escalation")
        return "human_escalation"
    
    logger.info("Execution planning completed, routing to performance analyst")
    return "performance_analyst"


def route_end(state: TradingState) -> Literal["__end__"]:
    """
    End routing - always ends the graph.
    
    The performance analyst is the last node in the daily cycle.
    """
    logger.info(f"Graph ending at {state.current_agent} with status {state.agent_status}")
    return "__end__"