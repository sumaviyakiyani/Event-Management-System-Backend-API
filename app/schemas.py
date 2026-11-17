"""Pydantic v2 schemas: request validation and response models."""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------- Events ----------
class EventCreate(BaseModel):
    """Body for POST /events and PUT /events/{id}."""

    model_config = ConfigDict(str_strip_whitespace=True)  # "   " becomes "" and is rejected

    title: str = Field(..., min_length=1, max_length=200, examples=["Python Workshop"])
    description: str | None = Field(None, max_length=5000)
    event_date: datetime = Field(..., examples=["2026-11-20T10:00:00"])
    location: str = Field(..., min_length=1, max_length=255, examples=["Main Hall"])
    capacity: int = Field(..., gt=0, examples=[50])

    @field_validator("event_date")
    @classmethod
    def to_naive_utc(cls, value: datetime) -> datetime:
        """Store dates as naive UTC; timezone-aware input is converted first."""
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class EventRead(BaseModel):
    """Event as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    event_date: datetime
    location: str
    capacity: int
    created_at: datetime


# ---------- Registrations ----------
class RegistrationCreate(BaseModel):
    """Body for POST /events/{id}/registrations."""

    model_config = ConfigDict(str_strip_whitespace=True)

    employee_name: str = Field(..., min_length=1, max_length=200, examples=["Ali Khan"])
    employee_email: EmailStr = Field(..., examples=["ali@company.com"])

    @field_validator("employee_email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        """Lower-case so Ali@x.com and ali@x.com count as the same employee."""
        return value.lower()


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_name: str
    employee_email: str
    event_id: int
    registered_at: datetime


# ---------- Users / auth ----------
class UserCreate(BaseModel):
    """Body for POST /auth/register."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, value: str) -> str:
        """bcrypt only accepts passwords up to 72 bytes."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes long")
        return value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ErrorResponse(BaseModel):
    """Shape of error bodies produced by HTTPException."""

    detail: str
