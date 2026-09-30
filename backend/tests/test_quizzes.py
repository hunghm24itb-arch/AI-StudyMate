from fastapi.testclient import TestClient

from app.main import app
from app.models.document import Document
from app.models.quiz import Quiz, Question, TopicPerformance
from app.models.user import User
from app.database import SessionLocal
from app.services.quiz_service import QuizService
from tests.conftest import reset_db

client = TestClient(app)


def test_quiz_scoring_and_topic_performance():
    reset_db()
    register = client.post("/api/auth/register", json={"name": "Student", "email": "student@example.com", "password": "pass123"})
    token = register.json()["access_token"]

    db = SessionLocal()
    quiz = Quiz(user_id=1, document_id=None, title="Math quiz", topic="Math", difficulty="medium")
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    db.add_all([
        Question(quiz_id=quiz.id, question="2 + 2", options=["3", "4", "5", "6"], correct_answer=1, explanation="Basic arithmetic.", topic="Math"),
        Question(quiz_id=quiz.id, question="7 * 2", options=["12", "13", "14", "15"], correct_answer=2, explanation="Multiply by two.", topic="Math"),
    ])
    db.commit()
    response = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"quiz_id": quiz.id, "answers": {"1": 0, "2": 2}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 50
    assert data["correct_answers"] == 1
    assert data["total_questions"] == 2
    assert data["question_results"] == [
        {
            "question_id": 1,
            "question": "2 + 2",
            "options": ["3", "4", "5", "6"],
            "selected_answer": 0,
            "correct_answer": 1,
            "is_correct": False,
            "explanation": "Basic arithmetic.",
            "topic": "Math",
        },
        {
            "question_id": 2,
            "question": "7 * 2",
            "options": ["12", "13", "14", "15"],
            "selected_answer": 2,
            "correct_answer": 2,
            "is_correct": True,
            "explanation": "Multiply by two.",
            "topic": "Math",
        },
    ]
    db.close()


def test_adaptive_topic_selection():
    reset_db()
    register = client.post("/api/auth/register", json={"name": "Student", "email": "student@example.com", "password": "pass123"})
    token = register.json()["access_token"]

    response = client.post("/api/quizzes/adaptive", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["topic"] in {"General", "Math"}


def test_adaptive_quiz_prioritizes_weakest_owned_topic(monkeypatch):
    reset_db()
    register = client.post("/api/auth/register", json={"name": "Student", "email": "adaptive@example.com", "password": "pass123"})
    user_id = register.json()["user"]["id"]
    db = SessionLocal()
    db.add_all([
        TopicPerformance(user_id=user_id, topic="Weak Biology", attempts=2, total_questions=10, correct_answers=3, accuracy=30, latest_score=30, status="WEAK"),
        TopicPerformance(user_id=user_id, topic="Normal Math", attempts=2, total_questions=10, correct_answers=7, accuracy=70, latest_score=70, status="NORMAL"),
        TopicPerformance(user_id=user_id + 1, topic="Other User Weak", attempts=1, total_questions=10, correct_answers=0, accuracy=0, latest_score=0, status="WEAK"),
    ])
    db.commit()
    service = QuizService(db)
    selected = {}
    monkeypatch.setattr(service, "generate_quiz", lambda **kwargs: selected.update(kwargs) or "generated")

    result = service.generate_adaptive_quiz(user_id)

    assert result == "generated"
    assert selected["topic"] == "Weak Biology"
    db.close()


def test_adaptive_fallback_uses_lowest_accuracy_from_user_history(monkeypatch):
    reset_db()
    register = client.post("/api/auth/register", json={"name": "Student", "email": "fallback@example.com", "password": "pass123"})
    user_id = register.json()["user"]["id"]
    db = SessionLocal()
    db.add_all([
        TopicPerformance(user_id=user_id, topic="Strong Biology", attempts=1, total_questions=10, correct_answers=9, accuracy=90, latest_score=90, status="STRONG"),
        TopicPerformance(user_id=user_id, topic="Normal Math", attempts=1, total_questions=10, correct_answers=65, accuracy=65, latest_score=65, status="NORMAL"),
    ])
    db.commit()
    service = QuizService(db)
    selected = {}
    monkeypatch.setattr(service, "generate_quiz", lambda **kwargs: selected.update(kwargs) or "generated")

    result = service.generate_adaptive_quiz(user_id)

    assert result == "generated"
    assert selected["topic"] == "Normal Math"
    db.close()


def test_quiz_generation_cannot_read_another_users_document():
    reset_db()
    owner = client.post("/api/auth/register", json={"name": "Owner", "email": "quiz-doc-owner@example.com", "password": "pass123"})
    other = client.post("/api/auth/register", json={"name": "Other", "email": "quiz-doc-other@example.com", "password": "pass123"})
    db = SessionLocal()
    document = Document(
        user_id=owner.json()["user"]["id"],
        filename="private.txt",
        storage_name="private.txt",
        content_type="text/plain",
        file_size=10,
        status="READY",
    )
    db.add(document)
    db.commit()

    response = client.post(
        "/api/quizzes/generate",
        json={"document_id": document.id, "topic": "Private topic", "question_count": 1},
        headers={"Authorization": f"Bearer {other.json()['access_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"
    db.close()


def test_quiz_detail_is_owner_scoped_and_hides_answer_keys():
    reset_db()
    owner = client.post("/api/auth/register", json={"name": "Owner", "email": "owner@example.com", "password": "pass123"})
    other = client.post("/api/auth/register", json={"name": "Other", "email": "other@example.com", "password": "pass123"})
    owner_id = owner.json()["user"]["id"]
    owner_token = owner.json()["access_token"]
    other_token = other.json()["access_token"]

    db = SessionLocal()
    quiz = Quiz(user_id=owner_id, document_id=None, title="Biology quiz", topic="Biology", difficulty="easy")
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    db.add(Question(
        quiz_id=quiz.id,
        question="What does photosynthesis produce?",
        options=["Glucose", "Sand", "Salt", "Iron"],
        correct_answer=0,
        explanation="Plants make glucose.",
        topic="Biology",
    ))
    db.commit()

    detail = client.get(f"/api/quizzes/{quiz.id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert detail.status_code == 200
    assert detail.json()["questions"][0]["options"] == ["Glucose", "Sand", "Salt", "Iron"]
    assert "correct_answer" not in detail.json()["questions"][0]
    assert "explanation" not in detail.json()["questions"][0]

    owner_list = client.get("/api/quizzes", headers={"Authorization": f"Bearer {owner_token}"})
    assert owner_list.status_code == 200
    assert owner_list.json() == [{
        "id": quiz.id,
        "title": "Biology quiz",
        "topic": "Biology",
        "difficulty": "easy",
        "question_count": 1,
    }]

    hidden_detail = client.get(f"/api/quizzes/{quiz.id}", headers={"Authorization": f"Bearer {other_token}"})
    assert hidden_detail.status_code == 404
    assert client.get("/api/quizzes", headers={"Authorization": f"Bearer {other_token}"}).json() == []

    hidden_submission = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"quiz_id": quiz.id, "answers": {}},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert hidden_submission.status_code == 404
    db.close()
