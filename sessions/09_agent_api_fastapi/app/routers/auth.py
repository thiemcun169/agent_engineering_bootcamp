"""Sign up and sign in. Sign-in follows OAuth2's password flow: a form with username + password returns a bearer
token, so Swagger UI's "Authorize" button works too."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import CurrentUser, authenticate, create_access_token, create_user
from app.dependencies import Store
from app.schemas import SignupRequest, Token, User

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/signup", status_code=201)
async def signup(body: SignupRequest, store: Store) -> User:
    user = await create_user(store, body.username, body.password, body.name)
    if user is None:
        raise HTTPException(409, f"Username {body.username} is already taken")
    logger.info("user %s signed up", user.user_id)
    return user


@router.post("/token")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], store: Store) -> Token:
    user = await authenticate(store, form.username, form.password)
    if user is None:  # same answer for an unknown user and a wrong password
        raise HTTPException(401, "Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    token, expires_in = create_access_token(user)
    return Token(access_token=token, expires_in=expires_in)


@router.get("/me")
async def me(user: CurrentUser) -> User:
    return user
