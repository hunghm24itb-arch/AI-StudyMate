from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.security import hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, name: str, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        if self.db.query(User).filter(User.email == normalized_email).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User(
            name=name.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> User | None:
        user = self.db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
