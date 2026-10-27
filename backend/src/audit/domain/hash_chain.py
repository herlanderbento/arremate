import hashlib
import hmac
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from shared.domain.money import canonical


def canonical_ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("timestamps in the chain must be timezone-aware")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class HashChain:
    def __init__(self, secret: str | bytes):
        self._key = secret.encode() if isinstance(secret, str) else secret

    def _hmac(self, message: str) -> str:
        return hmac.new(self._key, message.encode(), hashlib.sha256).hexdigest()

    def genesis(self, lot_id: UUID) -> str:
        return self._hmac(f"genesis|{lot_id}")

    def bid_hash(
        self,
        prev_hash: str,
        lot_id: UUID,
        seq: int,
        bidder_id: UUID,
        amount: Decimal,
        created_at: datetime,
    ) -> str:
        return self._hmac(
            f"{prev_hash}|{lot_id}|{seq}|{bidder_id}|{canonical(amount)}|{canonical_ts(created_at)}"
        )

    def chain_head(self, lot_id: UUID, bid_count: int, last_hash: str | None) -> str:
        return self._hmac(f"head|{lot_id}|{bid_count}|{last_hash or self.genesis(lot_id)}")

    def alias(self, user_id: UUID, lot_id: UUID) -> str:
        return "Licitante " + self._hmac(f"alias|{user_id}|{lot_id}")[:8]

    @staticmethod
    def same(a: str, b: str) -> bool:
        return hmac.compare_digest(a, b)
