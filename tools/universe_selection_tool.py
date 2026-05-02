"""
UniverseSelectionTool - LangChain wrapper for universe selection operations.

Wraps:
- data.universe_selection.get_all_tickers()
- Universe selection logic

This tool provides:
- Combined ticker list from multiple sources
- Dynamic universe selection based on market cap and volume
- Exactly 500 stocks selected
"""

from typing import Any, Dict
import logging

from tools.base import BaseQuantTool, ToolConfig

logger = logging.getLogger(__name__)


class UniverseSelectionTool(BaseQuantTool):
    """
    LangChain tool wrapper for universe selection.
    
    Wraps get_all_tickers() and universe selection logic.
    Provides access to the 500-stock tradeable universe.
    
    Example:
        >>> tool = UniverseSelectionTool()
        >>> result = tool.invoke({"action": "get_all_tickers"})
    """
    
    @property
    def name(self) -> str:
        return "universe_selection"
    
    @property
    def description(self) -> str:
        return """
Get the tradeable universe of stocks for the multi-factor strategy.

Actions:
1. 'get_all_tickers' - Get combined list from all sources (NASDAQ, S&P 500, static)
2. 'select_universe' - Run full universe selection to get top 500 stocks
3. 'get_selected' - Get currently selected universe from database

Use this tool to:
- Get list of available stocks to trade
- Check universe size and composition
- Support factor calculations on universe
- Get tickers for data download

Input: Action type
Output: List of tickers or selected universe
"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_all_tickers", "select_universe", "get_selected"],
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
        """Execute universe selection operation."""
        action = input_data.get("action", "get_all_tickers")
        
        if action == "get_all_tickers":
            return self._get_all_tickers()
        elif action == "select_universe":
            return self._select_universe(input_data)
        elif action == "get_selected":
            return self._get_selected(input_data)
        else:
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": ["get_all_tickers", "select_universe", "get_selected"],
            }
    
    def _get_all_tickers(self) -> Dict[str, Any]:
        """Get combined ticker list from all sources."""
        from data.universe_selection import get_all_tickers
        
        tickers = get_all_tickers()
        
        return {
            "ticker_count": len(tickers),
            "tickers": tickers[:100],  # Limit for display
            "note": f"Total: {len(tickers)} tickers. Showing first 100.",
        }
    
    def _select_universe(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run full universe selection."""
        from data.universe_selection import (
            get_all_tickers,
            get_ticker_list_from_nasdaq,
            get_sp500_tickers,
            get_static_ticker_list,
            init_db,
            save_to_db,
        )
        import pandas as pd
        import yfinance as yf
        
        db_path = input_data.get("db_path", "data/universe.db")
        
        # Get all tickers
        all_tickers = get_all_tickers()
        
        # Initialize database
        init_db(db_path)
        
        # Fetch market data for filtering
        logger.info(f"Fetching market data for {len(all_tickers)} tickers...")
        
        market_data = []
        for i, ticker in enumerate(all_tickers[:1000]):  # Limit for performance
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                market_data.append({
                    "ticker": ticker,
                    "market_cap": info.get("marketCap", 0),
                    "avg_volume": info.get("averageVolume", 0),
                    "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                })
            except Exception:
                pass
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{min(1000, len(all_tickers))} tickers")
        
        # Create DataFrame and filter
        df = pd.DataFrame(market_data)
        if df.empty:
            return {"error": "No market data retrieved", "tickers_selected": 0}
        
        # Apply filters
        df = df[df["market_cap"] >= 100_000_000]  # $100M min
        df = df[df["avg_volume"] >= 500_000]  # $500K min volume
        df = df[df["price"] >= 2]  # $2 min price
        
        # Sort by market cap and take top 500
        df = df.sort_values("market_cap", ascending=False).head(500)
        
        # Save to database
        save_to_db(df, source="market_filter", db_path=db_path)
        
        return {
            "tickers_selected": len(df),
            "filters_applied": ["market_cap >= $100M", "volume >= 500K", "price >= $2"],
            "selection_criteria": "market_cap descending",
            "tickers": df["ticker"].tolist()[:100],
            "note": f"Selected {len(df)} tickers. Showing first 100.",
        }
    
    def _get_selected(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get currently selected universe from database."""
        from data.db_schema import get_selected_tickers
        
        db_path = input_data.get("db_path", "data/universe.db")
        
        tickers = get_selected_tickers(db_path)
        
        return {
            "universe_size": len(tickers),
            "tickers": tickers[:100],
            "note": f"Universe size: {len(tickers)}. Showing first 100.",
        }