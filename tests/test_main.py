
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.database import Base


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def register_and_login(client):
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "password": "TestPass123!",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "testuser",
            "password": "TestPass123!",
        },
    )

    return response.json()["access_token"]


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "password": "TestPass123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert "hashed_password" not in response.json()


def test_duplicate_registration(client):
    user = {
        "username": "duplicateuser",
        "password": "TestPass123!",
    }

    first = client.post("/auth/register", json=user)
    second = client.post("/auth/register", json=user)

    assert first.status_code == 201
    assert second.status_code == 409


def test_login(client):
    token = register_and_login(client)
    assert token


def test_items_require_authentication(client):
    response = client.get("/items")
    assert response.status_code == 401


def test_create_and_get_items(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/items",
        json={
            "name": "Test Item",
            "description": "Created during testing",
        },
        headers=headers,
    )

    assert created.status_code == 201
    item_id = created.json()["id"]

    fetched = client.get(
        f"/items/{item_id}",
        headers=headers,
    )

    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Test Item"


def test_invalid_login(client):
    client.post(
        "/auth/register",
        json={
            "username": "wrongpassuser",
            "password": "CorrectPass123!",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "wrongpassuser",
            "password": "WrongPass123!",
        },
    )

    assert response.status_code == 401
