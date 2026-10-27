from sqlalchemy.ext.asyncio import AsyncSession

from shared.application.unit_of_work import IUnitOfWork


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()
