import pytest

from app import create_app
from app.database import init_db
from app.seed import seed_demo_content


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
        seed_demo_content()
    yield app


@pytest.fixture()
def client(app):
    client = app.test_client()
    client.post(
        "/auth/register",
        data={
            "name": "Practice Student",
            "email": "practice@example.com",
            "password": "securepass",
            "confirm_password": "securepass",
        },
    )
    return client


def test_mock_library_and_reading_submission(client):
    response = client.get("/mocks/")
    assert response.status_code == 200
    assert b"Reading Mock 1" in response.data
    assert b"Listening Mock 1" in response.data
    assert response.data.count(b"Original content") == 20

    response = client.get("/mocks/1")
    assert response.status_code == 200
    assert b"The Repair Caf" in response.data
    assert b"Next passage" in response.data
    assert b"not submitted this mock yet" in response.data

    response = client.get("/mocks/2")
    assert response.status_code == 200
    assert b"Next section" in response.data
    assert b"20 seconds" in response.data

    response = client.post(
        "/mocks/1/submit",
        data={
            "question_1": "B",
            "question_2": "C",
            "question_3": "FALSE",
            "question_4": "bicycles",
            "question_5": "C",
            "question_6": "TRUE",
            "question_7": "being difficult to open",
            "question_8": "B",
            "question_9": "patient explanation",
            "question_10": "FALSE",
        },
    )
    assert response.status_code == 200
    assert b"/ 40" in response.data
