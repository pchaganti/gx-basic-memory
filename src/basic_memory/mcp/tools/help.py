"""Help and schema introspection tools."""

from typing import Dict, Optional

from basic_memory.mcp.server import mcp


@mcp.tool(
    category="system",
    description="""
    Get schema information about available tools.
    
    This tool provides access to the MCP schema catalog, showing:
    - Available tools and their capabilities
    - Input/output type definitions
    - Example usage patterns
    - Related schema models
    
    You can:
    - Get the full tool catalog
    - Look up specific tools
    - Control example inclusion
    - Access referenced models
    
    The schema information helps understand tool capabilities
    and ensure correct usage.
    """,
    examples=[
        {
            "name": "View All Tools",
            "description": "Get complete schema catalog",
            "code": """
# Get full tool catalog
catalog = await get_schema()

# Show available tools by category
for category, info in catalog['categories'].items():
    print(f"\\n{category.title()}:")
    for tool in info['tools']:
        print(f"- {tool}")
"""
        },
        {
            "name": "Tool Details",
            "description": "Examine specific tool schema",
            "code": """
# Get schema for create_entities
tool = await get_schema(
    tool_name="create_entities",
    include_referenced=True  # Include type definitions
)

# Show input/output types
print("Inputs:")
for param, info in tool['tools']['create_entities']['inputSchema']['properties'].items():
    print(f"- {param}: {info.get('description', '')}")

print("\\nOutput:")
print(tool['tools']['create_entities']['outputSchema']['description'])
"""
        },
        {
            "name": "Simple Schema",
            "description": "Get minimal schema without examples",
            "code": """
# Get core schema without examples
schema = await get_schema(
    include_examples=False,
    include_referenced=False
)

# List available tools
tools = list(schema['tools'].keys())
print("Available tools:")
for tool in sorted(tools):
    print(f"- {tool}")
"""
        }
    ],
    output_schema={
        "description": "Tool schema catalog",
        "properties": {
            "tools": {
                "type": "object",
                "description": "Map of tool names to their schemas",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "category": {"type": "string"},
                        "inputSchema": {"type": "object"},
                        "outputSchema": {"type": "object"},
                        "examples": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "code": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            },
            "categories": {
                "type": "object",
                "description": "Tool categories and their tools",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "tools": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "referencedModels": {
                "type": "object",
                "description": "Shared type definitions",
                "additionalProperties": {"type": "object"}
            }
        }
    }
)
async def get_schema(
    tool_name: Optional[str] = None, 
    include_examples: bool = True, 
    include_referenced: bool = True
) -> Dict:
    """Get schema information about available tools."""
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