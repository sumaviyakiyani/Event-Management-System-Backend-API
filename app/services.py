"""Business logic. Routers call these functions; they talk to the database."""
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import auth
from app.models import Event, Registration, User
from app.schemas import EventCreate, RegistrationCreate, UserCreate


# ---------- Users ----------
async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """Create a user; 409 if username or email is taken."""
    exists = await db.scalar(
        select(User.id).where((User.username == data.username) | (User.email == data.email))
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already registered")
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=await auth.hash_password(data.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:  # two simultaneous sign-ups with the same name
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already registered")
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    """Return the user for valid credentials, otherwise raise 401."""
    user = await db.scalar(select(User).where(User.username == username))
    if user is None or not await auth.verify_password(password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ---------- Events ----------
async def get_event_or_404(db: AsyncSession, event_id: int, lock: bool = False) -> Event:
    """Fetch an event or raise 404. lock=True takes a row lock (SELECT ... FOR UPDATE)."""
    query = select(Event).where(Event.id == event_id)
    if lock:
        query = query.with_for_update()
    event = await db.scalar(query)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Event {event_id} not found")
    return event


async def create_event(db: AsyncSession, data: EventCreate) -> Event:
    event = Event(**data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_events(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    title: str | None = None,
    on_date: date | None = None,
) -> list[Event]:
    """List events. Filters (title, date) and pagination can be combined."""
    query = select(Event)
    if title:
        query = query.where(Event.title.ilike(f"%{title}%"))
    if on_date:
        start = datetime.combine(on_date, time.min)
        query = query.where(Event.event_date >= start, Event.event_date < start + timedelta(days=1))
    query = query.order_by(Event.event_date, Event.id).offset(skip).limit(limit)
    return list((await db.scalars(query)).all())


async def _count_registrations(db: AsyncSession, event_id: int) -> int:
    return await db.scalar(
        select(func.count(Registration.id)).where(Registration.event_id == event_id)
    ) or 0


async def update_event(db: AsyncSession, event_id: int, data: EventCreate) -> Event:
    """Replace an event's fields. Capacity cannot drop below current registrations."""
    event = await get_event_or_404(db, event_id, lock=True)
    if data.capacity < await _count_registrations(db, event_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Capacity cannot be lower than the number of registrations"
        )
    for field, value in data.model_dump().items():
        setattr(event, field, value)
    await db.commit()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event_id: int) -> None:
    """Delete an event (its registrations are removed by ON DELETE CASCADE)."""
    event = await get_event_or_404(db, event_id)
    await db.delete(event)
    await db.commit()


# ---------- Registrations ----------
async def register_employee(db: AsyncSession, event_id: int, data: RegistrationCreate) -> Registration:
    """Register an employee inside one transaction.

    The event row is locked (SELECT ... FOR UPDATE) so two simultaneous
    requests for the last seat are processed one after the other. This
    prevents overbooking. The unique constraint is a second safety net.
    """
    event = await get_event_or_404(db, event_id, lock=True)

    duplicate = await db.scalar(
        select(Registration.id).where(
            Registration.event_id == event_id,
            Registration.employee_email == data.employee_email,
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "Employee is already registered for this event")

    if await _count_registrations(db, event_id) >= event.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "Event is full")

    registration = Registration(event_id=event_id, **data.model_dump())
    db.add(registration)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Employee is already registered for this event")
    await db.refresh(registration)
    return registration


async def list_registrations(db: AsyncSession, event_id: int) -> list[Registration]:
    await get_event_or_404(db, event_id)
    result = await db.scalars(
        select(Registration).where(Registration.event_id == event_id).order_by(Registration.id)
    )
    return list(result.all())


async def cancel_registration(db: AsyncSession, registration_id: int) -> None:
    registration = await db.get(Registration, registration_id)
    if registration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Registration {registration_id} not found")
    await db.delete(registration)
    await db.commit()
