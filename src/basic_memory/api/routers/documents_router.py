"""Router for document management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from basic_memory.deps import DocumentServiceDep, get_search_service
from basic_memory.schemas.request import DocumentRequest, DocumentPathId
from basic_memory.schemas.response import DocumentResponse, DocumentCreateResponse
from basic_memory.services.document_service import (
    DocumentNotFoundError,
    DocumentWriteError,
    DocumentError,
)

# Router
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/create", response_model=DocumentCreateResponse, status_code=201)
async def create_document(
    doc: DocumentRequest,
    background_tasks: BackgroundTasks,
    service: DocumentServiceDep,
    search_service = Depends(get_search_service)
) -> DocumentCreateResponse:
    """Create a new document with search indexing."""
    try:
        document = await service.create_document(
            path_id=doc.path_id,
            content=doc.content,
            metadata=doc.doc_metadata,
        )
        # Index the new document
        await search_service.index_document(
            document,
            doc.content,
            background_tasks=background_tasks
        )
        return DocumentCreateResponse.model_validate(document.__dict__)
    except DocumentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=List[DocumentCreateResponse])
async def list_documents(
    service: DocumentServiceDep,
) -> List[DocumentCreateResponse]:
    """List all documents (without content)."""
    documents = await service.list_documents()
    return [DocumentCreateResponse.model_validate(doc.__dict__) for doc in documents]


@router.get("/{path_id:path}", response_model=DocumentResponse)
async def get_document(
    path_id: DocumentPathId,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Get a document by ID."""
    try:
        document, content = await service.read_document_by_path_id(path_id)
        doc_dict = document.__dict__ | {"content": content}
        response = DocumentResponse.model_validate(doc_dict)
        return response
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path_id}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{path_id:path}", response_model=DocumentResponse)
async def update_document(
    path_id: DocumentPathId,
    doc: DocumentRequest,
    background_tasks: BackgroundTasks,
    service: DocumentServiceDep,
    search_service = Depends(get_search_service)
) -> DocumentResponse:
    """Update a document by ID with search indexing."""
    # Verify FilePaths match
    if doc.path_id != path_id:
        raise HTTPException(
            status_code=400, detail="Document path in URL must match path in request body"
        )

    try:
        document = await service.update_document_by_path_id(
            path_id=path_id,
            content=doc.content,
            metadata=doc.doc_metadata,
        )
        # Update search index
        await search_service.index_document(
            document,
            doc.content,
            background_tasks=background_tasks
        )
        doc_dict = document.__dict__ | {"content": doc.content}
        return DocumentResponse.model_validate(doc_dict)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path_id}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{path_id:path}", status_code=204)
async def delete_document(
    path_id: DocumentPathId,
    background_tasks: BackgroundTasks,
    service: DocumentServiceDep,
    search_service = Depends(get_search_service)
) -> None:
    """Delete a document by ID and remove from search index."""
    try:
        # Delete from storage
        await service.delete_document_by_path_id(path_id)
        # Remove from search index (in background)
        background_tasks.add_task(search_service.delete_by_path_id, path_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path_id}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))