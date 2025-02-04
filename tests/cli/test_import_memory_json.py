"""Test import-json command functionality."""

import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from basic_memory.cli.commands.import_memory_json import process_memory_json
from basic_memory.markdown import EntityParser, MarkdownProcessor


@pytest.fixture
def console():
    """Create test console that captures output."""
    output = StringIO()
    return Console(file=output), output


@pytest.fixture
def sample_memory_json(tmp_path) -> Path:
    """Create a sample memory.json file with test data."""
    json_path = tmp_path / "memory.json"
    
    # Create test data modeling the real format
    test_data = [
        {
            "type": "entity",
            "name": "Basic_Memory",
            "entityType": "software_system",
            "observations": [
                "A core component of Basic Machines",
                "Local-first knowledge management system",
                "Combines filesystem persistence with graph-based knowledge representation"
            ]
        },
        {
            "type": "entity",
            "name": "Basic_Machines",
            "entityType": "project",
            "observations": [
                "Local-first knowledge management system",
                "Focuses on enhancing human agency and understanding",
                "Current focus includes basic-memory system"
            ]
        },
        {
            "type": "relation",
            "from": "Basic_Memory",
            "to": "Basic_Machines",
            "relationType": "is_component_of"
        }
    ]
    
    # Write each item as a JSON line
    with open(json_path, 'w') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')
    
    return json_path



@pytest.mark.asyncio
async def test_process_memory_json(
    sample_memory_json: Path,
    markdown_processor: MarkdownProcessor,
    test_config,
):
    """Test importing from memory.json format."""
    # Process the import
    results = await process_memory_json(sample_memory_json, test_config.home, markdown_processor)
    
    # Check results
    assert results["entities"] == 2
    assert results["relations"] == 1
    
    # Verify Basic_Memory entity file was created correctly
    basic_memory_path = test_config.home / "software_system/Basic_Memory.md"
    entity = await markdown_processor.read_file(basic_memory_path)
    
    assert entity.frontmatter.title == "Basic_Memory"
    assert entity.frontmatter.type == "software_system"
    assert len(entity.observations) == 3
    assert len(entity.relations) == 1  # Should have the outgoing relation
    assert entity.relations[0].type == "is_component_of"
    assert entity.relations[0].target == "Basic_Machines"
    
    # Verify Basic_Machines entity file
    basic_machines_path = test_config.home / "project/Basic_Machines.md"
    entity = await markdown_processor.read_file(basic_machines_path)
    
    assert entity.frontmatter.title == "Basic_Machines"
    assert entity.frontmatter.type == "project"
    assert len(entity.observations) == 3
    assert len(entity.relations) == 0  # No outgoing relations


@pytest.mark.asyncio
async def test_process_memory_json_empty_observations(
    tmp_path: Path,
    markdown_processor: MarkdownProcessor,
    test_config,
):
    """Test handling entities with no observations."""
    # Create test data
    json_path = tmp_path / "memory.json"
    test_data = [
        {
            "type": "entity",
            "name": "Empty_Entity",
            "entityType": "test",
            "observations": []  # Empty observations
        }
    ]
    
    with open(json_path, 'w') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')
    
    # Process import
    results = await process_memory_json(json_path, test_config.home, markdown_processor)
    
    # Check results
    assert results["entities"] == 1
    assert results["relations"] == 0
    
    # Verify file was created
    entity_path = test_config.home / "test/Empty_Entity.md"
    entity = await markdown_processor.read_file(entity_path)
    
    assert entity.frontmatter.title == "Empty_Entity"
    assert entity.observations == []
    assert entity.relations == []


@pytest.mark.asyncio
async def test_process_memory_json_special_characters(
    tmp_path: Path,
    markdown_processor: MarkdownProcessor,
    test_config,
):
    """Test handling entities with special characters in text."""
    # Create test data
    json_path = tmp_path / "memory.json"
    test_data = [
        {
            "type": "entity",
            "name": "Special_Entity",
            "entityType": "test",
            "observations": [
                "Contains *markdown* formatting",
                "Has #hashtags and @mentions",
                "Uses [square brackets] and {curly braces}"
            ]
        }
    ]
    
    with open(json_path, 'w') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')
    
    # Process import
    results = await process_memory_json(json_path, test_config.home, markdown_processor)
    assert results["entities"] == 1
    
    # Verify file was created and content preserved
    entity_path = test_config.home / "test/Special_Entity.md"
    entity = await markdown_processor.read_file(entity_path)
    
    assert len(entity.observations) == 3
    assert entity.observations[0].content == "Contains *markdown* formatting"
    assert entity.observations[1].content == "Has #hashtags and @mentions"
    assert entity.observations[2].content == "Uses [square brackets] and {curly braces}"