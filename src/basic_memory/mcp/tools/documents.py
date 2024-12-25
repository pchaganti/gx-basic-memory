"""Document management tools for Basic Memory MCP server."""

from typing import Dict, List

from basic_memory.schemas.request import DocumentRequest, FilePath
from basic_memory.schemas.response import DocumentResponse, DocumentCreateResponse
from basic_memory.mcp.async_client import client
from basic_memory.mcp.server import mcp


@mcp.tool()
async def create_document(request: DocumentRequest) -> DocumentCreateResponse:
    """Create a new markdown document.
    
    Examples:
        # Create a technical specification
        request = DocumentRequest(
            path="specs/memory_format.md",
            content='''# Memory Format Specification
                
                ## Overview
                This document defines the standard format for memory files.
                
                ## Format
                - Markdown with frontmatter
                - UTF-8 encoding
                - Required metadata fields
                ''',
            doc_metadata={
                "author": "AI team",
                "status": "draft",
                "version": "0.1"
            }
        )
        response = await create_document(request)
        
        # Response contains document info:
        # DocumentCreateResponse(
        #     path="specs/memory_format.md",
        #     checksum="abc123...",
        #     doc_metadata={...},
        #     created_at="2024-12-25T12:00:00Z",
        #     updated_at="2024-12-25T12:00:00Z"
        # )
    """
    url = "/documents/create"
    response = await client.post(url, json=request.model_dump())
    return DocumentCreateResponse.model_validate(response.json())


@mcp.tool()
async def update_document(request: DocumentRequest) -> DocumentResponse:
    """Update an existing document.
    
    Examples:
        # Update implementation docs with new details
        request = DocumentRequest(
            path="docs/implementation.md",
            content='''# Implementation Details
                
                ## Recent Changes
                - Added FTS5 support
                - Improved error handling
                - Enhanced sync reliability
                ''',
            doc_metadata={
                "last_reviewed": "2024-12-25",
                "status": "current"
            }
        )
        response = await update_document(request)
        
        # Response contains updated document:
        # DocumentResponse(
        #     path="docs/implementation.md",
        #     content="# Implementation Details\n...",
        #     checksum="def456...",
        #     doc_metadata={...},
        #     created_at="2024-12-20T10:00:00Z", 
        #     updated_at="2024-12-25T14:30:00Z"
        # )
    """
    url = f"/documents/{request.path}"
    response = await client.put(url, json=request.model_dump())
    return DocumentResponse.model_validate(response.json())


@mcp.tool()
async def get_document(path: FilePath) -> DocumentResponse:
    """Get a document by its path.
    
    Examples:
        # Load an API specification
        response = await get_document("specs/api_format.md")
        
        # Response contains complete document:
        # DocumentResponse(
        #     path="specs/api_format.md",
        #     content="# API Format\n\n## Endpoints\n...",
        #     checksum="789ghi...",
        #     doc_metadata={
        #         "status": "current",
        #         "version": "1.0"
        #     },
        #     created_at="2024-12-01T09:00:00Z",
        #     updated_at="2024-12-20T15:45:00Z"
        # )

        # Load implementation details
        response = await get_document("docs/implementation.md")
    """
    url = f"/documents/{path}"
    response = await client.get(url)
    return DocumentResponse.model_validate(response.json())


@mcp.tool()
async def list_documents() -> List[DocumentCreateResponse]:
    """List all documents in the system.
    
    Examples:
        # Get all documents with metadata
        documents = await list_documents()
        
        # Response is list of document info:
        # [
        #     DocumentCreateResponse(
        #         path="specs/format.md",
        #         checksum="abc123...",
        #         doc_metadata={"status": "draft"},
        #         created_at="2024-12-01T09:00:00Z",
        #         updated_at="2024-12-25T10:30:00Z"
        #     ),
        #     DocumentCreateResponse(
        #         path="docs/implementation.md",
        #         checksum="def456...",
        #         doc_metadata={"status": "current"},
        #         created_at="2024-12-20T10:00:00Z",
        #         updated_at="2024-12-25T14:30:00Z"
        #     )
        # ]
    """
    url = "/documents/list"
    response = await client.get(url)
    return [DocumentCreateResponse.model_validate(doc) for doc in response.json()]


@mcp.tool()
async def delete_document(path: FilePath) -> Dict[str, bool]:
    """Delete a document.
    
    Examples:
        # Remove an obsolete document
        result = await delete_document("docs/outdated_spec.md")
        
        # Response indicates success:
        # {
        #     "deleted": true
        # }
    """
    url = f"/documents/{path}"
    response = await client.delete(url)
    if response.status_code == 204:
        return {"deleted": True}
    return response.json()