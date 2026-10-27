from typing import List, Optional, Set, Type

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from account.domain.user import UserId
from shared.domain.money import money
from wallet.domain.entities.wallet import Wallet, WalletId
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.infra.db.sql_models import WalletModel


def _to_model(entity: Wallet) -> WalletModel:
    return WalletModel(
        id=entity.id.value,
        user_id=entity.user_id.value,
        balance=entity.balance,
        committed=entity.committed,
    )


def _to_entity(model: WalletModel) -> Wallet:
    return Wallet(
        id=WalletId(value=model.id),
        user_id=UserId(value=model.user_id),
        balance=money(model.balance),
        committed=money(model.committed),
    )


class WalletPostgresRepository(IWalletRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, entity: Wallet) -> None:
        self.session.add(_to_model(entity))
        await self.session.flush()

    async def bulk_insert(self, entities: List[Wallet]) -> None:
        self.session.add_all([_to_model(entity) for entity in entities])
        await self.session.flush()

    async def find_by_id(self, entity_id: WalletId) -> Optional[Wallet]:
        result = await self.session.execute(
            select(WalletModel).where(WalletModel.id == entity_id.value)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def find_all(self) -> List[Wallet]:
        result = await self.session.execute(select(WalletModel))
        return [_to_entity(model) for model in result.scalars().all()]

    async def find_by_ids(self, entity_ids: Set[WalletId]) -> List[Wallet]:
        raw_ids = [entity_id.value for entity_id in entity_ids]
        result = await self.session.execute(select(WalletModel).where(WalletModel.id.in_(raw_ids)))
        return [_to_entity(model) for model in result.scalars().all()]

    async def update(self, entity: Wallet) -> None:
        await self.session.execute(
            update(WalletModel)
            .where(WalletModel.id == entity.id.value)
            .values(
                balance=entity.balance,
                committed=entity.committed,
            )
        )

    async def delete(self, entity_id: WalletId) -> None:
        await self.session.execute(delete(WalletModel).where(WalletModel.id == entity_id.value))

    async def find_by_user_id(self, user_id: UserId) -> Wallet | None:
        result = await self.session.execute(
            select(WalletModel).where(WalletModel.user_id == user_id.value)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def lock_by_user_id(self, user_id: UserId) -> Wallet | None:
        result = await self.session.execute(
            select(WalletModel)
            .where(WalletModel.user_id == user_id.value)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def lock_by_user_ids(self, user_ids: set[UserId]) -> dict[UserId, Wallet]:
        if not user_ids:
            return {}
        result = await self.session.execute(
            select(WalletModel)
            .where(WalletModel.user_id.in_([user_id.value for user_id in user_ids]))
            .order_by(WalletModel.id.asc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        wallets = [_to_entity(model) for model in result.scalars().all()]
        return {wallet.user_id: wallet for wallet in wallets}

    def get_entity(self) -> Type[Wallet]:
        return Wallet
