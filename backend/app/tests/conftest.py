import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # Point at a fresh, isolated SQLite file per test so tests never share state.
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    from app.database import session as session_module

    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(session_module, "engine", test_engine)
    monkeypatch.setattr(session_module, "SessionLocal", TestSessionLocal)

    # Point the websocket module's SessionLocal reference too since it imports it directly.
    from app.websocket import chat as chat_ws

    monkeypatch.setattr(chat_ws, "SessionLocal", TestSessionLocal)

    from app.main import app

    session_module.Base.metadata.create_all(bind=test_engine)

    with TestClient(app) as c:
        yield c
