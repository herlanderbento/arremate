from dataclasses import dataclass

from account.application.use_cases.common.user_output import UserOutput
from account.domain.user import User, UserCreateCommand, UserRole
from account.domain.user_repository import IUserRepository
from shared.application.cryptography import IPasswordHasher
from shared.application.use_cases import UseCase
from shared.domain.exceptions import ConflictException
from wallet.domain.entities.wallet import Wallet
from wallet.domain.repositories.wallet_repository import IWalletRepository

EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"


@dataclass
class CreateUserInput:
    name: str
    role: UserRole
    email: str
    password: str


@dataclass(frozen=True)
class CreateUserOutput(UserOutput):
    pass


class CreateUserUseCase(UseCase):
    def __init__(
        self,
        user_repository: IUserRepository,
        wallet_repository: IWalletRepository,
        password_hasher: IPasswordHasher,
    ):
        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.password_hasher = password_hasher

    async def execute(self, input: CreateUserInput) -> CreateUserOutput:
        if await self.user_repository.find_by_email(input.email):
            raise ConflictException(
                "Já existe um usuário com este email.", code=EMAIL_ALREADY_REGISTERED
            )

        command = UserCreateCommand(
            name=input.name.strip(),
            email=input.email,
            password=self.password_hasher.hash(input.password),
            role=input.role,
        )
        user = User.create(command)

        await self.user_repository.insert(user)
        await self.wallet_repository.insert(Wallet(user_id=user.id))

        return self.__to_output(user)

    def __to_output(self, user: User):
        return CreateUserOutput.from_entity(user)
