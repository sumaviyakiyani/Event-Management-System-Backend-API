"""Authentication routes: register, login, current user."""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import auth, services
from app.db import get_db
from app.models import User
from app.schemas import ErrorResponse, Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account",
    responses={409: {"model": ErrorResponse, "description": "Username or email already used"}},
)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await services.create_user(db, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Log in and receive a JWT access token",
    description="Send username and password as form data. Use the token as `Authorization: Bearer <token>`.",
    responses={401: {"model": ErrorResponse, "description": "Wrong username or password"}},
)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await services.authenticate_user(db, form.username, form.password)
    return Token(access_token=auth.create_access_token(user.username))


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the logged-in user",
    responses={401: {"model": ErrorResponse, "description": "Missing or invalid token"}},
)
async def me(current_user: User = Depends(auth.get_current_user)):
    return current_user
