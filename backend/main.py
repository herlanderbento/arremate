import sys
from pathlib import Path

_src = Path(__file__).resolve().parent / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from account.infra.api.auth_controller import router as auth_router
from auction.infra.api.lot_controller import router as lot_router
from auction.infra.api.bids_controller import router as bids_router
from auction.infra.api.receipt_controller import router as receipt_router
from auction.infra.worker.settlement_worker import run_settlement_worker
from auction.infra.ws.connection_manager import lot_rooms
from auction.infra.ws.lot_room_controller import router as lot_room_router
from audit.infra.api.audit_controller import router as audit_router
from catalog.infra.api.catalog_controller import router as catalog_router
from shared.infra.api.exception_handlers import register_exception_handlers
from shared.infra.db.config import settings
from shared.infra.db.database import AsyncSessionLocal, engine
from wallet.infra.api.wallet_controller import router as wallet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    if settings.SETTLEMENT_WORKER_ENABLED:
        worker = asyncio.create_task(
            run_settlement_worker(
                AsyncSessionLocal, lot_rooms, settings.SETTLEMENT_INTERVAL_SECONDS
            )
        )
    yield
    if worker is not None:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker
    await engine.dispose()


logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

app = FastAPI(title="Arremate API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(wallet_router)
app.include_router(catalog_router)
app.include_router(lot_router)
app.include_router(lot_room_router)
app.include_router(bids_router)
app.include_router(receipt_router)
app.include_router(audit_router)


@app.get("/health", tags=["Health"])
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}
