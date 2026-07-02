from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.schemas import TokenResponse, UserCreate, UserLogin, UserRead
from app.auth.security import create_access_token
from app.auth.service import authenticate_user, register_user
from app.db import get_session
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(data: UserCreate, session: Session = Depends(get_session)):
    user = register_user(session, data)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, session: Session = Depends(get_session)):
    user = authenticate_user(session, data.email, data.password)
    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user=Depends(get_current_user)):
    return current_user
