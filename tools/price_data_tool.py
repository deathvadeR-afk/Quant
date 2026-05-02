"""
PriceDataTool - LangChain wrapper for price data operations.

Wraps:
- data.price_data.download_price_data()
- data.price_data.get_existing_price_dates()

This tool provides:
- OHLCV data download with error handling
- Split and dividend adjustment
- Delisted stock handling
- Existing date queries for incremental updates
"""

from typing import Any, Dict
import logging

from tools.base import BaseQuantTool, ToolConfig

logger = logging.getLogger(__name__)


class PriceDataTool(BaseQuantTool):
    """
    LangChain tool wrapper for price data operations.
    
    Wraps download_price_data() and get_existing_price_dates() functions.
    Supports both downloading new data and querying existing data.
    
    Example:
        >>> tool = PriceDataTool()
        >>> result = tool.invoke({
        ...     "action": "download",
        ...     "tickers": ["AAPL"],
        ...     "start_date": "2024-01-01",
        ...     "end_date": "2024-01-02"
        ... })
    """
    
    @property
    def name(self) -> str:
        return "price_data"
    
    @property
    def description(self) -> str:
        return """
Download OHLCV price data or query existing price dates.

Actions:
1. 'download' - Download price data for given tickers
2. 'get_dates' - Get existing dates for a ticker (for incremental updates)

Use this tool to:
- Download historical price data
- Check what data already exists
- Prepare data for factor calculations
- Support incremental data updates

Input: Action type and ticker parameters
Output: Price data or list of existing dates
"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["download", "get_dates"],
                    "description": "Action to perform: 'download' or 'get_dates'",
                },
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ticker symbols (for download action)",
                },
                "ticker": {
                    "type": "string",
                    "description": "Single ticker symbol (for get_dates action)",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
                "db_path": {
                    "type": "string",
                    "description": "Path to SQLite database",
                    "default": "data/universe.db",
                },
            },
        }
    
    def _execute_impl(self, input_data: Dict[str, Any]) -> Any:
        """Execute price data operation based on action type."""
        action = input_data.get("action", "download")
        
        if action == "download":
            return self._download_prices(input_data)
        elif action == "get_dates":
            return self._get_existing_dates(input_data)
        else:
            # Return error in a way that indicates failure
            raise ValueError(f"Unknown action: {action}. Use 'download' or 'get_dates'.")
    
    def _download_prices(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Download price data for given tickers."""
        from data.price_data import download_price_data
        
        tickers = input_data.get("tickers", [])
        start_date = input_data.get("start_date", "2020-01-01")
        end_date = input_data.get("end_date", "2024-12-31")
        db_path = input_data.get("db_path", "data/universe.db")
        
        if not tickers:
            return {"error": "No tickers provided", "downloaded": 0}
        
        result = download_price_data(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            db_path=db_path,
        )
        
        # Summarize results
        success_count = sum(1 for v in result.values() if not isinstance(v, Exception))
        error_count = sum(1 for v in result.values() if isinstance(v, Exception))
        
        return {
            "tickers_requested": len(tickers),
            "tickers_downloaded": success_count,
            "tickers_failed": error_count,
            "date_range": {"start": start_date, "end": end_date},
            "results": self._serialize_result(result),
        }
    
    def _get_existing_dates(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get existing price dates for a ticker."""
        from data.price_data import get_existing_price_dates
        
        ticker = input_data.get("ticker", "")
        db_path = input_data.get("db_path", "data/universe.db")
        
        if not ticker:
            return {"error": "No ticker provided", "dates": []}
        
        dates = get_existing_price_dates(ticker=ticker, db_path=db_path)
        
        return {
            "ticker": ticker,
            "date_count": len(dates),
            "date_range": {
                "start": str(dates[0]) if dates else None,
                "end": str(dates[-1]) if dates else None,
            },
            "dates": [str(d) for d in dates],
        }
    
    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        """Ensure result is JSON-serializable."""
        import pandas as pd
        import numpy as np
        
        if isinstance(result, dict):
            serialized = {}
            for key, value in result.items():
                if isinstance(value, pd.DataFrame):
                    serialized[key] = {
                        "type": "dataframe",
                        "rows": len(value),
                        "columns": value.columns.tolist(),
                        "data": value.head(50).to_dict(orient="records"),
                    }
                elif isinstance(value, Exception):
                    serialized[key] = {"error": str(value), "type": "exception"}
                elif isinstance(value, np.ndarray):
                    serialized[key] = value.tolist()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    serialized[key] = value
                else:
                    serialized[key] = str(value)
            return serialized
        return {"data": str(result)}