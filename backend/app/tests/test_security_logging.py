"""SQL exception traces must not disclose bound application data."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from app.database import session


def test_sql_error_hides_bound_values():
    assert session.engine.hide_parameters is True
    engine = create_engine("sqlite:///:memory:", hide_parameters=session.engine.hide_parameters)
    try:
        with engine.begin() as db:
            db.execute(text("CREATE TABLE private_data (value TEXT UNIQUE)"))
            statement = text("INSERT INTO private_data VALUES (:value)")
            db.execute(statement, {"value": "PRIVATE_CHAT_SENTINEL"})
            with pytest.raises(IntegrityError) as error:
                db.execute(statement, {"value": "PRIVATE_CHAT_SENTINEL"})
            assert "PRIVATE_CHAT_SENTINEL" not in str(error.value)
            assert "parameters hidden" in str(error.value)
    finally:
        engine.dispose()
