from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.quiz import Quiz, Question
from app.models.user import User
from app.schemas.quiz import GenerateQuizRequest, QuizDetail, QuizListItem, QuizQuestionForAttempt, QuizSubmissionRequest, QuizSubmissionResponse
from app.services.quiz_service import QuizService

router = APIRouter(tags=["quizzes"])


@router.get("/quizzes", response_model=list[QuizListItem])
def list_quizzes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[QuizListItem]:
    quizzes = db.query(Quiz).filter(Quiz.user_id == current_user.id).order_by(Quiz.created_at.desc()).all()
    items = []
    for quiz in quizzes:
        items.append(
            QuizListItem(
                id=quiz.id,
                title=quiz.title,
                topic=quiz.topic,
                difficulty=quiz.difficulty,
                question_count=db.query(Question).filter(Question.quiz_id == quiz.id).count(),
            )
        )
    return items


@router.get("/quizzes/{quiz_id}", response_model=QuizDetail)
def get_quiz(quiz_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> QuizDetail:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == current_user.id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    questions = db.query(Question).filter(Question.quiz_id == quiz.id).order_by(Question.id).all()
    return QuizDetail(
        id=quiz.id,
        title=quiz.title,
        topic=quiz.topic,
        difficulty=quiz.difficulty,
        questions=[
            QuizQuestionForAttempt(
                id=question.id,
                question=question.question,
                options=question.options,
                topic=question.topic,
            )
            for question in questions
        ],
    )


@router.post("/quizzes/generate", response_model=dict)
def generate_quiz(payload: GenerateQuizRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    service = QuizService(db)
    quiz = service.generate_quiz(current_user.id, payload.document_id, payload.topic, payload.difficulty, payload.question_count)
    return {
        "id": quiz.id,
        "title": quiz.title,
        "topic": quiz.topic,
        "difficulty": quiz.difficulty,
        "question_count": db.query(Question).filter(Question.quiz_id == quiz.id).count(),
    }


@router.post("/quizzes/adaptive", response_model=dict)
def generate_adaptive_quiz(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    service = QuizService(db)
    quiz = service.generate_adaptive_quiz(current_user.id)
    return {
        "id": quiz.id,
        "title": quiz.title,
        "topic": quiz.topic,
        "difficulty": quiz.difficulty,
        "question_count": db.query(Question).filter(Question.quiz_id == quiz.id).count(),
    }


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizSubmissionResponse)
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizSubmissionResponse:
    if payload.quiz_id != quiz_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz ID mismatch")
    service = QuizService(db)
    result = service.submit_quiz(current_user.id, quiz_id, payload.answers)
    return QuizSubmissionResponse(**result)
