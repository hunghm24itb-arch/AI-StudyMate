import os
from typing import Any

import chromadb

from app.config import settings


class VectorService:
    def __init__(self) -> None:
        os.makedirs(settings.chroma_persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)

    def get_collection(self, user_id: int):
        collection_name = f"user_{user_id}_documents"
        return self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, user_id: int, document_id: int, chunks: list[str], embeddings: list[list[float]], metadata: list[dict[str, Any]]) -> None:
        collection = self.get_collection(user_id)
        ids = [f"{document_id}_{index}" for index in range(len(chunks))]
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadata,
        )

    def search(self, user_id: int, document_id: int, query_embedding: list[float], limit: int = 4):
        collection = self.get_collection(user_id)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"document_id": str(document_id)},
        )
