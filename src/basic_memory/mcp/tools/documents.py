"""Document management tools for Basic Memory MCP server."""

from typing import Dict, List

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.schemas.request import DocumentRequest, DocumentPathId
from basic_memory.schemas.response import DocumentResponse, DocumentCreateResponse
from basic_memory.mcp.async_client import client


@mcp.tool(
    category="documents",
    description="Create a new markdown document. Metadata should be passed in doc_metadata, not in content.",
    examples=[
        {
            "name": "Technical Spec",
            "description": "Create a specification with structured metadata",
            "code": """
# Create new spec with metadata
spec = await create_document(
    request=DocumentRequest(
        path_id="specs/memory_format.md",
        content='''# Memory Format Specification

## Overview
This document defines our standard format.

## Structure
1. Content structured in markdown
2. Metadata handled by doc_metadata field
3. Optional structured data sections''',
        doc_metadata={
            "title": "Memory Format Specification",
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
            "name": "Design Decision",
            "description": "Document architectural decisions with context",
            "code": """
# Create ADR with metadata
design = await create_document(
    request=DocumentRequest(
        path_id="design/decisions/use-sqlite.md",
        content='''# Use SQLite for Local Storage

## Context
We need reliable local-first storage that provides:
- SQL query capabilities
- Atomic transactions
- No external dependencies
- Simple deployment

## Decision
We will use SQLite as our primary storage engine.

## Consequences
### Positive
- Simple deployment (single file)
- Full SQL support
- Strong atomicity guarantees
- Local-first operation
- Proven reliability

### Negative
- Limited concurrent access
- No built-in replication
- Size limitations for some filesystems

## Implementation Notes
- Using SQLite version 3.35+ for JSON support
- Implementing connection pooling
- Adding automated backups''',
        doc_metadata={
            "title": "Use SQLite for Local Storage",
            "type": "decision",
            "status": "accepted",
            "date": "2024-12-25",
            "impact": "high",
            "area": "storage"
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
        request: Document creation request. The content should be plain markdown 
                without frontmatter. Any metadata should be passed in doc_metadata.
                Required fields (id, created, modified) will be added automatically.
        
    Returns:
        DocumentCreateResponse with document details and checksum
    """
    url = "/documents/create"
    response = await client.post(url, json=request.model_dump())
    logger.info(response.status_code)
    logger.info(response.json())
    return DocumentCreateResponse.model_validate(response.json())


@mcp.tool(
    category="documents",
    description="Update an existing markdown document while preserving its history",
    examples=[
        {
            "name": "Implementation Update",
            "description": "Document implementation changes with structured sections",
            "code": """
# Update implementation details
updated = await update_document(
    request=DocumentRequest(
        path_id="docs/components/memory-service.md",
        content='''# Memory Service

## Overview
Core service handling knowledge persistence and retrieval.

## Recent Changes
- Added async/await support
- Improved error handling
- Enhanced performance monitoring

## Implementation Details
### Storage Layer
- Using SQLite 3.35 with JSON1 extension
- Connection pooling via aiosqlite
- Automated backup system

### Key Features
- Atomic file operations
- Transactional consistency
- Automated recovery
- Full text search

### Error Handling
- Retries with exponential backoff
- Detailed error context
- Automatic cleanup
- Failure auditing

## Performance Notes
- Query optimization implemented
- Index tuning automated
- Cache layer added
- Bulk operation support''',
        doc_metadata={
            "title": "Memory Service",
            "status": "stable",
            "last_updated": "2024-12-25",
            "reviewed_by": ["@alice", "@bob"]
        }
    )
)

# Verify update
print(f"Updated: {updated.path_id}")
print(f"New checksum: {updated.checksum}")
"""
        },
        {
            "name": "Collaborative Documentation",
            "description": "Build documentation through tool collaboration",
            "code": """
# First, get recent changes
activity = await get_recent_activity(
    timeframe="1d",
    activity_types=["entity"]
)

# Build documentation from changes
doc_content = ["# Recent Development Activity\\n"]
doc_content.append("## Key Changes\\n")

# Group changes by component
changes_by_type = defaultdict(list)
for change in activity.changes:
    type_ = change.path_id.split("/")[0]
    changes_by_type[type_].append(change)

# Document each area's changes
for type_, changes in changes_by_type.items():
    doc_content.append(f"### {type_.title()}\\n")
    for change in changes:
        doc_content.append(f"- {change.summary}\\n")

# Create the document
await create_document(
    request=DocumentRequest(
        path_id=f"docs/changes/daily-update-{datetime.now():%Y-%m-%d}.md",
        content="\\n".join(doc_content),
        doc_metadata={
            "type": "changelog",
            "title": f"Daily Update {datetime.now():%Y-%m-%d}",
            "auto_generated": True,
            "source": "activity_tracking"
        }
    )
)
"""
        }
    ],
    output_model=DocumentResponse
)
async def update_document(request: DocumentRequest) -> DocumentResponse:
    """Update an existing document.
    
    Args:
        request: Document update request. Content should be plain markdown without frontmatter.
                Metadata should be passed in doc_metadata. Frontmatter fields like created/modified
                will be handled automatically.
        
    Returns:
        DocumentResponse with updated document details
    """
    url = f"/documents/{request.path_id}"
    response = await client.put(url, json=request.model_dump())
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    category="documents",
    description="Get a document's content and metadata",
    examples=[
        {
            "name": "Load Documentation",
            "description": "Read and analyze document content",
            "code": """
# Get API documentation
doc = await get_document("docs/api/memory-service.md")

# Show document structure
print(f"Document: {doc.path_id}")
print(f"Status: {doc.doc_metadata.get('status', 'unknown')}")
print(f"Last updated: {doc.updated_at}")
print("\\nContent sections:")

# Simple section parser
sections = []
current = []
for line in doc.content.split("\\n"):
    if line.startswith("# "):
        if current:
            sections.append("\\n".join(current))
        current = [line]
    else:
        current.append(line)
if current:
    sections.append("\\n".join(current))

for i, section in enumerate(sections, 1):
    title = section.split("\\n")[0].lstrip("#").strip()
    print(f"{i}. {title}")
"""
        },
        {
            "name": "Build Context",
            "description": "Extract technical context from documentation",
            "code": """
# Get implementation spec
doc = await get_document("specs/implementation/memory-service.md")

# Extract code examples
import re
code_blocks = re.findall(r"```(.*?)```", doc.content, re.DOTALL)
if code_blocks:
    print("Found code examples:")
    for i, block in enumerate(code_blocks, 1):
        print(f"\\nExample {i}:")
        print(block.strip())

# Look for decision points
decisions = []
lines = doc.content.split("\\n")
for i, line in enumerate(lines):
    if "decided" in line.lower() or "decision" in line.lower():
        context = lines[max(0, i-1):min(len(lines), i+2)]
        decisions.append("\\n".join(context))

if decisions:
    print("\\nKey decisions:")
    for d in decisions:
        print(f"\\n- {d.strip()}")
"""
        }
    ],
    output_model=DocumentResponse
)
async def get_document(path: DocumentPathId) -> DocumentResponse:
    """Get a document by its path.
    
    Args:
        path: Path of the document to retrieve
        
    Returns:
        DocumentResponse containing document content and metadata
    """
    url = f"/documents/{path}"
    response = await client.get(url)
    return DocumentResponse.model_validate(response.json())


@mcp.tool(
    category="documents",
    description="List all documents with metadata and version information",
    examples=[
        {
            "name": "Document Overview",
            "description": "Analyze document organization and status",
            "code": """
# Get document listing
docs = await list_documents()

# Group by status and type
from collections import defaultdict
by_status = defaultdict(list)
by_type = defaultdict(list)

for doc in docs:
    status = doc.doc_metadata.get("status", "unknown")
    doc_type = doc.doc_metadata.get("type", "unknown")
    by_status[status].append(doc)
    by_type[doc_type].append(doc)

# Show status summary
print("Document Status:")
for status, items in by_status.items():
    print(f"\\n{status.title()} ({len(items)} docs):")
    for doc in items:
        print(f"- {doc.path_id}")

# Show type distribution
print("\\nDocument Types:")
for doc_type, items in by_type.items():
    print(f"{doc_type}: {len(items)} documents")"""
        },
        {
            "name": "Documentation Analysis",
            "description": "Analyze documentation patterns and gaps",
            "code": """
# Get all documents
docs = await list_documents()

# Analyze coverage
coverage = {
    "components": set(),
    "features": set(),
    "apis": set()
}

# Extract documented items
for doc in docs:
    path = doc.path_id.lower()
    if "components" in path:
        coverage["components"].add(path.split("/")[-1])
    elif "features" in path:
        coverage["features"].add(path.split("/")[-1])
    elif "api" in path:
        coverage["apis"].add(path.split("/")[-1])

# Get actual components
components = await list_by_type("component")
features = await list_by_type("feature")

# Find documentation gaps
component_names = {e.name.lower() for e in components.entities}
feature_names = {e.name.lower() for e in features.entities}

missing_components = component_names - coverage["components"]
missing_features = feature_names - coverage["features"]

print("Documentation Gaps:")
if missing_components:
    print("\\nUndocumented Components:")
    for c in missing_components:
        print(f"- {c}")

if missing_features:
    print("\\nUndocumented Features:")
    for f in missing_features:
        print(f"- {f}")"""
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
    description="Delete a document and update related indexes",
    examples=[
        {
            "name": "Safe Document Removal",
            "description": "Delete a document with relation checking",
            "code": """
# First check for references
results = await search_nodes(
    request=SearchNodesRequest(
        query=f"specs/old_format.md"
    )
)

# Check if document is referenced
has_references = any(
    "specs/old_format.md" in obs.content
    for entity in results.matches
    for obs in entity.observations
)

if has_references:
    print("Document is referenced by other entities!")
    print("\\nReferences found in:")
    for entity in results.matches:
        print(f"- {entity.path_id}")
else:
    # Safe to delete
    result = await delete_document("specs/old_format.md")
    if result["deleted"]:
        print("Document successfully removed")"""
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