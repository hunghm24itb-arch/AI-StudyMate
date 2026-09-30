import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from google.genai.errors import ServerError

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.services.study_service import StudyService
from app.services.gemini_service import GeminiService
from app.services.vector_service import VectorService
from tests.conftest import reset_db


class StubGemini:
    def __init__(self):
        self.prompt = ""

    def embed_text(self, text):
        assert text == "What does the plant produce?"
        return [0.2, 0.4]

    def generate_text(self, prompt, system_instruction=None):
        self.prompt = prompt
        self.system_instruction = system_instruction
        return "The plant produces glucose and oxygen."


class StubVector:
    def __init__(self):
        self.arguments = None

    def search(self, user_id, document_id, query_embedding, limit):
        self.arguments = (user_id, document_id, query_embedding, limit)
        return {
            "documents": [["Retrieved material: plants produce glucose and oxygen."]],
            "metadatas": [[{
                "user_id": str(user_id),
                "document_id": str(document_id),
                "filename": "plants.txt",
                "page": 1,
            }]],
        }


def test_study_question_uses_vector_retrieval_as_gemini_context():
    reset_db()
    db = SessionLocal()
    user = User(email="retrieval@example.com", name="Retrieval", password_hash="unused")
    db.add(user)
    db.commit()
    document = Document(
        user_id=user.id,
        filename="plants.txt",
        storage_name="plants.txt",
        content_type="text/plain",
        file_size=10,
        status="READY",
    )
    db.add(document)
    db.commit()
    db.add(DocumentChunk(document_id=document.id, chunk_index=0, content="Stored database text", page=1, source_filename="plants.txt", chunk_metadata={}))
    db.commit()

    service = StudyService(db)
    gemini = StubGemini()
    vector = StubVector()
    service.gemini = gemini
    service.vector = vector

    response = service.ask_question(user.id, document.id, "What does the plant produce?")

    assert vector.arguments == (user.id, document.id, [0.2, 0.4], 4)
    assert "Retrieved material: plants produce glucose and oxygen." in gemini.prompt
    assert "Stored database text" not in gemini.prompt
    assert "[Source: plants.txt, page 1]" in gemini.prompt
    assert "explicitly say" in gemini.system_instruction
    assert response.answer == "The plant produces glucose and oxygen."
    assert response.sources[0].filename == "plants.txt"
    assert response.sources[0].page == 1
    db.close()


def test_study_question_reports_gemini_429_without_fallback_answer():
    reset_db()
    db = SessionLocal()
    user = User(email="quota@example.com", name="Quota", password_hash="unused")
    db.add(user)
    db.commit()
    document = Document(
        user_id=user.id,
        filename="plants.txt",
        storage_name="plants.txt",
        content_type="text/plain",
        file_size=10,
        status="READY",
    )
    db.add(document)
    db.commit()
    db.add(DocumentChunk(document_id=document.id, chunk_index=0, content="Stored plant information", page=1, source_filename="plants.txt", chunk_metadata={}))
    db.commit()

    class QuotaGemini(StubGemini):
        def generate_text(self, prompt, system_instruction=None):
            raise ServerError(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota exhausted"}})

    service = StudyService(db)
    service.gemini = QuotaGemini()
    service.vector = StubVector()

    with pytest.raises(HTTPException) as raised:
        service.ask_question(user.id, document.id, "What does the plant produce?")

    assert raised.value.status_code == 429
    assert "No answer was generated" in raised.value.detail
    db.close()


def test_study_question_rejects_another_users_document_before_ai_call():
    reset_db()
    db = SessionLocal()
    owner = User(email="document-owner@example.com", name="Owner", password_hash="unused")
    other = User(email="document-other@example.com", name="Other", password_hash="unused")
    db.add_all([owner, other])
    db.commit()
    document = Document(
        user_id=owner.id,
        filename="private.txt",
        storage_name="private.txt",
        content_type="text/plain",
        file_size=10,
        status="READY",
    )
    db.add(document)
    db.commit()
    service = StudyService(db)

    with pytest.raises(HTTPException) as raised:
        service.ask_question(other.id, document.id, "What is in this document?")

    assert raised.value.status_code == 404
    db.close()


def test_study_endpoint_returns_not_found_for_another_users_document():
    reset_db()
    client = TestClient(app)
    owner = client.post("/api/auth/register", json={"name": "Owner", "email": "rag-owner@example.com", "password": "pass123"})
    other = client.post("/api/auth/register", json={"name": "Other", "email": "rag-other@example.com", "password": "pass123"})
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
        "/api/study/ask",
        json={"document_id": document.id, "question": "What is in this file?"},
        headers={"Authorization": f"Bearer {other.json()['access_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"
    db.close()


def test_study_endpoint_returns_clear_429_when_gemini_generation_is_unavailable(monkeypatch):
    reset_db()
    client = TestClient(app)
    registered = client.post("/api/auth/register", json={"name": "Student", "email": "study-quota@example.com", "password": "pass123"})
    db = SessionLocal()
    document = Document(
        user_id=registered.json()["user"]["id"],
        filename="plants.txt",
        storage_name="plants.txt",
        content_type="text/plain",
        file_size=10,
        status="READY",
    )
    db.add(document)
    db.commit()
    db.add(DocumentChunk(document_id=document.id, chunk_index=0, content="Stored plant information", page=1, source_filename="plants.txt", chunk_metadata={}))
    db.commit()
    document_id = document.id
    user_id = registered.json()["user"]["id"]
    db.close()

    monkeypatch.setattr(GeminiService, "embed_text", lambda self, text: [0.1, 0.2])
    monkeypatch.setattr(
        VectorService,
        "search",
        lambda self, current_user_id, current_document_id, query_embedding, limit: {
            "documents": [["Stored plant information"]],
            "metadatas": [[{"user_id": str(current_user_id), "document_id": str(current_document_id), "filename": "plants.txt", "page": 1}]],
        },
    )

    def raise_quota_error(self, prompt, system_instruction=None):
        raise ServerError(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota exhausted"}})

    monkeypatch.setattr(GeminiService, "generate_text", raise_quota_error)
    response = client.post(
        "/api/study/ask",
        json={"document_id": document_id, "question": "What does the plant produce?"},
        headers={"Authorization": f"Bearer {registered.json()['access_token']}"},
    )

    assert response.status_code == 429
    assert "temporarily unavailable" in response.json()["detail"]
    assert "No answer was generated" in response.json()["detail"]