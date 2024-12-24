# """Tests for the MCP server implementation using FastAPI TestClient."""
#
# import pytest
# from mcp.types import EmbeddedResource
#
# from basic_memory.mcp.server import MIME_TYPE, handle_call_tool
# from basic_memory.schemas import SearchNodesResponse
#
#
# @pytest.mark.asyncio
# async def test_search_nodes(app, test_entity_data, client):
#     """Test searching for an entity after creating it."""
#
#     # First create an entity
#     await handle_call_tool("create_entities", test_entity_data)
#
#     # Then search for it
#     result = await handle_call_tool("search_nodes", {"query": "Test Entity"})
#
#     # Verify response format
#     assert len(result) == 1
#     assert isinstance(result[0], EmbeddedResource)
#     assert result[0].type == "resource"
#     assert result[0].resource.mimeType == MIME_TYPE
#
#     # Verify search results
#     response = SearchNodesResponse.model_validate_json(result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
#     assert len(response.matches) == 1
#     assert response.matches[0].name == "Test Entity"
#     assert response.query == "Test Entity"
#
#     # Verify through API
#     api_response = await client.post("/knowledge/search", json={"query": "Test Entity"})
#     assert api_response.status_code == 200
#     data = api_response.json()
#     assert len(data["matches"]) == 1
#     assert data["matches"][0]["name"] == "Test Entity"
