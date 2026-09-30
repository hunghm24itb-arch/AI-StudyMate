from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.quiz import Question, Quiz, QuizAttempt, TopicPerformance
from app.schemas.quiz import QuizSchema
from app.services.gemini_service import GeminiService


class QuizService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini = GeminiService()

    def _build_document_context(self, user_id: int, document_id: int | None) -> str:
        if not document_id:
            return "General study material."
        document = self.db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if document.status != "READY":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document is not ready for quiz generation.")
        chunks = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index).all()
        return "\n\n".join(chunk.content for chunk in chunks[:8])

    def generate_quiz(self, user_id: int, document_id: int | None, topic: str | None, difficulty: str, question_count: int) -> Quiz:
        if question_count <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question count must be positive.")
        topic_name = topic or "General"
        context = self._build_document_context(user_id, document_id)
        prompt = (
            "Generate a multiple-choice quiz in valid JSON.\n"
            "Return exactly this schema: {\n"
            "  \"title\": string,\n"
            "  \"topic\": string,\n"
            "  \"difficulty\": string,\n"
            "  \"questions\": [{\n"
            "    \"question\": string,\n"
            "    \"options\": [string, string, string, string],\n"
            "    \"correct_answer\": integer,\n"
            "    \"explanation\": string,\n"
            "    \"topic\": string,\n"
            "    \"difficulty\": string\n"
            "  }]\n"
            "}.\n"
            f"Generate {question_count} questions. Topic: {topic_name}. Difficulty: {difficulty}.\n"
            f"Source material:\n{context[:12000]}"
        )
        quiz_schema = self.gemini.generate_json(prompt, QuizSchema)
        quiz = Quiz(
            user_id=user_id,
            document_id=document_id,
            title=quiz_schema.title,
            topic=quiz_schema.topic or topic_name,
            difficulty=quiz_schema.difficulty or difficulty,
        )
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)

        for item in quiz_schema.questions:
            question = Question(
                quiz_id=quiz.id,
                question=item.question,
                options=[str(option) for option in item.options],
                correct_answer=int(item.correct_answer),
                explanation=item.explanation,
                topic=item.topic or quiz.topic,
            )
            self.db.add(question)
        self.db.commit()
        return quiz

    def generate_adaptive_quiz(self, user_id: int, difficulty: str = "medium", question_count: int = 5) -> Quiz:
        rows = (
            self.db.query(TopicPerformance)
            .filter(TopicPerformance.user_id == user_id)
            .order_by(TopicPerformance.accuracy.asc(), TopicPerformance.updated_at.asc())
            .all()
        )
        weak_rows = [row for row in rows if row.status == "WEAK"]
        if weak_rows:
            topic = weak_rows[0].topic
        elif rows:
            topic = rows[0].topic
        else:
            topic = "General"
        return self.generate_quiz(user_id=user_id, document_id=None, topic=topic, difficulty=difficulty, question_count=question_count)

    def submit_quiz(self, user_id: int, quiz_id: int, answers: dict[str, int]) -> dict:
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user_id).first()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

        questions = self.db.query(Question).filter(Question.quiz_id == quiz.id).all()
        correct_answers = 0
        question_results = []
        for question in questions:
            selected = answers.get(str(question.id))
            is_correct = selected == question.correct_answer
            if is_correct:
                correct_answers += 1
            question_results.append({
                "question_id": question.id,
                "question": question.question,
                "options": question.options,
                "selected_answer": selected,
                "correct_answer": question.correct_answer,
                "is_correct": is_correct,
                "explanation": question.explanation,
                "topic": question.topic,
            })

        total_questions = len(questions)
        score = round((correct_answers / total_questions) * 100) if total_questions else 0

        attempt = QuizAttempt(
            user_id=user_id,
            quiz_id=quiz.id,
            score=score,
            correct_answers=correct_answers,
            total_questions=total_questions,
            answers=answers,
        )
        self.db.add(attempt)
        self.db.commit()

        self._update_topic_performance(user_id, quiz.topic, score, total_questions, correct_answers)

        return {
            "score": score,
            "correct_answers": correct_answers,
            "total_questions": total_questions,
            "percentage": score,
            "topic_performance": self._topic_performance_summary(user_id),
            "question_results": question_results,
        }

    def _update_topic_performance(self, user_id: int, topic: str, score: int, total_questions: int, correct_answers: int) -> None:
        record = self.db.query(TopicPerformance).filter(TopicPerformance.user_id == user_id, TopicPerformance.topic == topic).first()
        if not record:
            record = TopicPerformance(user_id=user_id, topic=topic, attempts=0, total_questions=0, correct_answers=0, accuracy=0.0, latest_score=0, status="NORMAL")
            self.db.add(record)

        record.attempts = (record.attempts or 0) + 1
        record.total_questions = (record.total_questions or 0) + total_questions
        record.correct_answers = (record.correct_answers or 0) + correct_answers
        record.latest_score = score
        record.accuracy = round((record.correct_answers / record.total_questions) * 100) if record.total_questions else 0
        if record.accuracy >= 80:
            record.status = "STRONG"
        elif record.accuracy >= 60:
            record.status = "NORMAL"
        else:
            record.status = "WEAK"
        record.updated_at = datetime.utcnow()
        self.db.commit()

    def _topic_performance_summary(self, user_id: int) -> dict:
        rows = self.db.query(TopicPerformance).filter(TopicPerformance.user_id == user_id).all()
        summary = {}
        for row in rows:
            summary[row.topic] = {
                "accuracy": row.accuracy,
                "attempts": row.attempts,
                "status": row.status,
                "latest_score": row.latest_score,
            }
        return summary
