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


@router.post("/", response_model=DocumentResponse)
async def create_document(
    doc: DocumentCreate,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Create a new document."""
    try:
        document = await service.create_document(
            path=doc.path,
            content=doc.content,
            metadata=doc.metadata,
        )
        return document
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    service: DocumentServiceDep,
) -> List[DocumentResponse]:
    """List all documents."""
    return await service.list_documents()


@router.get("/{path:path}", response_model=DocumentResponse)
async def get_document(
    path: str,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Get a document by path."""
    try:
        document, content = await service.read_document(path)
        # Attach content to response
        response = DocumentResponse.from_orm(document)
        response.content = content  # type: ignore
        return response
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
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
            metadata=doc.metadata,
        )
        return document
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{path:path}", response_model=DocumentResponse)
async def patch_document(
    path: str,
    patch: DocumentPatch,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """
    Partially update a document.

    TODO: Implement partial content updates to minimize data transfer.
    For now, this is stubbed to require full content on update.
    """
    # For now, require full content updates
    if patch.content is None:
        raise HTTPException(
            status_code=400,
            detail="Partial content updates not yet implemented. Please provide full content.",
        )

    try:
        document = await service.update_document(
            path=path,
            content=patch.content,
            metadata=patch.metadata,
        )
        return document
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
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
        raise HTTPException(status_code=404, detail="Document not found")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))
