from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from account.application.use_cases.authenticate_user import AuthenticateUserUseCase
from account.application.use_cases.create_user import CreateUserUseCase
from account.application.use_cases.get_user import GetUserUseCase
from account.domain.user_repository import IUserRepository
from account.infra.db.user_postgres_repository import UserPostgresRepository
from shared.application.cryptography import IPasswordHasher
from shared.application.token_generator import ITokenGenerator
from shared.infra.api.dependencies import get_bcrypt_hasher, get_token_generator
from shared.infra.db.database import get_db_session
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.infra.db.wallet_postgres_repository import WalletPostgresRepository


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IUserRepository:
    return UserPostgresRepository(session)


def _get_wallet_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IWalletRepository:
    return WalletPostgresRepository(session)


def get_create_user_use_case(
    user_repo: IUserRepository = Depends(get_user_repository),
    wallet_repo: IWalletRepository = Depends(_get_wallet_repository),
    password_hasher: IPasswordHasher = Depends(get_bcrypt_hasher),
) -> CreateUserUseCase:
    return CreateUserUseCase(user_repo, wallet_repo, password_hasher)


def get_authenticate_user_use_case(
    user_repo: IUserRepository = Depends(get_user_repository),
    token_generator: ITokenGenerator = Depends(get_token_generator),
    password_hasher: IPasswordHasher = Depends(get_bcrypt_hasher),
) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(user_repo, token_generator, password_hasher)


def get_get_user_use_case(
    user_repo: IUserRepository = Depends(get_user_repository),
) -> GetUserUseCase:
    return GetUserUseCase(user_repo)
