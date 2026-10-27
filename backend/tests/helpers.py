from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from auction.infra.db.sql_models import LotModel
from shared.infra.db.database import AsyncSessionLocal

PASSWORD = "segredo123"


async def register(client, email: str, role: str = "BIDDER", name: str = "Ana"):
    response = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": PASSWORD, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(client, email: str) -> None:
    """Logs `client` in; the session cookie stays in its cookie jar."""
    response = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text


async def register_and_login(client, email: str, role: str = "BIDDER"):
    user = await register(client, email, role)
    await login(client, email)
    return user


def at(**delta) -> str:
    """ISO timestamp relative to now, e.g. at(minutes=-5)."""
    return (datetime.now(UTC) + timedelta(**delta)).isoformat()


async def create_lot(
    client,
    external_id: str = "16568",
    starts_at: str | None = None,
    ends_at: str | None = None,
    starting_bid: str = "100.00",
    min_increment: str = "5.00",
) -> dict:
    """Creates a lot as the auctioneer logged in on `client` (live for an hour by default)."""
    response = await client.post(
        "/lots",
        json={
            "external_id": external_id,
            "starting_bid": starting_bid,
            "min_increment": min_increment,
            "starts_at": starts_at or at(minutes=-1),
            "ends_at": ends_at or at(hours=1),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def set_lot_times(lot_id, starts_at: datetime | None = None, ends_at: datetime | None = None):
    """Moves a lot in time directly in the database (the API refuses past end dates).
    Moving only the end into the past also moves the start, to keep ends_at > starts_at."""
    if ends_at is not None and starts_at is None:
        starts_at = min(ends_at - timedelta(hours=1), datetime.now(UTC) - timedelta(hours=1))
    values = {k: v for k, v in {"starts_at": starts_at, "ends_at": ends_at}.items() if v}
    async with AsyncSessionLocal() as session:
        await session.execute(update(LotModel).where(LotModel.id == lot_id).values(**values))
        await session.commit()


async def deposit(client, amount: str) -> None:
    response = await client.post("/wallet/deposit", json={"amount": amount})
    assert response.status_code == 200, response.text


async def bid(client, lot_id, amount: str):
    return await client.post(f"/lots/{lot_id}/bids", json={"amount": amount})


async def wallet(client) -> dict:
    return (await client.get("/wallet")).json()
