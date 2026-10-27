from dataclasses import dataclass

from account.application.use_cases.common.user_output import UserOutput
from account.domain.user import normalize_email
from account.domain.user_repository import IUserRepository
from shared.application.cryptography import IPasswordHasher
from shared.application.token_generator import ITokenGenerator
from shared.application.use_cases import UseCase
from shared.domain.exceptions import UnauthorizedException

INVALID_CREDENTIALS = "INVALID_CREDENTIALS"


@dataclass
class AuthenticateUserInput:
    email: str
    password: str


@dataclass(frozen=True)
class AuthenticateUserOutput:
    access_token: str
    user: UserOutput


class AuthenticateUserUseCase(UseCase):
    def __init__(
        self,
        user_repository: IUserRepository,
        token_generator: ITokenGenerator,
        password_hasher: IPasswordHasher,
    ):
        self.user_repository = user_repository
        self.token_generator = token_generator
        self.password_hasher = password_hasher

    async def execute(self, input: AuthenticateUserInput) -> AuthenticateUserOutput:
        user = await self.user_repository.find_by_email(normalize_email(input.email))

        if user is None or not self.password_hasher.verify(input.password, user.password):
            raise UnauthorizedException("Email ou senha incorretos.", code=INVALID_CREDENTIALS)

        return AuthenticateUserOutput(
            access_token=self.token_generator.generate(
                {"sub": str(user.id.value), "type": "access"}
            ),
            user=UserOutput.from_entity(user),
        )
