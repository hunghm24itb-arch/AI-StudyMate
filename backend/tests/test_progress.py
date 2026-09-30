from fastapi.testclient import TestClient

from app.main import app
from app.models.quiz import TopicPerformance
from app.database import SessionLocal
from tests.conftest import reset_db

client = TestClient(app)


def test_topic_performance_summary():
    reset_db()
    register = client.post("/api/auth/register", json={"name": "Student", "email": "student@example.com", "password": "pass123"})
    token = register.json()["access_token"]

    db = SessionLocal()
    db.add(TopicPerformance(user_id=1, topic="Math", attempts=1, total_questions=5, correct_answers=3, accuracy=60, latest_score=60, status="NORMAL"))
    db.commit()
    db.close()

    response = client.get("/api/progress", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert any(item["topic"] == "Math" for item in data["topic_performance"])
    assert data["normal_topics"] == ["Math"]
    assert data["strong_topics"] == []
    assert data["weak_topics"] == []
    assert data["overall_accuracy"] == 0
    assert data["average_score"] == 0
