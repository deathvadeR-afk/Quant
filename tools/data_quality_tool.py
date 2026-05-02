"""
DataQualityTool - LangChain wrapper for data quality checking.

Wraps: data.data_quality.run_full_data_quality_check()

This tool provides:
- Structured quality metrics for price and fundamental data
- Missing value detection
- Outlier detection
- Consistency validation
"""

from typing import Any, Dict, List
import logging

from tools.base import BaseQuantTool, ToolConfig

logger = logging.getLogger(__name__)


class DataQualityTool(BaseQuantTool):
    """
    LangChain tool wrapper for data quality validation.
    
    Wraps the run_full_data_quality_check() function from data_quality module.
    Returns structured quality metrics as JSON for LLM consumption.
    
    Example:
        >>> tool = DataQualityTool()
        >>> result = tool.invoke({"tickers": ["AAPL", "MSFT"]})
        >>> print(result["data"]["overall_quality_score"])
    """
    
    @property
    def name(self) -> str:
        return "data_quality"
    
    @property
    def description(self) -> str:
        return """
Run comprehensive data quality validation on price and fundamental data.

Returns structured quality metrics including:
- Overall quality score (0-1)
- Missing value counts and percentages
- Outlier detection results
- Consistency validation results
- Per-ticker quality breakdown

Use this tool to:
- Validate data before analysis
- Identify data quality issues
- Check for missing or corrupted data
- Verify data consistency across sources

Input: List of ticker symbols to check
Output: JSON with quality metrics and any issues found
"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ticker symbols to check (e.g., ['AAPL', 'MSFT'])",
                },
                "db_path": {
                    "type": "string",
                    "description": "Path to SQLite database (default: data/universe.db)",
                    "default": "data/universe.db",
                },
            },
            "required": ["tickers"],
        }
    
    def _execute_impl(self, input_data: Dict[str, Any]) -> Any:
        """
        Execute data quality check.
        
        Wraps data.data_quality.run_full_data_quality_check() and ensures
        the result is JSON-serializable.
        """
        from data.data_quality import run_full_data_quality_check
        
        tickers = input_data.get("tickers", [])
        db_path = input_data.get("db_path", "data/universe.db")
        
        if not tickers:
            return {
                "overall_quality_score": 0.0,
                "tickers_checked": 0,
                "issues_found": 0,
                "message": "No tickers provided",
            }
        
        # Call the underlying function
        result = run_full_data_quality_check(
            tickers=tickers,
            db_path=db_path,
        )
        
        # Ensure JSON-serializable output
        return self._serialize_result(result)
    
    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        """
        Ensure result is JSON-serializable.
        
        Handles pandas DataFrames, Series, and other non-serializable types.
        """
        import pandas as pd
        import numpy as np
        
        if isinstance(result, pd.DataFrame):
            return {
                "type": "dataframe",
                "columns": result.columns.tolist(),
                "rows": len(result),
                "data": result.head(100).to_dict(orient="records"),
                "summary": {
                    "total_rows": len(result),
                    "total_columns": len(result.columns),
                }
            }
        elif isinstance(result, pd.Series):
            return {
                "type": "series",
                "data": result.to_dict(),
            }
        elif isinstance(result, dict):
            # Recursively serialize nested structures
            serialized = {}
            for key, value in result.items():
                if isinstance(value, (pd.DataFrame, pd.Series)):
                    serialized[key] = self._serialize_result(value)
                elif isinstance(value, np.ndarray):
                    serialized[key] = value.tolist()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    serialized[key] = value
                elif isinstance(value, (list, tuple)):
                    serialized[key] = [
                        self._serialize_result(v) if isinstance(v, (dict, pd.DataFrame, pd.Series)) else v
                        for v in value
                    ]
                else:
                    serialized[key] = str(value)
            return serialized
        elif isinstance(result, (list, tuple)):
            return [
                self._serialize_result(item) if isinstance(item, (dict, list)) else item
                for item in result
            ]
        elif isinstance(result, np.ndarray):
            return result.tolist()
        elif isinstance(result, (int, float, str, bool, type(None))):
            return result
        else:
            return {"value": str(result), "type": type(result).__name__}