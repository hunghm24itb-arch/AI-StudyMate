from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: int
    filename: str
    status: str
    content_type: str
    file_size: int
    summary: str | None = None
    error: str | None = None

    class Config:
        from_attributes = True


class AskQuestionRequest(BaseModel):
    document_id: int
    question: str = Field(..., min_length=1)


class AnswerSource(BaseModel):
    document_id: int
    filename: str
    page: int | None = None


class AskQuestionResponse(BaseModel):
    answer: str
    sources: list[AnswerSource]
