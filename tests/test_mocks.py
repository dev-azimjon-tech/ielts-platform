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
    assert b"The Hidden Life of Urban Trees" in response.data
    assert b"Next passage" in response.data
    assert b'id="exit-mock"' in response.data
    assert b'class="site-nav"' not in response.data
    assert b'class="site-footer"' not in response.data
    assert b'id="section-notes"' in response.data
    assert b'data-highlight-id="passage-' in response.data
    assert b'/static/js/exam.js' in response.data

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


def test_official_resources_are_available_without_using_allowance(app, client):
    from app.database import get_db

    with app.app_context():
        db = get_db()
        user_id = db.execute("SELECT id FROM users WHERE email = 'practice@example.com'").fetchone()["id"]
        db.executemany(
            "INSERT INTO attempts (user_id, mock_id, score, total_points, answers_json) VALUES (?, 1, 20, 40, '{}')",
            [(user_id,)] * 10,
        )
        db.commit()

    response = client.get('/mocks/?skill=reading')
    assert response.status_code == 200
    assert b'23435-ielts-sample-papers.zip' in response.data
    assert b'Official Academic Reading sample' in response.data
    assert b'Official Listening sample' not in response.data
    assert b'Listening Mock 1' not in response.data
    assert b'Free limit reached' in response.data
    assert client.get('/mocks/1').status_code == 302


def test_mock_page_does_not_send_correct_answers_or_duplicate_passage_json(client):
    response = client.get('/mocks/1')
    assert b'correct_answer' not in response.data
    assert b'"options_json"' not in response.data
    # The long passage is rendered once, not repeated in a JavaScript payload.
    assert response.data.count(b'When a city plants a tree, the visible part') == 1
