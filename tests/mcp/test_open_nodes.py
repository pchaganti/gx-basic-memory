# """Tests for MCP open_nodes tool."""
#
# import pytest
# from mcp.types import EmbeddedResource
#
# from basic_memory.mcp.server import MIME_TYPE, handle_call_tool
# from basic_memory.schemas import OpenNodesResponse, CreateEntityResponse
#
#
# @pytest.mark.asyncio
# async def test_open_nodes(app):
#     """Test retrieving specific nodes by name."""
#     # Create test entities
#     entity_data = {
#         "entities": [
#             {
#                 "name": "OpenTestA",
#                 "entity_type": "test",
#                 "observations": ["First test entity"],
#             },
#             {
#                 "name": "OpenTestB",
#                 "entity_type": "test",
#                 "observations": ["Second test entity"],
#             },
#             {
#                 "name": "OpenTestC",
#                 "entity_type": "test",
#                 "observations": ["Third test entity"],
#             },
#         ]
#     }
#
#     create_entity_result = await handle_call_tool("create_entities", entity_data)
#     create_entity_response = CreateEntityResponse.model_validate_json(
#         create_entity_result[0].resource.text  # pyright: ignore [reportAttributeAccessIssue]
#     )
#     entity_a = create_entity_response.entities[0]
#     entity_b = create_entity_response.entities[1]
#
#     # Open specific nodes
#     result = await handle_call_tool("open_nodes", {"entity_ids": [entity_a.id, entity_b.id]})
#
#     # Verify response format
#     assert len(result) == 1
#     assert isinstance(result[0], EmbeddedResource)
#     assert result[0].type == "resource"
#     assert result[0].resource.mimeType == MIME_TYPE
#
#     # Verify entities returned
#     response = OpenNodesResponse.model_validate_json(result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
#     assert len(response.entities) == 2
#
#     # Entities should be returned in same order as requested
#     assert response.entities[0].name == "OpenTestA"
#     assert response.entities[1].name == "OpenTestB"
#
#     # Verify entity content
#     entity = response.entities[0]
#     assert entity.id == entity_a.id
#     assert entity.entity_type == "test"
#     assert len(entity.observations) == 1
#     assert entity.observations[0].content == "First test entity"
