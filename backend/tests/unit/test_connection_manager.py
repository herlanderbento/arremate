from datetime import UTC, datetime
from uuid import uuid4

from auction.infra.ws.connection_manager import ConnectionManager


class FakeSocket:
    def __init__(self, dead: bool = False):
        self.dead = dead
        self.accepted = False
        self.sent: list = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        if self.dead:
            raise RuntimeError("connection closed")
        self.sent.append(payload)


async def test_publish_reaches_only_the_lot_room_and_is_json_encoded():
    manager, lot_a, lot_b = ConnectionManager(), uuid4(), uuid4()
    a1, a2, b1 = FakeSocket(), FakeSocket(), FakeSocket()
    for lot, ws in ((lot_a, a1), (lot_a, a2), (lot_b, b1)):
        await manager.connect(lot, ws)

    when = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
    await manager.publish(lot_a, {"type": "lot_extended", "lot_id": lot_a, "ends_at": when})

    expected = {"type": "lot_extended", "lot_id": str(lot_a), "ends_at": when.isoformat()}
    assert a1.accepted and a1.sent == [expected] and a2.sent == [expected]
    assert b1.sent == []


async def test_dead_connections_are_dropped_silently():
    manager, lot = ConnectionManager(), uuid4()
    alive, dead = FakeSocket(), FakeSocket(dead=True)
    await manager.connect(lot, alive)
    await manager.connect(lot, dead)

    await manager.publish(lot, {"type": "x"})

    assert manager.rooms[lot] == {alive}
    manager.disconnect(lot, alive)
    assert lot not in manager.rooms
