from typing import Generator

from fastapi import Header
from sqlalchemy.orm import Session

from app.core.access import AccessContext, build_access_context
from app.core.config import get_settings
from app.db.session import get_db


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_access_context(x_kvitt_tier: str | None = Header(default=None)) -> AccessContext:
    settings = get_settings()
    return build_access_context(x_kvitt_tier, default=settings.default_access_tier)
