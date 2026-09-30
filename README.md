# AI StudyMate

AI StudyMate is a university study assistant with a React frontend and FastAPI backend. It supports JWT authentication, document ingestion and retrieval, study questions, AI-generated quizzes, server-side scoring, adaptive topic selection, and progress summaries.

## Current Features

- Register and log in with a JWT bearer token.
- Upload PDF, DOCX, and TXT files; validate, extract, clean, chunk, and persist content.
- Generate real Gemini embeddings and store/retrieve vectors using persistent ChromaDB.
- Ask questions against retrieved document chunks. Answers use the real Gemini API and include retrieved source/page metadata.
- Generate quizzes from a document or topic, take them without exposing answer keys, submit answers for server-side scoring, and review results.
- Select adaptive quiz topics from persisted user performance and view overall and per-topic progress.

Gemini text generation for RAG answers, summaries, and generated quizzes requires a configured API key and available quota. The last live generation checks received `429 RESOURCE_EXHAUSTED`; those generation outcomes remain unverified. The application does not substitute generated or retrieved content when Gemini is unavailable. Embedding and Chroma retrieval have been verified separately.

## Architecture

The frontend calls the authenticated FastAPI routes, which delegate to services. SQLAlchemy persists users, documents, chunks, quizzes, attempts, and topic performance in PostgreSQL. Document embeddings and retrieval use ChromaDB. The Gemini API is used for embeddings and generation. The component view is [docs/architecture.puml](docs/architecture.puml).

## Configuration

The backend reads `backend/.env` from the backend working directory. Start with `backend/.env.example` if no local `.env` exists. Set a real PostgreSQL `DATABASE_URL`, a strong `JWT_SECRET_KEY`, and `GEMINI_API_KEY` locally; do not commit `.env` or place the Gemini key in frontend variables. Model defaults are `gemini-3.8-flash` and `gemini-embedding-2`. Chroma and uploads default to `./vector_store` and `./uploads`; upload size defaults to 8 MiB.

## Run Locally

Requirements: Python 3.12, PostgreSQL, Node.js, and npm. From PowerShell:

```powershell
Set-Location backend
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`; `GET /api/health` is a liveness check and does not prove database connectivity. In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

The frontend defaults to `http://localhost:8000/api`. Override that URL with `VITE_API_BASE_URL` in the frontend's local environment when needed. The Gemini key remains backend-only.

## API Routes

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/documents`, `POST /api/documents/upload`, `GET /api/documents/{id}`, `POST /api/documents/{id}/summary`
- `POST /api/study/ask`
- `GET /api/quizzes`, `GET /api/quizzes/{id}`, `POST /api/quizzes/generate`, `POST /api/quizzes/adaptive`, `POST /api/quizzes/{id}/submit`
- `GET /api/progress`

User-owned document and quiz routes require authentication and enforce ownership. Quiz detail omits answer keys; answer review is returned only after submission.

## Tests

Run backend tests from `backend` using its virtual environment:

```powershell
python -m pytest
```

Build the frontend from `frontend`:

```powershell
npm run build
```

Automated tests use deterministic test-only Gemini substitutes. They do not verify live generation; a successful real Gemini generation request is still required before claiming RAG, summary, or AI quiz generation is verified.
