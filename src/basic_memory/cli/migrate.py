"""Migration tools for basic-memory"""
import json
import asyncio
from typing import List
from pathlib import Path
import typer
from basic_memory.mcp.server import get_project_services
from basic_memory.config import ProjectConfig
from basic_memory.schemas import EntityIn, ObservationIn, RelationIn

app = typer.Typer()

class Migrator:
    def __init__(self, memory_service):
        self.memory_service = memory_service
        self.entity_map = {}  # name -> id mapping
        
    async def migrate_entities(self, entity_data_list: List[dict]):
        """Migrate all entities at once"""
        entities_in = [
            EntityIn(
                name=entity['name'],
                entity_type=entity['entityType'],
                observations=[
                    ObservationIn(content=obs)
                    for obs in entity['observations']
                ]
            ) 
            for entity in entity_data_list
        ]
        
        entities = await self.memory_service.create_entities(entities_in)
        
        # Track IDs for relations
        for entity in entities:
            self.entity_map[entity.name] = entity.id
            
        return entities

    async def migrate_relations(self, relation_data_list: List[dict]):
        """Create all relations at once"""
        relations_in = []
        
        for rel in relation_data_list:
            # Extract source/target IDs handling different formats
            from_id = rel.get('from') or rel.get('from_id')
            to_id = rel.get('to') or rel.get('to_id')
            relation_type = rel.get('relationType') or rel.get('relation_type')
            
            if from_id and to_id and relation_type:
                if from_id in self.entity_map and to_id in self.entity_map:
                    relations_in.append(
                        RelationIn(
                            fromId=self.entity_map[from_id],
                            toId=self.entity_map[to_id],
                            relationType=relation_type
                        )
                    )
                else:
                    typer.echo(f"Skipping relation - missing entities: {from_id} -> {to_id}")
                    
        return await self.memory_service.create_relations(relations_in)

@app.command()
def migrate_json(
    json_path: Path = typer.Argument(..., help="Path to JSON memory store file"),
    project_path: Path = typer.Argument(..., help="Path to basic-memory project"),
):
    """Migrate data from JSON memory store to basic-memory"""
    async def run_migration():
        config = ProjectConfig(path=project_path)
        async with get_project_services(config.path) as service:
            migrator = Migrator(service)
            
            # Load JSONL data line by line
            typer.echo(f"Loading data from {json_path}")
            entities = []
            relations = []
            with open(json_path) as f:
                for line in f:
                    if line.strip():  # Skip empty lines
                        item = json.loads(line)
                        if item['type'] == 'entity':
                            entities.append(item)
                        elif item['type'] == 'relation':
                            relations.append(item)
            
            # Create all entities in parallel
            typer.echo(f"Migrating {len(entities)} entities...")
            result = await migrator.migrate_entities(entities)
            typer.echo(f"Migrated {len(result)} entities")
            
            # Create all relations in parallel
            typer.echo(f"Migrating {len(relations)} relations...")
            result = await migrator.migrate_relations(relations)
            typer.echo(f"Migrated {len(result)} relations")

    asyncio.run(run_migration())

if __name__ == "__main__":
    app()