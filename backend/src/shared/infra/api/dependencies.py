from shared.application.cryptography import IPasswordHasher
from shared.application.token_generator import ITokenGenerator
from shared.infra.cryptography.bcrypt_hasher import BcryptHasher
from shared.infra.token.jwt_token_generator import JwtTokenGenerator


def get_bcrypt_hasher() -> IPasswordHasher:
    return BcryptHasher()


def get_token_generator() -> ITokenGenerator:
    return JwtTokenGenerator()
