"""Document management tools for Basic Memory MCP server."""

from typing import Dict, List

from basic_memory.mcp.server import mcp
from basic_memory.schemas.request import DocumentRequest, DocumentPathId
from basic_memory.schemas.response import DocumentResponse, DocumentCreateResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    description="Create a new markdown document with frontmatter metadata and content",
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
    """Create a new markdown document."""
    url = "/documents/create"
    response = await client.post(url, json=request.model_dump())
    return DocumentCreateResponse.model_validate(response.json())


@mcp.tool(
    description="Update an existing markdown document while preserving its history",
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
    """Update an existing document."""
    url = f"/documents/{request.path_id}"
    response = await client.put(url, json=request.model_dump())
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    description="Retrieve a document's content and metadata by path",
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
    """Get a document by its path."""
    url = f"/documents/{path}"
    response = await client.get(url)
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    description="List all documents with their metadata and version information",
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
    """List all documents in the system."""
    url = "/documents/list"
    response = await client.get(url)
    return [DocumentCreateResponse.model_validate(doc) for doc in response.json()]


@mcp.tool(
    description="Delete a document and update related indexes",
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
    """Delete a document."""
    url = f"/documents/{path}"
    response = await client.delete(url)
    if response.status_code == 204:
        return {"deleted": True}
    return response.json()