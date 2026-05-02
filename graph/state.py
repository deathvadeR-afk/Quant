"""
Trading State Schema for LangGraph.

Defines Pydantic models for:
- TradingState: Main state container
- AgentStatus: Agent execution status
- AgentTransition: Agent transition records
- ErrorInfo: Error tracking
- Result models for each agent
"""

from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    RETRYING = "retrying"
    WAITING_HUMAN = "waiting_human"


class DataQualityResults(BaseModel):
    """Results from Data Guardian agent."""
    quality_score: float = Field(description="Overall data quality score (0-1)")
    issues: List[str] = Field(default_factory=list, description="List of data quality issues")
    passes: bool = Field(description="Whether quality check passes threshold")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed results")


class FactorResults(BaseModel):
    """Results from Factor Analyst agent."""
    top_factors: List[str] = Field(description="Top performing factors")
    factor_scores: Dict[str, float] = Field(default_factory=dict, description="All factor scores")
    ic_scores: Dict[str, float] = Field(default_factory=dict, description="Information coefficients")
    backtest_results: Optional[Dict[str, Any]] = Field(default=None, description="Backtest results")


class PortfolioResults(BaseModel):
    """Results from Portfolio Constructor agent."""
    allocations: Dict[str, float] = Field(description="Ticker to weight allocations")
    expected_return: float = Field(description="Expected portfolio return")
    expected_risk: float = Field(description="Expected portfolio risk")
    sharpe_ratio: Optional[float] = Field(default=None, description="Expected Sharpe ratio")
    constraints_satisfied: bool = Field(description="Whether constraints were satisfied")


class RiskResults(BaseModel):
    """Results from Risk Manager agent."""
    acceptable: bool = Field(description="Whether risk is within limits")
    circuit_breaker_triggered: bool = Field(default=False, description="Circuit breaker status")
    risk_metrics: Dict[str, float] = Field(default_factory=dict, description="Risk metric values")
    violations: List[str] = Field(default_factory=list, description="Constraint violations")


class ExecutionResults(BaseModel):
    """Results from Execution Strategist agent."""
    orders: List[Dict[str, Any]] = Field(default_factory=list, description="Orders to execute")
    expected_cost: float = Field(description="Expected execution cost")
    fill_probabilities: Dict[str, float] = Field(default_factory=dict, description="Fill probabilities")


class PerformanceResults(BaseModel):
    """Results from Performance Analyst agent."""
    pnl: float = Field(description="Profit/loss")
    benchmark_return: float = Field(description="Benchmark return")
    alpha: float = Field(description="Alpha")
    tracking_error: float = Field(description="Tracking error")
    attribution: Optional[Dict[str, float]] = Field(default=None, description="P&L attribution")


class AgentTransition(BaseModel):
    """Records an agent transition with timestamp and reasoning."""
    from_agent: str = Field(description="Source agent")
    to_agent: str = Field(description="Destination agent")
    timestamp: datetime = Field(description="Transition timestamp")
    reasoning: str = Field(description="Why this transition occurred")
    status: AgentStatus = Field(description="Status at transition")


class ErrorInfo(BaseModel):
    """Error information for recovery."""
    agent: str = Field(description="Agent where error occurred")
    error_type: str = Field(description="Type of error")
    message: str = Field(description="Error message")
    timestamp: datetime = Field(description="When error occurred")
    recoverable: bool = Field(description="Whether error is recoverable")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")


class TradingState(BaseModel):
    """
    Main state container for the trading graph.
    
    Tracks:
    - Current date and agent
    - Agent execution status
    - Transition history
    - Error tracking
    - Results from each agent
    """
    date: str = Field(description="Trading date (YYYY-MM-DD)")
    current_agent: str = Field(description="Currently executing agent")
    agent_status: AgentStatus = Field(default=AgentStatus.IDLE, description="Agent status")
    
    # Transition history
    transitions: List[AgentTransition] = Field(default_factory=list, description="Agent transitions")
    
    # Error tracking
    errors: List[ErrorInfo] = Field(default_factory=list, description="Errors encountered")
    
    # Agent results
    data_quality_results: Optional[DataQualityResults] = Field(default=None, description="Data Guardian results")
    factor_results: Optional[FactorResults] = Field(default=None, description="Factor Analyst results")
    portfolio_results: Optional[PortfolioResults] = Field(default=None, description="Portfolio Constructor results")
    risk_results: Optional[RiskResults] = Field(default=None, description="Risk Manager results")
    execution_results: Optional[ExecutionResults] = Field(default=None, description="Execution Strategist results")
    performance_results: Optional[PerformanceResults] = Field(default=None, description="Performance Analyst results")
    
    model_config = ConfigDict(use_enum_values=True)