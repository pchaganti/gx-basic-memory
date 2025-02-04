"""Tests for file operations service."""

from pathlib import Path
from unittest.mock import patch
from textwrap import dedent

import pytest

from basic_memory.models import Entity, Relation, Observation
from basic_memory.repository import RelationRepository, EntityRepository, ObservationRepository
from basic_memory.services.exceptions import FileOperationError
from basic_memory.services.file_service import FileService


@pytest.mark.asyncio
async def test_exists(tmp_path: Path, file_service: FileService):
    """Test file existence checking."""
    # Test path
    test_path = tmp_path / "test.md"

    # Should not exist initially
    assert not await file_service.exists(test_path)

    # Create file
    test_path.write_text("test content")
    assert await file_service.exists(test_path)

    # Delete file
    test_path.unlink()
    assert not await file_service.exists(test_path)


@pytest.mark.asyncio
async def test_exists_error_handling(tmp_path: Path, file_service: FileService):
    """Test error handling in exists() method."""
    test_path = tmp_path / "test.md"

    # Mock Path.exists to raise an error
    with patch.object(Path, "exists") as mock_exists:
        mock_exists.side_effect = PermissionError("Access denied")

        with pytest.raises(FileOperationError) as exc_info:
            await file_service.exists(test_path)

        assert "Failed to check file existence" in str(exc_info.value)


@pytest.mark.asyncio
async def test_write_read_file(tmp_path: Path, file_service: FileService):
    """Test basic write/read operations with checksums."""
    test_path = tmp_path / "test.md"
    test_content = "test content\nwith multiple lines"

    # Write file and get checksum
    checksum = await file_service.write_file(test_path, test_content)
    assert test_path.exists()

    # Read back and verify content/checksum
    content, read_checksum = await file_service.read_file(test_path)
    assert content == test_content
    assert read_checksum == checksum


@pytest.mark.asyncio
async def test_write_creates_directories(tmp_path: Path, file_service: FileService):
    """Test directory creation on write."""
    test_path = tmp_path / "subdir" / "nested" / "test.md"
    test_content = "test content"

    # Write should create directories
    await file_service.write_file(test_path, test_content)
    assert test_path.exists()
    assert test_path.parent.is_dir()


@pytest.mark.asyncio
async def test_write_atomic(tmp_path: Path, file_service: FileService):
    """Test atomic write with no partial files."""
    test_path = tmp_path / "test.md"
    temp_path = test_path.with_suffix(".tmp")

    # Mock write_file_atomic to raise an error
    with patch("basic_memory.file_utils.write_file_atomic") as mock_write:
        mock_write.side_effect = Exception("Write failed")

        # Attempt write that will fail
        with pytest.raises(FileOperationError):
            await file_service.write_file(test_path, "test content")

        # No partial files should exist
        assert not test_path.exists()
        assert not temp_path.exists()


@pytest.mark.asyncio
async def test_delete_file(tmp_path: Path, file_service: FileService):
    """Test file deletion."""
    test_path = tmp_path / "test.md"
    test_content = "test content"

    # Create then delete
    await file_service.write_file(test_path, test_content)
    assert test_path.exists()

    await file_service.delete_file(test_path)
    assert not test_path.exists()

    # Delete non-existent file should not error
    await file_service.delete_file(test_path)


@pytest.mark.asyncio
async def test_checksum_consistency(tmp_path: Path, file_service: FileService):
    """Test checksum remains consistent."""
    test_path = tmp_path / "test.md"
    test_content = "test content\n" * 10

    # Get checksum from write
    checksum1 = await file_service.write_file(test_path, test_content)

    # Get checksum from read
    _, checksum2 = await file_service.read_file(test_path)

    # Write again and get new checksum
    checksum3 = await file_service.write_file(test_path, test_content)

    # All should match
    assert checksum1 == checksum2 == checksum3


@pytest.mark.asyncio
async def test_error_handling_missing_file(tmp_path: Path, file_service: FileService):
    """Test error handling for missing files."""
    test_path = tmp_path / "missing.md"

    with pytest.raises(FileOperationError):
        await file_service.read_file(test_path)


@pytest.mark.asyncio
async def test_error_handling_invalid_path(tmp_path: Path, file_service: FileService):
    """Test error handling for invalid paths."""
    # Try to write to a directory instead of file
    test_path = tmp_path / "test.md"
    test_path.mkdir()  # Create a directory instead of a file

    with pytest.raises(FileOperationError):
        await file_service.write_file(test_path, "test")


@pytest.mark.asyncio
async def test_write_unicode_content(tmp_path: Path, file_service: FileService):
    """Test handling of unicode content."""
    test_path = tmp_path / "test.md"
    test_content = """
    # Test Unicode
    - Emoji: 🚀 ⭐️ 🔥
    - Chinese: 你好世界
    - Arabic: مرحبا بالعالم
    - Russian: Привет, мир
    """

    # Write and read back
    await file_service.write_file(test_path, test_content)
    content, _ = await file_service.read_file(test_path)

    assert content == test_content


@pytest.mark.asyncio
async def test_write_entity_with_content(
    file_service: FileService,
    sample_entity: Entity,
):
    """Test that write_entity_file uses content when explicitly provided."""
    # Write initial content
    initial_content = dedent("""
                # My Note
                
                This is my original content.
                It should be included in the file.""")

    path, _ = await file_service.write_entity_file(sample_entity, content=initial_content)

    # Verify content was written
    content, _ = await file_service.read_file(path)

    # Content should have frontmatter and supplied content
    assert "# My Note" in content
    assert "This is my original content" in content
    assert "It should be included in the file." in content


@pytest.mark.asyncio
async def test_write_entity_preserves_existing_content(
    file_service: FileService,
    observation_repository: ObservationRepository,
    relation_repository: RelationRepository,
    entity_repository: EntityRepository,
    sample_entity: Entity,
    full_entity: Entity,
):
    """Test that write_entity_file preserves existing content when not explicitly provided."""
    # Write initial content
    initial_content = dedent("""
                # My Note
                This is my original content.
                It should be preserved.""")

    path, _ = await file_service.write_entity_file(sample_entity, content=initial_content)

    # add observation
    observation = await observation_repository.add(
        Observation(
            entity_id=sample_entity.id,
            content="Test observation",
            category="note",
            context="test context",
        )
    )

    # Add a relation
    relation = await relation_repository.add(
        Relation(
            from_id=sample_entity.id,
            to_id=full_entity.id,
            to_name=full_entity.title,
            relation_type="relates_to",
        )
    )
    # reload entity
    sample_entity = await entity_repository.find_by_id(sample_entity.id)

    # Write entity file without providing content
    await file_service.write_entity_file(sample_entity)

    # Verify content was preserved
    content, _ = await file_service.read_file(path)

    # Content should have frontmatter and preserved content
    assert "# My Note" in content
    assert "This is my original content" in content
    assert "It should be preserved" in content

    # And should also have the new observation
    assert f"- [{observation.category}] {observation.content} ({observation.context})" in content

    # And should also have the new relation
    assert f"- relates_to [[{full_entity.title}]]" in content


@pytest.mark.asyncio
async def test_write_entity_handles_missing_content(
    file_service: FileService,
    sample_entity: Entity,
):
    """Test that write_entity_file handles case where there is no existing content gracefully."""
    # Write without any content
    path, _ = await file_service.write_entity_file(sample_entity)

    # Should still create a valid file
    content, _ = await file_service.read_file(path)

    # Should have frontmatter
    assert "permalink:" in content

    # Should have title
    assert sample_entity.title in content


@pytest.mark.asyncio
async def test_write_entity_adds_semantic_info(
    file_service: FileService,
    full_entity: Entity,
):
    """Test that write_entity_file uses content when explicitly provided."""
    # Write initial content
    initial_content = dedent("""
                # My Note

                This is my original content.
                It should be included in the file.""")

    path, _ = await file_service.write_entity_file(full_entity, content=initial_content)

    # Verify content was written
    content, _ = await file_service.read_file(path)

    # Content should have frontmatter and supplied content
    assert "# My Note" in content
    assert "This is my original content" in content
    assert "It should be included in the file." in content
    
    # semantic info should be added 
    assert "- [tech] Tech note" in content
    assert "- [design] Design note" in content
    
    assert "- out1 [[Test Entity]]" in content 
    assert "- out2 [[Test Entity]]" in content


@pytest.mark.asyncio
async def test_write_entity_adds_semantic_info_partial(
        file_service: FileService,
        full_entity: Entity,
):
    """Test that write_entity_file uses content when explicitly provided."""
    # Write initial content
    initial_content = dedent("""
                # My Note

                This is my original content.
                It should be included in the file.
                
                - [tech] Tech note
                - out1 [[Test Entity]]
                """)

    path, _ = await file_service.write_entity_file(full_entity, content=initial_content)

    # Verify content was written
    content, _ = await file_service.read_file(path)

    # Content should have frontmatter and supplied content
    assert "# My Note" in content
    assert "This is my original content" in content
    assert "It should be included in the file." in content

    # assert content contains semantic info
    assert "- [tech] Tech note" in content
    assert "- out1 [[Test Entity]]" in content
    
    # semantic info should be added if not in content 
    assert "- [design] Design note" in content
    assert "- out2 [[Test Entity]]" in content


@pytest.mark.asyncio
async def test_write_entity_includes_semantic_info_in_content(
        file_service: FileService,
        full_entity: Entity,
):
    """Test that write_entity_file does not overwrite semantic info in content when explicitly provided."""
    # Write initial content
    initial_content = dedent("""
                # My Note

                This is my original content.
                It should be included in the file.
                
                - [tech] Tech note
                - [design] Design note
                
                - out1 [[Test Entity]]
                - out2 [[Test Entity]]
                """)

    path, _ = await file_service.write_entity_file(full_entity, content=initial_content)

    # Verify content was written
    content, _ = await file_service.read_file(path)

    # Content should have frontmatter and supplied content
    assert "# My Note" in content
    assert "This is my original content" in content
    assert "It should be included in the file." in content
    
    assert content.count("- [tech] Tech note") == 1
    assert content.count("- [design] Design note") == 1
    assert content.count("- out1 [[Test Entity]]") == 1
    assert content.count("- out2 [[Test Entity]]") == 1

