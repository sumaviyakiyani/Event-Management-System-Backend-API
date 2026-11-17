"""SQLAlchemy 2.0 ORM models: User, Event, Registration."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    """An account that may create, update and delete events."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))


class Event(Base):
    """A corporate event employees can register for."""

    __tablename__ = "events"
    __table_args__ = (CheckConstraint("capacity > 0", name="ck_events_capacity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    event_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    location: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # passive_deletes lets PostgreSQL's ON DELETE CASCADE remove registrations.
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", passive_deletes=True
    )


class Registration(Base):
    """One employee's registration for one event."""

    __tablename__ = "registrations"
    __table_args__ = (
        # Database-level protection against duplicate registrations.
        UniqueConstraint("event_id", "employee_email", name="uq_registration_event_email"),
        Index("ix_registrations_event_id", "event_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_name: Mapped[str] = mapped_column(String(200))
    employee_email: Mapped[str] = mapped_column(String(255))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped[Event] = relationship(back_populates="registrations")
