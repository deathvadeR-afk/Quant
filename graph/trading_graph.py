"""
Main LangGraph Trading Graph.

Defines the complete trading workflow as a LangGraph with:
- Agent nodes
- Conditional edges
- Error handling
- Streaming support
"""

from typing import Annotated, Dict, Any, Optional
import logging

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from graph.state import TradingState, AgentStatus
from graph.nodes import (
    DATA_GUARDIAN_NODE,
    FACTOR_ANALYST_NODE,
    PORTFOLIO_CONSTRUCTOR_NODE,
    RISK_MANAGER_NODE,
    EXECUTION_STRATEGIST_NODE,
    PERFORMANCE_ANALYST_NODE,
    HUMAN_ESCALATION_NODE,
    RETRY_NODE,
    data_guardian_node,
    factor_analyst_node,
    portfolio_constructor_node,
    risk_manager_node,
    execution_strategist_node,
    performance_analyst_node,
    human_escalation_node,
    retry_node,
)
from graph.edges import (
    route_after_data_guardian,
    route_after_factor_analyst,
    route_after_portfolio_constructor,
    route_after_risk_manager,
    route_after_execution_strategist,
    route_end,
)

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """
    LangGraph state that wraps TradingState.
    
    LangGraph requires a TypedDict for the graph state.
    We use messages for LangGraph's built-in streaming.
    """
    messages: Annotated[list, add_messages]
    trading_state: TradingState


def create_trading_graph() -> StateGraph:
    """
    Create the main trading graph.
    
    The graph topology is:
    
    [Start] --> [Data Guardian] --> [Factor Analyst] --> [Portfolio Constructor]
                                                        |
                                                        v
                                                   [Risk Manager]
                                                        |
                                                        v
                                              [Execution Strategist]
                                                        |
                                                        v
                                              [Performance Analyst] --> [End]
    
    Error paths:
    - Any agent error --> [Retry] (if recoverable) --> [Human Escalation] (if still failing)
    - Circuit breaker --> [Human Escalation]
    
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating trading graph")
    
    # Define the graph
    graph = StateGraph(TradingState)
    
    # Add all agent nodes
    graph.add_node(DATA_GUARDIAN_NODE, data_guardian_node)
    graph.add_node(FACTOR_ANALYST_NODE, factor_analyst_node)
    graph.add_node(PORTFOLIO_CONSTRUCTOR_NODE, portfolio_constructor_node)
    graph.add_node(RISK_MANAGER_NODE, risk_manager_node)
    graph.add_node(EXECUTION_STRATEGIST_NODE, execution_strategist_node)
    graph.add_node(PERFORMANCE_ANALYST_NODE, performance_analyst_node)
    graph.add_node(HUMAN_ESCALATION_NODE, human_escalation_node)
    graph.add_node(RETRY_NODE, retry_node)
    
    # Set entry point
    graph.set_entry_point(DATA_GUARDIAN_NODE)
    
    # Add conditional edges after each agent
    graph.add_conditional_edges(
        DATA_GUARDIAN_NODE,
        route_after_data_guardian,
        {
            "factor_analyst": FACTOR_ANALYST_NODE,
            "human_escalation": HUMAN_ESCALATION_NODE,
            "retry": RETRY_NODE,
        }
    )
    
    graph.add_conditional_edges(
        FACTOR_ANALYST_NODE,
        route_after_factor_analyst,
        {
            "portfolio_constructor": PORTFOLIO_CONSTRUCTOR_NODE,
            "human_escalation": HUMAN_ESCALATION_NODE,
            "retry": RETRY_NODE,
        }
    )
    
    graph.add_conditional_edges(
        PORTFOLIO_CONSTRUCTOR_NODE,
        route_after_portfolio_constructor,
        {
            "risk_manager": RISK_MANAGER_NODE,
            "human_escalation": HUMAN_ESCALATION_NODE,
            "retry": RETRY_NODE,
        }
    )
    
    graph.add_conditional_edges(
        RISK_MANAGER_NODE,
        route_after_risk_manager,
        {
            "execution_strategist": EXECUTION_STRATEGIST_NODE,
            "human_escalation": HUMAN_ESCALATION_NODE,
            "retry": RETRY_NODE,
        }
    )
    
    graph.add_conditional_edges(
        EXECUTION_STRATEGIST_NODE,
        route_after_execution_strategist,
        {
            "performance_analyst": PERFORMANCE_ANALYST_NODE,
            "human_escalation": HUMAN_ESCALATION_NODE,
            "retry": RETRY_NODE,
        }
    )
    
    # Performance analyst leads to end
    graph.add_conditional_edges(
        PERFORMANCE_ANALYST_NODE,
        route_end,
        {
            "__end__": END,
        }
    )
    
    # Retry node goes back to the failed agent
    # This requires knowing which agent failed, which we track in state
    def route_from_retry(state: TradingState) -> str:
        """Route from retry node back to the failed agent."""
        if state.errors:
            failed_agent = state.errors[-1].agent
            logger.info(f"Retrying {failed_agent}")
            return failed_agent
        # Default to data guardian if no error info
        return DATA_GUARDIAN_NODE
    
    graph.add_conditional_edges(
        RETRY_NODE,
        route_from_retry,
        {
            DATA_GUARDIAN_NODE: DATA_GUARDIAN_NODE,
            FACTOR_ANALYST_NODE: FACTOR_ANALYST_NODE,
            PORTFOLIO_CONSTRUCTOR_NODE: PORTFOLIO_CONSTRUCTOR_NODE,
            RISK_MANAGER_NODE: RISK_MANAGER_NODE,
            EXECUTION_STRATEGIST_NODE: EXECUTION_STRATEGIST_NODE,
            PERFORMANCE_ANALYST_NODE: PERFORMANCE_ANALYST_NODE,
        }
    )
    
    # Human escalation is an end state (waits for human)
    graph.add_edge(HUMAN_ESCALATION_NODE, END)
    
    logger.info("Trading graph created successfully")
    
    return graph


def compile_trading_graph() -> StateGraph:
    """
    Compile the trading graph.
    
    Returns:
        Compiled graph ready for execution
    """
    graph = create_trading_graph()
    return graph.compile()


# Singleton compiled graph
_compiled_graph: StateGraph = None


def get_compiled_graph() -> StateGraph:
    """
    Get the singleton compiled graph.
    
    Returns:
        Compiled trading graph
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_trading_graph()
    return _compiled_graph


def run_daily_cycle(date: str) -> TradingState:
    """
    Run the daily trading cycle.
    
    Args:
        date: Trading date (YYYY-MM-DD)
        
    Returns:
        Final trading state
    """
    from graph.state import TradingState, AgentStatus
    
    graph = get_compiled_graph()
    
    initial_state = TradingState(
        date=date,
        current_agent=DATA_GUARDIAN_NODE,
        agent_status=AgentStatus.IDLE,
    )
    
    result = graph.invoke(initial_state)
    return result


def run_daily_cycle_with_state_manager(
    date: str,
    state_manager: "RedisStateManager",
    cycle_id: Optional[str] = None,
) -> TradingState:
    """
    Run the daily trading cycle with state persistence.
    
    Args:
        date: Trading date (YYYY-MM-DD)
        state_manager: Redis state manager
        cycle_id: Optional cycle ID (defaults to date-based)
        
    Returns:
        Final trading state
    """
    from graph.state import TradingState, AgentStatus
    
    if cycle_id is None:
        cycle_id = f"cycle_{date}"
    
    # Try to load existing state
    initial_state = state_manager.load_state(cycle_id)
    
    if initial_state is None:
        initial_state = TradingState(
            date=date,
            current_agent=DATA_GUARDIAN_NODE,
            agent_status=AgentStatus.IDLE,
        )
    
    graph = get_compiled_graph()
    
    # Execute with per-node state persistence
    final_state = initial_state
    for step_state in graph.stream(initial_state, stream_mode="values"):
        final_state = step_state
        # Save state after each node completes
        state_manager.save_state(cycle_id, final_state)
    result = final_state

    return result