from datetime import UTC, datetime, timedelta

import jwt

from shared.application.token_generator import ITokenGenerator
from shared.infra.db.config import settings


class JwtTokenGenerator(ITokenGenerator):
    def generate(self, payload: dict) -> str:
        claims = {
            "sub": payload["sub"],
            "type": payload.get("type", "access"),
            "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }

        return jwt.encode(
            claims,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
