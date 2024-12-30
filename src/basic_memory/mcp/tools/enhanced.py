"""Enhanced MCP tool support with rich schema information."""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ToolExample(BaseModel):
    """Example usage of a tool."""
    name: str
    description: str
    code: str


class EnhancedToolMetadata(BaseModel):
    """Enhanced tool metadata."""
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    examples: List[ToolExample] = Field(
        default_factory=list,
        description="Example tool usage"
    )
    category: Optional[str] = Field(
        default=None,
        description="Tool category for organization"
    )
    input_schema: Optional[Dict] = Field(
        default=None,
        description="Input parameter schema"
    )
    output_schema: Optional[Dict] = Field(
        default=None,
        description="Return value schema"
    )


def enhanced_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    examples: Optional[List[Dict]] = None,
    category: Optional[str] = None,
    input_schema: Optional[Dict] = None,
    output_schema: Optional[Dict] = None,
):
    """Enhanced MCP tool decorator with rich metadata."""
    def decorator(fn: Callable):
        # Create metadata
        metadata = EnhancedToolMetadata(
            name=name or fn.__name__,
            description=description or fn.__doc__ or "",
            examples=[ToolExample(**ex) for ex in (examples or [])],
            category=category,
            input_schema=input_schema,
            output_schema=output_schema
        )
        
        # Try to extract schemas from type hints if not provided
        if input_schema is None or output_schema is None:
            sig = inspect.signature(fn)
            
            # Input schema from parameters
            if input_schema is None:
                for param in sig.parameters.values():
                    if hasattr(param.annotation, "model_json_schema"):
                        metadata.input_schema = param.annotation.model_json_schema()
                        break
            
            # Output schema from return type
            if output_schema is None:
                return_type = sig.return_annotation
                if hasattr(return_type, "model_json_schema"):
                    metadata.output_schema = return_type.model_json_schema()
        
        # Use regular MCP decorator first
        from basic_memory.mcp.server import mcp
        tool = mcp.tool(name=metadata.name, description=metadata.description)(fn)
        
        # Store metadata on tool model
        setattr(tool, "_enhanced_metadata", metadata)
        
        return tool
    
    return decorator