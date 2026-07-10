import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    """Rebuild the seeded in-memory DB before each test for isolation."""
    db.reset_db()
    yield
    db.reset_db()


@pytest.fixture
def client():
    return TestClient(app)


# Seeded principals: Alice is org 1 (Acme), Bob is org 2 (Globex).
ALICE = {"X-User-Id": "1"}
BOB = {"X-User-Id": "2"}
