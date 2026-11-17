"""Application settings.

All secrets and connection details come from environment variables (loaded
from the .env file). Nothing sensitive is hardcoded in the source code.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Return an environment variable or stop with a clear message."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Environment variable {name} is not set. "
            "Copy .env.example to .env and fill in the values."
        )
    return value


DATABASE_URL: str = _require("DATABASE_URL")
JWT_SECRET_KEY: str = _require("JWT_SECRET_KEY")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
