"""Parser for Basic Memory entity markdown files."""
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter
from markdown_it import MarkdownIt
from pydantic import BaseModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    id: str
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

    def _parse_observation(self, content: str) -> Optional[Observation]:
        """Parse an observation line."""
        try:
            if not content.strip():
                return None

            # Parse category [type]
            match = re.match(r'^\s*(?:-\s*)?\[([^\]]+)\](.*)', content)
            if not match:
                return None
            category = match.group(1).strip()
            content = match.group(2).strip()

            # Parse tags and content
            tags = []
            words = []
            for word in content.split():
                if word.startswith('#'):
                    # Handle #tag1#tag2#tag3
                    for tag in word.lstrip('#').split('#'):
                        if tag:
                            tags.append(tag)
                else:
                    words.append(word)

            content = ' '.join(words)
            
            # Extract context in parentheses
            context = None
            if content.endswith(')'):
                ctx_start = content.rfind('(')
                if ctx_start != -1:
                    context = content[ctx_start + 1:-1].strip()
                    content = content[:ctx_start].strip()

            return Observation(
                category=category,
                content=content,
                tags=tags,
                context=context
            )
        except Exception as e:
            logger.exception("Failed to parse observation: %s", content)
            return None

    def _parse_relation(self, content: str) -> Optional[Relation]:
        """Parse a relation line."""
        try:
            if not content.strip():
                return None

            # Find the link
            match = re.search(r'\[\[([^\]]+)\]\]', content)
            if not match:
                return None
                
            target = match.group(1).strip()
            before_link = content[:match.start()].strip(' -')
            after_link = content[match.end():].strip()
            
            # Everything before the link is the type
            rel_type = before_link.strip()
            if not rel_type:
                return None

            # Check for context in parentheses
            context = None
            if after_link.startswith('(') and after_link.endswith(')'):
                context = after_link[1:-1].strip()

            return Relation(
                target=target,
                type=rel_type,
                context=context
            )
        except Exception as e:
            logger.exception("Failed to parse relation: %s", content)
            return None

    def parse_file(self, path: Path, encoding: str = 'utf-8') -> Entity:
        """Parse an entity markdown file."""
        if not path.exists():
            raise ParseError(f"File does not exist: {path}")
            
        try:
            # Read and parse frontmatter
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
                post = frontmatter.loads(content)
            
            # Handle frontmatter
            metadata = dict(post.metadata)
            if isinstance(metadata.get('tags'), str):
                metadata['tags'] = [t.strip() for t in metadata['tags'].split(',')]
            frontmatter_data = EntityFrontmatter(**metadata)
            
            # Parse markdown
            tokens = self.md.parse(post.content)
            
            # State for parsing
            title = ""
            description = ""
            observations = []
            relations = []
            context = ""
            metadata = {}
            
            current_section = None
            current_list = []
            in_list = False
            
            # Process tokens
            for token in tokens:
                if token.type == 'heading_open':
                    if token.tag == 'h1':
                        current_section = 'title'
                    elif token.tag == 'h2':
                        current_section = 'section_name'
                elif token.type == 'inline':
                    if current_section == 'title':
                        title = token.content
                        current_section = None
                    elif current_section == 'section_name':
                        section = token.content.lower()
                        current_section = section
                        if section in ['observations', 'relations']:
                            in_list = False
                            current_list = []
                    elif current_section == 'description':
                        description = token.content
                    elif current_section == 'observations' and token.content.strip():
                        if obs := self._parse_observation(token.content):
                            observations.append(obs)
                    elif current_section == 'relations' and token.content.strip():
                        if rel := self._parse_relation(token.content):
                            relations.append(rel)
                    elif current_section == 'context':
                        context = token.content
                elif token.type == 'bullet_list_open':
                    in_list = True
                elif token.type == 'bullet_list_close':
                    in_list = False
                    
            # Create entity
            content_data = EntityContent(
                title=title,
                description=description,
                observations=observations,
                relations=relations,
                context=context,
                metadata=metadata
            )
            
            return Entity(
                frontmatter=frontmatter_data,
                content=content_data
            )
            
        except UnicodeError as e:
            if encoding == 'utf-8':
                return self.parse_file(path, encoding='utf-16')
            raise ParseError(f"Failed to read {path} with encoding {encoding}: {str(e)}")
        except Exception as e:
            raise ParseError(f"Failed to parse {path}: {str(e)}") from e