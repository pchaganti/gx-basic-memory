from pathlib import Path
from typing import Optional

from frontmatter import Post

from basic_memory.markdown import EntityMarkdown, EntityFrontmatter, Observation, Relation
from basic_memory.markdown.entity_parser import parse
from basic_memory.models import Entity, ObservationCategory, Observation as ObservationModel
from basic_memory.utils import generate_permalink


def entity_model_to_markdown(entity: Entity, content: Optional[str] = None) -> EntityMarkdown:
    """
    Converts an entity model to its Markdown representation, including metadata,
    observations, relations, and content. Ensures that observations and relations
    from the provided content are synchronized with the entity model. Removes
    duplicate or unmatched observations and relations from the content to maintain
    consistency.

    :param entity: An instance of the Entity class containing metadata, observations,
        relations, and other properties of the entity.
    :type entity: Entity
    :param content: Optional raw Markdown-formatted content to be parsed for semantic
        information like observations or relations.
    :type content: Optional[str]
    :return: An instance of the EntityMarkdown class containing the entity's
        frontmatter, observations, relations, and sanitized content formatted
        in Markdown.
    :rtype: EntityMarkdown
    """
    metadata = entity.entity_metadata or {}
    metadata["permalink"] = entity.permalink
    metadata["type"] = entity.entity_type or "note"
    metadata["title"] = entity.title
    metadata["created"] = entity.created_at
    metadata["modified"] = entity.updated_at

    # convert model to markdown
    entity_observations = [
        Observation(
            category=obs.category,
            content=obs.content,
            tags=obs.tags if obs.tags else None,
            context=obs.context,
        )
        for obs in entity.observations
    ]

    entity_relations = [
        Relation(
            type=r.relation_type,
            target=r.to_entity.title if r.to_entity else r.to_name,
            context=r.context,
        )
        for r in entity.outgoing_relations
    ]

    observations = entity_observations
    relations = entity_relations

    # parse the content to see if it has semantic info (observations/relations)
    entity_content = parse(content) if content else None

    if entity_content:
        # remove if they are already in the content
        observations = [o for o in entity_observations if o not in entity_content.observations]
        relations = [r for r in entity_relations if r not in entity_content.relations]

        # remove from the content if not present in the db entity
        for o in entity_content.observations:
            if o not in entity_observations:
                content = content.replace(str(o), "")

        for r in entity_content.relations:
            if r not in entity_relations:
                content = content.replace(str(r), "")

    return EntityMarkdown(
        frontmatter=EntityFrontmatter(metadata=metadata),
        content=content,
        observations=observations,
        relations=relations,
    )


def entity_model_from_markdown(file_path: Path, markdown: EntityMarkdown, entity: Optional[Entity] = None) -> Entity:
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

    permalink = markdown.frontmatter.permalink or generate_permalink(file_path)
    model = entity or Entity()
    
    model.title=markdown.frontmatter.title or file_path.stem
    model.entity_type=markdown.frontmatter.type
    model.permalink=permalink
    model.file_path=str(file_path)
    model.content_type="text/markdown"
    model.created_at=markdown.created
    model.updated_at=markdown.modified
    model.entity_metadata={k:str(v) for k,v in markdown.frontmatter.metadata.items()}
    model.observations=[
            ObservationModel(
                content=obs.content,
                category=get_valid_category(obs),
                context=obs.context,
                tags=obs.tags,
            )
            for obs in markdown.observations
        ]
    
    return model

async def schema_to_markdown(schema):
    """
    Convert schema to markdown.
    :param schema: the schema to convert 
    :return: Post 
    """
    # Add metadata to dict
    frontmatter_dict = schema.entity_metadata or {}
    
    # set permalink and type
    frontmatter_dict["permalink"] = schema.permalink
    frontmatter_dict["type"] = schema.entity_type
    
    # Create Post object
    content = schema.content or ""
    post = Post(content, **frontmatter_dict)
    return post
