"""
Tests for LangChain Tool Wrappers.

These tests verify that tool wrappers correctly:
- Return JSON-serializable outputs
- Handle timeouts gracefully
- Handle errors with graceful degradation
- Match direct function call output
- Work with LangChain integration

Run with: pytest tools/test_tools.py -v
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import pandas as pd
import numpy as np

# Import tools (will fail until implemented)
from tools import (
    DataQualityTool,
    PriceDataTool,
    FundamentalDataTool,
    UniverseSelectionTool,
    PortfolioQueryTool,
    ToolConfig,
    get_default_registry,
)


class TestDataQualityTool:
    """Tests for DataQualityTool wrapper."""
    
    def test_tool_has_correct_name(self):
        """Tool should have the correct name for registry."""
        tool = DataQualityTool()
        assert tool.name == "data_quality"
    
    def test_tool_has_description(self):
        """Tool should have an LLM-optimized description."""
        tool = DataQualityTool()
        assert len(tool.description) > 50  # Description should be informative
        assert "quality" in tool.description.lower()
    
    def test_tool_has_input_schema(self):
        """Tool should have a JSON schema for inputs."""
        tool = DataQualityTool()
        schema = tool.input_schema
        assert "type" in schema
        assert "properties" in schema
        # Should accept tickers as input
        assert "tickers" in schema["properties"]
    
    def test_invoke_returns_standard_response_format(self):
        """Tool invoke should return standardized response format."""
        tool = DataQualityTool()
        
        # Mock the underlying function
        with patch('data.data_quality.run_full_data_quality_check') as mock_check:
            mock_check.return_value = {
                "overall_quality_score": 0.95,
                "tickers_checked": 10,
                "issues_found": 0,
            }
            
            result = tool.invoke({"tickers": ["AAPL", "MSFT"]})
        
        # Verify standard response format
        assert "success" in result
        assert "data" in result
        assert "error" in result
        assert "metadata" in result
        assert result["success"] is True
        assert result["metadata"]["tool_name"] == "data_quality"
        assert "execution_time_ms" in result["metadata"]
    
    def test_invoke_returns_json_serializable(self):
        """Tool invoke should return JSON-serializable data."""
        tool = DataQualityTool()
        
        with patch('data.data_quality.run_full_data_quality_check') as mock_check:
            mock_check.return_value = {
                "overall_quality_score": 0.95,
                "tickers_checked": 10,
            }
            
            result = tool.invoke({"tickers": ["AAPL"]})
        
        # Should not raise when serializing
        json_str = json.dumps(result)
        assert len(json_str) > 0
    
    def test_invoke_handles_empty_tickers(self):
        """Tool should handle empty ticker list gracefully."""
        tool = DataQualityTool()
        
        with patch('data.data_quality.run_full_data_quality_check') as mock_check:
            mock_check.return_value = {
                "overall_quality_score": 0.0,
                "tickers_checked": 0,
                "issues_found": 0,
            }
            
            result = tool.invoke({"tickers": []})
        
        assert result["success"] is True
    
    def test_invoke_handles_timeout(self):
        """Tool should handle timeout gracefully."""
        config = ToolConfig(timeout_seconds=0.1)
        tool = DataQualityTool(config=config)
        
        def slow_function(*args, **kwargs):
            import time
            time.sleep(5)  # Simulate slow function
            return {"quality_score": 0.9}
        
        with patch('data.data_quality.run_full_data_quality_check', side_effect=slow_function):
            result = tool.invoke({"tickers": ["AAPL"]})
        
        assert result["success"] is False
        # Check for either "timeout" or "timed out" in error message
        assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()
        assert result["metadata"]["error_type"] == "timeout"
    
    def test_invoke_handles_exception(self):
        """Tool should handle exceptions with graceful degradation."""
        tool = DataQualityTool()
        
        with patch('data.data_quality.run_full_data_quality_check', side_effect=Exception("Database error")):
            result = tool.invoke({"tickers": ["AAPL"]})
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None
        assert "Database error" in result["error"]
    
    def test_invoke_with_custom_config(self):
        """Tool should respect custom configuration."""
        config = ToolConfig(timeout_seconds=60.0, enable_caching=False)
        tool = DataQualityTool(config=config)
        
        with patch('data.data_quality.run_full_data_quality_check') as mock_check:
            mock_check.return_value = {"quality_score": 0.9}
            result = tool.invoke({"tickers": ["AAPL"]})
        
        assert result["success"] is True
        assert tool.config.timeout_seconds == 60.0
        assert tool.config.enable_caching is False


class TestPriceDataTool:
    """Tests for PriceDataTool wrapper."""
    
    def test_tool_has_correct_name(self):
        """Tool should have the correct name."""
        tool = PriceDataTool()
        assert tool.name == "price_data"
    
    def test_invoke_download_price_data(self):
        """Tool should wrap download_price_data function."""
        tool = PriceDataTool()
        
        mock_df = pd.DataFrame({
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000000, 1100000],
        }, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
        
        with patch('data.price_data.download_price_data') as mock_download:
            mock_download.return_value = {"AAPL": mock_df}
            
            result = tool.invoke({
                "action": "download",
                "tickers": ["AAPL"],
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
            })
        
        assert result["success"] is True
        assert result["data"] is not None
    
    def test_invoke_get_existing_dates(self):
        """Tool should wrap get_existing_price_dates function."""
        tool = PriceDataTool()
        
        with patch('data.price_data.get_existing_price_dates') as mock_dates:
            mock_dates.return_value = [date(2024, 1, 1), date(2024, 1, 2)]
            
            result = tool.invoke({
                "action": "get_dates",
                "ticker": "AAPL",
            })
        
        assert result["success"] is True
        assert "dates" in str(result["data"]).lower() or "2024" in str(result["data"])
    
    def test_invoke_invalid_action(self):
        """Tool should handle invalid action gracefully."""
        tool = PriceDataTool()
        
        result = tool.invoke({
            "action": "invalid_action",
            "tickers": ["AAPL"],
        })
        
        assert result["success"] is False
        assert "error" in result


class TestFundamentalDataTool:
    """Tests for FundamentalDataTool wrapper."""
    
    def test_tool_has_correct_name(self):
        """Tool should have the correct name."""
        tool = FundamentalDataTool()
        assert tool.name == "fundamental_data"
    
    def test_invoke_download_fundamental(self):
        """Tool should wrap download_fundamental_data function."""
        tool = FundamentalDataTool()
        
        mock_income = pd.DataFrame({"Revenue": [100000, 110000]})
        
        with patch('data.fundamental_data.download_fundamental_data') as mock_download:
            mock_download.return_value = {
                "AAPL": {
                    "income_stmt": mock_income,
                    "balance_sheet": pd.DataFrame(),
                    "cash_flow": pd.DataFrame(),
                }
            }
            
            result = tool.invoke({
                "tickers": ["AAPL"],
            })
        
        assert result["success"] is True
        assert result["data"] is not None


class TestUniverseSelectionTool:
    """Tests for UniverseSelectionTool wrapper."""
    
    def test_tool_has_correct_name(self):
        """Tool should have the correct name."""
        tool = UniverseSelectionTool()
        assert tool.name == "universe_selection"
    
    def test_invoke_get_all_tickers(self):
        """Tool should wrap get_all_tickers function."""
        tool = UniverseSelectionTool()
        
        with patch('data.universe_selection.get_all_tickers') as mock_tickers:
            mock_tickers.return_value = ["AAPL", "MSFT", "GOOGL"]
            
            result = tool.invoke({
                "action": "get_all_tickers",
            })
        
        assert result["success"] is True
        assert "tickers" in result["data"] or "AAPL" in str(result["data"])
    
    def test_invoke_select_universe(self):
        """Tool should wrap universe selection logic."""
        tool = UniverseSelectionTool()
        
        # Mock all the external dependencies to avoid network calls
        with patch('data.universe_selection.get_all_tickers') as mock_tickers:
            mock_tickers.return_value = ["AAPL", "MSFT", "GOOGL"] * 200
            
            with patch('data.universe_selection.init_db'):
                with patch('data.universe_selection.save_to_db'):
                    with patch('data.universe_selection.get_ticker_list_from_nasdaq', return_value=[]):
                        with patch('data.universe_selection.get_sp500_tickers', return_value=[]):
                            with patch('data.universe_selection.get_static_ticker_list', return_value=[]):
                                with patch('yfinance.Ticker') as mock_ticker_class:
                                    # Mock yfinance to return data quickly
                                    mock_stock = MagicMock()
                                    mock_stock.info = {"marketCap": 1000000000, "averageVolume": 1000000, "currentPrice": 100}
                                    mock_ticker_class.return_value = mock_stock
                                    
                                    result = tool.invoke({
                                        "action": "select_universe",
                                    })
        
        assert result["success"] is True
        assert "tickers_selected" in result["data"]


class TestPortfolioQueryTool:
    """Tests for PortfolioQueryTool wrapper."""
    
    def test_tool_has_correct_name(self):
        """Tool should have the correct name."""
        tool = PortfolioQueryTool()
        assert tool.name == "portfolio_query"
    
    def test_invoke_get_selected_tickers(self):
        """Tool should wrap get_selected_tickers function."""
        tool = PortfolioQueryTool()
        
        with patch('data.db_schema.get_selected_tickers') as mock_tickers:
            mock_tickers.return_value = ["AAPL", "MSFT", "GOOGL"]
            
            result = tool.invoke({
                "action": "get_selected_tickers",
            })
        
        assert result["success"] is True
        assert result["data"] is not None


class TestToolRegistry:
    """Tests for ToolRegistry."""
    
    def test_get_default_registry(self):
        """Should return a registry with all tools."""
        registry = get_default_registry()
        assert registry is not None
        assert len(registry.list_tools()) >= 5  # At least 5 tools
    
    def test_registry_list_tools(self):
        """Registry should list all available tools."""
        registry = get_default_registry()
        tools = registry.list_tools()
        
        expected_tools = ["data_quality", "price_data", "fundamental_data", 
                         "universe_selection", "portfolio_query"]
        
        tool_names = [t["name"] for t in tools]
        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
    
    def test_registry_get_tool(self):
        """Registry should be able to retrieve a specific tool."""
        registry = get_default_registry()
        tool = registry.get_tool("data_quality")
        assert tool is not None
        assert tool.name == "data_quality"
    
    def test_registry_to_langchain_tools(self):
        """Registry should be able to convert all tools to LangChain format."""
        # Check if langchain_core is available
        try:
            import langchain_core
        except ImportError:
            pytest.skip("langchain_core not installed")
        
        registry = get_default_registry()
        lc_tools = registry.to_langchain_tools()
        
        assert len(lc_tools) >= 5
        # Each should have name and description
        for lc_tool in lc_tools:
            assert hasattr(lc_tool, 'name')
            assert hasattr(lc_tool, 'description')


class TestToolIntegration:
    """Integration tests for tool wrappers."""
    
    def test_concurrent_tool_execution(self):
        """Tools should support concurrent execution."""
        from concurrent.futures import ThreadPoolExecutor
        
        registry = get_default_registry()
        tools = {
            "data_quality": registry.get_tool("data_quality"),
            "universe_selection": registry.get_tool("universe_selection"),
        }
        
        def execute_tool(tool_name, tool):
            with patch('data.data_quality.run_full_data_quality_check') as mock:
                mock.return_value = {"quality_score": 0.9}
                return tool.invoke({"tickers": ["AAPL"]})
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(execute_tool, name, tool)
                for name, tool in tools.items()
            ]
            results = [f.result() for f in futures]
        
        assert len(results) == 2
        assert all(r["success"] for r in results)
    
    def test_cache_functionality(self):
        """Tools should support caching."""
        config = ToolConfig(enable_caching=True, cache_ttl_seconds=60)
        tool = DataQualityTool(config=config)
        
        call_count = 0
        
        def counting_mock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"quality_score": 0.9}
        
        with patch('data.data_quality.run_full_data_quality_check', side_effect=counting_mock):
            # First call
            result1 = tool.invoke({"tickers": ["AAPL"]})
            # Second call with same input (should hit cache)
            result2 = tool.invoke({"tickers": ["AAPL"]})
        
        assert call_count == 1  # Only one actual call
        assert result1["success"] and result2["success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])