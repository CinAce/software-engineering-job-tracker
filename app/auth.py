from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, security
from app.db import get_db

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
    auto_error=False,
)


def current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "not authenticated",
        )

    try:
        payload = security.decode_access_token(token)
    except Exception:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "invalid token",
        ) from None

    user = db.scalar(
        select(models.User).where(
            models.User.email == payload.get("sub")
        )
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "unknown or inactive user",
        )

    return user
