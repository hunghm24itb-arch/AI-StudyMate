export interface User {
  id: number;
  name: string;
  email: string;
}

export interface DocumentItem {
  id: number;
  filename: string;
  status: string;
  content_type: string;
  file_size: number;
  summary?: string | null;
  error?: string | null;
}

export interface AnswerSource {
  document_id: number;
  filename: string;
  page: number | null;
}

export interface StudyAnswer {
  answer: string;
  sources: AnswerSource[];
}

export interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
  topic: string;
}

export interface QuizDetail {
  id: number;
  title: string;
  topic: string;
  difficulty: string;
  questions: QuizQuestion[];
}

export interface QuizItem {
  id: number;
  title: string;
  topic: string;
  difficulty: string;
  question_count: number;
}

export interface QuizQuestionResult {
  question_id: number;
  question: string;
  options: string[];
  selected_answer: number | null;
  correct_answer: number;
  is_correct: boolean;
  explanation: string;
  topic: string;
}

export interface QuizSubmissionResult {
  score: number;
  correct_answers: number;
  total_questions: number;
  percentage: number;
  topic_performance: Record<string, { accuracy: number; attempts: number; status: string; latest_score: number }>;
  question_results: QuizQuestionResult[];
}

export interface TopicPerformance {
  topic: string;
  attempts: number;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  latest_score: number;
  status: 'STRONG' | 'NORMAL' | 'WEAK';
}

export interface RecentQuizAttempt {
  quiz_id: number;
  score: number;
  correct_answers: number;
  total_questions: number;
  submitted_at: string;
}

export interface ProgressOverview {
  total_quizzes: number;
  average_score: number;
  overall_accuracy: number;
  weak_topics: string[];
  normal_topics: string[];
  strong_topics: string[];
  recent_attempts: RecentQuizAttempt[];
  topic_performance: TopicPerformance[];
}
