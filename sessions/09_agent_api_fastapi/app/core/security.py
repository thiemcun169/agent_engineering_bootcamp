"""Authentication: who is calling. The demo tokens stand in for an identity provider (OAuth/OIDC); a real service
verifies a signed token (issuer, audience, expiry) instead of looking it up in a file."""
import json
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.schemas import User

bearer = HTTPBearer(auto_error=False)  # reads "Authorization: Bearer <token>"; adds the Authorize button to /docs


@lru_cache
def load_users() -> dict[str, User]:
    users = json.loads(get_settings().users_file.read_text())["users"]
    return {u["token"]: User(user_id=u["user_id"], name=u["name"]) for u in users}


async def current_user(cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    user = load_users().get(cred.credentials) if cred else None
    if user is None:
        raise HTTPException(401, "Missing or invalid bearer token", headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(current_user)]
