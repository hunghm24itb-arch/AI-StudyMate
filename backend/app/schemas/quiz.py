from pydantic import BaseModel, Field


class QuizQuestionSchema(BaseModel):
    question: str
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_answer: int
    explanation: str
    topic: str
    difficulty: str


class QuizSchema(BaseModel):
    title: str
    topic: str
    difficulty: str
    questions: list[QuizQuestionSchema]


class GenerateQuizRequest(BaseModel):
    document_id: int | None = None
    topic: str | None = None
    difficulty: str = "medium"
    question_count: int = 5


class QuizSubmissionRequest(BaseModel):
    quiz_id: int
    answers: dict[str, int]


class QuizSubmissionResponse(BaseModel):
    score: int
    correct_answers: int
    total_questions: int
    percentage: int
    topic_performance: dict[str, dict[str, float | int | str]]
    question_results: list["QuizQuestionResult"]


class QuizQuestionResult(BaseModel):
    question_id: int
    question: str
    options: list[str]
    selected_answer: int | None
    correct_answer: int
    is_correct: bool
    explanation: str
    topic: str


class QuizListItem(BaseModel):
    id: int
    title: str
    topic: str
    difficulty: str
    question_count: int

    class Config:
        from_attributes = True


class QuizQuestionForAttempt(BaseModel):
    id: int
    question: str
    options: list[str]
    topic: str


class QuizDetail(BaseModel):
    id: int
    title: str
    topic: str
    difficulty: str
    questions: list[QuizQuestionForAttempt]
