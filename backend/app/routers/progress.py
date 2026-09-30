from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.progress import ProgressOverview
from app.services.progress_service import ProgressService

router = APIRouter(tags=["progress"])


@router.get("/progress", response_model=ProgressOverview)
def get_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProgressOverview:
    service = ProgressService(db)
    overview = service.get_overview(current_user.id)
    return ProgressOverview(**overview)
