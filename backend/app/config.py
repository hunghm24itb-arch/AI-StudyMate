from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI-StudyMate"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_studymate"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "gemini-embedding-2"
    chroma_persist_directory: str = "./vector_store"
    upload_dir: str = "./uploads"
    max_upload_size: int = 8 * 1024 * 1024
    allowed_extensions: set[str] = {".pdf", ".docx", ".txt"}
    allowed_content_types: set[str] = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
