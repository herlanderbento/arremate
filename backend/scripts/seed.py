"""Demo data: python -m scripts.seed [--refresh-live]

Idempotent. Everything goes through the real use cases (hash chain, wallets and receipt stay
valid) and the artworks are fixed here, so the seed never calls the external API.

--refresh-live creates a new live lot with bids when none is live anymore (run it if the
seeded live lot has ended by the time someone evaluates the app).
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from decimal import Decimal as D
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from sqlalchemy import select, update  # noqa: E402

from account.application.use_cases.create_user import (  # noqa: E402
    CreateUserInput,
    CreateUserUseCase,
)
from account.domain.user import UserId, UserRole  # noqa: E402
from account.infra.db.user_postgres_repository import UserPostgresRepository  # noqa: E402
from auction.application.ports.lot_room_notifier import ILotRoomNotifier  # noqa: E402
from auction.application.use_cases.bids.place_bid import (  # noqa: E402
    PlaceBidInput,
    PlaceBidUseCase,
)
from auction.application.use_cases.lots.create_lot import (  # noqa: E402
    CreateLotInput,
    CreateLotUseCase,
)
from auction.application.use_cases.lots.settle_lot import SettleLotInput  # noqa: E402
from auction.domain.entities.lot import LotId  # noqa: E402
from auction.infra.composition import build_settle_lot_use_case  # noqa: E402
from auction.infra.db.bid_postgres_repository import BidPostgresRepository  # noqa: E402
from auction.infra.db.lot_postgres_repository import LotPostgresRepository  # noqa: E402
from auction.infra.db.sql_models import LotModel  # noqa: E402
from audit.infra.hash_chain_provider import get_hash_chain  # noqa: E402
from catalog.domain.catalog_gateway import (  # noqa: E402
    CatalogGateway,
    CatalogSearchInput,
    CatalogSearchOutput,
)
from catalog.domain.catalog_item import CatalogItem  # noqa: E402
from shared.infra.cryptography.bcrypt_hasher import BcryptHasher  # noqa: E402
from shared.infra.db.database import AsyncSessionLocal, engine  # noqa: E402
from shared.infra.db.unit_of_work import SqlAlchemyUnitOfWork  # noqa: E402
from wallet.application.use_cases.deposit import DepositInput, DepositUseCase  # noqa: E402
from wallet.infra.db.wallet_postgres_repository import WalletPostgresRepository  # noqa: E402
from wallet.infra.db.wallet_transaction_postgres_repository import (  # noqa: E402
    WalletTransactionPostgresRepository,
)

PASSWORD = "arremate123"
AUCTIONEER = ("Leiloeiro Demo", "leiloeiro@arremate.dev")
BIDDERS = [("Ana Licitante", "ana@arremate.dev"), ("Bruno Licitante", "bruno@arremate.dev")]
DEPOSIT = Decimal("10000.00")

IIIF = "https://www.artic.edu/iiif/2/{}/full/843,/0/default.jpg"
ARTWORKS = {
    "111628": CatalogItem(
        "111628",
        "Nighthawks",
        IIIF.format("831a05de-d3f6-f4fa-a460-23008dd58dda"),
        {"artist": "Edward Hopper", "date": "1942", "medium": "Oil on canvas"},
    ),
    "6565": CatalogItem(
        "6565",
        "American Gothic",
        IIIF.format("b272df73-a965-ac37-4172-be4e99483637"),
        {"artist": "Grant Wood", "date": "1930", "medium": "Oil on beaverboard"},
    ),
    "28560": CatalogItem(
        "28560",
        "The Bedroom",
        IIIF.format("6644829f-f292-c5c4-a73c-0356a6fdbf0d"),
        {"artist": "Vincent van Gogh", "date": "1889", "medium": "Oil on canvas"},
    ),
    "16568": CatalogItem(
        "16568",
        "Water Lilies",
        IIIF.format("3c27b499-af56-f0d5-93b5-a7f2f1ad5813"),
        {"artist": "Claude Monet", "date": "1906", "medium": "Oil on canvas"},
    ),
}


class SeedCatalog(CatalogGateway):
    async def search_items(self, props: CatalogSearchInput) -> CatalogSearchOutput:
        term = ((props.filter.query if props.filter else None) or "").strip().lower()
        found = [i for i in ARTWORKS.values() if term in i.title.lower()]
        start = (props.page - 1) * props.per_page
        return CatalogSearchOutput(
            items=found[start : start + props.per_page],
            total=len(found),
            current_page=props.page,
            per_page=props.per_page,
        )

    async def get_item(self, external_id: str) -> CatalogItem | None:
        return ARTWORKS.get(external_id)


class SilentNotifier(ILotRoomNotifier):
    async def publish(self, lot_id, event) -> None:
        pass


def now() -> datetime:
    return datetime.now(UTC)


async def create_user(name: str, email: str, role: UserRole) -> UserId:
    async with AsyncSessionLocal() as session:
        use_case = CreateUserUseCase(
            UserPostgresRepository(session), WalletPostgresRepository(session), BcryptHasher()
        )
        user = await use_case.execute(CreateUserInput(name, role, email, PASSWORD))
        await session.commit()
        return UserId(value=user.id)


async def deposit(user_id: UserId, amount: Decimal) -> None:
    async with AsyncSessionLocal() as session:
        use_case = DepositUseCase(
            WalletPostgresRepository(session), WalletTransactionPostgresRepository(session)
        )
        await use_case.execute(DepositInput(user_id, amount))
        await session.commit()


async def create_lot(
    auctioneer: UserId, external_id: str, starts_at, ends_at, starting: Decimal, increment: Decimal
) -> LotId:
    async with AsyncSessionLocal() as session:
        use_case = CreateLotUseCase(LotPostgresRepository(session), SeedCatalog(), get_hash_chain())
        lot = await use_case.execute(
            CreateLotInput(auctioneer, external_id, starting, increment, starts_at, ends_at)
        )
        await session.commit()
        return LotId(value=lot.id)


async def place_bid(lot_id: LotId, bidder: UserId, amount: Decimal) -> None:
    async with AsyncSessionLocal() as session:
        use_case = PlaceBidUseCase(
            LotPostgresRepository(session),
            BidPostgresRepository(session),
            WalletPostgresRepository(session),
            WalletTransactionPostgresRepository(session),
            get_hash_chain(),
            SqlAlchemyUnitOfWork(session),
            SilentNotifier(),
        )
        await use_case.execute(PlaceBidInput(lot_id, bidder, UserRole.BIDDER, amount))


async def create_live_lot_with_bids(auctioneer: UserId, ana: UserId, bruno: UserId) -> LotId:
    # Long window on purpose: it must still be live whenever the app is evaluated.
    lot = await create_lot(
        auctioneer,
        "111628",
        now() - timedelta(hours=1),
        now() + timedelta(days=30),
        D("1000.00"),
        D("50.00"),
    )
    for bidder, amount in ((ana, D("1000.00")), (bruno, D("1100.00")), (ana, D("1200.00"))):
        await place_bid(lot, bidder, amount)
    return lot


async def create_settled_lot(auctioneer: UserId, ana: UserId, bruno: UserId) -> None:
    lot = await create_lot(
        auctioneer,
        "6565",
        now() - timedelta(hours=3),
        now() + timedelta(hours=1),
        D("500.00"),
        D("25.00"),
    )
    for bidder, amount in ((ana, D("500.00")), (bruno, D("600.00"))):
        await place_bid(lot, bidder, amount)
    # The only shortcut: move the end into the past, then settle through the real use case.
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(LotModel)
            .where(LotModel.id == lot.value)
            .values(ends_at=now() - timedelta(minutes=1))
        )
        await session.commit()
    async with AsyncSessionLocal() as session:
        await build_settle_lot_use_case(session, SilentNotifier()).execute(SettleLotInput(lot))


async def find_user(email: str) -> UserId | None:
    async with AsyncSessionLocal() as session:
        user = await UserPostgresRepository(session).find_by_email(email)
        return user.id if user else None


async def has_live_lot_with_bids() -> bool:
    async with AsyncSessionLocal() as session:
        current = now()
        found = await session.execute(
            select(LotModel.id).where(
                LotModel.status == "ACTIVE",
                LotModel.starts_at <= current,
                LotModel.ends_at > current,
                LotModel.bid_count > 0,
            )
        )
        return found.first() is not None


async def seed(refresh_live: bool = False) -> str:
    auctioneer = await find_user(AUCTIONEER[1])
    if auctioneer is not None:
        if not refresh_live:
            return "Seed already applied; nothing to do."
        if await has_live_lot_with_bids():
            return "A live lot with bids already exists; nothing to do."
        ana, bruno = [await find_user(email) for _, email in BIDDERS]
        if ana is None or bruno is None:
            return "Seed users are missing; cannot refresh the live lot."
        await create_live_lot_with_bids(auctioneer, ana, bruno)
        return "Created a new live lot with bids."

    auctioneer = await create_user(*AUCTIONEER, UserRole.AUCTIONEER)
    ana, bruno = [await create_user(name, email, UserRole.BIDDER) for name, email in BIDDERS]
    for bidder in (ana, bruno):
        await deposit(bidder, DEPOSIT)

    await create_live_lot_with_bids(auctioneer, ana, bruno)
    await create_lot(
        auctioneer,
        "16568",
        now() - timedelta(minutes=5),
        now() + timedelta(days=3),
        D("800.00"),
        D("50.00"),
    )
    await create_lot(
        auctioneer,
        "28560",
        now() + timedelta(days=7),
        now() + timedelta(days=14),
        D("1500.00"),
        D("100.00"),
    )
    await create_settled_lot(auctioneer, ana, bruno)
    return "Seed applied."


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh-live", action="store_true")
    args = parser.parse_args()
    try:
        print(await seed(refresh_live=args.refresh_live))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
