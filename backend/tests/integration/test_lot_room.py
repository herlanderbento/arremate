from fastapi.testclient import TestClient

from auction.infra.ws.connection_manager import get_lot_room_notifier
from main import app
from tests.helpers import PASSWORD, at


def test_room_receives_bid_events_without_personal_data():
    app.dependency_overrides.pop(get_lot_room_notifier, None)
    with TestClient(app) as http:

        def login(email, role):
            body = {"name": "X", "email": email, "password": PASSWORD, "role": role}
            assert http.post("/auth/register", json=body).status_code == 201
            assert (
                http.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code
                == 200
            )

        login("boss@example.com", "AUCTIONEER")
        lot = http.post(
            "/lots",
            json={
                "external_id": "16568",
                "starting_bid": "100.00",
                "min_increment": "5.00",
                "starts_at": at(minutes=-1),
                "ends_at": at(seconds=90),
            },
        ).json()
        http.post("/auth/logout")
        login("ana@example.com", "BIDDER")
        http.post("/wallet/deposit", json={"amount": "500.00"})

        with http.websocket_connect(f"/ws/lots/{lot['id']}") as room:
            response = http.post(f"/lots/{lot['id']}/bids", json={"amount": "100.00"})
            assert response.status_code == 201
            placed = room.receive_json()
            extended = room.receive_json()

    assert placed["type"] == "bid_placed"
    assert placed["lot_id"] == lot["id"]
    assert (placed["seq"], placed["amount"], placed["min_next_bid"]) == (
        1,
        "100.00",
        "105.00",
    )
    assert placed["bidder_alias"] == response.json()["bidder_alias"]
    assert not {"bidder_id", "user_id", "email", "name"} & set(placed)
    assert extended == {"type": "lot_extended", "lot_id": lot["id"], "ends_at": placed["ends_at"]}
