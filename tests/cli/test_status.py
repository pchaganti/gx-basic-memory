# """Test status command functionality."""
#
# from io import StringIO
#
# import pytest
# from rich.console import Console
#
# from basic_memory.cli.commands.status import display_changes, run_status
# from basic_memory.sync.file_change_scanner import FileState
# from basic_memory.sync.utils import SyncReport
# from basic_memory.file_utils import compute_checksum
#
#
# @pytest.fixture
# def console():
#     """Create test console that captures output."""
#     output = StringIO()
#     return Console(file=output), output
#
#
# @pytest.mark.asyncio
# async def test_display_no_changes(console):
#     """Test display with no changes."""
#     test_console, output = console
#     changes = SyncReport()
#     display_changes("Test Files", changes, verbose=False)
#     assert "No changes" in output.getvalue()
#
#
# @pytest.mark.asyncio
# async def test_display_compact_changes(console):
#     """Test compact display of changes."""
#     test_console, output = console
#     changes = SyncReport(
#         new={"docs/new.md"},
#         modified={"docs/mod.md"},
#         deleted={"old/deleted.md"},
#         moved={
#             "new/location.md": FileState(
#                 permalink="new/location.md", checksum="abc123", moved_from="old/location.md"
#             )
#         },
#     )
#     display_changes("Test Files", changes, verbose=False)
#     output_text = output.getvalue()
#
#     # Check directory summaries
#     assert "docs/ +1 new" in output_text.replace("  ", " ")
#     assert "docs/ ~1 modified" in output_text.replace("  ", " ")
#     assert "old/ -1 deleted" in output_text.replace("  ", " ")
#     assert "new/ ->1 moved" in output_text.replace("  ", " ")
#
#
# @pytest.mark.asyncio
# async def test_display_verbose_changes(console):
#     """Test verbose display of changes."""
#     test_console, output = console
#     changes = SyncReport(
#         new={"docs/new.md"},
#         modified={"docs/mod.md"},
#         deleted={"old/deleted.md"},
#         moved={
#             "new/location.md": FileState(
#                 permalink="new/location.md",
#                 checksum="abc123def",  # 8 chars for display
#                 moved_from="old/location.md",
#             )
#         },
#         checksums={
#             "docs/new.md": "def456789abcdef",
#             "docs/mod.md": "ghi789abcdef123",
#         },
#     )
#     display_changes("Test Files", changes, verbose=True)
#     output_text = output.getvalue()
#
#     # Verify sections
#     assert "New Files" in output_text
#     assert "Modified" in output_text
#     assert "Deleted" in output_text
#     assert "Moved" in output_text
#
#     # Check file listings with checksums
#     assert "new.md (def45678)" in output_text
#     assert "mod.md (ghi78789)" in output_text
#     assert "location.md (abc123de)" in output_text
#
#
# @pytest.mark.asyncio
# async def test_end_to_end_status(file_change_scanner, test_config, entity_repository):
#     """Test complete status command with real files."""
#     # Create test files in both knowledge and documents directories
#     project_dir = test_config.home
#
#     # Create knowledge files
#     component_dir = project_dir / "component"
#     component_dir.mkdir(exist_ok=True)
#     component_path = component_dir / "test.md"
#     component_path.write_text("test component")
#
#     # Add some files to DB with different paths to test moves
#     await entity_repository.create(
#         {"permalink": "old/doc.md", "file_path": "old/doc.md", "checksum": "abc123"}
#     )
#
#     # Run status check
#     await run_status(file_change_scanner, verbose=True)
#
#     # Verify changes through sync service directly
#     doc_changes = await file_change_scanner.find_knowledge_changes(project_dir)
#     assert len(doc_changes.new) == 2  # test.md and nested.md
#     assert "test.md" in doc_changes.new
#     assert "subdir/nested.md" in doc_changes.new
#     assert len(doc_changes.deleted) == 1  # old/doc.md
#
#     knowledge_changes = await file_change_scanner.find_knowledge_changes(project_dir)
#     assert len(knowledge_changes.new) == 1
#     assert "component/test.md" in knowledge_changes.new
#
#
# @pytest.mark.asyncio
# async def test_status_with_case_changes(file_change_scanner, test_config, entity_repository):
#     """Test status detection with case-sensitive path changes."""
#     docs_dir = test_config.documents_dir
#     docs_dir.mkdir(parents=True, exist_ok=True)
#
#     # Create file with initial case
#     content = "test content"
#     original_path = "Test.md"
#     orig_file = docs_dir / original_path
#     orig_file.write_text(content)
#     checksum = await compute_checksum(content)
#
#     # Add to DB
#     await entity_repository.create(
#         {"permalink": original_path, "file_path": original_path, "checksum": checksum}
#     )
#
#     # Simulate case change in filesystem
#     orig_file.rename(docs_dir / "test.md")
#
#     # Check changes
#     changes = await file_change_scanner.find_knowledge_changes(docs_dir)
#     assert len(changes.moved) == 1
#     assert "test.md" in changes.moved
#     assert changes.moved["test.md"].moved_from == original_path
#
#
# @pytest.mark.asyncio
# async def test_status_with_spaces(file_change_scanner, test_config, entity_repository):
#     """Test status handling files with spaces and special characters."""
#     docs_dir = test_config.documents_dir
#     docs_dir.mkdir(parents=True, exist_ok=True)
#
#     # Create file with spaces
#     content = "test content"
#     path = "My Document.md"
#     file_path = docs_dir / path
#     file_path.write_text(content)
#     checksum = await compute_checksum(content)
#
#     # Add to DB with same path
#     await entity_repository.create({"permalink": path, "file_path": path, "checksum": checksum})
#
#     # Check changes
#     changes = await file_change_scanner.find_knowledge_changes(docs_dir)
#     assert not changes.modified  # File unchanged
#     assert not changes.moved  # Path matches exactly
#     assert not changes.deleted
#     assert not changes.new
