import os
import re
from pathlib import Path

from dotenv import dotenv_values

_ROOT = Path(__file__).resolve().parents[1]
_env = {**dotenv_values(_ROOT / ".env"), **os.environ}

_base_url = _env.get(
    "DATABASE_URL", "postgresql+asyncpg://arremate:arremate@localhost:5433/arremate"
)
TEST_DATABASE_URL = _env.get("TEST_DATABASE_URL") or re.sub(
    r"/([^/?]+)(\?|$)", r"/\1_test\2", _base_url
)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENV"] = "test"
os.environ["COOKIE_SECURE"] = "false"
os.environ["SETTLEMENT_WORKER_ENABLED"] = "false"
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-" + "x" * 32)
os.environ.setdefault("AUDIT_SECRET", "test-audit-secret-" + "x" * 32)
