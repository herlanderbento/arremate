# Import every module's models so Base.metadata knows all tables (used by Alembic).
from account.infra.db import sql_models as _account_models  # noqa: F401
from auction.infra.db import sql_models as _auction_models  # noqa: F401
from shared.infra.db.database import Base
from wallet.infra.db import sql_models as _wallet_models  # noqa: F401

target_metadata = Base.metadata
