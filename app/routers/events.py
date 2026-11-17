"""Event CRUD routes. Reading is public; create/update/delete need a JWT."""
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import ErrorResponse, EventCreate, EventRead

router = APIRouter(prefix="/events", tags=["Events"])

_401 = {401: {"model": ErrorResponse, "description": "Missing or invalid token"}}
_404 = {404: {"model": ErrorResponse, "description": "Event not found"}}


@router.post(
    "", response_model=EventRead, status_code=status.HTTP_201_CREATED,
    summary="Create an event (login required)", responses=_401,
)
async def create_event(
    data: EventCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)
):
    return await services.create_event(db, data)


@router.get(
    "", response_model=list[EventRead], summary="List events",
    description="Supports pagination (`skip`, `limit`), title search and filtering by date. "
    "All parameters can be combined.",
)
async def list_events(
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum events to return"),
    title: str | None = Query(None, description="Case-insensitive title search"),
    on_date: date | None = Query(None, alias="date", description="Only events on this day (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    return await services.list_events(db, skip, limit, title, on_date)


@router.get("/{event_id}", response_model=EventRead, summary="Get one event", responses=_404)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    return await services.get_event_or_404(db, event_id)


@router.put(
    "/{event_id}", response_model=EventRead, summary="Update an event (login required)",
    responses={**_401, **_404, 409: {"model": ErrorResponse, "description": "Capacity below current registrations"}},
)
async def update_event(
    event_id: int, data: EventCreate, db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await services.update_event(db, event_id, data)


@router.delete(
    "/{event_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event (login required)", responses={**_401, **_404},
)
async def delete_event(
    event_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)
):
    await services.delete_event(db, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
