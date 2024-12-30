"""Tests for MCP schema and tool discovery."""

import pytest
from pydantic import BaseModel
from typing import List, Optional

from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.enhanced import enhanced_tool, EnhancedToolMetadata, ToolExample
from basic_memory.mcp.tools.help import get_schema


class TestInput(BaseModel):
    """Test input model."""
    name: str
    value: int


class TestOutput(BaseModel):
    """Test output model."""
    result: str
    values: List[int]


# Create the enhanced metadata explicitly
test_metadata = EnhancedToolMetadata(
    name="test_tool",
    description="A test tool with enhanced metadata",
    category="test",
    examples=[
        ToolExample(
            name="Basic Usage",
            description="Simple example",
            code="await test_tool({\"name\": \"test\", \"value\": 42})"
        )
    ]
)

# Test tool with enhanced metadata
@enhanced_tool(
    name="test_tool",
    description="A test tool with enhanced metadata",
    category="test",
    examples=[{
        "name": "Basic Usage",
        "description": "Simple example",
        "code": "await test_tool({\"name\": \"test\", \"value\": 42})"
    }]
)
async def test_tool(request: TestInput) -> TestOutput:
    """Test tool."""
    # Add metadata directly
    setattr(test_tool, "_enhanced_metadata", test_metadata)
    return TestOutput(
        result=f"Processed {request.name}",
        values=[request.value]
    )


# Test basic tool without enhancements
@mcp.tool(name="basic_tool")
async def basic_tool(value: str) -> str:
    """A basic tool without enhanced metadata"""
    return f"Echo: {value}"


@pytest.mark.asyncio
async def test_get_schema_all():
    """Test getting complete tool catalog."""
    catalog = await get_schema()
    
    assert "tools" in catalog
    assert "test_tool" in catalog["tools"]
    assert "basic_tool" in catalog["tools"]


@pytest.mark.asyncio
async def test_get_schema_enhanced_tool():
    """Test getting schema for enhanced tool."""
    schema = await get_schema("test_tool")
    
    assert "tools" in schema
    assert "test_tool" in schema["tools"]
    
    tool_info = schema["tools"]["test_tool"]
    assert tool_info["category"] == "test"
    assert len(tool_info["examples"]) == 1
    assert tool_info["inputSchema"] is not None


@pytest.mark.asyncio
async def test_get_schema_basic_tool():
    """Test getting schema for basic tool."""
    schema = await get_schema("basic_tool")
    
    assert "tools" in schema
    assert "basic_tool" in schema["tools"]
    
    tool_info = schema["tools"]["basic_tool"]
    assert tool_info["name"] == "basic_tool"
    assert tool_info["description"] == "A basic tool without enhanced metadata"
    assert "inputSchema" in tool_info


@pytest.mark.asyncio
async def test_get_schema_unknown_tool():
    """Test getting schema for unknown tool."""
    with pytest.raises(ValueError, match="Unknown tool: unknown_tool"):
        await get_schema("unknown_tool")