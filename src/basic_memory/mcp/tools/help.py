"""Help and schema introspection tools."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from basic_memory.mcp.server import mcp


class ToolExample(BaseModel):
    """Example usage of a tool."""
    name: str = Field(description="Name of the example")
    description: str = Field(description="Description of what the example demonstrates")
    code: str = Field(description="Example code showing how to use the tool")


class ToolSchema(BaseModel):
    """Schema information for a single tool."""
    name: str = Field(description="Name of the tool")
    description: str = Field(description="Description of what the tool does")
    category: Optional[str] = Field(None, description="Optional category for organization")
    input_schema: Dict = Field(description="Schema for tool inputs")
    output_schema: Dict = Field(description="Schema for tool outputs")
    examples: List[ToolExample] = Field(
        default_factory=list,
        description="Example usages of the tool"
    )


class CategoryInfo(BaseModel):
    """Information about a tool category."""
    name: str = Field(description="Category name")
    tools: List[str] = Field(description="Tools in this category")


class SchemaCatalog(BaseModel):
    """Complete schema catalog for all tools."""
    tools: Dict[str, ToolSchema] = Field(
        description="Map of tool names to their schemas"
    )
    categories: Dict[str, CategoryInfo] = Field(
        default_factory=dict,
        description="Tool categories and their tools"
    )
    referenced_models: Dict[str, Dict] = Field(
        default_factory=dict,
        description="Shared type definitions used by tools",
        alias="referencedModels"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "description": "Tool schema catalog showing available tools and their capabilities"
        }


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
    output_model=SchemaCatalog
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
            response = {
                "tools": {tool_name: tool_schema},
                "referencedModels": tool_schema.get("referencedModels", {})
            }
        else:
            response = {"tools": {tool_name: tool_schema}}

        return SchemaCatalog.model_validate(response).model_dump()

    # Return full catalog with requested inclusions
    result = catalog

    if not include_examples:
        for tool in result["tools"].values():
            tool.pop("examples", None)

    return SchemaCatalog.model_validate(result).model_dump()
