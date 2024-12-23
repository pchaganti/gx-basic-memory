"""Tests for the markdown entity parser."""

import pytest

from basic_memory.markdown.knowledge_parser import KnowledgeParser, ParseError


@pytest.mark.asyncio
async def test_parse_relation_basic():
    """Test basic relation parsing."""
    parser = KnowledgeParser()

    rel = await parser.parse_relation("- implements [[Auth Service]]")
    assert rel is not None
    assert rel.type == "implements"
    assert rel.target == "Auth Service"
    assert rel.context is None


@pytest.mark.asyncio
async def test_parse_relation_with_context():
    """Test relation parsing with context."""
    parser = KnowledgeParser()

    rel = await parser.parse_relation("- depends_on [[Database]] (Required for persistence)")
    assert rel is not None
    assert rel.type == "depends_on"
    assert rel.target == "Database"
    assert rel.context == "Required for persistence"


@pytest.mark.asyncio
async def test_parse_relation_edge_cases():
    """Test relation parsing edge cases."""
    parser = KnowledgeParser()

    # Multiple word type
    rel = await parser.parse_relation("- is used by [[Client App]] (Primary consumer)")
    assert rel is not None
    assert rel.type == "is used by"

    # Brackets in context
    rel = await parser.parse_relation("- implements [[API]] (Follows [OpenAPI] spec)")
    assert rel is not None
    assert rel.context == "Follows [OpenAPI] spec"

    # Extra spaces
    rel = await parser.parse_relation("-   specifies   [[Format]]   (Documentation)")
    assert rel is not None
    assert rel.type == "specifies"
    assert rel.target == "Format"


@pytest.mark.asyncio
async def test_parse_relation_errors():
    """Test error handling in relation parsing."""
    parser = KnowledgeParser()

    # Missing target brackets
    with pytest.raises(ParseError, match="missing \\[\\["):
        await parser.parse_relation("- implements Auth Service")

    # Unclosed target
    with pytest.raises(ParseError, match="Invalid relation format - missing \\[\\[entity\\]\\]"):
        await parser.parse_relation("- implements [[Auth Service")
