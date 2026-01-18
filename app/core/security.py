from fastapi import Header

from app.core.config import API_TOKEN
from app.core.exceptions import AuthError


def verify_bearer_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization:
        raise AuthError()
    if not authorization.startswith("Bearer "):
        raise AuthError()
    token = authorization.split("Bearer ", 1)[1].strip()
    if token != API_TOKEN:
        raise AuthError()
