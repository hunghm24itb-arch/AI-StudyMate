import os
from pathlib import Path

test_database_path = Path(__file__).resolve().parents[1] / ".pytest_cache" / "test_app.db"
test_database_path.parent.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{test_database_path.as_posix()}"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.dependencies import get_db
from app.main import app
from app.schemas.quiz import QuizSchema
from app.services.gemini_service import GeminiService


def fake_generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
    return "This answer is grounded in the uploaded material."


def fake_generate_json(self, prompt: str, schema, system_instruction: str | None = None):
    return schema.model_validate(
        {
            "title": "Sample quiz",
            "topic": "General",
            "difficulty": "medium",
            "questions": [
                {
                    "question": "What is 2 + 2?",
                    "options": ["3", "4", "5", "6"],
                    "correct_answer": 1,
                    "explanation": "Two plus two equals four.",
                    "topic": "General",
                    "difficulty": "medium",
                }
            ],
        }
    )


GeminiService.generate_text = fake_generate_text
GeminiService.generate_json = fake_generate_json

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
