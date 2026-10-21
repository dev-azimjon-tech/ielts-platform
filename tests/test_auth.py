import pytest

from app import create_app
from app.database import init_db


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "test.sqlite3"),
        }
    )
    with app.app_context():
        init_db()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_register_login_and_logout(client):
    response = client.post(
        "/auth/register",
        data={
            "name": "Amina Student",
            "email": "amina@example.com",
            "password": "securepass",
            "confirm_password": "securepass",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    with client.session_transaction() as session:
        assert "_user_id" in session

    client.post("/auth/logout")
    response = client.post(
        "/auth/login",
        data={"email": "amina@example.com", "password": "securepass"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_registration_validates_password_and_duplicate_email(client):
    response = client.post(
        "/auth/register",
        data={
            "name": "Amina Student",
            "email": "amina@example.com",
            "password": "short",
            "confirm_password": "short",
        },
    )
    assert b"at least 8 characters" in response.data

    client.post(
        "/auth/register",
        data={
            "name": "Amina Student",
            "email": "amina@example.com",
            "password": "securepass",
            "confirm_password": "securepass",
        },
    )
    client.post("/auth/logout")
    response = client.post(
        "/auth/register",
        data={
            "name": "Another Student",
            "email": "AMINA@example.com",
            "password": "securepass",
            "confirm_password": "securepass",
        },
    )
    assert b"already exists" in response.data
