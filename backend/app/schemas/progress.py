from pydantic import BaseModel


class TopicPerformanceResponse(BaseModel):
    topic: str
    attempts: int
    total_questions: int
    correct_answers: int
    accuracy: float
    latest_score: int
    status: str

    class Config:
        from_attributes = True


class ProgressOverview(BaseModel):
    total_quizzes: int
    average_score: float
    overall_accuracy: float
    weak_topics: list[str]
    strong_topics: list[str]
    normal_topics: list[str]
    recent_attempts: list[dict]
    topic_performance: list[TopicPerformanceResponse]
