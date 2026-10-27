import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auction.application.ports.lot_room_notifier import ILotRoomNotifier
from auction.application.use_cases.lots.settle_lot import SettleLotInput
from auction.infra.composition import build_settle_lot_use_case
from auction.infra.db.lot_postgres_repository import LotPostgresRepository
from shared.application.clock import utc_now

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


async def settle_due_lots(
    session_factory: async_sessionmaker[AsyncSession], notifier: ILotRoomNotifier
) -> int:
    async with session_factory() as session:
        due = await LotPostgresRepository(session).list_due_for_settlement(utc_now(), BATCH_SIZE)

    settled = 0
    for lot_id in due:
        try:
            async with session_factory() as session:
                use_case = build_settle_lot_use_case(session, notifier)
                if await use_case.execute(SettleLotInput(lot_id=lot_id)):
                    settled += 1
        except Exception:
            logger.exception("Failed to settle lot %s", lot_id)
    return settled


async def run_settlement_worker(
    session_factory: async_sessionmaker[AsyncSession],
    notifier: ILotRoomNotifier,
    interval_seconds: float,
) -> None:
    logger.info("Settlement worker started (every %ss)", interval_seconds)
    while True:
        try:
            count = await settle_due_lots(session_factory, notifier)
            if count:
                logger.info("Settled %d lot(s)", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Settlement pass failed")
        await asyncio.sleep(interval_seconds)
