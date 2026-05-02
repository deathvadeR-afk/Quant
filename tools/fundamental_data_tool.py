"""
FundamentalDataTool - LangChain wrapper for fundamental data operations.

Wraps: data.fundamental_data.download_fundamental_data()

This tool provides:
- Quarterly and annual financial statements
- Balance sheet data
- Cash flow data
- Point-in-time correctness
"""

from typing import Any, Dict
import logging

from tools.base import BaseQuantTool, ToolConfig

logger = logging.getLogger(__name__)


class FundamentalDataTool(BaseQuantTool):
    """
    LangChain tool wrapper for fundamental data operations.
    
    Wraps download_fundamental_data() function.
    Downloads income statements, balance sheets, and cash flow data.
    
    Example:
        >>> tool = FundamentalDataTool()
        >>> result = tool.invoke({"tickers": ["AAPL", "MSFT"]})
    """
    
    @property
    def name(self) -> str:
        return "fundamental_data"
    
    @property
    def description(self) -> str:
        return """
Download fundamental financial data for given tickers.

Returns:
- Income statements (quarterly and annual)
- Balance sheets (quarterly and annual)
- Cash flow statements (quarterly and annual)
- Company info (market cap, P/E, etc.)

Use this tool to:
- Get financial statements for valuation
- Download balance sheet data
- Access cash flow information
- Support fundamental factor calculations

Input: List of ticker symbols
Output: Dictionary of financial data by ticker
"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ticker symbols",
                },
                "db_path": {
                    "type": "string",
                    "description": "Path to SQLite database",
                    "default": "data/universe.db",
                },
            },
            "required": ["tickers"],
        }
    
    def _execute_impl(self, input_data: Dict[str, Any]) -> Any:
        """Execute fundamental data download."""
        from data.fundamental_data import download_fundamental_data
        
        tickers = input_data.get("tickers", [])
        db_path = input_data.get("db_path", "data/universe.db")
        
        if not tickers:
            return {"error": "No tickers provided", "tickers_downloaded": 0}
        
        result = download_fundamental_data(
            tickers=tickers,
            db_path=db_path,
        )
        
        # Summarize results
        success_count = sum(1 for v in result.values() if not isinstance(v, Exception))
        error_count = sum(1 for v in result.values() if isinstance(v, Exception))
        
        return {
            "tickers_requested": len(tickers),
            "tickers_downloaded": success_count,
            "tickers_failed": error_count,
            "results": self._serialize_result(result),
        }
    
    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        """Ensure result is JSON-serializable."""
        import pandas as pd
        import numpy as np
        
        if isinstance(result, dict):
            serialized = {}
            for key, value in result.items():
                if isinstance(value, dict):
                    # Fundamental data is a dict of DataFrames
                    serialized[key] = self._serialize_fundamental_data(value)
                elif isinstance(value, Exception):
                    serialized[key] = {"error": str(value), "type": "exception"}
                else:
                    serialized[key] = str(value)
            return serialized
        return {"data": str(result)}
    
    def _serialize_fundamental_data(self, data: Dict) -> Dict[str, Any]:
        """Serialize fundamental data dictionary."""
        import pandas as pd
        
        serialized = {}
        for stmt_type, df in data.items():
            if isinstance(df, pd.DataFrame):
                if df.empty:
                    serialized[stmt_type] = {"rows": 0, "data": []}
                else:
                    serialized[stmt_type] = {
                        "rows": len(df),
                        "columns": df.columns.tolist(),
                        "index": df.index.tolist()[:20],  # Limit index items
                        "data": df.head(10).to_dict(orient="records"),
                    }
            elif isinstance(df, dict):
                # Company info dict
                serialized[stmt_type] = df
            else:
                serialized[stmt_type] = str(df)
        return serialized