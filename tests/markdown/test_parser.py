"""Tests for markdown entity parser."""
import pytest
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from basic_memory.markdown.parser import EntityParser, ParseError

def test_parse_observation():
    """Test parsing individual observation lines."""
    parser = EntityParser()
    
    # Basic observation with category and content
    obs = parser._parse_observation("- [design] Simple observation")
    assert obs.category == "design"
    assert obs.content == "Simple observation"
    assert obs.tags == []
    assert obs.context is None
    
    # Observation with tags
    obs = parser._parse_observation("- [feature] Added search #important #core")
    assert obs.category == "feature"
    assert obs.content == "Added search"
    assert set(obs.tags) == {"important", "core"}
    assert obs.context is None
    
    # Observation with context
    obs = parser._parse_observation('- [design] Core system design #architecture "Initial version"')
    assert obs.category == "design"
    assert obs.content == "Core system design"
    assert obs.tags == ["architecture"]
    assert obs.context == "Initial version"
    
def test_parse_observation_errors():
    """Test error handling in observation parsing."""
    parser = EntityParser()
    
    # Missing category brackets
    with pytest.raises(ParseError, match="missing category"):
        parser._parse_observation("- Design without brackets")
        
    # Unclosed category
    with pytest.raises(ParseError, match="unclosed category"):
        parser._parse_observation("- [design Core system")

def test_parse_relation():
    """Test parsing individual relation lines."""
    parser = EntityParser()
    
    # Basic relation
    rel = parser._parse_relation("- [[EntityA]] #depends_on")
    assert rel.target == "EntityA"
    assert rel.type == "depends_on"
    assert rel.context is None
    
    # Relation with context
    rel = parser._parse_relation('- [[Component]] #implements "Core functionality"')
    assert rel.target == "Component"
    assert rel.type == "implements"
    assert rel.context == "Core functionality"

def test_parse_relation_errors():
    """Test error handling in relation parsing."""
    parser = EntityParser()
    
    # Missing [[ prefix
    with pytest.raises(ParseError, match="missing \\[\\["):
        parser._parse_relation("- EntityA #depends_on")
        
    # Missing ]] suffix
    with pytest.raises(ParseError, match="missing \\]\\]"):
        parser._parse_relation("- [[EntityA #depends_on")
        
    # Missing relation type
    with pytest.raises(ParseError, match="missing relation type"):
        parser._parse_relation("- [[EntityA]] depends_on")

def test_parse_complete_file(tmp_path):
    """Test parsing a complete entity file."""
    content = dedent('''
        ---
        type: concept
        created: 2024-12-21T10:00:00Z
        modified: 2024-12-21T10:00:00Z
        tags: [testing, validation]
        status: active
        version: 1
        priority: high
        ---
        
        # Test Entity
        
        This is a test entity for validation.
        
        ## Description
        A more detailed description of the test entity.
        
        ## Observations
        - [test] First observation #testing
        - [design] Second observation #important "With context"
        
        ## Relations
        - [[EntityA]] #depends_on "Required dependency"
        - [[EntityB]] #implements
        
        ## Context
        Additional context information.
        
        ## Metadata
        schema_version: 1.0
        validation_status: verified
    ''').lstrip()
    
    # Write test file
    test_file = tmp_path / "test_entity.md"
    test_file.write_text(content)
    
    # Parse file
    parser = EntityParser()
    entity = parser.parse_file(test_file)
    
    # Check frontmatter
    assert entity.frontmatter.type == "concept"
    assert entity.frontmatter.tags == ["testing", "validation"]
    assert entity.frontmatter.status == "active"
    assert entity.frontmatter.priority == "high"
    
    # Check content
    assert entity.content.title == "Test Entity"
    assert "detailed description" in entity.content.description
    assert "context information" in entity.content.context
    
    # Check observations
    assert len(entity.content.observations) == 2
    first_obs = entity.content.observations[0]
    assert first_obs.category == "test"
    assert first_obs.content == "First observation"
    assert first_obs.tags == ["testing"]
    
    # Check relations
    assert len(entity.content.relations) == 2
    first_rel = entity.content.relations[0]
    assert first_rel.target == "EntityA"
    assert first_rel.type == "depends_on"
    assert first_rel.context == "Required dependency"
    
    # Check metadata
    assert entity.content.metadata["schema_version"] == "1.0"
    assert entity.content.metadata["validation_status"] == "verified"

def test_parse_missing_file():
    """Test handling of missing files."""
    parser = EntityParser()
    with pytest.raises(ParseError, match="File does not exist"):
        parser.parse_file(Path("nonexistent.md"))

def test_parse_minimal_file(tmp_path):
    """Test parsing a minimal valid entity file."""
    content = dedent('''
        ---
        type: concept
        created: 2024-12-21T10:00:00Z
        modified: 2024-12-21T10:00:00Z
        tags: []
        ---
        
        # Minimal Entity
        
        ## Description
        Minimal valid entity.
    ''').lstrip()
    
    test_file = tmp_path / "minimal.md"
    test_file.write_text(content)
    
    parser = EntityParser()
    entity = parser.parse_file(test_file)
    
    # Check required fields
    assert entity.frontmatter.type == "concept"
    assert isinstance(entity.frontmatter.created, datetime)
    assert entity.content.title == "Minimal Entity"
    
    # Optional fields should have default values
    assert entity.content.observations == []
    assert entity.content.relations == []
    assert entity.content.metadata == {}