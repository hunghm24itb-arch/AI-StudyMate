from sqlalchemy.orm import Session

from app.models.quiz import QuizAttempt, TopicPerformance


class ProgressService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, user_id: int) -> dict:
        attempts = self.db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).order_by(QuizAttempt.submitted_at.desc()).all()
        topic_rows = self.db.query(TopicPerformance).filter(TopicPerformance.user_id == user_id).order_by(TopicPerformance.updated_at.desc()).all()

        total_quizzes = len({attempt.quiz_id for attempt in attempts})
        average_score = round(sum(attempt.score for attempt in attempts) / len(attempts), 2) if attempts else 0
        overall_accuracy = round(
            sum(attempt.correct_answers for attempt in attempts) / sum(attempt.total_questions for attempt in attempts) * 100,
            2,
        ) if any(attempt.total_questions for attempt in attempts) else 0

        weak_topics = [row.topic for row in topic_rows if row.status == "WEAK"]
        strong_topics = [row.topic for row in topic_rows if row.status == "STRONG"]
        normal_topics = [row.topic for row in topic_rows if row.status == "NORMAL"]

        recent_attempts = [
            {
                "quiz_id": attempt.quiz_id,
                "score": attempt.score,
                "correct_answers": attempt.correct_answers,
                "total_questions": attempt.total_questions,
                "submitted_at": attempt.submitted_at.isoformat(),
            }
            for attempt in attempts[:10]
        ]

        return {
            "total_quizzes": total_quizzes,
            "average_score": average_score,
            "overall_accuracy": overall_accuracy,
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "normal_topics": normal_topics,
            "recent_attempts": recent_attempts,
            "topic_performance": [
                {
                    "topic": row.topic,
                    "attempts": row.attempts,
                    "total_questions": row.total_questions,
                    "correct_answers": row.correct_answers,
                    "accuracy": row.accuracy,
                    "latest_score": row.latest_score,
                    "status": row.status,
                }
                for row in topic_rows
            ],
        }
