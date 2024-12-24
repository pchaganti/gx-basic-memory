# """Tests for the MCP server implementation using FastAPI TestClient."""
#
# import pytest
#
# from basic_memory.mcp.server import handle_call_tool
# from basic_memory.schemas import SearchNodesResponse, CreateEntityResponse
#
#
# @pytest.mark.asyncio
# async def test_create_relations(app):
#     """Test creating relations between entities."""
#     # Create two test entities
#     entity_data = {
#         "entities": [
#             {"name": "TestEntityA", "entity_type": "test", "observations": ["Entity A"]},
#             {"name": "TestEntityB", "entity_type": "test", "observations": ["Entity B"]},
#         ]
#     }
#
#     create_entity_result = await handle_call_tool("create_entities", entity_data)
#     create_entity_response = CreateEntityResponse.model_validate_json(
#         create_entity_result[0].resource.text  # pyright: ignore [reportAttributeAccessIssue]
#     )
#
#     from_entity = create_entity_response.entities[0]
#     to_entity = create_entity_response.entities[1]
#     # Create relation between them
#     relation_data = {
#         "relations": [
#             {
#                 "from_id": from_entity.id,
#                 "to_id": to_entity.id,
#                 "relation_type": "relates_to",
#             }
#         ]
#     }
#
#     result = await handle_call_tool("create_relations", relation_data)
#
#     # Verify through search
#     search_result = await handle_call_tool("search_nodes", {"query": "TestEntityA"})
#     response = SearchNodesResponse.model_validate_json(search_result[0].resource.text)  # pyright: ignore [reportAttributeAccessIssue]
#
#     assert len(response.matches) == 1
#     entity = response.matches[0]
#     assert len(entity.relations) == 1
#     assert entity.relations[0].to_id == to_entity.id
#     assert entity.relations[0].relation_type == "relates_to"
