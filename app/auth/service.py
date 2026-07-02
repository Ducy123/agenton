from sqlmodel import Session, select

from app.auth.models import User
from app.auth.schemas import UserCreate
from app.auth.security import hash_password, verify_password
from app.common.errors import ConflictError, UnauthorizedError


def register_user(session: Session, data: UserCreate) -> User:
    existing = session.exec(select(User).where(User.email == data.email)).first()
    if existing:
        raise ConflictError("An account with this email already exists")

    try:
        hashed = hash_password(data.password)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc

    user = User(
        email=data.email,
        hashed_password=hashed,
        display_name=data.display_name or data.email.split("@")[0],
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")
    return user


def get_user_by_id(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)
