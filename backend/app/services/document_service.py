import os
from pathlib import Path
from typing import Any

from fastapi import UploadFile, HTTPException, status
from google.genai.errors import APIError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document, DocumentChunk
from app.services.gemini_service import GeminiService
from app.services.vector_service import VectorService
from app.utils.file_utils import chunk_text, ensure_upload_directory, extract_pages_from_file, safe_filename, validate_upload


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini = GeminiService()
        self.vector_service = VectorService()

    def _save_upload(self, user_id: int, file: UploadFile) -> tuple[Document, str]:
        validate_upload(file)
        upload_dir = ensure_upload_directory()
        safe_name = safe_filename(file.filename)
        storage_name = f"{user_id}_{safe_name}"
        storage_path = os.path.join(upload_dir, storage_name)

        contents = file.file.read()
        with open(storage_path, "wb") as destination:
            destination.write(contents)

        document = Document(
            user_id=user_id,
            filename=safe_name,
            storage_name=storage_name,
            content_type=file.content_type or "application/octet-stream",
            file_size=len(contents),
            status="PROCESSING",
            error=None,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document, storage_path

    def process_document(self, user_id: int, file: UploadFile) -> Document:
        document, storage_path = self._save_upload(user_id, file)
        try:
            pages = extract_pages_from_file(storage_path)
            chunks_with_pages = []
            for page_number, page_text in pages:
                cleaned_text = " ".join(page_text.split())
                chunks_with_pages.extend((page_number, chunk) for chunk in chunk_text(cleaned_text))
            chunks = [chunk for _, chunk in chunks_with_pages]
            if not chunks:
                raise ValueError("No readable text could be extracted from the uploaded file.")

            embeddings = self.gemini.embed_documents(chunks)
            if len(embeddings) != len(chunks):
                raise ValueError(
                    f"Embedding count mismatch: expected {len(chunks)} vectors for document chunks, "
                    f"received {len(embeddings)}."
                )
            vector_metadata = []
            for index, (page_number, _) in enumerate(chunks_with_pages):
                vector_metadata.append({
                    "user_id": str(user_id),
                    "document_id": str(document.id),
                    "chunk_id": str(index),
                    "filename": document.filename,
                    "page": page_number,
                })

            self.vector_service.add_documents(
                user_id=user_id,
                document_id=document.id,
                chunks=chunks,
                embeddings=embeddings,
                metadata=vector_metadata,
            )

            for index, (page_number, chunk) in enumerate(chunks_with_pages):
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    page=page_number,
                    source_filename=document.filename,
                    chunk_metadata={
                        "user_id": user_id,
                        "document_id": document.id,
                        "chunk_id": index,
                        "filename": document.filename,
                        "page": page_number,
                    },
                )
                self.db.add(db_chunk)

            document.status = "READY"
            document.error = None
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception as exc:  # pragma: no cover - actual failure path
            document.status = "FAILED"
            document.error = str(exc)
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    def get_documents_for_user(self, user_id: int):
        return self.db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).all()

    def get_document_for_user(self, user_id: int, document_id: int) -> Document:
        document = self.db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return document

    def generate_summary(self, user_id: int, document_id: int) -> str:
        document = self.get_document_for_user(user_id, document_id)
        if document.status != "READY":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document is not ready for summarization.")
        chunks = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index).all()
        combined_text = "\n\n".join(chunk.content for chunk in chunks)
        if not combined_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document content is unavailable.")

        prompt = (
            "Summarize the provided study material in a structured format with sections: overview, key_points, "
            "important_concepts, and conclusion. Use only the content provided."
        )
        try:
            summary = self.gemini.generate_text(f"{prompt}\n\nContent:\n{combined_text[:15000]}")
        except APIError as exc:
            if exc.code in {408, 429, 500, 502, 503, 504}:
                detail = f"Gemini summary generation is temporarily unavailable ({exc.code} {exc.status}). No summary was generated."
                raise HTTPException(status_code=exc.code, detail=detail) from exc
            raise
        document.summary = summary
        self.db.commit()
        return summary
