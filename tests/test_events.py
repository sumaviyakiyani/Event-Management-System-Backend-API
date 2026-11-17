"""API tests (pytest + HTTPX). Require a PostgreSQL test database."""
import asyncio

EVENT = {
    "title": "Python Workshop",
    "description": "Intro to FastAPI",
    "event_date": "2026-11-20T10:00:00",
    "location": "Main Hall",
    "capacity": 2,
}


async def make_event(client, headers, **overrides):
    resp = await client.post("/events", json={**EVENT, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def reg(n=1):
    return {"employee_name": f"Employee {n}", "employee_email": f"emp{n}@company.com"}


# ---------- Events CRUD ----------
async def test_create_event(client, auth_headers):
    event = await make_event(client, auth_headers)
    assert event["id"] and event["title"] == "Python Workshop" and event["created_at"]


async def test_list_events_is_public(client, auth_headers):
    await make_event(client, auth_headers)
    resp = await client.get("/events")  # no token
    assert resp.status_code == 200 and len(resp.json()) == 1


async def test_get_event(client, auth_headers):
    event = await make_event(client, auth_headers)
    resp = await client.get(f"/events/{event['id']}")
    assert resp.status_code == 200 and resp.json()["id"] == event["id"]


async def test_update_event(client, auth_headers):
    event = await make_event(client, auth_headers)
    resp = await client.put(
        f"/events/{event['id']}", json={**EVENT, "title": "Updated", "capacity": 10}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated" and resp.json()["capacity"] == 10


async def test_delete_event(client, auth_headers):
    event = await make_event(client, auth_headers)
    assert (await client.delete(f"/events/{event['id']}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/events/{event['id']}")).status_code == 404


async def test_delete_event_removes_registrations(client, auth_headers):
    event = await make_event(client, auth_headers)
    reg_id = (await client.post(f"/events/{event['id']}/registrations", json=reg())).json()["id"]
    await client.delete(f"/events/{event['id']}", headers=auth_headers)
    assert (await client.delete(f"/registrations/{reg_id}")).status_code == 404


async def test_non_existent_event(client, auth_headers):
    assert (await client.get("/events/9999")).status_code == 404
    assert (await client.put("/events/9999", json=EVENT, headers=auth_headers)).status_code == 404
    assert (await client.delete("/events/9999", headers=auth_headers)).status_code == 404


# ---------- Validation ----------
async def test_invalid_event_data(client, auth_headers):
    bad_payloads = [
        {**EVENT, "title": ""},
        {**EVENT, "title": "   "},
        {**EVENT, "capacity": 0},
        {**EVENT, "capacity": -5},
        {**EVENT, "event_date": "not-a-date"},
        {k: v for k, v in EVENT.items() if k != "location"},
    ]
    for payload in bad_payloads:
        resp = await client.post("/events", json=payload, headers=auth_headers)
        assert resp.status_code == 422, payload


async def test_invalid_registration_data(client, auth_headers):
    event = await make_event(client, auth_headers)
    url = f"/events/{event['id']}/registrations"
    assert (await client.post(url, json={"employee_name": "", "employee_email": "a@b.com"})).status_code == 422
    assert (await client.post(url, json={"employee_name": "Ali", "employee_email": "bad"})).status_code == 422
    assert (await client.post(url, json={"employee_name": "Ali"})).status_code == 422


# ---------- Pagination, search, date filter ----------
async def test_pagination_search_and_date_filter(client, auth_headers):
    await make_event(client, auth_headers, title="Python Workshop", event_date="2026-11-20T09:00:00")
    await make_event(client, auth_headers, title="Python Advanced", event_date="2026-11-21T09:00:00")
    await make_event(client, auth_headers, title="Team Lunch", event_date="2026-11-20T12:00:00")

    assert len((await client.get("/events?limit=2")).json()) == 2
    assert len((await client.get("/events?skip=2&limit=10")).json()) == 1
    assert len((await client.get("/events?title=python")).json()) == 2
    assert len((await client.get("/events?date=2026-11-20")).json()) == 2
    combined = (await client.get("/events?title=python&date=2026-11-20")).json()
    assert len(combined) == 1 and combined[0]["title"] == "Python Workshop"
    assert (await client.get("/events?limit=0")).status_code == 422


# ---------- Registrations ----------
async def test_register_employee(client, auth_headers):
    event = await make_event(client, auth_headers)
    resp = await client.post(f"/events/{event['id']}/registrations", json=reg())
    assert resp.status_code == 201 and resp.json()["event_id"] == event["id"]
    listing = await client.get(f"/events/{event['id']}/registrations")
    assert listing.status_code == 200 and len(listing.json()) == 1


async def test_duplicate_registration_returns_409(client, auth_headers):
    event = await make_event(client, auth_headers)
    url = f"/events/{event['id']}/registrations"
    assert (await client.post(url, json=reg())).status_code == 201
    assert (await client.post(url, json=reg())).status_code == 409


async def test_event_capacity_limit_returns_409(client, auth_headers):
    event = await make_event(client, auth_headers, capacity=2)
    url = f"/events/{event['id']}/registrations"
    assert (await client.post(url, json=reg(1))).status_code == 201
    assert (await client.post(url, json=reg(2))).status_code == 201
    assert (await client.post(url, json=reg(3))).status_code == 409


async def test_cancel_registration_frees_a_seat(client, auth_headers):
    event = await make_event(client, auth_headers, capacity=1)
    url = f"/events/{event['id']}/registrations"
    first = (await client.post(url, json=reg(1))).json()
    assert (await client.post(url, json=reg(2))).status_code == 409
    assert (await client.delete(f"/registrations/{first['id']}")).status_code == 204
    assert (await client.post(url, json=reg(2))).status_code == 201


async def test_registration_for_missing_event_or_registration(client):
    assert (await client.post("/events/9999/registrations", json=reg())).status_code == 404
    assert (await client.get("/events/9999/registrations")).status_code == 404
    assert (await client.delete("/registrations/9999")).status_code == 404


async def test_capacity_cannot_drop_below_registrations(client, auth_headers):
    event = await make_event(client, auth_headers, capacity=2)
    url = f"/events/{event['id']}/registrations"
    await client.post(url, json=reg(1))
    await client.post(url, json=reg(2))
    resp = await client.put(f"/events/{event['id']}", json={**EVENT, "capacity": 1}, headers=auth_headers)
    assert resp.status_code == 409


async def test_concurrent_registrations_never_overbook(client, auth_headers):
    event = await make_event(client, auth_headers, capacity=2)
    url = f"/events/{event['id']}/registrations"
    responses = await asyncio.gather(*[client.post(url, json=reg(i)) for i in range(6)])
    codes = [r.status_code for r in responses]
    assert codes.count(201) == 2 and codes.count(409) == 4


# ---------- Authentication ----------
async def test_register_and_login(client):
    body = {"username": "alice", "email": "alice@example.com", "password": "Secret123!"}
    created = await client.post("/auth/register", json=body)
    assert created.status_code == 201
    assert "password" not in created.text and "hashed_password" not in created.text
    login = await client.post("/auth/login", data={"username": "alice", "password": "Secret123!"})
    assert login.status_code == 200 and login.json()["token_type"] == "bearer"
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.json()["username"] == "alice"


async def test_duplicate_user_returns_409(client):
    body = {"username": "alice", "email": "alice@example.com", "password": "Secret123!"}
    await client.post("/auth/register", json=body)
    assert (await client.post("/auth/register", json=body)).status_code == 409


async def test_login_with_wrong_password_returns_401(client):
    await client.post(
        "/auth/register", json={"username": "bob", "email": "bob@example.com", "password": "Secret123!"}
    )
    resp = await client.post("/auth/login", data={"username": "bob", "password": "wrong-password"})
    assert resp.status_code == 401


async def test_protected_routes_reject_unauthenticated_requests(client, auth_headers):
    event = await make_event(client, auth_headers)
    assert (await client.post("/events", json=EVENT)).status_code == 401
    assert (await client.put(f"/events/{event['id']}", json=EVENT)).status_code == 401
    assert (await client.delete(f"/events/{event['id']}")).status_code == 401


async def test_invalid_token_is_rejected(client):
    resp = await client.post("/events", json=EVENT, headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401
