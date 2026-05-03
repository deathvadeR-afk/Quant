"""
PortfolioQueryTool - LangChain wrapper for portfolio query operations.

Wraps:
- data.db_schema.get_selected_tickers()
- Portfolio exposure queries

This tool provides:
- Selected universe access
- Portfolio state queries
- Exposure analysis
"""

from typing import Any, Dict
import logging

from tools.base import BaseQuantTool, ToolConfig

logger = logging.getLogger(__name__)


class PortfolioQueryTool(BaseQuantTool):
    """
    LangChain tool wrapper for portfolio queries.
    
    Provides access to portfolio state and selected universe.
    
    Example:
        >>> tool = PortfolioQueryTool()
        >>> result = tool.invoke({"action": "get_selected_tickers"})
    """
    
    @property
    def name(self) -> str:
        return "portfolio_query"
    
    @property
    def description(self) -> str:
        return """
Query portfolio state and selected universe information.

Actions:
1. 'get_selected_tickers' - Get list of currently selected tickers
2. 'get_portfolio_exposure' - Get sector/industry exposure breakdown
3. 'get_portfolio_summary' - Get overall portfolio statistics

Use this tool to:
- Check what stocks are in the universe
- Analyze portfolio composition
- Support risk calculations
- Get tickers for further analysis

Input: Action type
Output: Portfolio information
"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_selected_tickers", "get_portfolio_exposure", "get_portfolio_summary"],
                    "description": "Action to perform",
                },
                "db_path": {
                    "type": "string",
                    "description": "Path to SQLite database",
                    "default": "data/universe.db",
                },
            },
        }
    
    def _execute_impl(self, input_data: Dict[str, Any]) -> Any:
        """Execute portfolio query operation."""
        action = input_data.get("action", "get_selected_tickers")
        
        if action == "get_selected_tickers":
            return self._get_selected_tickers(input_data)
        elif action == "get_portfolio_exposure":
            return self._get_portfolio_exposure(input_data)
        elif action == "get_portfolio_summary":
            return self._get_portfolio_summary(input_data)
        else:
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": ["get_selected_tickers", "get_portfolio_exposure", "get_portfolio_summary"],
            }
    
    def _get_selected_tickers(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of selected tickers from database."""
        from data.db_schema import get_selected_tickers
        
        db_path = input_data.get("db_path", "data/universe.db")
        
        tickers = get_selected_tickers(db_path)
        
        return {
            "universe_size": len(tickers),
            "tickers": tickers,
        }
    
    def _get_portfolio_exposure(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get sector/industry exposure breakdown."""
        from data.db_schema import get_portfolio_exposure
        
        db_path = input_data.get("db_path", "data/universe.db")
        return get_portfolio_exposure(db_path)
    
    def _get_portfolio_summary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get overall portfolio statistics."""
        import sqlite3
        import pandas as pd
        
        db_path = input_data.get("db_path", "data/universe.db")
        
        try:
            conn = sqlite3.connect(db_path)
            
            # Get universe stats
            universe_query = """
                SELECT 
                    COUNT(*) as total_tickers,
                    SUM(CASE WHEN price_data_complete = 1 THEN 1 ELSE 0 END) as tickers_with_price,
                    SUM(CASE WHEN fundamental_data_complete = 1 THEN 1 ELSE 0 END) as tickers_with_fundamental,
                    SUM(market_cap) as total_market_cap,
                    AVG(market_cap) as avg_market_cap
                FROM selected_universe
            """
            summary_df = pd.read_sql_query(universe_query, conn)
            conn.close()
            
            if summary_df.empty:
                return {"error": "No universe data found", "total_tickers": 0}
            
            row = summary_df.iloc[0]
            return {
                "total_tickers": int(row["total_tickers"]) if pd.notna(row["total_tickers"]) else 0,
                "tickers_with_price_data": int(row["tickers_with_price"]) if pd.notna(row["tickers_with_price"]) else 0,
                "tickers_with_fundamental_data": int(row["tickers_with_fundamental"]) if pd.notna(row["tickers_with_fundamental"]) else 0,
                "total_market_cap": float(row["total_market_cap"]) if pd.notna(row["total_market_cap"]) else 0,
                "avg_market_cap": float(row["avg_market_cap"]) if pd.notna(row["avg_market_cap"]) else 0,
            }
            
        except Exception as e:
            return {"error": str(e), "total_tickers": 0}