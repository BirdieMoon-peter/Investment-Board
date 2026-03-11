from collections.abc import Generator

from sqlmodel import Session

from app.core.settings import Settings
from app.db.session import make_engine, make_session


_engine = make_engine(Settings())


def get_session() -> Generator[Session, None, None]:
    with make_session(_engine) as session:
        yield session
