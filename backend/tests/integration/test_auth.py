import asyncio

import jwt
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from account.domain.user import UserRole
from account.infra.db.sql_models import UserModel
from shared.infra.api.auth_dependencies import AuthContext, optional_user, require_role
from shared.infra.api.exception_handlers import register_exception_handlers
from shared.infra.db.config import settings
from wallet.infra.db.sql_models import WalletModel

PASSWORD = "segredo123"


def _register_payload(email="ana@example.com", role="BIDDER", **overrides):
    return {"name": "Ana", "email": email, "password": PASSWORD, "role": role, **overrides}


async def _register_and_login(client, email="ana@example.com", role="BIDDER"):
    registered = await client.post("/auth/register", json=_register_payload(email, role))
    assert registered.status_code == 201
    response = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return response


async def test_register_creates_user_and_empty_wallet(client, db_session):
    response = await client.post("/auth/register", json=_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert body["role"] == "BIDDER"
    assert "password" not in body and "password_hash" not in body

    user = (await db_session.execute(select(UserModel))).scalar_one()
    assert user.password_hash != PASSWORD
    wallet = (await db_session.execute(select(WalletModel))).scalar_one()
    assert wallet.user_id == user.id
    assert (wallet.balance, wallet.committed) == (0, 0)


async def test_auctioneer_also_gets_a_wallet(client, db_session):
    await client.post("/auth/register", json=_register_payload(role="AUCTIONEER"))

    assert len((await db_session.execute(select(WalletModel))).scalars().all()) == 1


async def test_register_rejects_duplicate_email_case_insensitively(client):
    await client.post("/auth/register", json=_register_payload("ana@example.com"))

    response = await client.post("/auth/register", json=_register_payload("  ANA@Example.com"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_concurrent_duplicate_registrations_create_a_single_user(client, db_session):
    responses = await asyncio.gather(
        client.post("/auth/register", json=_register_payload()),
        client.post("/auth/register", json=_register_payload()),
    )

    assert sorted(r.status_code for r in responses) == [201, 409]
    assert len((await db_session.execute(select(UserModel))).scalars().all()) == 1
    assert len((await db_session.execute(select(WalletModel))).scalars().all()) == 1


async def test_register_validates_input(client):
    response = await client.post(
        "/auth/register", json=_register_payload(password="curta", role="ADMIN")
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {f["field"] for f in error["details"]["fields"]} == {"password", "role"}


async def test_login_sets_httponly_cookies_and_me_returns_user(client):
    response = await _register_and_login(client, "Ana@Example.com")

    set_cookie = response.headers.get_list("set-cookie")
    assert any(c.startswith("access_token=") and "HttpOnly" in c for c in set_cookie)
    assert not any(c.startswith("refresh_token=") for c in set_cookie)
    assert "access_token" not in response.json()

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "ana@example.com"


async def test_login_with_wrong_password_or_unknown_email_gives_same_error(client):
    await client.post("/auth/register", json=_register_payload())

    wrong_password = await client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "errada123"}
    )
    unknown_email = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong_password.json() == unknown_email.json()


async def test_me_without_session_is_401(client):
    response = await client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_expired_token_is_401(client):
    await _register_and_login(client)
    user_id = (await client.get("/auth/me")).json()["id"]
    expired = jwt.encode(
        {"sub": user_id, "type": "access", "exp": 0},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set("access_token", expired)

    assert (await client.get("/auth/me")).status_code == 401


async def test_refresh_route_no_longer_exists(client):
    assert (await client.post("/auth/refresh")).status_code == 404


async def test_logout_clears_cookies(client):
    await _register_and_login(client)

    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401


_probe = FastAPI()
register_exception_handlers(_probe)


@_probe.get("/auctioneer-only")
async def _auctioneer_only(auth: AuthContext = Depends(require_role(UserRole.AUCTIONEER))):
    return {"role": auth.user.role.value}


@_probe.get("/maybe-user")
async def _maybe_user(auth: AuthContext | None = Depends(optional_user)):
    return {"email": auth.user.email if auth else None}


async def _probe_get(client, path):
    async with AsyncClient(
        transport=ASGITransport(app=_probe), base_url="http://test", cookies=client.cookies
    ) as probe:
        return await probe.get(path)


async def test_require_role(client):
    assert (await _probe_get(client, "/auctioneer-only")).status_code == 401

    await _register_and_login(client, "bidder@example.com", "BIDDER")
    forbidden = await _probe_get(client, "/auctioneer-only")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "WRONG_ROLE"

    await _register_and_login(client, "boss@example.com", "AUCTIONEER")
    assert (await _probe_get(client, "/auctioneer-only")).json() == {"role": "AUCTIONEER"}


async def test_optional_user_is_anonymous_without_or_with_bad_cookie(client):
    assert (await _probe_get(client, "/maybe-user")).json() == {"email": None}

    client.cookies.set("access_token", "not-a-jwt")
    assert (await _probe_get(client, "/maybe-user")).json() == {"email": None}

    client.cookies.clear()
    await _register_and_login(client)
    assert (await _probe_get(client, "/maybe-user")).json() == {"email": "ana@example.com"}
