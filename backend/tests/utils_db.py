from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.session import get_session_factory


@contextmanager
def db_test_session() -> Iterator[Session]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
