"""
File I/O operations for basic-memory.
Handles reading and writing entities and observations to the filesystem.
"""
from pathlib import Path

from basic_memory.schemas import EntityIn, ObservationIn, RelationIn


class FileOperationError(Exception):
    """Raised when file operations fail"""
    pass


class EntityNotFoundError(Exception):
    """Raised when an entity cannot be found"""
    pass


async def write_entity_file(entities_path: Path, entity: EntityIn) -> bool:
    """
    Write entity to filesystem in markdown format.
    
    Args:
        entities_path: Path to entities directory
        entity: Entity to write
        
    Returns:
        True if successful
        
    Raises:
        FileOperationError: If file operations fail
    """
    entity_path = entities_path / f"{entity.id}.md"
    
    # Handle directory creation separately
    try:
        entity_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise FileOperationError(f"Failed to create entity directory: {str(e)}") from e

    # Format entity data as markdown
    content = [
        f"# {entity.name}\n",
        f"type: {entity.entity_type}\n",
        "\n",  # Observations section
        "## Observations\n",
    ]

    # Add observations
    for obs in entity.observations:
        obs_line = f"- {obs.content}"
        if obs.context:
            obs_line += f" | {obs.context}"
        content.append(f"{obs_line}\n")
        
    # Add relations section if we have relations
    if hasattr(entity, 'relations') and entity.relations:
        content.extend([
            "\n",  # Blank line before relations
            "## Relations\n"
        ])
        # Use model_dump to get proper storage format
        for rel in entity.relations:
            rel_data = rel.model_dump()
            relation_line = f"- [{rel_data['to_id']}] {rel_data['relation_type']}"
            if rel_data.get('context'):
                relation_line += f" | {rel_data['context']}"
            content.append(f"{relation_line}\n")
    
    # Handle atomic write operation
    temp_path = entity_path.with_suffix('.tmp')
    try:
        temp_path.write_text("".join(content))
    except Exception as e:
        raise FileOperationError(f"Failed to write temporary entity file: {str(e)}") from e

    try:
        temp_path.rename(entity_path)
    except Exception as e:
        raise FileOperationError(f"Failed to finalize entity file: {str(e)}") from e
        
    return True


async def read_entity_file(entities_path: Path, entity_id: str) -> EntityIn:
    """
    Read entity data from filesystem.
    
    Args:
        entities_path: Path to entities directory
        entity_id: ID of entity to read
        
    Returns:
        Entity object
        
    Raises:
        EntityNotFoundError: If entity file doesn't exist
        FileOperationError: If file operations fail
    """
    entity_path = entities_path / f"{entity_id}.md"
    if not entity_path.exists():
        raise EntityNotFoundError(f"Entity file not found: {entity_id}")
    
    try:
        content = entity_path.read_text().split("\n")
    except Exception as e:
        raise FileOperationError(f"Failed to read entity file: {str(e)}") from e
            
    # Parse markdown content
    # First line should be "# Name"
    name = content[0].lstrip("# ").strip()
    
    # Parse metadata (type)
    entity_type = ""
    observations = []
    relations = []
    
    # Parse content sections
    in_observations = False
    in_relations = False
    
    for line in content[1:]:  # Skip the title line
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("type: "):
            entity_type = line.replace("type: ", "").strip()
        elif line == "## Observations":
            in_observations = True
            in_relations = False
        elif line == "## Relations":
            in_observations = False
            in_relations = True
        elif in_observations and line.startswith("- "):
            # Parse observation line: content | context
            line = line[2:]  # Remove the "- "
            parts = line.split(" | ", 1)
            content = parts[0]
            context = parts[1] if len(parts) > 1 else None
            observations.append(ObservationIn(content=content, context=context))
        elif in_relations and line.startswith("- "):
            # Parse relation line: - [target_id] relation_type | context
            line = line[2:]  # Remove the bullet point
            if "] " not in line:
                continue  # Skip malformed lines
                
            # Split on the first "] " to separate ID from relation_type
            id_part, rest = line.split("] ", 1)
            target_id = id_part[1:]  # Remove leading [
            
            # Split rest on " | " if there's a context
            parts = rest.split(" | ", 1)
            relation_type = parts[0]
            context = parts[1] if len(parts) > 1 else None
            
            # Create temporary entities for the relation
            # TODO what is this for?
            target_entity = EntityIn(id=target_id, name=target_id, entity_type="unknown")
            source_entity = EntityIn(id=entity_id, name=name, entity_type=entity_type)
            
            relations.append(RelationIn(
                from_id=source_entity.id,
                to_id=target_entity.id,
                relation_type=relation_type,
                context=context
            ))
    
    return EntityIn(
        id=entity_id,
        name=name,
        entity_type=entity_type,
        observations=observations,
        relations=relations
    )


async def delete_entity_file(entities_path: Path, entity_id: str) -> bool:
    """
    Delete an entity's file from the filesystem.
    
    Args:
        entities_path: Path to entities directory
        entity_id: ID of entity to delete
        
    Returns:
        True if successful or file didn't exist
        
    Raises:
        FileOperationError: If file deletion fails
    """
    entity_path = entities_path / f"{entity_id}.md"
    
    if entity_path.exists():
        try:
            entity_path.unlink()
        except Exception as e:
            raise FileOperationError(f"Failed to delete entity file: {str(e)}") from e
    
    return True