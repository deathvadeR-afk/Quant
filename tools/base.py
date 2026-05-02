"""
Base classes for LangChain tool wrappers.

Provides common functionality for all tool wrappers including:
- Timeout handling
- Error handling with graceful degradation
- JSON serialization
- LLM-optimized descriptions
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type
import logging
import json
import threading
from concurrent.futures import TimeoutError as FuturesTimeoutError
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class ToolConfig:
    """Configuration for tool execution."""
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


class BaseQuantTool(ABC):
    """
    Abstract base class for all quantitative data tools.
    
    Provides common functionality:
    - Timeout handling with ThreadPoolExecutor
    - Error handling with graceful degradation (returns error message, not exception)
    - JSON serialization for LLM consumption
    - Tool metadata for agent discovery
    
    Subclasses must implement:
    - _execute_impl(): The actual tool logic
    - name: Tool name for registry
    - description: LLM-optimized description
    - input_schema: JSON schema for tool inputs
    """
    
    def __init__(self, config: Optional[ToolConfig] = None):
        """Initialize tool with optional configuration."""
        self.config = config or ToolConfig()
        self._cache: Dict[str, tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._lock = threading.Lock()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for registry and agent invocation."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """LLM-optimized description explaining what the tool does."""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema for tool inputs."""
        pass
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """JSON schema for tool outputs (can be overridden)."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {"type": "object", "description": "Tool-specific output data"},
                "error": {"type": "string", "description": "Error message if success=false"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "execution_time_ms": {"type": "number"},
                        "timestamp": {"type": "string", "format": "date-time"},
                    }
                }
            }
        }
    
    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for tool invocation.
        
        Handles timeout, error catching, and JSON serialization.
        Returns a standardized response format.
        """
        import time
        from datetime import datetime
        
        start_time = time.time()
        cache_key = self._get_cache_key(input_data)
        
        # Check cache
        if self.config.enable_caching:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info(f"Cache hit for {self.name}")
                return cached
        
        # Execute with timeout
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._execute_impl, input_data)
                result = future.result(timeout=self.config.timeout_seconds)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            response = {
                "success": True,
                "data": result,
                "error": None,
                "metadata": {
                    "tool_name": self.name,
                    "execution_time_ms": round(execution_time_ms, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            }
            
            # Cache successful results
            if self.config.enable_caching:
                self._put_in_cache(cache_key, response)
            
            logger.info(f"{self.name} executed successfully in {execution_time_ms:.2f}ms")
            return response
            
        except FuturesTimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"{self.name} timed out after {self.config.timeout_seconds}s")
            return {
                "success": False,
                "data": None,
                "error": f"Tool execution timed out after {self.config.timeout_seconds} seconds",
                "metadata": {
                    "tool_name": self.name,
                    "execution_time_ms": round(execution_time_ms, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error_type": "timeout",
                }
            }
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"{self.name} failed: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"Tool execution failed: {str(e)}",
                "metadata": {
                    "tool_name": self.name,
                    "execution_time_ms": round(execution_time_ms, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error_type": type(e).__name__,
                }
            }
    
    @abstractmethod
    def _execute_impl(self, input_data: Dict[str, Any]) -> Any:
        """
        Implement the actual tool logic.
        
        This method should be overridden by subclasses.
        Should return JSON-serializable data.
        Should NOT raise exceptions - return error info in response instead.
        """
        pass
    
    def _get_cache_key(self, input_data: Dict[str, Any]) -> str:
        """Generate cache key from input data."""
        # Sort keys for consistent hashing
        return json.dumps(input_data, sort_keys=True, default=str)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if not expired."""
        import time
        with self._lock:
            if cache_key in self._cache:
                value, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self.config.cache_ttl_seconds:
                    return value
                else:
                    del self._cache[cache_key]
        return None
    
    def _put_in_cache(self, cache_key: str, value: Dict[str, Any]) -> None:
        """Store result in cache."""
        import time
        with self._lock:
            self._cache[cache_key] = (value, time.time())
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()
    
    def to_langchain_tool(self) -> "langchain_core.tools.BaseTool":
        """
        Convert to LangChain tool for agent integration.
        
        Returns a LangChain BaseTool instance.
        """
        from langchain_core.tools import BaseTool
        from pydantic import BaseModel, Field
        
        class ToolInput(BaseModel):
            """Input schema for this tool."""
            pass
        
        # Build input schema from our schema
        input_fields = self.input_schema.get("properties", {})
        for field_name, field_schema in input_fields.items():
            ToolInput.model_fields[field_name] = Field(
                description=field_schema.get("description", ""),
                default=field_schema.get("default"),
            )
        
        class LangChainToolWrapper(BaseTool):
            """LangChain-compatible wrapper for this tool."""
            name: str = self.name
            description: str = self.description
            args_schema: Type[BaseModel] = ToolInput
            
            def _run(self, **kwargs) -> str:
                """Execute the tool and return JSON string."""
                result = self.invoke(kwargs)
                return json.dumps(result, indent=2, default=str)
        
        return LangChainToolWrapper()
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"