from functools import lru_cache

from audit.domain.hash_chain import HashChain
from shared.infra.db.config import settings


@lru_cache
def get_hash_chain() -> HashChain:
    return HashChain(settings.AUDIT_SECRET)
