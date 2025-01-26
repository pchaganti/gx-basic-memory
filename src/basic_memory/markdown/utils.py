from pathlib import Path
from typing import Optional

from basic_memory.markdown import EntityMarkdown, EntityFrontmatter, Observation, Relation
from basic_memory.markdown.entity_parser import parse
from basic_memory.models import Entity, ObservationCategory, Observation as ObservationModel
from basic_memory.utils import generate_permalink


def entity_model_to_markdown(entity: Entity, content: Optional[str] = None) -> EntityMarkdown:
    """Convert entity model to markdown schema.

    Args:
        entity: Entity model to convert
        content: Optional content to use (falls back to title)

    Returns:
        EntityMarkdown schema
    """
    metadata = entity.entity_metadata or {}
    metadata["permalink"] = entity.permalink
    metadata["type"] = entity.entity_type or "note"
    metadata["title"] = entity.title
    metadata["created"] = entity.created_at
    metadata["modified"] = entity.updated_at

    observations = [
        Observation(category=obs.category, content=obs.content, tags=obs.tags, context=obs.context)
        for obs in entity.observations
    ]

    relations = [
        Relation(type=r.relation_type, target=r.to_entity.title, context=r.context)
        for r in entity.outgoing_relations
    ]

    # parse the content to see if it has semantic info (observations/relations)
    entity_content = parse(content) if content else None
    if entity_content:
        # remove duplicates by comparing to values in content
        observations = [
            o
            for o in observations
            if Observation(
                category=o.category,
                content=o.content,
                tags=o.tags if o.tags else None,
                context=o.context,
            )
            not in entity_content.observations
        ]

        relations = [
            r
            for r in relations
            if Relation(type=r.type, target=r.target, context=r.context)
            not in entity_content.relations
        ]

    return EntityMarkdown(
        frontmatter=EntityFrontmatter(metadata=metadata),
        content=content,
        observations=observations,
        relations=relations,
    )


def entity_model_from_markdown(file_path: str, markdown: EntityMarkdown) -> Entity:
    """
    Convert markdown entity to model.
    Does not include relations.

    Args:
        markdown: Parsed markdown entity
        include_relations: Whether to include relations. Set False for first sync pass.
    """

    # Validate/default category
    def get_valid_category(obs):
        if not obs.category or obs.category not in [c.value for c in ObservationCategory]:
            return ObservationCategory.NOTE.value
        return obs.category

    # TODO handle permalink conflicts
    permalink = markdown.frontmatter.permalink or generate_permalink(file_path)
    model = Entity(
        title=markdown.frontmatter.title or Path(file_path).stem,
        entity_type=markdown.frontmatter.type,
        permalink=permalink,
        file_path=file_path,
        content_type="text/markdown",
        created_at=markdown.frontmatter.created,
        updated_at=markdown.frontmatter.modified,
        observations=[
            ObservationModel(
                content=obs.content,
                category=get_valid_category(obs),
                context=obs.context,
                tags=obs.tags,
            )
            for obs in markdown.observations
        ],
    )
    return model
