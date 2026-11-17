# Corporate Event Management API

A REST API for creating corporate events and registering employees, built with **FastAPI**, **PostgreSQL** and **SQLAlchemy 2.0 (async)**. University assignment project.

## Features
- Event CRUD with pagination, title search and date filtering (combinable)
- Employee registration with capacity limit and duplicate prevention (database unique constraint + row locking against overbooking)
- JWT authentication (bcrypt password hashing); only logged-in users can create, update or delete events
- Pydantic v2 validation, clear HTTP status codes (200, 201, 204, 401, 404, 409, 422, 503)
- Swagger UI with a JWT "Authorize" button
- Automated tests (pytest + HTTPX) on a separate test database

## Technologies
Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy 2.0 + asyncpg, Pydantic v2, PyJWT, bcrypt, python-dotenv, pytest, pytest-asyncio, HTTPX, Uvicorn.

## Project structure
```
app/
  config.py     settings from environment variables
  db.py         async engine, sessions, connection check
  models.py     User, Event, Registration tables
  schemas.py    Pydantic request/response models
  auth.py       password hashing, JWT, current-user dependency
  services.py   business rules (capacity, duplicates, locking)
  routers/      HTTP routes: users.py, events.py, registrations.py
  main.py       app creation, startup DB check, error handlers
tests/          conftest.py (test DB setup) and test_events.py
```

## Installation
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## PostgreSQL setup
Install PostgreSQL, then in `psql` as the admin user:
```sql
CREATE USER event_user WITH PASSWORD 'choose-a-password';
CREATE DATABASE event_management OWNER event_user;
CREATE DATABASE event_management_test OWNER event_user;
```
(`event_management_test` is only used by pytest and is wiped by the tests.)

## Environment variables
```bash
cp .env.example .env     # Windows: copy .env.example .env
```
Edit `.env`: put your password in `DATABASE_URL` and `TEST_DATABASE_URL`, and set `JWT_SECRET_KEY`
(`python -c "import secrets; print(secrets.token_urlsafe(48))"`). `.env` is git-ignored; never commit it.

## Run
```bash
uvicorn app.main:app --reload
```
On startup the app checks the PostgreSQL connection and creates the tables. If the database is unreachable it stops with a clear error.

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

To use protected routes in Swagger: call `POST /auth/register`, then click **Authorize** and enter your username and password.

## Tests
```bash
pytest -v
```
Tests use `TEST_DATABASE_URL` and refuse to run against the main database.

## API endpoints
| Method | Path | Auth | Description | Codes |
|---|---|---|---|---|
| POST | /auth/register | – | Create user | 201, 409, 422 |
| POST | /auth/login | – | Login (form data), returns JWT | 200, 401 |
| GET | /auth/me | JWT | Current user | 200, 401 |
| POST | /events | JWT | Create event | 201, 401, 422 |
| GET | /events | – | List events: `skip`, `limit`, `title`, `date` | 200, 422 |
| GET | /events/{id} | – | Get event | 200, 404 |
| PUT | /events/{id} | JWT | Update event | 200, 401, 404, 409, 422 |
| DELETE | /events/{id} | JWT | Delete event (and its registrations) | 204, 401, 404 |
| POST | /events/{id}/registrations | – | Register employee | 201, 404, 409, 422 |
| GET | /events/{id}/registrations | – | List registrations | 200, 404 |
| DELETE | /registrations/{id} | – | Cancel registration | 204, 404 |
| GET | /health | – | API + DB check | 200 |

Example: `GET /events?title=Python&date=2026-11-20&skip=0&limit=10`

## Design notes
- **Overbooking protection:** registering locks the event row (`SELECT ... FOR UPDATE`), then checks duplicates and capacity, then inserts, all in one transaction.
- **Duplicates:** unique constraint on `(event_id, employee_email)`; emails are stored lower-case.
- **Dates:** `event_date` is stored as naive UTC; timezone-aware input is converted.
- Tables are created with `create_all` (no migration tool, to keep the project simple).
