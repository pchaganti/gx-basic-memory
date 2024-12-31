"""Help and schema introspection tools."""

from typing import Dict, Optional

from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.enhanced import enhanced_tool


@enhanced_tool(
    category="system",
    examples=[
        {
            "name": "Get All Tools",
            "description": "Get complete schema catalog for all tools",
            "code": "catalog = await get_schema()"
        },
        {
            "name": "Get Specific Tool",
            "description": "Get schema for a specific tool",
            "code": 'tool_schema = await get_schema("create_entity")'
        }
    ]
)
async def get_schema(
    tool_name: Optional[str] = None,
    include_examples: bool = True,
    include_referenced: bool = True
) -> Dict:
    """Get schema information about available tools.
    
    Args:
        tool_name: Optional name of specific tool to get schema for
        include_examples: Whether to include usage examples
        include_referenced: Whether to include referenced model schemas
        
    Returns:
        Complete tool catalog if tool_name is None,
        or specific tool schema if tool_name is provided.
        
    Tool catalog includes:
    - Tool descriptions and purposes
    - Input/output schemas
    - Example usage (if include_examples=True)
    - Referenced Pydantic models (if include_referenced=True)
    - Tool categories
    """
    # Our tool manager has the enhanced schema support
    catalog = mcp._tool_manager.get_schema_catalog()
    
    # Filter if specific tool requested
    if tool_name:
        if tool_name not in catalog["tools"]:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool_schema = catalog["tools"][tool_name]
        
        if not include_examples:
            tool_schema.pop("examples", None)
            
        if include_referenced:
            return {
                "tools": {tool_name: tool_schema},
                "referencedModels": tool_schema.get("referencedModels", {})
            }
        else:
            return {"tools": {tool_name: tool_schema}}
    
    # Return full catalog with requested inclusions
    result = catalog
    
    if not include_examples:
        for tool in result["tools"].values():
            tool.pop("examples", None)
            
    return result