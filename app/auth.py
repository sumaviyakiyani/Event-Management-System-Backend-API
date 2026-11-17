"""Password hashing, JWT creation/verification and the current-user dependency."""
import asyncio
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY
from app.db import get_db
from app.models import User

# tokenUrl makes the "Authorize" button in Swagger log in via /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def hash_password(password: str) -> str:
    """Hash with bcrypt (run in a thread because bcrypt is deliberately slow)."""
    hashed = await asyncio.to_thread(bcrypt.hashpw, password.encode(), bcrypt.gensalt())
    return hashed.decode()


async def verify_password(password: str, hashed_password: str) -> bool:
    """Check a plain password against a bcrypt hash."""
    return await asyncio.to_thread(bcrypt.checkpw, password.encode(), hashed_password.encode())


def create_access_token(username: str) -> str:
    """Create a signed JWT whose subject is the username."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency for protected routes: returns the user or raises 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise credentials_error
    username = payload.get("sub")
    if not username:
        raise credentials_error
    user = await db.scalar(select(User).where(User.username == username))
    if user is None:
        raise credentials_error
    return user
