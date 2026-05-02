"""
Tool Registry for LangChain agent integration.

Provides a central registry for all tool wrappers, enabling:
- Easy agent access to all tools
- LangChain tool conversion
- Tool discovery and documentation
"""

from typing import Any, Dict, List, Optional
import logging

from tools.base import BaseQuantTool, ToolConfig
from tools.data_quality_tool import DataQualityTool
from tools.price_data_tool import PriceDataTool
from tools.fundamental_data_tool import FundamentalDataTool
from tools.universe_selection_tool import UniverseSelectionTool
from tools.portfolio_query_tool import PortfolioQueryTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all quantitative data tools.
    
    Provides:
    - Tool registration and retrieval
    - LangChain tool conversion
    - Tool metadata for agent discovery
    
    Example:
        >>> registry = ToolRegistry()
        >>> registry.register(DataQualityTool())
        >>> tool = registry.get_tool("data_quality")
        >>> lc_tools = registry.to_langchain_tools()
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, BaseQuantTool] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
    
    def register(self, tool: BaseQuantTool) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        self._metadata[tool.name] = {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "output_schema": tool.output_schema,
        }
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseQuantTool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools with metadata.
        
        Returns:
            List of tool metadata dictionaries
        """
        return list(self._metadata.values())
    
    def to_langchain_tools(self) -> List[Any]:
        """
        Convert all registered tools to LangChain format.
        
        Returns:
            List of LangChain BaseTool instances
        """
        lc_tools = []
        for tool in self._tools.values():
            try:
                lc_tool = tool.to_langchain_tool()
                lc_tools.append(lc_tool)
            except Exception as e:
                logger.warning(f"Failed to convert {tool.name} to LangChain tool: {e}")
        return lc_tools
    
    def get_tool_by_category(self, category: str) -> List[BaseQuantTool]:
        """
        Get tools by category.
        
        Categories:
        - 'data': Data access tools (quality, price, fundamental)
        - 'universe': Universe selection tools
        - 'portfolio': Portfolio query tools
        
        Args:
            category: Tool category
            
        Returns:
            List of tools in the category
        """
        categories = {
            "data": ["data_quality", "price_data", "fundamental_data"],
            "universe": ["universe_selection"],
            "portfolio": ["portfolio_query"],
        }
        
        tool_names = categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)
    
    def __repr__(self) -> str:
        return f"<ToolRegistry(tools={len(self._tools)})>"


# Global default registry instance
_default_registry: Optional[ToolRegistry] = None


def get_default_registry() -> ToolRegistry:
    """
    Get the default tool registry with all tools registered.
    
    This function creates and populates a registry on first call,
    then returns the same instance on subsequent calls.
    
    Returns:
        ToolRegistry with all tools registered
    """
    global _default_registry
    
    if _default_registry is None:
        _default_registry = ToolRegistry()
        
        # Register all tools
        _default_registry.register(DataQualityTool())
        _default_registry.register(PriceDataTool())
        _default_registry.register(FundamentalDataTool())
        _default_registry.register(UniverseSelectionTool())
        _default_registry.register(PortfolioQueryTool())
        
        logger.info(f"Initialized default registry with {len(_default_registry)} tools")
    
    return _default_registry


def create_registry_with_config(config: ToolConfig) -> ToolRegistry:
    """
    Create a new registry with tools configured with the given config.
    
    Args:
        config: Tool configuration to apply to all tools
        
    Returns:
        ToolRegistry with configured tools
    """
    registry = ToolRegistry()
    
    registry.register(DataQualityTool(config))
    registry.register(PriceDataTool(config))
    registry.register(FundamentalDataTool(config))
    registry.register(UniverseSelectionTool(config))
    registry.register(PortfolioQueryTool(config))
    
    return registry