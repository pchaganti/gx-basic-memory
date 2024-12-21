"""
Parser for Basic Memory entity markdown files.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter
from markdown_it import MarkdownIt
from pydantic import BaseModel

class ParseError(Exception):
    """Raised when parsing fails"""
    pass

class Observation(BaseModel):
    """An observation about an entity."""
    category: str
    content: str
    tags: List[str]
    context: Optional[str] = None

class Relation(BaseModel):
    """A relation between entities."""
    target: str  # The entity being linked to
    type: str    # The type of relation
    context: Optional[str] = None

class EntityFrontmatter(BaseModel):
    """Frontmatter metadata for an entity."""
    type: str
    created: datetime
    modified: datetime
    tags: List[str]
    status: Optional[str] = None
    version: Optional[int] = None
    priority: Optional[str] = None
    domain: Optional[str] = None
    maturity: Optional[str] = None
    owner: Optional[str] = None
    review_interval: Optional[str] = None
    last_reviewed: Optional[datetime] = None
    confidence: Optional[str] = None
    aliases: Optional[List[str]] = None

class EntityContent(BaseModel):
    """Content sections of an entity markdown file."""
    title: str
    description: Optional[str] = None
    observations: List[Observation] = []
    relations: List[Relation] = []
    context: Optional[str] = None
    metadata: Dict[str, Any] = {}

class Entity(BaseModel):
    """Complete entity combining frontmatter and content."""
    frontmatter: EntityFrontmatter
    content: EntityContent

class EntityParser:
    """Parser for entity markdown files."""
    
    def __init__(self):
        self.md = MarkdownIt()

    def _parse_observation(self, line: str) -> Observation:
        """Parse a single observation line.
        
        Format: - [category] content #tag1 #tag2 "optional context"
        """
        # Remove leading "- " if present
        content = line.strip()
        if content.startswith("- "):
            content = content[2:].strip()
        
        # Extract category
        if not content.startswith("["):
            raise ParseError(f"Invalid observation format, missing category: {line}")
        category_end = content.find("]")
        if category_end == -1:
            raise ParseError(f"Invalid observation format, unclosed category: {line}")
        category = content[1:category_end].strip()
        
        # Remove category from content
        content = content[category_end + 1:].strip()
        
        # Extract tags
        tags = []
        words = content.split()
        filtered_words = []
        for word in words:
            if word.startswith("#"):
                tags.append(word[1:])  # Remove # from tag
            else:
                filtered_words.append(word)
        content = " ".join(filtered_words)
        
        # Extract context if present
        context = None
        if content.endswith('"'):
            last_quote = content.rfind('"')
            second_last_quote = content.rfind('"', 0, last_quote)
            if second_last_quote != -1:
                context = content[second_last_quote + 1:last_quote]
                content = content[:second_last_quote].strip()
        
        return Observation(
            category=category,
            content=content,
            tags=tags,
            context=context
        )

    def _parse_relation(self, line: str) -> Relation:
        """Parse a single relation line.
        
        Format: - [[Entity]] #relation_type "optional context"
        """
        # Remove leading "- " if present
        content = line.strip()
        if content.startswith("- "):
            content = content[2:].strip()
        
        # Extract target
        if not content.startswith("[["):
            raise ParseError(f"Invalid relation format, missing [[ : {line}")
        link_end = content.find("]]")
        if link_end == -1:
            raise ParseError(f"Invalid relation format, missing ]] : {line}")
        target = content[2:link_end].strip()
        
        # Move past ]]
        content = content[link_end + 2:].strip()
        
        # Extract relation type
        if not content.startswith("#"):
            raise ParseError(f"Invalid relation format, missing relation type: {line}")
        
        words = content.split()
        rel_type = words[0][1:]  # Remove # from type
        
        # Extract context if present
        context = None
        remaining = " ".join(words[1:])
        if remaining:
            if remaining.startswith('"') and remaining.endswith('"'):
                context = remaining[1:-1]
        
        return Relation(
            target=target,
            type=rel_type,
            context=context
        )

    def _parse_metadata_line(self, line: str) -> tuple[str, str]:
        """Parse a single metadata line."""
        if ":" not in line:
            return None, None
            
        key, value = line.split(":", 1)
        return key.strip(), value.strip()

    def parse_file(self, path: Path) -> Entity:
        """Parse an entity markdown file."""
        if not path.exists():
            raise ParseError(f"File does not exist: {path}")
            
        try:
            # Parse frontmatter and content
            post = frontmatter.load(path)
            
            # Parse frontmatter
            frontmatter_data = EntityFrontmatter(**post.metadata)
            
            # Parse markdown
            tokens = self.md.parse(post.content)
            
            # Extract title, description, observations, etc
            title = ""
            description = ""
            observations = []
            relations = []
            context = ""
            metadata = {}
            
            current_section = None
            collecting_description = False
            
            for token in tokens:
                if token.type == "heading_open" and token.tag == "h1":
                    # Next token will be title
                    current_section = "title"
                elif token.type == "heading_open" and token.tag == "h2":
                    # Next token will be section name
                    current_section = "section_name"
                    collecting_description = False
                elif token.type == "inline":
                    if current_section == "title":
                        title = token.content
                        current_section = None
                    elif current_section == "section_name":
                        section_name = token.content.lower()
                        if section_name == "description":
                            collecting_description = True
                        current_section = section_name
                    elif collecting_description:
                        description = token.content
                    elif current_section == "observations":
                        if token.content.strip():  # Skip empty lines
                            observations.append(self._parse_observation(token.content))
                    elif current_section == "relations":
                        if token.content.strip():  # Skip empty lines
                            relations.append(self._parse_relation(token.content))
                    elif current_section == "context":
                        context = token.content
                    elif current_section == "metadata":
                        # Process each line of metadata separately
                        for line in token.content.split("\n"):
                            key, value = self._parse_metadata_line(line.strip())
                            if key and value:
                                metadata[key] = value
            
            # Create EntityContent
            content_data = EntityContent(
                title=title,
                description=description,
                observations=observations,
                relations=relations,
                context=context,
                metadata=metadata
            )
            
            # Return complete Entity
            return Entity(
                frontmatter=frontmatter_data,
                content=content_data
            )
            
        except Exception as e:
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e