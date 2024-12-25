"""Router for document management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from basic_memory.deps import DocumentServiceDep
from basic_memory.schemas.request import DocumentRequest, FilePath
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
    service: DocumentServiceDep,
) -> DocumentCreateResponse:
    """Create a new document.

    The document will be created with appropriate frontmatter including:
    - Generated ID
    - Creation timestamp
    - Last modified timestamp
    - Any provided doc_metadata
    """
    try:
        document = await service.create_document(
            doc_path=doc.path,
            content=doc.content,
            metadata=doc.doc_metadata,
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


@router.get("/{doc_path:path}", response_model=DocumentResponse)
async def get_document(
    doc_path: FilePath,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Get a document by ID."""
    try:
        document, content = await service.read_document_by_path(doc_path)
        doc_dict = document.__dict__ | {"content": content}
        response = DocumentResponse.model_validate(doc_dict)
        return response
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{doc_path:path}", response_model=DocumentResponse)
async def update_document(
    doc_path: FilePath,
    doc: DocumentRequest,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Update a document by ID."""
    # Verify FilePaths match
    if doc.path != doc_path:
        raise HTTPException(
            status_code=400, detail="Document path in URL must match path in request body"
        )

    try:
        document = await service.update_document_by_path(
            path_id=doc_path,
            content=doc.content,
            metadata=doc.doc_metadata,
        )
        doc_dict = document.__dict__ | {"content": doc.content}
        return DocumentResponse.model_validate(doc_dict)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {id}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{doc_path:path}", status_code=204)
async def delete_document(
    doc_path: FilePath,
    service: DocumentServiceDep,
) -> None:
    """Delete a document by ID."""
    try:
        await service.delete_document_by_path(doc_path)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {id}")
    except DocumentWriteError as e:
        raise HTTPException(status_code=400, detail=str(e))
