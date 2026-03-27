import os
from pathlib import Path

from fastapi.testclient import TestClient

TEST_DB_PATH = Path(__file__).resolve().parent / ".kvitt-test.sqlite3"

os.environ.setdefault("KVITT_DATABASE_URL", f"sqlite+pysqlite:///{TEST_DB_PATH}")
os.environ.setdefault("KVITT_AUTO_CREATE_TABLES", "true")
os.environ.setdefault("KVITT_REQUIRE_DB_READY", "true")

from app.core.config import get_settings
from app.db.session import reset_db_state
from app.main import create_app


def create_test_client() -> TestClient:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    get_settings.cache_clear()
    reset_db_state()

    client = TestClient(create_app())
    client.__enter__()
    return client
