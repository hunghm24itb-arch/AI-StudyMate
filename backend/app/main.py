from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, documents, progress, quizzes, study, health

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI StudyMate",
    version="0.1.0",
    description="AI-powered study assistant for university students.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(documents.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(quizzes.router, prefix="/api")
app.include_router(progress.router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI StudyMate API"}
