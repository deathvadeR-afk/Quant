"""
Tests for LangGraph Trading Graph and State Management.

These tests verify:
- State serialization/deserialization
- Graph node execution
- Conditional routing logic
- Error recovery flows
- State persistence across restarts
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import json

# Test state schema serialization/deserialization
class TestStateSchema:
    """Test Pydantic state models."""

    def test_trading_state_can_be_created(self):
        """TradingState can be created with required fields."""
        from graph.state import TradingState, AgentStatus, AgentTransition
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        assert state.date == "2024-01-15"
        assert state.current_agent == "data_guardian"
        assert state.agent_status == AgentStatus.IDLE

    def test_trading_state_serialization(self):
        """TradingState can be serialized to JSON."""
        from graph.state import TradingState, AgentStatus, AgentTransition
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        # Should be serializable
        json_str = state.model_dump_json()
        assert "2024-01-15" in json_str
        assert "data_guardian" in json_str

    def test_trading_state_deserialization(self):
        """TradingState can be deserialized from JSON."""
        from graph.state import TradingState, AgentStatus, AgentTransition
        
        json_str = '{"date": "2024-01-15", "current_agent": "data_guardian", "agent_status": "idle", "transitions": [], "errors": [], "data_quality_results": null, "factor_results": null, "portfolio_results": null, "risk_results": null, "execution_results": null, "performance_results": null}'
        
        state = TradingState.model_validate_json(json_str)
        
        assert state.date == "2024-01-15"
        assert state.current_agent == "data_guardian"
        assert state.agent_status == AgentStatus.IDLE

    def test_agent_transition_records_timestamp_and_reasoning(self):
        """AgentTransition captures timestamp and reasoning."""
        from graph.state import AgentTransition, AgentStatus
        
        transition = AgentTransition(
            from_agent="data_guardian",
            to_agent="factor_analyst",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            reasoning="Data quality check passed, proceeding to factor analysis",
            status=AgentStatus.COMPLETED,
        )
        
        assert transition.from_agent == "data_guardian"
        assert transition.to_agent == "factor_analyst"
        assert "Data quality" in transition.reasoning
        assert transition.status == AgentStatus.COMPLETED

    def test_trading_state_with_transitions(self):
        """TradingState tracks agent transitions."""
        from graph.state import TradingState, AgentStatus, AgentTransition
        
        transitions = [
            AgentTransition(
                from_agent="",
                to_agent="data_guardian",
                timestamp=datetime(2024, 1, 15, 9, 0, 0),
                reasoning="Starting daily cycle",
                status=AgentStatus.RUNNING,
            ),
            AgentTransition(
                from_agent="data_guardian",
                to_agent="factor_analyst",
                timestamp=datetime(2024, 1, 15, 9, 30, 0),
                reasoning="Data quality check passed",
                status=AgentStatus.COMPLETED,
            ),
        ]
        
        state = TradingState(
            date="2024-01-15",
            current_agent="factor_analyst",
            agent_status=AgentStatus.RUNNING,
            transitions=transitions,
        )
        
        assert len(state.transitions) == 2
        assert state.transitions[0].to_agent == "data_guardian"
        assert state.transitions[1].to_agent == "factor_analyst"


# Test graph node execution
class TestGraphNodes:
    """Test LangGraph node implementations."""

    def test_data_guardian_node_exists(self):
        """Data Guardian node is defined."""
        from graph.nodes import DATA_GUARDIAN_NODE, DataGuardianNode
        
        assert DATA_GUARDIAN_NODE == "data_guardian"
        assert callable(DataGuardianNode)

    def test_factor_analyst_node_exists(self):
        """Factor Analyst node is defined."""
        from graph.nodes import FACTOR_ANALYST_NODE, FactorAnalystNode
        
        assert FACTOR_ANALYST_NODE == "factor_analyst"
        assert callable(FactorAnalystNode)

    def test_portfolio_constructor_node_exists(self):
        """Portfolio Constructor node is defined."""
        from graph.nodes import PORTFOLIO_CONSTRUCTOR_NODE, PortfolioConstructorNode
        
        assert PORTFOLIO_CONSTRUCTOR_NODE == "portfolio_constructor"
        assert callable(PortfolioConstructorNode)

    def test_risk_manager_node_exists(self):
        """Risk Manager node is defined."""
        from graph.nodes import RISK_MANAGER_NODE, RiskManagerNode
        
        assert RISK_MANAGER_NODE == "risk_manager"
        assert callable(RiskManagerNode)

    def test_execution_strategist_node_exists(self):
        """Execution Strategist node is defined."""
        from graph.nodes import EXECUTION_STRATEGIST_NODE, ExecutionStrategistNode
        
        assert EXECUTION_STRATEGIST_NODE == "execution_strategist"
        assert callable(ExecutionStrategistNode)

    def test_performance_analyst_node_exists(self):
        """Performance Analyst node is defined."""
        from graph.nodes import PERFORMANCE_ANALYST_NODE, PerformanceAnalystNode
        
        assert PERFORMANCE_ANALYST_NODE == "performance_analyst"
        assert callable(PerformanceAnalystNode)

    def test_data_guardian_node_updates_state(self):
        """Data Guardian node updates state with quality results."""
        from graph.state import TradingState, AgentStatus, DataQualityResults
        from graph.nodes import data_guardian_node
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        # Mock the tool invocation
        with patch('tools.registry.get_default_registry') as mock_registry:
            mock_tool = MagicMock()
            mock_tool.invoke.return_value = {
                "success": True,
                "data": {"quality_score": 0.95, "issues": []},
            }
            mock_registry.return_value.get_tool.return_value = mock_tool
            
            result = data_guardian_node(state)
        
        assert result.agent_status == AgentStatus.COMPLETED
        assert result.data_quality_results is not None
        assert result.data_quality_results.quality_score == 0.95


# Test conditional routing logic
class TestConditionalEdges:
    """Test conditional edge routing."""

    def test_route_after_data_quality_success(self):
        """Route to factor analyst when data quality passes."""
        from graph.edges import route_after_data_guardian
        from graph.state import TradingState, AgentStatus, DataQualityResults
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.COMPLETED,
            data_quality_results=DataQualityResults(
                quality_score=0.95,
                issues=[],
                passes=True,
            ),
        )
        
        next_node = route_after_data_guardian(state)
        
        assert next_node == "factor_analyst"

    def test_route_after_data_quality_failure(self):
        """Route to human escalation when data quality fails."""
        from graph.edges import route_after_data_guardian
        from graph.state import TradingState, AgentStatus, DataQualityResults
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.COMPLETED,
            data_quality_results=DataQualityResults(
                quality_score=0.5,
                issues=["Missing data for AAPL"],
                passes=False,
            ),
        )
        
        next_node = route_after_data_guardian(state)
        
        assert next_node == "human_escalation"

    def test_route_after_factor_analysis(self):
        """Route to portfolio constructor after factor analysis."""
        from graph.edges import route_after_factor_analyst
        from graph.state import TradingState, AgentStatus, FactorResults
        
        state = TradingState(
            date="2024-01-15",
            current_agent="factor_analyst",
            agent_status=AgentStatus.COMPLETED,
            factor_results=FactorResults(
                top_factors=["momentum_1m", "value_pe"],
                factor_scores={"momentum_1m": 0.65, "value_pe": 0.62},
                ic_scores={"momentum_1m": 0.08, "value_pe": 0.07},
            ),
        )
        
        next_node = route_after_factor_analyst(state)
        
        assert next_node == "portfolio_constructor"

    def test_route_after_risk_assessment_safe(self):
        """Route to execution when risk is acceptable."""
        from graph.edges import route_after_risk_manager
        from graph.state import TradingState, AgentStatus, RiskResults
        
        state = TradingState(
            date="2024-01-15",
            current_agent="risk_manager",
            agent_status=AgentStatus.COMPLETED,
            risk_results=RiskResults(
                acceptable=True,
                circuit_breaker_triggered=False,
                risk_metrics={"var_95": 0.02},
                violations=[],
            ),
        )
        
        next_node = route_after_risk_manager(state)
        
        assert next_node == "execution_strategist"

    def test_route_after_risk_circuit_breaker(self):
        """Route to human escalation when circuit breaker triggers."""
        from graph.edges import route_after_risk_manager
        from graph.state import TradingState, AgentStatus, RiskResults
        
        state = TradingState(
            date="2024-01-15",
            current_agent="risk_manager",
            agent_status=AgentStatus.COMPLETED,
            risk_results=RiskResults(
                acceptable=False,
                circuit_breaker_triggered=True,
                risk_metrics={"var_95": 0.15},
                violations=["VaR exceeded", "Max drawdown exceeded"],
            ),
        )
        
        next_node = route_after_risk_manager(state)
        
        assert next_node == "human_escalation"


# Test error recovery flows
class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_error_state_captured(self):
        """Errors are captured in state."""
        from graph.state import TradingState, AgentStatus, ErrorInfo
        
        error = ErrorInfo(
            agent="data_guardian",
            error_type="TimeoutError",
            message="Data download timed out",
            timestamp=datetime(2024, 1, 15, 9, 15, 0),
            recoverable=True,
        )
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.ERROR,
            errors=[error],
        )
        
        assert len(state.errors) == 1
        assert state.errors[0].error_type == "TimeoutError"
        assert state.errors[0].recoverable is True

    def test_retry_node_exists(self):
        """Retry node handles recoverable errors."""
        from graph.nodes import RETRY_NODE, retry_node
        from graph.state import TradingState, AgentStatus, ErrorInfo
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.ERROR,
            errors=[ErrorInfo(
                agent="data_guardian",
                error_type="TimeoutError",
                message="Data download timed out",
                timestamp=datetime.now(),
                recoverable=True,
            )],
        )
        
        result = retry_node(state)
        
        assert result.current_agent == "data_guardian"
        assert result.agent_status == AgentStatus.RETRYING

    def test_human_escalation_node_exists(self):
        """Human escalation node handles unrecoverable errors."""
        from graph.nodes import HUMAN_ESCALATION_NODE, human_escalation_node
        from graph.state import TradingState, AgentStatus, ErrorInfo
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.ERROR,
            errors=[ErrorInfo(
                agent="data_guardian",
                error_type="CriticalError",
                message="Database corruption detected",
                timestamp=datetime.now(),
                recoverable=False,
            )],
        )
        
        result = human_escalation_node(state)
        
        assert result.current_agent == "human_escalation"
        assert result.agent_status == AgentStatus.WAITING_HUMAN


# Test Redis state persistence
class TestRedisStateManager:
    """Test Redis-backed state management."""

    def test_redis_state_manager_can_save_state(self):
        """State can be saved to Redis."""
        from graph.state_manager import RedisStateManager
        from graph.state import TradingState, AgentStatus
        
        manager = RedisStateManager(host="localhost", port=6379, db=0)
        
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        # This should not raise (mocked)
        with patch('redis.Redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_pipeline = MagicMock()
            mock_client.pipeline.return_value = mock_pipeline
            
            manager.save_state("cycle_2024_01_15", state)
            
            mock_pipeline.set.assert_called()

    def test_redis_state_manager_can_load_state(self):
        """State can be loaded from Redis."""
        from graph.state_manager import RedisStateManager
        
        with patch('redis.Redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = b'{"date": "2024-01-15", "current_agent": "data_guardian", "agent_status": "idle", "transitions": [], "errors": [], "data_quality_results": null, "factor_results": null, "portfolio_results": null, "risk_results": null, "execution_results": null, "performance_results": null}'
            
            manager = RedisStateManager(host="localhost", port=6379, db=0)
            state = manager.load_state("cycle_2024_01_15")
            
            assert state is not None
            assert state.date == "2024-01-15"

    def test_redis_state_manager_returns_none_for_missing_state(self):
        """Returns None when state doesn't exist."""
        from graph.state_manager import RedisStateManager
        
        with patch('redis.Redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = None
            
            manager = RedisStateManager(host="localhost", port=6379, db=0)
            state = manager.load_state("nonexistent_key")
            
            assert state is None


# Test graph compilation and execution
class TestTradingGraph:
    """Test the main trading graph."""

    def test_trading_graph_can_be_compiled(self):
        """Trading graph can be compiled."""
        from graph.trading_graph import create_trading_graph
        
        graph = create_trading_graph()
        
        assert graph is not None
        # Should have nodes
        assert len(graph.nodes) > 0

    def test_trading_graph_has_all_agent_nodes(self):
        """Graph contains all required agent nodes."""
        from graph.trading_graph import create_trading_graph
        
        graph = create_trading_graph()
        
        expected_nodes = [
            "data_guardian",
            "factor_analyst",
            "portfolio_constructor",
            "risk_manager",
            "execution_strategist",
            "performance_analyst",
            "human_escalation",
            "retry",
        ]
        
        for node in expected_nodes:
            assert node in graph.nodes, f"Missing node: {node}"

    def test_trading_graph_has_conditional_edges(self):
        """Graph has conditional edges for routing."""
        from graph.trading_graph import create_trading_graph
        
        graph = create_trading_graph()
        
        # Graph should have edges
        assert len(graph.edges) > 0

    def test_graph_execution_with_mock(self):
        """Graph can execute with mock state."""
        from graph.trading_graph import compile_trading_graph
        from graph.state import TradingState, AgentStatus
        import threading
        
        graph = compile_trading_graph()
        
        initial_state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        # Mock all tool invocations
        with patch('tools.registry.get_default_registry') as mock_registry:
            mock_tool = MagicMock()
            mock_tool.invoke.return_value = {
                "success": True,
                "data": {"quality_score": 0.95, "issues": []},
            }
            mock_registry.return_value.get_tool.return_value = mock_tool
            
            # Run graph with timeout using threading (cross-platform)
            result_holder = [None]
            error_holder = [None]
            
            def run_graph():
                try:
                    result_holder[0] = graph.invoke(initial_state)
                except Exception as e:
                    error_holder[0] = e
            
            thread = threading.Thread(target=run_graph)
            thread.daemon = True
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            if thread.is_alive():
                # Thread is still running, timeout occurred
                pytest.fail("Graph execution timed out")
            
            if error_holder[0] is not None:
                pytest.fail(f"Graph execution error: {error_holder[0]}")
            
            result = result_holder[0]
            assert result is not None
            # LangGraph returns a dict with state fields
            assert isinstance(result, dict)
            # The result should contain agent_status key
            assert 'agent_status' in result or 'trading_state' in result


# Test streaming support
class TestStreaming:
    """Test streaming updates."""

    def test_graph_supports_streaming(self):
        """Graph supports streaming mode."""
        from graph.trading_graph import compile_trading_graph
        from graph.state import TradingState, AgentStatus
        
        # Use compiled graph which has stream method
        graph = compile_trading_graph()
        
        initial_state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        # Should be able to stream
        assert hasattr(graph, 'stream')
        
        # Mock tool invocations
        with patch('tools.registry.get_default_registry') as mock_registry:
            mock_tool = MagicMock()
            mock_tool.invoke.return_value = {
                "success": True,
                "data": {"quality_score": 0.95, "issues": []},
            }
            mock_registry.return_value.get_tool.return_value = mock_tool
            
            # Stream should yield states
            states = list(graph.stream(initial_state))
            
            assert len(states) > 0

    def test_streaming_support(self):
        """Streaming functionality works and returns correct output format."""
        from graph.trading_graph import compile_trading_graph
        from graph.state import TradingState, AgentStatus
        
        graph = compile_trading_graph()
        initial_state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        with patch('tools.registry.get_default_registry') as mock_registry:
            mock_tool = MagicMock()
            mock_tool.invoke.return_value = {
                "success": True,
                "data": {"quality_score": 0.95, "issues": []},
            }
            mock_registry.return_value.get_tool.return_value = mock_tool
            
            # Stream and collect states
            stream_states = list(graph.stream(initial_state, stream_mode="values"))
            
            assert len(stream_states) > 0, "Stream produced no states"
            # Each state should be a dict or TradingState
            for state in stream_states:
                assert isinstance(state, dict) or hasattr(state, 'current_agent')


# Performance tests
class TestPerformance:
    """Test performance requirements."""

    def test_state_serialization_under_100ms(self):
        """State serialization completes in under 100ms."""
        import time
        from graph.state import TradingState, AgentStatus, AgentTransition
        
        transitions = [
            AgentTransition(
                from_agent=f"agent_{i}",
                to_agent=f"agent_{i+1}",
                timestamp=datetime.now(),
                reasoning=f"Transition {i}",
                status=AgentStatus.COMPLETED,
            )
            for i in range(10)
        ]
        
        state = TradingState(
            date="2024-01-15",
            current_agent="performance_analyst",
            agent_status=AgentStatus.RUNNING,
            transitions=transitions,
        )
        
        start = time.time()
        json_str = state.model_dump_json()
        elapsed_ms = (time.time() - start) * 1000
        
        assert elapsed_ms < 100, f"Serialization took {elapsed_ms}ms, expected < 100ms"

    def test_state_deserialization_under_100ms(self):
        """State deserialization completes in under 100ms."""
        import time
        from graph.state import TradingState
        
        json_str = json.dumps({
            "date": "2024-01-15",
            "current_agent": "performance_analyst",
            "agent_status": "running",
            "transitions": [
                {
                    "from_agent": f"agent_{i}",
                    "to_agent": f"agent_{i+1}",
                    "timestamp": datetime.now().isoformat(),
                    "reasoning": f"Transition {i}",
                    "status": "completed",
                }
                for i in range(10)
            ],
            "errors": [],
            "data_quality_results": None,
            "factor_results": None,
            "portfolio_results": None,
            "risk_results": None,
            "execution_results": None,
            "performance_results": None,
        })
        
        start = time.time()
        state = TradingState.model_validate_json(json_str)
        elapsed_ms = (time.time() - start) * 1000
        
        assert elapsed_ms < 100, f"Deserialization took {elapsed_ms}ms, expected < 100ms"

    def test_graph_execution_time(self):
        """Graph execution completes in under 2 hours (7200 seconds)."""
        import time
        from graph.trading_graph import compile_trading_graph
        from graph.state import TradingState, AgentStatus
        
        graph = compile_trading_graph()
        initial_state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        # Mock all tool invocations to avoid real API calls
        with patch('tools.registry.get_default_registry') as mock_registry:
            mock_tool = MagicMock()
            mock_tool.invoke.return_value = {
                "success": True,
                "data": {"quality_score": 0.95, "issues": []},
            }
            mock_registry.return_value.get_tool.return_value = mock_tool
            
            start_time = time.time()
            result = graph.invoke(initial_state)
            elapsed = time.time() - start_time
            
            assert elapsed < 7200, f"Graph execution took {elapsed}s, expected <7200s (2h)"

    def test_state_query_performance(self):
        """State query (load_state) completes in under 100ms on average."""
        import time
        from graph.state_manager import RedisStateManager
        from graph.state import TradingState, AgentStatus
        
        manager = RedisStateManager(host="localhost", port=6379, db=0)
        state = TradingState(
            date="2024-01-15",
            current_agent="data_guardian",
            agent_status=AgentStatus.IDLE,
        )
        
        # Mock Redis client to avoid real Redis connection
        with patch('redis.Redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            # Mock load_state to return the state quickly
            mock_client.get.return_value = state.model_dump_json().encode()
            
            num_queries = 100
            total_time = 0.0
            for _ in range(num_queries):
                start = time.time()
                manager.load_state("test_cycle")
                total_time += time.time() - start
            
            avg_ms = (total_time / num_queries) * 1000
            assert avg_ms < 100, f"Average query time {avg_ms}ms, expected <100ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])