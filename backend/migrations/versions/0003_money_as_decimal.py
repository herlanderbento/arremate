"""money as decimal

Monetary columns go from integer cents (BIGINT, `*_cents`) to exact decimals in reais
(NUMERIC(14,2), no suffix): 105000 -> 1050.00. The conversion is exact (division by 100).

The amount is part of every bid's HMAC, and its canonical text changes from "105000" to
"1050.00". So, per lot, the chain is first verified with the formula it was sealed with; only
an intact chain is re-sealed with the new one (bids, lot.chain_head and the receipt's
chain_head). A chain that was already tampered with is left as is and keeps failing the audit:
the migration never launders a tampered history. Needs AUDIT_SECRET in the environment.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25
"""

import hashlib
import hmac
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# (table, old column, new column, nullable default)
COLUMNS = [
    ("wallets", "balance_cents", "balance", "0"),
    ("wallets", "committed_cents", "committed", "0"),
    ("wallet_transactions", "amount_cents", "amount", None),
    ("lots", "starting_bid_cents", "starting_bid", None),
    ("lots", "min_increment_cents", "min_increment", None),
    ("lots", "current_bid_cents", "current_bid", None),
    ("bids", "amount_cents", "amount", None),
    ("receipts", "amount_cents", "amount", None),
]


# Hash chain copied here so the migration does not depend on the app code.


def _old_amount(amount: Decimal) -> str:  # how 0001/0002 sealed it: integer cents
    return str(int((amount * 100).to_integral_exact()))


def _new_amount(amount: Decimal) -> str:  # canonical decimal with two places
    return f"{amount:.2f}"


def _reseal(fmt_from: Callable[[Decimal], str], fmt_to: Callable[[Decimal], str]) -> None:
    from shared.infra.db.config import settings

    key = settings.AUDIT_SECRET.encode()
    conn = op.get_bind()

    def h(message: str) -> str:
        return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

    def ts(dt: datetime) -> str:
        return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def chain(lot_id, bids, fmt) -> tuple[list[tuple[str, str]], str]:
        genesis, links, prev = h(f"genesis|{lot_id}"), [], None
        prev = genesis
        for b in bids:
            current = h(f"{prev}|{lot_id}|{b.seq}|{b.bidder_id}|{fmt(b.amount)}|{ts(b.created_at)}")
            links.append((prev, current))
            prev = current
        last = links[-1][1] if links else None
        return links, h(f"head|{lot_id}|{len(bids)}|{last or genesis}")

    resealed = skipped = 0
    for lot in conn.execute(sa.text("SELECT id, chain_head FROM lots")).all():
        bids = conn.execute(
            sa.text(
                "SELECT id, seq, bidder_id, amount, created_at, prev_hash, hash "
                "FROM bids WHERE lot_id = :id ORDER BY seq"
            ),
            {"id": lot.id},
        ).all()
        if not bids:
            continue  # nothing depends on an amount

        expected, expected_head = chain(lot.id, bids, fmt_from)
        intact = (
            [b.seq for b in bids] == list(range(1, len(bids) + 1))
            and all(
                (b.prev_hash.strip(), b.hash.strip()) == link for b, link in zip(bids, expected)
            )
            and lot.chain_head.strip() == expected_head
        )
        if not intact:
            skipped += 1
            continue

        links, head = chain(lot.id, bids, fmt_to)
        for b, (prev_hash, bid_hash) in zip(bids, links):
            conn.execute(
                sa.text("UPDATE bids SET prev_hash = :p, hash = :h WHERE id = :id"),
                {"p": prev_hash, "h": bid_hash, "id": b.id},
            )
        conn.execute(
            sa.text("UPDATE lots SET chain_head = :h WHERE id = :id"), {"h": head, "id": lot.id}
        )
        # Only a receipt that matched the intact history follows it.
        conn.execute(
            sa.text("UPDATE receipts SET chain_head = :h WHERE lot_id = :id AND chain_head = :old"),
            {"h": head, "id": lot.id, "old": lot.chain_head},
        )
        resealed += 1

    logger.info(
        "Hash chains re-sealed: %d; left untouched (already invalid): %d", resealed, skipped
    )


def _tables() -> dict[str, list[tuple[str, str, str | None]]]:
    tables: dict[str, list[tuple[str, str, str | None]]] = {}
    for table, old, new, default in COLUMNS:
        tables.setdefault(table, []).append((old, new, default))
    return tables


def _convert(table: str, columns: list[tuple[str, str, str | None]], to_decimal: bool) -> None:
    # One statement per table, so CHECK (committed <= balance) sees both columns converted.
    clauses = []
    for old, new, default in columns:
        name = new if to_decimal else old
        if default is not None:
            clauses.append(f"ALTER COLUMN {name} DROP DEFAULT")
        if to_decimal:
            clauses.append(f"ALTER COLUMN {name} TYPE NUMERIC(14, 2) USING {name}::numeric / 100")
        else:
            clauses.append(f"ALTER COLUMN {name} TYPE BIGINT USING ({name} * 100)::bigint")
        if default is not None:
            clauses.append(f"ALTER COLUMN {name} SET DEFAULT {default}")
    op.execute(f"ALTER TABLE {table} " + ", ".join(clauses))


def upgrade() -> None:
    for table, columns in _tables().items():
        for old, new, _ in columns:
            op.alter_column(table, old, new_column_name=new)
        _convert(table, columns, to_decimal=True)
    _reseal(_old_amount, _new_amount)


def downgrade() -> None:
    _reseal(_new_amount, _old_amount)
    for table, columns in _tables().items():
        for old, new, _ in columns:
            op.alter_column(table, new, new_column_name=old)
        _convert(table, columns, to_decimal=False)
