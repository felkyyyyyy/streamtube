from collections.abc import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    settings = get_settings()
    url = settings.DATABASE_URL
    connect_args = {}
    engine_kwargs = {"pool_pre_ping": True}

    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        engine_kwargs.update({"pool_size": 10, "max_overflow": 20})

    eng = create_engine(url, connect_args=connect_args, **engine_kwargs)

    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return eng


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
