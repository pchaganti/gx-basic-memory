# """Test to show MCP tool documentation."""
#
# import json
# import pytest
# from mcp.types import Tool
# from basic_memory.mcp.server import handle_list_tools
#
#
# @pytest.mark.asyncio
# async def test_list_tools():
#     """List available tools and their documentation."""
#     tools = await handle_list_tools()
#     assert isinstance(tools, list)
#     assert all(isinstance(t, Tool) for t in tools)
#
#     print("\nAvailable MCP Tools:\n")
#
#     # Print each tool's documentation
#     for tool in tools:
#         print(f"Tool: {tool.name}")
#         print(f"Description: {tool.description}")
#         print("Required fields:", tool.inputSchema.get("required", []))
#         print()
#         print("Schema:", json.dumps(tool.inputSchema, indent=2))
#         print("-" * 80 + "\n")
