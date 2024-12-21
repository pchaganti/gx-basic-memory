"""Tests for the markdown entity parser."""
import pytest
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from basic_memory.markdown.parser import EntityParser, ParseError

def test_parse_observation_basic():
    """Test basic observation parsing with category and tags."""
    parser = EntityParser()
    
    obs = parser._parse_observation("- [design] Core feature #important #mvp")
    assert obs.category == "design"
    assert obs.content == "Core feature"
    assert set(obs.tags) == {"important", "mvp"}
    assert obs.context is None

def test_parse_observation_with_context():
    """Test observation parsing with context in parentheses."""
    parser = EntityParser()
    
    obs = parser._parse_observation("- [feature] Authentication system #security #auth (Required for MVP)")
    assert obs.category == "feature"
    assert obs.content == "Authentication system"
    assert set(obs.tags) == {"security", "auth"}
    assert obs.context == "Required for MVP"

def test_parse_observation_edge_cases():
    """Test observation parsing edge cases."""
    parser = EntityParser()
    
    # Multiple word tags
    obs = parser._parse_observation("- [tech] Database #high-priority #needs-review")
    assert set(obs.tags) == {"high-priority", "needs-review"}
    
    # Multiple word category
    obs = parser._parse_observation("- [user experience] Design #ux")
    assert obs.category == "user experience"
    
    # Parentheses in content shouldn't be treated as context
    obs = parser._parse_observation("- [code] Function (x) returns y #function")
    assert obs.content == "Function (x) returns y"
    assert obs.context is None
    
    # Multiple hashtags together
    obs = parser._parse_observation("- [test] Feature #important#urgent#now")
    assert set(obs.tags) == {"important", "urgent", "now"}

def test_parse_observation_errors():
    """Test error handling in observation parsing."""
    parser = EntityParser()
    
    # Missing category brackets
    with pytest.raises(ParseError, match="missing category"):
        parser._parse_observation("- Design without brackets #test")
    
    # Unclosed category
    with pytest.raises(ParseError, match="unclosed category"):
        parser._parse_observation("- [design Core feature #test")

def test_parse_relation_basic():
    """Test basic relation parsing."""
    parser = EntityParser()
    
    rel = parser._parse_relation("- implements [[Auth Service]]")
    assert rel.type == "implements"
    assert rel.target == "Auth Service"
    assert rel.context is None

def test_parse_relation_with_context():
    """Test relation parsing with context."""
    parser = EntityParser()
    
    rel = parser._parse_relation("- depends_on [[Database]] (Required for persistence)")
    assert rel.type == "depends_on"
    assert rel.target == "Database"
    assert rel.context == "Required for persistence"

def test_parse_relation_edge_cases():
    """Test relation parsing edge cases."""
    parser = EntityParser()
    
    # Multiple word type
    rel = parser._parse_relation("- is used by [[Client App]] (Primary consumer)")
    assert rel.type == "is used by"
    
    # Brackets in context
    rel = parser._parse_relation("- implements [[API]] (Follows [OpenAPI] spec)")
    assert rel.context == "Follows [OpenAPI] spec"
    
    # Extra spaces
    rel = parser._parse_relation("-   specifies   [[Format]]   (Documentation)")
    assert rel.type == "specifies"
    assert rel.target == "Format"

def test_parse_relation_errors():
    """Test error handling in relation parsing."""
    parser = EntityParser()
    
    # Missing target brackets
    with pytest.raises(ParseError, match="missing \\[\\["):
        parser._parse_relation("- implements Auth Service")
    
    # Unclosed target
    with pytest.raises(ParseError, match="missing ]]"):
        parser._parse_relation("- implements [[Auth Service")

def test_parse_complete_file(tmp_path):
    """Test parsing a complete entity file."""
    content = dedent('''
        ---
        type: component
        id: component/auth_service
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: authentication, security, core
        status: active
        version: 1
        ---
        
        # Auth Service
        
        Core authentication service.
        
        <!-- Some comments that should be ignored -->
        
        ## Observations
        - [design] Stateless authentication #security #architecture (JWT based)
        - [feature] Mobile client support #mobile #oauth (Required for App Store)
        - [tech] Caching layer #performance (Redis implementation)
        
        ## Relations
        - implements [[OAuth Implementation]] (Core auth flows)
        - uses [[Redis Cache]] (Token caching)
        - specified_by [[Auth API Spec]] (OpenAPI spec)
        
        ## Metadata
        owner: team-auth
        priority: high
        ''')
    
    test_file = tmp_path / "test_entity.md"
    test_file.write_text(content)
    
    parser = EntityParser()
    entity = parser.parse_file(test_file)
    
    # Check frontmatter
    assert entity.frontmatter.type == "component"
    assert entity.frontmatter.id == "component/auth_service"
    assert "authentication" in entity.frontmatter.tags
    assert entity.frontmatter.status == "active"
    
    # Check content
    assert entity.content.title == "Auth Service"
    assert len(entity.content.observations) == 3
    assert len(entity.content.relations) == 3
    
    # Check specific observation
    obs = entity.content.observations[0]
    assert obs.category == "design"
    assert "security" in obs.tags
    assert obs.context == "JWT based"
    
    # Check specific relation
    rel = entity.content.relations[0]
    assert rel.type == "implements"
    assert rel.target == "OAuth Implementation"
    assert rel.context == "Core auth flows"
    
    # Check metadata
    assert entity.content.metadata["owner"] == "team-auth"
    assert entity.content.metadata["priority"] == "high"

def test_parse_minimal_file(tmp_path):
    """Test parsing a minimal valid entity file."""
    content = dedent('''
        ---
        type: component
        id: minimal
        created: 2024-12-21T14:00:00Z
        modified: 2024-12-21T14:00:00Z
        tags: []
        ---
        
        # Minimal Entity
        
        ## Observations
        - [note] Basic observation #test
        
        ## Relations
        - references [[Other Entity]]
    ''')
    
    test_file = tmp_path / "minimal.md"
    test_file.write_text(content)
    
    parser = EntityParser()
    entity = parser.parse_file(test_file)
    
    assert entity.frontmatter.type == "component"
    assert len(entity.content.observations) == 1
    assert len(entity.content.relations) == 1

def test_parse_file_errors(tmp_path):
    """Test error handling for invalid files."""
    parser = EntityParser()
    
    # Missing file
    with pytest.raises(ParseError, match="does not exist"):
        parser.parse_file(Path("nonexistent.md"))
    
    # Invalid frontmatter
    content = dedent('''
        ---
        invalid: yaml: [
        ---
        # Title
    ''')
    test_file = tmp_path / "invalid.md"
    test_file.write_text(content)
    with pytest.raises(ParseError):
        parser.parse_file(test_file)
    
    # Missing required frontmatter
    content = dedent('''
        ---
        type: component
        ---
        # Title
    ''')
    test_file.write_text(content)
    with pytest.raises(ParseError):
        parser.parse_file(test_file)