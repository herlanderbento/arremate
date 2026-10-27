import asyncio
from decimal import Decimal as D

from sqlalchemy import select

from tests.helpers import login, register, register_and_login
from tests.integration.conftest import new_client
from wallet.infra.db.sql_models import WalletTransactionModel


async def test_new_bidder_wallet_is_empty(client):
    await register_and_login(client, "ana@example.com")

    response = await client.get("/wallet")

    assert response.status_code == 200
    assert response.json() == {"balance": "0.00", "committed": "0.00", "available": "0.00"}


async def test_deposit_updates_balance_and_records_transaction(client, db_session):
    await register_and_login(client, "ana@example.com")

    first = await client.post("/wallet/deposit", json={"amount": "1500.00"})
    second = await client.post("/wallet/deposit", json={"amount": "500.00"})

    assert first.status_code == 200
    assert second.json() == {
        "balance": "2000.00",
        "committed": "0.00",
        "available": "2000.00",
    }
    assert (await client.get("/wallet")).json()["balance"] == "2000.00"
    entries = (await db_session.execute(select(WalletTransactionModel))).scalars().all()
    assert sorted((e.type, e.amount) for e in entries) == [
        ("DEPOSIT", D("500.00")),
        ("DEPOSIT", D("1500.00")),
    ]


async def test_deposit_rejections(client):
    await register_and_login(client, "ana@example.com")

    async def deposit_code(amount):
        response = await client.post("/wallet/deposit", json={"amount": amount})
        return response.status_code, response.json()["error"]["code"]

    assert await deposit_code("0.00") == (422, "INVALID_AMOUNT")
    assert await deposit_code("-5.00") == (422, "INVALID_AMOUNT")
    assert await deposit_code("100000.01") == (422, "DEPOSIT_LIMIT_EXCEEDED")
    for invalid in ("10.005", 10.005, "dez", "", None, "NaN", "Infinity", [1]):
        assert await deposit_code(invalid) == (422, "VALIDATION_ERROR"), invalid
    assert (await client.get("/wallet")).json()["balance"] == "0.00"


async def test_deposit_accepts_number_or_string_with_up_to_two_decimals(client):
    await register_and_login(client, "ana@example.com")

    for amount in ("10.50", 10.5, 1, "0.01", "0.1"):
        response = await client.post("/wallet/deposit", json={"amount": amount})
        assert response.status_code == 200, (amount, response.text)

    # 10.50 + 10.50 + 1.00 + 0.01 + 0.10, exact (floats would drift)
    assert (await client.get("/wallet")).json() == {
        "balance": "22.11",
        "committed": "0.00",
        "available": "22.11",
    }


async def test_wallet_is_bidder_only(client):
    assert (await client.get("/wallet")).status_code == 401

    await register_and_login(client, "boss@example.com", role="AUCTIONEER")

    assert (await client.get("/wallet")).status_code == 403
    deposit = await client.post("/wallet/deposit", json={"amount": "10.00"})
    assert (deposit.status_code, deposit.json()["error"]["code"]) == (403, "WRONG_ROLE")


async def test_concurrent_deposits_are_not_lost(client):
    """FOR UPDATE serialises the read-modify-write; without it some deposits would vanish."""
    await register(client, "ana@example.com")
    clients = [new_client() for _ in range(10)]
    try:
        for c in clients:
            await login(c, "ana@example.com")
        responses = await asyncio.gather(
            *(c.post("/wallet/deposit", json={"amount": "10.00"}) for c in clients)
        )
    finally:
        for c in clients:
            await c.aclose()

    assert all(r.status_code == 200 for r in responses)
    await login(client, "ana@example.com")
    assert (await client.get("/wallet")).json()["balance"] == "100.00"
