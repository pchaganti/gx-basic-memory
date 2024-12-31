"""Enhanced FastMCP server instance for Basic Memory."""

from typing import Any, Callable, Dict, List, Optional, Type

from fastmcp import FastMCP
import inspect
from pydantic import BaseModel, Field, create_model
from pydantic.json_schema import model_json_schema
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
        output_model: Optional[Type[BaseModel]] = None,
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
    code: str = Field(description="Example code")


class EnhancedTool(FastMCPTool):
    """Extended tool registration with rich metadata."""
    examples: List[ToolExample] = Field(default_factory=list)
    category: Optional[str] = Field(None)
    input_schema: Optional[Dict] = Field(None)
    output_schema: Optional[Dict] = Field(None)
    output_model: Optional[Type[BaseModel]] = Field(None)

    @classmethod
    def from_function(
        cls,
        fn: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[List[Dict]] = None,
        category: Optional[str] = None,
        output_model: Optional[Type[BaseModel]] = None,
    ) -> "EnhancedTool":
        """Create an enhanced tool from a function."""
        # First create the base tool
        base_tool = super().from_function(fn, name=name, description=description)

        # Create instance for schema extraction
        instance = cls(
            fn=fn,
            name=base_tool.name,
            description=base_tool.description,
            parameters=base_tool.parameters,
            fn_metadata=base_tool.fn_metadata,
            is_async=base_tool.is_async,
            context_kwarg=base_tool.context_kwarg,
            examples=[],
            category=category,
        )

        # Get output schema either from output_model or return type annotation
        output_schema = None
        if output_model:
            try:
                schema_dict = model_json_schema(output_model)
                # Take top level schema if exists, otherwise look in $defs
                if 'properties' in schema_dict:
                    output_schema = schema_dict
                elif '$defs' in schema_dict and output_model.__name__ in schema_dict['$defs']:
                    output_schema = schema_dict['$defs'][output_model.__name__]
            except Exception as e:
                logger.error(f"Error getting schema for {output_model.__name__}: {e}")
                output_schema = {"type": "object"}
        else:
            # Try to get schema from return type annotation
            sig = inspect.signature(fn)
            return_type = sig.return_annotation
            if return_type != inspect.Signature.empty:
                if hasattr(return_type, 'model_json_schema'):
                    try:
                        schema_dict = model_json_schema(return_type)
                        if 'properties' in schema_dict:
                            output_schema = schema_dict
                        elif '$defs' in schema_dict and return_type.__name__ in schema_dict['$defs']:
                            output_schema = schema_dict['$defs'][return_type.__name__]
                    except Exception as e:
                        logger.error(f"Error getting schema from return type {return_type}: {e}")
                        output_schema = {"type": "object"}
                elif hasattr(return_type, '__origin__'):  # Handle List[T], Dict[K,V] etc
                    try:
                        if return_type.__origin__ == list:
                            schema_dict = {
                                "type": "array",
                                "items": {"type": "object"}  # Basic schema for items
                            }
                            # Try to get item type schema if it's a pydantic model
                            item_type = return_type.__args__[0]
                            if hasattr(item_type, 'model_json_schema'):
                                try:
                                    item_schema = model_json_schema(item_type)
                                    schema_dict["items"] = item_schema
                                except Exception as e:
                                    logger.error(f"Error getting item schema: {e}")
                        elif return_type.__origin__ == dict:
                            schema_dict = {
                                "type": "object",
                                "additionalProperties": True
                            }
                            # Try to get value type schema if it's a pydantic model
                            key_type, value_type = return_type.__args__
                            if hasattr(value_type, 'model_json_schema'):
                                try:
                                    value_schema = model_json_schema(value_type)
                                    schema_dict["additionalProperties"] = value_schema
                                except Exception as e:
                                    logger.error(f"Error getting value schema: {e}")
                        output_schema = schema_dict
                    except Exception as e:
                        logger.error(f"Error handling complex type {return_type}: {e}")
                        output_schema = {"type": "object"}

        # Convert examples to ToolExample models
        tool_examples = [ToolExample(**ex) for ex in (examples or [])]

        # Update instance with final values
        instance.examples = tool_examples
        instance.output_schema = output_schema
        instance.output_model = output_model
        
        return instance

    def get_schema(self) -> Dict:
        """Get complete tool schema including examples and metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
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
        output_model: Optional[Type[BaseModel]] = None,
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