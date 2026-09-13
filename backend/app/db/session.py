from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.settings import Settings
from app.db.models import (
    Announcement,
    CompanyProfile,
    FinancialMetrics,
    Holding,
    InvestmentAdviceCache,
    NewsItem,
    PriceBarDaily,
    PriceHistory,
    QuoteSnapshot,
    Security,
    WatchlistItem,
)

_ = (
    Security,
    WatchlistItem,
    QuoteSnapshot,
    PriceBarDaily,
    PriceHistory,
    FinancialMetrics,
    CompanyProfile,
    Holding,
    InvestmentAdviceCache,
    Announcement,
    NewsItem,
)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    del connection_record
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def make_engine(settings: Settings) -> Engine:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)


def create_db_and_tables(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


def make_session(engine: Engine) -> Session:
    return Session(engine)
