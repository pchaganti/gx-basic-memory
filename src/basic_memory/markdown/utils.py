from typing import Optional

from basic_memory.markdown import EntityMarkdown, EntityFrontmatter, EntityContent, Observation, Relation


class EntityModel:
    pass


def entity_model_to_markdown(entity: EntityModel, content: Optional[str] = None) -> EntityMarkdown:
    """Convert entity model to markdown schema.

    Args:
        entity: Entity model to convert
        content: Optional content to use (falls back to title)

    Returns:
        EntityMarkdown schema
    """
    metadata=entity.entity_metadata or {}
    metadata["permalink"] = entity.permalink
    metadata["type"] = entity.entity_type or "note"
    metadata["title"] = entity.title
    metadata["created"] = entity.created_at
    metadata["modified"] = entity.updated_at
    
    entity_frontmatter = EntityFrontmatter(
        metadata=metadata
    )

    entity_content = EntityContent(
        content=content,  # Use provided content
        observations=[
            Observation(
                category=obs.category, content=obs.content, tags=obs.tags, context=obs.context
            )
            for obs in entity.observations
        ],
        relations=[
            Relation(type=r.relation_type, target=r.to_entity.title, context=r.context) for r in entity.outgoing_relations
        ],
    )

    return EntityMarkdown(
        frontmatter=entity_frontmatter,
        content=entity_content,
    )
