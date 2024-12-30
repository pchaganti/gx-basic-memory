"""Help and schema tools for Basic Memory MCP server."""

from typing import Optional, Dict, List
import inspect

from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.enhanced import EnhancedToolMetadata


def get_tool_metadata(tool) -> Optional[EnhancedToolMetadata]:
    """Get enhanced tool metadata if available."""
    # Try to get metadata directly from tool
    if hasattr(tool, "_enhanced_metadata"):
        return getattr(tool, "_enhanced_metadata")
    return None


@mcp.tool()
async def get_schema(tool_name: Optional[str] = None) -> Dict:
    """Get schema information about available tools.
    
    Returns complete tool catalog if tool_name is None,
    or specific tool schema if tool_name is provided.
    
    Tool catalog includes:
    - Tool descriptions and purposes
    - Input/output schemas
    - Example usage
    - Referenced Pydantic models
    
    Examples:
        # Get complete tool catalog
        catalog = await get_schema()
        
        # Get schema for specific tool
        entity_tool = await get_schema("create_entities")
    """
    # Build catalog from enhanced tools
    catalog = {"tools": {}, "schemas": {}}
    
    # Get all tools
    tools = await mcp.list_tools()
    
    for tool in tools:
        # Get enhanced metadata if available
        metadata = get_tool_metadata(tool)
        if metadata:
            catalog["tools"][tool.name] = {
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category,
                "examples": [ex.model_dump() for ex in metadata.examples],
                "inputSchema": metadata.input_schema,
                "outputSchema": metadata.output_schema,
            }
        else:
            # Basic metadata for non-enhanced tools
            model_data = tool.model_dump()
            catalog["tools"][tool.name] = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": model_data.get("inputSchema", {})
            }

    if tool_name:
        if tool_name not in catalog["tools"]:
            raise ValueError(f"Unknown tool: {tool_name}")
        return {"tools": {tool_name: catalog["tools"][tool_name]}}

    return catalog