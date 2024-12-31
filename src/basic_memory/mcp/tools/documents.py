"""Document management tools for Basic Memory MCP server."""

from typing import Dict, List

from basic_memory.mcp.server import mcp
from basic_memory.schemas.request import DocumentRequest, DocumentPathId
from basic_memory.schemas.response import DocumentResponse, DocumentCreateResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    description="""
    Create a new markdown document in the knowledge base.

    This tool stores markdown documents with:
    - Structured frontmatter metadata
    - Rich markdown content
    - Version tracking via checksums
    - Automatic timestamp management
    - Optional custom metadata

    Documents are stored in a git-friendly format and can be
    edited either through the API or directly in the filesystem.
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
    output_schema={
        "description": "Created document information",
        "properties": {
            "path_id": {
                "type": "string",
                "description": "Document path and filename"
            },
            "checksum": {
                "type": "string",
                "description": "Content checksum for version tracking"
            },
            "doc_metadata": {
                "type": "object",
                "description": "Custom document metadata",
                "additionalProperties": True
            },
            "created_at": {
                "type": "string",
                "format": "date-time",
                "description": "Creation timestamp"
            },
            "updated_at": {
                "type": "string",
                "format": "date-time",
                "description": "Last modification timestamp"
            }
        },
        "required": ["path_id", "checksum", "created_at", "updated_at"]
    }
)
async def create_document(request: DocumentRequest) -> DocumentCreateResponse:
    """Create a new markdown document."""
    url = "/documents/create"
    response = await client.post(url, json=request.model_dump())
    return DocumentCreateResponse.model_validate(response.json())


@mcp.tool(
    description="""
    Update an existing document while preserving its history.
    
    This tool handles:
    - Content updates
    - Metadata changes
    - Version tracking
    - Timestamp management
    
    The update preserves document history and maintains
    consistency with any linked knowledge graph entities.
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
    output_schema={
        "description": "Updated document with content",
        "properties": {
            "path_id": {
                "type": "string",
                "description": "Document path and filename"
            },
            "content": {
                "type": "string",
                "description": "Current document content"
            },
            "checksum": {
                "type": "string",
                "description": "New content checksum"
            },
            "doc_metadata": {
                "type": "object",
                "description": "Current document metadata"
            },
            "created_at": {
                "type": "string",
                "format": "date-time"
            },
            "updated_at": {
                "type": "string",
                "format": "date-time"
            }
        },
        "required": ["path_id", "content", "checksum"]
    }
)
async def update_document(request: DocumentRequest) -> DocumentResponse:
    """Update an existing document."""
    url = f"/documents/{request.path_id}"
    response = await client.put(url, json=request.model_dump())
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    description="""
    Retrieve a document's content and metadata.
    
    This tool provides access to:
    - Full document content
    - Current metadata
    - Version information
    - Timestamps
    
    Documents are returned with their complete context, useful
    for reading or preparing updates.
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
    output_schema={
        "description": "Complete document information",
        "properties": {
            "path_id": {
                "type": "string",
                "description": "Document identifier"
            },
            "content": {
                "type": "string",
                "description": "Document content"
            },
            "checksum": {
                "type": "string",
                "description": "Content checksum"
            },
            "doc_metadata": {
                "type": "object",
                "description": "Document metadata"
            }
        }
    }
)
async def get_document(path: DocumentPathId) -> DocumentResponse:
    """Get a document by its path."""
    url = f"/documents/{path}"
    response = await client.get(url)
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    description="""
    List all documents in the knowledge base.
    
    Provides an overview of the document collection including:
    - Document paths and names
    - Metadata for each document
    - Version information
    - Timestamps
    
    Useful for browsing content or finding specific documents.
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
    output_schema={
        "description": "List of document information",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "path_id": {
                    "type": "string",
                    "description": "Document path"
                },
                "checksum": {
                    "type": "string",
                    "description": "Version checksum"
                },
                "doc_metadata": {
                    "type": "object",
                    "description": "Document metadata"
                }
            }
        }
    }
)
async def list_documents() -> List[DocumentCreateResponse]:
    """List all documents in the system."""
    url = "/documents/list"
    response = await client.get(url)
    return [DocumentCreateResponse.model_validate(doc) for doc in response.json()]


@mcp.tool(
    description="""
    Delete a document from the knowledge base.
    
    This tool:
    - Removes the document file
    - Updates related indexes
    - Maintains consistency
    
    Note that deletion is permanent and cannot be undone
    through the API (though git history may preserve it).
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
    output_schema={
        "description": "Deletion result",
        "type": "object",
        "properties": {
            "deleted": {
                "type": "boolean",
                "description": "Whether deletion succeeded"
            }
        }
    }
)
async def delete_document(path: DocumentPathId) -> Dict[str, bool]:
    """Delete a document."""
    url = f"/documents/{path}"
    response = await client.delete(url)
    if response.status_code == 204:
        return {"deleted": True}
    return response.json()
