"""Authentication with JWT access tokens (FastAPI tutorial "OAuth2 with Password, Bearer with JWT tokens").

Flow:  POST /auth/signup  -> the password is stored only as an Argon2 hash
       POST /auth/token   -> username + password checked -> a signed JWT {"sub": user_id, "exp": ...}
       any other route    -> Authorization: Bearer <JWT> -> current_user() verifies signature and expiry -> User

Used by: routers/auth.py (signup, token), every route that declares `user: CurrentUser`."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from langgraph.store.base import BaseStore
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.schemas import User

# ── Passwords: store only a slow, salted hash ─────────────────────────────────
password_hash = PasswordHash.recommended()  # Argon2
DUMMY_HASH = password_hash.hash("dummy password")  # checked when the user does not exist: same response time
USERS_NS = ("auth", "users")  # store namespace: key = username, value = {user_id, name, password_hash}


async def create_user(store: BaseStore, username: str, password: str, name: str) -> User | None:
    """None if the username is taken."""
    if await store.aget(USERS_NS, username) is not None:
        return None
    await store.aput(USERS_NS, username, {"user_id": username, "name": name,
                                          "password_hash": password_hash.hash(password)})
    return User(user_id=username, name=name)


async def authenticate(store: BaseStore, username: str, password: str) -> User | None:
    item = await store.aget(USERS_NS, username)
    if item is None:
        password_hash.verify(password, DUMMY_HASH)  # do not reveal which usernames exist by timing
        return None
    if not password_hash.verify(password, item.value["password_hash"]):
        return None
    return User(user_id=item.value["user_id"], name=item.value["name"])


# ── Tokens: a signed JWT the client sends back on every request ───────────────
def create_access_token(user: User) -> tuple[str, int]:
    settings = get_settings()
    expires = timedelta(minutes=settings.access_token_minutes)
    claims = {"sub": user.user_id, "name": user.name, "exp": datetime.now(timezone.utc) + expires}
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> User:
    """Verify signature and expiry; raises InvalidTokenError otherwise."""
    settings = get_settings()
    claims = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=[settings.jwt_algorithm])
    return User(user_id=claims["sub"], name=claims.get("name", claims["sub"]))


# OAuth2PasswordBearer reads "Authorization: Bearer <token>" and gives /docs an Authorize form (username + password)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


async def current_user(request: Request, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    unauthorized = HTTPException(401, "Missing, invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    if not token:
        raise unauthorized
    try:
        user = decode_access_token(token)
    except (InvalidTokenError, KeyError):
        raise unauthorized from None
    if await request.app.state.store.aget(USERS_NS, user.user_id) is None:  # account deleted since login
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(current_user)]
