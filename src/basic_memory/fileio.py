"""
File I/O operations for basic-memory.
Handles reading and writing entities and observations to the filesystem.
"""
from pathlib import Path

from basic_memory.schemas import Entity, Observation


class FileOperationError(Exception):
    """Raised when file operations fail"""
    pass


class EntityNotFoundError(Exception):
    """Raised when an entity cannot be found"""
    pass


async def write_entity_file(entities_path: Path, entity: Entity) -> bool:
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
        content.append(f"- {obs.content}\n")
    
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


async def read_entity_file(entities_path: Path, entity_id: str) -> Entity:
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
    
    # Parse content sections
    in_observations = False
    for line in content[1:]:  # Skip the title line
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("type: "):
            entity_type = line.replace("type: ", "").strip()
        elif line == "## Observations":
            in_observations = True
        elif in_observations and line.startswith("- "):
            observations.append(Observation(content=line[2:]))
    
    return Entity(
        id=entity_id,
        name=name,
        entity_type=entity_type,
        observations=observations
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