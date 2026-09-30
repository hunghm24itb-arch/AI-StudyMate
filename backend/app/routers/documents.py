from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.document import AskQuestionRequest, AskQuestionResponse, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


@router.post("/documents/upload", response_model=DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    service = DocumentService(db)
    try:
        document = service.process_document(current_user.id, file)
        return DocumentResponse.model_validate(document)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DocumentResponse]:
    service = DocumentService(db)
    documents = service.get_documents_for_user(current_user.id)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentResponse:
    service = DocumentService(db)
    document = service.get_document_for_user(current_user.id, document_id)
    return DocumentResponse.model_validate(document)


@router.post("/documents/{document_id}/summary")
def summarize_document(document_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    service = DocumentService(db)
    summary = service.generate_summary(current_user.id, document_id)
    return {"summary": summary}
