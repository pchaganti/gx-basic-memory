"""Core pydantic models for basic-memory entities, observations, and relations.

This module defines the foundational data structures for the knowledge graph system.
The graph consists of entities (nodes) connected by relations (edges), where each
entity can have multiple observations (facts) attached to it.

Key Concepts:
1. Entities are nodes with a type and name, storing factual observations
2. Relations are directed edges between entities using active voice verbs
3. Observations are atomic facts/notes about an entity
4. Everything is stored in both SQLite and markdown files
5. Entity IDs are auto-generated as '{type}/{normalized_name}'

Common Entity Types:
- 'person': People (contributors, users, etc.)
- 'project': Major initiatives or repositories
- 'component': Software components/modules
- 'concept': Ideas or abstract concepts
- 'conversation': Chat discussions
- 'document': Documentation or specifications
- 'implementation': Specific code implementations
- 'test': Test suites or test cases

Common Relation Types:
- 'created': Attribution of creation
- 'depends_on': Technical dependency
- 'implements': Implementation of concept/design
- 'documents': Documentation relationship
- 'related_to': General relation
- 'part_of': Compositional relationship
- 'extends': Inheritance/extension
- 'tested_by': Test coverage
"""

import re
from enum import Enum
from typing import List, Optional, Annotated

from annotated_types import MinLen, MaxLen
from pydantic import BaseModel, BeforeValidator


def to_snake_case(name: str) -> str:
    """Convert a string to snake_case.

    Examples:
        BasicMemory -> basic_memory
        Memory Service -> memory_service
        memory-service -> memory_service
        Memory_Service -> memory_service
    """
    name = name.strip()
    
    # Replace spaces and hyphens and . with underscores
    s1 = re.sub(r"[\s\-\\.]", "_", name)

    # Insert underscore between camelCase
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)

    # Convert to lowercase
    return s2.lower()


def validate_path_format(path: str) -> str:
    """Validate path has the correct format: not empty."""
    if not path or not isinstance(path, str):
        raise ValueError("Path must be a non-empty string")

    return path



class ObservationCategory(str, Enum):
    """Categories for structuring observations.

    Categories help organize knowledge and make it easier to find later:
    - tech: Implementation details and technical notes
    - design: Architecture decisions and patterns
    - feature: User-facing capabilities
    - note: General observations (default)
    - issue: Problems or concerns
    - todo: Future work items

    Categories are case-insensitive for easier use.
    """
    TECH = "tech"
    DESIGN = "design"
    FEATURE = "feature"
    NOTE = "note"
    ISSUE = "issue"
    TODO = "todo"

    @classmethod
    def _missing_(cls, value: str) -> "ObservationCategory":
        """Handle case-insensitive lookup."""
        try:
            return cls(value.lower())
        except ValueError:
            return None
        
        
PathId = Annotated[str, BeforeValidator(to_snake_case), BeforeValidator(validate_path_format)]
"""Unique identifier in format '{path}/{normalized_name}'."""

Observation = Annotated[
    str, 
    BeforeValidator(str.strip),  # Clean whitespace
    MinLen(1),  # Ensure non-empty after stripping
    MaxLen(1000)  # Keep reasonable length
]
"""A single piece of information about an entity. Must be non-empty and under 1000 characters.

Best Practices:
- Keep observations atomic (one fact per observation)
- Use clear, complete sentences
- Include context when relevant
- Avoid duplicating information

Examples:
- "Implements SQLite storage for persistence"
- "Created on December 10, 2024"
- "Depends on SQLAlchemy for database operations"
"""

EntityType = Annotated[str, BeforeValidator(to_snake_case), MinLen(1), MaxLen(200)]
"""Classification of entity (e.g., 'person', 'project', 'concept'). 

The type serves multiple purposes:
1. Organizes entities in the filesystem
2. Enables filtering and querying
3. Provides context for relations
4. Helps generate meaningful IDs

Common types are listed in the module docstring.
"""

RelationType = Annotated[str, BeforeValidator(to_snake_case), MinLen(1), MaxLen(200)]
"""Type of relationship between entities. Always use active voice present tense.

Guidelines:
1. Use verbs that clearly describe the relationship
2. Keep it concise but unambiguous
3. Consider bidirectional meaning
4. Use established types when possible

Common types are listed in the module docstring.
"""


class Relation(BaseModel):
    """Represents a directed edge between entities in the knowledge graph.

    Relations are directed connections stored in active voice (e.g., "created", "depends_on").
    The from_id represents the source or actor entity, while to_id represents the target
    or recipient entity.

    Example Relations:
    1. Person creates Project:
       {
           "from_id": "person/alice",
           "to_id": "project/basic_memory",
           "relation_type": "created"
       }

    2. Component depends on another:
       {
           "from_id": "component/memory_service",
           "to_id": "component/database_service",
           "relation_type": "depends_on"
       }

    3. Test validates Implementation:
       {
           "from_id": "test/memory_service_test",
           "to_id": "implementation/memory_service",
           "relation_type": "validates"
       }

    4. Document describes Component:
       {
           "from_id": "document/architecture_spec",
           "to_id": "component/memory_service",
           "relation_type": "describes"
       }
    """

    from_id: PathId
    to_id: PathId
    relation_type: RelationType
    context: Optional[str] = None


class Entity(BaseModel):
    """Represents a node in our knowledge graph - could be a person, project, concept, etc.

    Each entity has:
    - A unique name (used to generate its ID)
    - An entity type (for classification)
    - A list of observations (facts/notes about the entity)
    - Optional relations to other entities
    - Optional description for high-level overview

    Example Entities:

    1. Project Entity:
    {
        "name": "BasicMemory",
        "entity_type": "project",
        "description": "Knowledge graph system for AI-human collaboration",
        "observations": [
            "Uses SQLite for local-first storage",
            "Implements MCP protocol for AI interaction",
            "Provides markdown file sync"
        ]
    }

    2. Component Entity:
    {
        "name": "MemoryService",
        "entity_type": "component",
        "description": "Core service managing knowledge persistence",
        "observations": [
            "Handles both file and database operations",
            "Implements entity lifecycle management",
            "Uses SQLAlchemy for database access"
        ]
    }

    3. Person Entity:
    {
        "name": "Alice_Smith",
        "entity_type": "person",
        "description": "Lead developer on Basic Memory project",
        "observations": [
            "Focuses on knowledge graph implementation",
            "Created initial SQLite integration"
        ]
    }

    4. Concept Entity:
    {
        "name": "Semantic_Search",
        "entity_type": "concept",
        "description": "Advanced search capabilities in knowledge graphs",
        "observations": [
            "Uses embeddings for semantic matching",
            "Enables natural language queries",
            "Planned for future implementation"
        ]
    }
    """

    name: str
    entity_type: EntityType
    description: Optional[str] = None
    observations: List[Observation] = []

    @property
    def path_id(self) -> PathId:
        """Get the path ID in format {type}/{snake_case_name}."""
        normalized_name = to_snake_case(self.name)
        return f"{self.entity_type}/{normalized_name}"
