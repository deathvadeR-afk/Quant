"""
LangChain Tool Wrappers for Quantitative Trading System.

This module provides LangChain-compatible tool wrappers around existing data modules.
Existing production code remains untouched - only thin wrapper layers are added.

Tools:
- DataQualityTool: Wraps data_quality.run_full_data_quality_check()
- PriceDataTool: Wraps price_data.download_price_data() and get_existing_price_dates()
- FundamentalDataTool: Wraps fundamental_data.download_fundamental_data()
- UniverseSelectionTool: Wraps universe_selection.get_all_tickers() and select_universe()
- PortfolioQueryTool: Wraps db_schema.get_selected_tickers() and get_portfolio_exposure()

Author: Quant Team
Version: 1.0.0
"""

from tools.base import BaseQuantTool, ToolConfig
from tools.data_quality_tool import DataQualityTool
from tools.price_data_tool import PriceDataTool
from tools.fundamental_data_tool import FundamentalDataTool
from tools.universe_selection_tool import UniverseSelectionTool
from tools.portfolio_query_tool import PortfolioQueryTool
from tools.registry import ToolRegistry, get_default_registry

__all__ = [
    "BaseQuantTool",
    "ToolConfig",
    "DataQualityTool",
    "PriceDataTool",
    "FundamentalDataTool",
    "UniverseSelectionTool",
    "PortfolioQueryTool",
    "ToolRegistry",
    "get_default_registry",
]