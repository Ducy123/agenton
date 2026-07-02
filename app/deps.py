from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.auth.models import User
from app.auth.security import decode_access_token
from app.auth.service import get_user_by_id
from app.common.errors import UnauthorizedError
from app.db import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    user_id = decode_access_token(token)
    if not user_id:
        raise UnauthorizedError("Invalid or expired token")
    user = get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    return user
