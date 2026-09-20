"""
Database engine/session setup.

Uses SQLAlchemy so the storage layer can be swapped from local SQLite to
Postgres/Supabase later just by changing DATABASE_URL - no model or query
code needs to change.
"""
from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def sqlite_constraints(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models so they're registered on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Additive migration for databases created before chat-to-chore support.
    with engine.begin() as connection:
        if "source_message_id" not in {c["name"] for c in inspect(connection).get_columns("chores")}:
            connection.execute(text(
                "ALTER TABLE chores ADD COLUMN source_message_id VARCHAR(36) "
                "REFERENCES messages(id) ON DELETE SET NULL"
            ))
            connection.execute(text(
                "CREATE UNIQUE INDEX uq_chores_source_message_id ON chores (source_message_id)"
            ))

        columns = {c["name"] for c in inspect(connection).get_columns("messages")}
        if "analysis_status" not in columns:
            # Existing history must never become eligible for a new provider call.
            connection.execute(text("ALTER TABLE messages ADD COLUMN analysis_status VARCHAR(20) NOT NULL DEFAULT 'skipped'"))
        if "analysis_data" not in columns:
            connection.execute(text("ALTER TABLE messages ADD COLUMN analysis_data JSON"))
