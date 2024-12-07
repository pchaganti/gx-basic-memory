from mcp.server import Server
from mcp.types import Tool, Prompt, GetPromptResult, PromptArgument
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..services.memory_service import MemoryService

class MemoryServer(Server):
    """MCP server implementation for basic-memory."""
    
    def __init__(self):
        self.memory_service: Optional[MemoryService] = None
        
    async def get_project_prompt(self) -> GetPromptResult:
        """Prompt to select which project to work with."""
        return GetPromptResult(
            prompt=Prompt(
                name="project",
                description="Select a project to work with",
                arguments=[
                    PromptArgument(
                        name="project_name", 
                        description="Name of the project to load"
                    )
                ]
            )
        )

    async def initialize_project(self, project_name: str) -> None:
        """Initialize the memory service for a specific project."""
        project_path = Path.home() / ".basic-memory" / "projects" / project_name
        self.memory_service = MemoryService(project_path)

    async def ensure_initialized(self) -> None:
        """Ensure we have an initialized memory service."""
        if not self.memory_service:
            project = await self.get_project_prompt()
            await self.initialize_project(project.prompt.arguments[0].value)

    async def create_entities(self, entities: List[Dict[str, Any]]) -> Tool:
        """Create new entities in the knowledge graph."""
        await self.ensure_initialized()
        result = await self.memory_service.create_entities(entities)
        return [entity.model_dump() for entity in result]

    async def create_relations(self, relations: List[Dict[str, Any]]) -> Tool:
        """Create new relations between entities."""
        await self.ensure_initialized()
        result = await self.memory_service.create_relations(relations)
        return [relation.model_dump() for relation in result]

    async def add_observations(self, observations: List[Dict[str, Any]]) -> Tool:
        """Add observations to existing entities."""
        await self.ensure_initialized()
        await self.memory_service.add_observations(observations)
        return {"status": "success"}

    async def delete_entities(self, entity_names: List[str]) -> Tool:
        """Delete entities from the knowledge graph."""
        await self.ensure_initialized()
        await self.memory_service.delete_entities(entity_names)
        return {"status": "success"}

    async def delete_observations(self, deletions: List[Dict[str, Any]]) -> Tool:
        """Delete specific observations from entities."""
        await self.ensure_initialized()
        await self.memory_service.delete_observations(deletions)
        return {"status": "success"}

    async def delete_relations(self, relations: List[Dict[str, Any]]) -> Tool:
        """Delete specific relations between entities."""
        await self.ensure_initialized()
        await self.memory_service.delete_relations(relations)
        return {"status": "success"}

    async def read_graph(self) -> Tool:
        """Read the entire knowledge graph."""
        await self.ensure_initialized()
        return await self.memory_service.read_graph()

    async def search_nodes(self, query: str) -> Tool:
        """Search for nodes in the knowledge graph."""
        await self.ensure_initialized()
        return await self.memory_service.search_nodes(query)

    async def open_nodes(self, names: List[str]) -> Tool:
        """Get specific nodes and their relationships."""
        await self.ensure_initialized()
        return await self.memory_service.open_nodes(names)

if __name__ == "__main__":
    server = MemoryServer()
    server.run()