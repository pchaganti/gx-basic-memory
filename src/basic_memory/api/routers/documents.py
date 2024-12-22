"""Router for document management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from basic_memory.deps import DocumentServiceDep
from basic_memory.schemas.request import DocumentCreate, DocumentUpdate, DocumentPatch
from basic_memory.schemas.response import DocumentResponse
from basic_memory.services.document_service import (
    DocumentNotFoundError,
    DocumentWriteError,
)

# Router
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=201)
async def create_document(
    doc: DocumentCreate,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Create a new document.

    The document will be created with appropriate frontmatter including:
    - Generated ID
    - Creation timestamp
    - Last modified timestamp
    - Any provided metadata
    """
    try:
        document = await service.create_document(
            path=doc.path,
            content=doc.content,
            metadata=doc.metadata,
        )
        return DocumentResponse.from_orm(document)
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    service: DocumentServiceDep,
) -> List[DocumentResponse]:
    """List all documents."""
    documents = await service.list_documents()
    return [DocumentResponse.from_orm(doc) for doc in documents]


@router.get("/{path:path}", response_model=DocumentResponse)
async def get_document(
    path: str,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Get a document by path."""
    try:
        document, content = await service.read_document(path)
        response = DocumentResponse.model_validate(document)
        response.content = content
        return response
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{path:path}", response_model=DocumentResponse)
async def update_document(
    path: str,
    doc: DocumentUpdate,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Update a document's content and/or metadata."""
    try:
        document = await service.update_document(
            path=path,
            content=doc.content,
            metadata=doc.doc_metadata,
        )
        return DocumentResponse.model_validate(document)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{path:path}", response_model=DocumentResponse)
async def patch_document(
    path: str,
    patch: DocumentPatch,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Partially update a document."""
    # Require full content updates for now
    if patch.content is None:
        raise HTTPException(
            status_code=400,
            detail=("Partial content updates not yet implemented. " "Please provide full content."),
        )

    try:
        document = await service.update_document(
            path=path,
            content=patch.content,
            metadata=patch.doc_metadata,
        )
        return DocumentResponse.from_orm(document)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{path:path}", status_code=204)
async def delete_document(
    path: str,
    service: DocumentServiceDep,
) -> None:
    """Delete a document."""
    try:
        await service.delete_document(path)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))
