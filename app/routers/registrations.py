"""Registration routes (public, as in the assignment)."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.db import get_db
from app.schemas import ErrorResponse, RegistrationCreate, RegistrationRead

router = APIRouter(tags=["Registrations"])


@router.post(
    "/events/{event_id}/registrations", response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED, summary="Register an employee for an event",
    responses={
        404: {"model": ErrorResponse, "description": "Event not found"},
        409: {"model": ErrorResponse, "description": "Duplicate registration or event full"},
    },
)
async def register(event_id: int, data: RegistrationCreate, db: AsyncSession = Depends(get_db)):
    return await services.register_employee(db, event_id, data)


@router.get(
    "/events/{event_id}/registrations", response_model=list[RegistrationRead],
    summary="List registrations of an event",
    responses={404: {"model": ErrorResponse, "description": "Event not found"}},
)
async def list_registrations(event_id: int, db: AsyncSession = Depends(get_db)):
    return await services.list_registrations(db, event_id)


@router.delete(
    "/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel a registration",
    responses={404: {"model": ErrorResponse, "description": "Registration not found"}},
)
async def cancel_registration(registration_id: int, db: AsyncSession = Depends(get_db)):
    await services.cancel_registration(db, registration_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
