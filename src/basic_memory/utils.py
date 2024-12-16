"""Utility functions for basic-memory."""

def normalize_entity_id(entity_id: str) -> str:
    """
    Normalize an entity ID by converting to lowercase and replacing spaces with underscores.
    
    Args:
        entity_id: Raw entity ID to normalize
        
    Returns:
        Normalized entity ID suitable for filesystem and database use
    """
    return entity_id.lower().replace(" ", "_")