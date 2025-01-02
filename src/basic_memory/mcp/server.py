"""Enhanced FastMCP server instance for Basic Memory."""

from typing import Any, Callable, Dict, List, Optional, Type, Union

from fastmcp import FastMCP
import inspect
from pydantic import BaseModel, Field, TypeAdapter
from loguru import logger

from fastmcp.tools import Tool as FastMCPTool
from fastmcp.tools.tool_manager import ToolManager as FastMCPToolManager


class BasicMemoryServer(FastMCP):
    """Enhanced FastMCP server with schema support."""

    def __init__(self, name: str | None = None, **settings: Any):
        super().__init__(name=name, **settings)
        # Replace default tool manager with our enhanced version
        self._tool_manager = EnhancedToolManager(
            warn_on_duplicate_tools=self.settings.warn_on_duplicate_tools
        )

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        output_model: Any = None,
    ):
        """Decorator to register an enhanced tool."""
        def decorator(fn: Callable) -> Callable:
            tool = self._tool_manager.add_tool(
                fn, 
                name=name, 
                description=description, 
                examples=examples, 
                category=category,
                output_model=output_model
            )
            return fn

        return decorator


class ToolExample(BaseModel):
    """Example usage of a tool."""
    name: str = Field(description="Name of the example")
    description: str = Field(description="Description of what the example demonstrates")
    code: str = Field(description="Example code showing how to use the tool")


class EnhancedTool(FastMCPTool):
    """Extended tool registration with rich metadata."""
    examples: List[ToolExample] = Field(default_factory=list)
    category: Optional[str] = Field(None)
    input_schema: Optional[Dict] = Field(None)
    output_schema: Optional[Dict] = Field(None)
    output_model: Any = Field(None)

    @staticmethod
    def _get_schema(type_: Any) -> Optional[Dict[str, Any]]:
        """Get JSON schema for a type using TypeAdapter."""
        try:
            # If it's already a dict schema, return it
            if isinstance(type_, dict):
                return type_
                
            # Handle simple types directly
            if type_ in (str, int, float, bool):
                return {"type": {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean"
                }[type_]}
                
            # Try using TypeAdapter for complex types
            adapter = TypeAdapter(type_)
            return adapter.json_schema()
        except Exception as e:
            logger.debug(f"Error getting schema for {type_}: {e}")
            return None

    @classmethod
    def from_function(
        cls,
        fn: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        output_model: Any = None,
    ) -> "EnhancedTool":
        """Create an enhanced tool from a function."""
        # First create the base tool
        base_tool = super().from_function(fn, name=name, description=description)

        # Get output schema
        output_schema = None
        if output_model:
            logger.debug(f"Getting schema for output_model {output_model}")
            output_schema = cls._get_schema(output_model)
        else:
            # Try return type annotation
            sig = inspect.signature(fn)
            return_type = sig.return_annotation
            if return_type != inspect.Signature.empty:
                logger.debug(f"Getting schema from return type {return_type}")
                output_schema = cls._get_schema(return_type)

        # Provide basic schema if we couldn't get a proper one
        if output_schema is None:
            output_schema = {"type": "object"}

        # Convert examples to ToolExample models
        tool_examples = [ToolExample(**ex) for ex in (examples or [])]

        return cls(
            fn=fn,
            name=base_tool.name,
            description=base_tool.description,
            parameters=base_tool.parameters,
            fn_metadata=base_tool.fn_metadata,
            is_async=base_tool.is_async,
            context_kwarg=base_tool.context_kwarg,
            examples=tool_examples,
            category=category,
            input_schema=base_tool.parameters,
            output_schema=output_schema,
            output_model=output_model,
        )

    def get_schema(self) -> Dict:
        """Get complete tool schema including examples and metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": [ex.model_dump() for ex in self.examples],
        }


class EnhancedToolManager(FastMCPToolManager):
    """Tool manager with enhanced metadata support."""

    def add_tool(
        self,
        fn: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        output_model: Any = None,
    ) -> EnhancedTool:
        """Add a tool with enhanced metadata."""
        tool = EnhancedTool.from_function(
            fn, 
            name=name, 
            description=description, 
            examples=examples, 
            category=category,
            output_model=output_model
        )
        self._tools[tool.name] = tool
        return tool

    def get_schema_catalog(self) -> Dict:
        """Get complete schema catalog for all tools."""
        catalog = {"tools": {}, "categories": {}}

        for tool in self._tools.values():
            if isinstance(tool, EnhancedTool):
                catalog["tools"][tool.name] = tool.get_schema()

                if tool.category:
                    if tool.category not in catalog["categories"]:
                        catalog["categories"][tool.category] = {"name": tool.category, "tools": []}
                    catalog["categories"][tool.category]["tools"].append(tool.name)

        return catalog


# Create the shared server instance
mcp = BasicMemoryServer("Basic Memory")