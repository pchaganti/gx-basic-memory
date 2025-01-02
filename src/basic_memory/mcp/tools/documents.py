"""Document management tools for Basic Memory MCP server."""

from typing import Dict, List

from basic_memory.mcp.server import mcp
from basic_memory.schemas.request import DocumentRequest, DocumentPathId
from basic_memory.schemas.response import DocumentResponse, DocumentCreateResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    category="documents",
    description="""Create a new markdown document with frontmatter metadata and content.
    
    This tool is essential for AI-human collaboration as it allows:
    - Creating structured documentation from conversations
    - Capturing design decisions with metadata
    - Building knowledge base content
    - Maintaining project documentation
    
    Documents are stored as markdown files with YAML frontmatter for metadata.
    The content supports full markdown syntax including:
    - Headers and sections
    - Lists and tables
    - Code blocks with syntax highlighting
    - Links to other documents
    """,
    examples=[
        {
            "name": "Create Technical Spec",
            "description": "Create a new technical specification document",
            "code": """
# Create new spec with metadata
spec = await create_document(
    request=DocumentRequest(
        path_id="specs/memory_format.md",
        content='''# Memory Format Specification

## Overview
This document defines our standard format.

## Structure
1. Frontmatter for metadata
2. Markdown content for documentation
3. Optional structured data sections''',
        doc_metadata={
            "status": "draft",
            "version": "0.1",
            "reviewers": ["@alice", "@bob"]
        }
    )
)

print(f"Created: {spec.path_id}")
print(f"Version: {spec.doc_metadata['version']}")
"""
        },
        {
            "name": "Create Design Document",
            "description": "Document a design decision with context",
            "code": """
# Create design document
design = await create_document(
    request=DocumentRequest(
        path_id="design/database_schema.md",
        content='''# Database Schema Design

## Decision
Using SQLite for local-first storage.

## Context
Need reliable local storage with SQL features.

## Consequences
+ Simple deployment
+ Local-first operation
- Limited concurrent access''',
        doc_metadata={
            "type": "decision",
            "status": "accepted",
            "date": "2024-12-25"
        }
    )
)
"""
        }
    ],
    output_model=DocumentCreateResponse
)
async def create_document(request: DocumentRequest) -> DocumentCreateResponse:
    """Create a new markdown document.
    
    Args:
        request: Document creation request containing path, content and metadata
        
    Returns:
        DocumentCreateResponse with document details and checksum
    """
    url = "/documents/create"
    response = await client.post(url, json=request.model_dump())
    return DocumentCreateResponse.model_validate(response.json())


@mcp.tool(
    category="documents",
    description="""Update an existing markdown document while preserving its history.
    
    This tool enables iterative document development by:
    - Preserving document history and metadata
    - Allowing incremental content updates
    - Maintaining document integrity
    - Tracking document evolution
    
    Updates are atomic and maintain document consistency.
    """,
    examples=[
        {
            "name": "Update Content",
            "description": "Add new content to existing document",
            "code": """
# Update implementation details
updated = await update_document(
    request=DocumentRequest(
        path_id="docs/implementation.md",
        content='''# Implementation Details

## Recent Updates
- Added async support
- Improved error handling
- Enhanced performance

## New Features
- Batch processing
- Automatic retries
- Error recovery''',
        doc_metadata={
            "status": "current",
            "last_updated": "2024-12-25"
        }
    )
)

print(f"Updated: {updated.path_id}")
print(f"New checksum: {updated.checksum}")
"""
        }
    ],
    output_model=DocumentResponse
)
async def update_document(request: DocumentRequest) -> DocumentResponse:
    """Update an existing document.
    
    Args:
        request: Document update request with new content and metadata
        
    Returns:
        DocumentResponse with updated document details
    """
    url = f"/documents/{request.path_id}"
    response = await client.put(url, json=request.model_dump())
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    category="documents",
    description="""Retrieve a document's content and metadata by path.
    
    This tool provides:
    - Access to document content and structure
    - Retrieval of document metadata
    - Version information
    - Document history
    
    Enables AI tools to read and analyze existing documentation.
    """,
    examples=[
        {
            "name": "Read Documentation",
            "description": "Load and display a document",
            "code": """
# Get API documentation
doc = await get_document("docs/api_reference.md")

# Show document info
print(f"Document: {doc.path_id}")
print(f"Status: {doc.doc_metadata.get('status', 'unknown')}")
print("\\nContent:")
print(doc.content)
"""
        }
    ],
    output_model=DocumentResponse
)
async def get_document(path: DocumentPathId) -> DocumentResponse:
    """Get a document by its path.
    
    Args:
        path: Path to the document to retrieve
        
    Returns:
        DocumentResponse containing document content and metadata
    """
    url = f"/documents/{path}"
    response = await client.get(url)
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    category="documents",
    description="""List all documents with their metadata and version information.
    
    This tool enables:
    - Document discovery and exploration
    - Metadata-based filtering and organization
    - Understanding document relationships
    - Knowledge base navigation
    
    Essential for maintaining awareness of available documentation.
    """,
    examples=[
        {
            "name": "List All Documents",
            "description": "Show overview of all documents",
            "code": """
# Get document listing
docs = await list_documents()

# Group by status
from collections import defaultdict
by_status = defaultdict(list)

for doc in docs:
    status = doc.doc_metadata.get('status', 'unknown')
    by_status[status].append(doc)

# Show summary
for status, items in by_status.items():
    print(f"\\n{status.title()} Documents:")
    for doc in items:
        print(f"- {doc.path_id}")
"""
        }
    ],
    output_model=List[DocumentCreateResponse] 
)
async def list_documents() -> List[DocumentCreateResponse]:
    """List all documents in the system.
    
    Returns:
        List of document information including paths and metadata
    """
    url = "/documents/list"
    response = await client.get(url)
    return [DocumentCreateResponse.model_validate(doc) for doc in response.json()]


@mcp.tool(
    category="documents",
    description="""Delete a document and update related indexes.
    
    This tool:
    - Removes document content and metadata
    - Updates document indexes
    - Maintains knowledge base consistency
    - Preserves related content
    
    Use with caution as deletions are permanent.
    """,
    examples=[
        {
            "name": "Remove Document",
            "description": "Delete an obsolete document",
            "code": """
# Delete old specification
result = await delete_document("specs/old_format.md")
if result['deleted']:
    print("Document successfully removed")
"""
        }
    ],
    output_model=Dict[str, bool] 
)
async def delete_document(path: DocumentPathId) -> Dict[str, bool]:
    """Delete a document.
    
    Args:
        path: Path of document to delete
        
    Returns:
        Dict indicating success of deletion
    """
    url = f"/documents/{path}"
    response = await client.delete(url)
    if response.status_code == 204:
        return {"deleted": True}
    return response.json()