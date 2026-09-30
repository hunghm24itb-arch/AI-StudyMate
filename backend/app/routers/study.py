from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.document import AskQuestionRequest, AskQuestionResponse
from app.services.study_service import StudyService

router = APIRouter(tags=["study"])


@router.post("/study/ask", response_model=AskQuestionResponse)
def ask_question(
    payload: AskQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskQuestionResponse:
    service = StudyService(db)
    return service.ask_question(current_user.id, payload.document_id, payload.question)
