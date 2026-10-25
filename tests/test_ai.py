import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.ai_seed import seed_ai_content
from app.database import get_db, init_db
from app.models import User


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
        seed_ai_content()
        User.create(
            "AI Student",
            "student@example.com",
            generate_password_hash("securepass"),
        )
        premium = User.create(
            "Premium Student",
            "premium@example.com",
            generate_password_hash("securepass"),
        )
        get_db().execute(
            "UPDATE users SET is_premium = 1 WHERE id = ?", (premium.id,)
        )
        get_db().commit()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email):
    return client.post(
        "/auth/login", data={"email": email, "password": "securepass"}
    )


def test_ai_library_and_student_pages(app, client):
    login(client, "student@example.com")
    response = client.get("/ai/")
    assert response.status_code == 200
    assert b"Speaking examiner" in response.data
    assert b"Writing checker" in response.data
    assert response.data.count(b"AI feedback") >= 20

    with app.app_context():
        speaking_id = get_db().execute(
            "SELECT id FROM ai_mocks WHERE skill = 'speaking' ORDER BY id LIMIT 1"
        ).fetchone()["id"]
        writing_id = get_db().execute(
            "SELECT id FROM ai_mocks WHERE skill = 'writing' ORDER BY id LIMIT 1"
        ).fetchone()["id"]
    assert client.get(f"/ai/speaking/{speaking_id}").status_code == 200
    assert client.get(f"/ai/writing/{writing_id}").status_code == 200


def test_free_user_is_limited_to_two_ai_mocks_per_skill(app):
    client = app.test_client()
    login(client, "student@example.com")
    with app.app_context():
        user_id = User.get_by_email("student@example.com").id
        speaking_ids = [
            row["id"]
            for row in get_db()
            .execute("SELECT id FROM ai_mocks WHERE skill = 'speaking' ORDER BY id LIMIT 2")
            .fetchall()
        ]
        for mock_id in speaking_ids:
            get_db().execute(
                """
                INSERT INTO ai_attempts
                    (user_id, ai_mock_id, submission_text, feedback_json, band_score)
                VALUES (?, ?, '[]', '{}', 5)
                """,
                (user_id, mock_id),
            )
        get_db().commit()
        next_mock_id = get_db().execute(
            "SELECT id FROM ai_mocks WHERE skill = 'speaking' ORDER BY id LIMIT 1 OFFSET 2"
        ).fetchone()["id"]
    assert client.get(f"/ai/speaking/{next_mock_id}").status_code == 302


def test_premium_user_can_access_ai_mocks_after_two_attempts(app):
    client = app.test_client()
    login(client, "premium@example.com")
    with app.app_context():
        user_id = User.get_by_email("premium@example.com").id
        speaking_ids = [
            row["id"]
            for row in get_db()
            .execute("SELECT id FROM ai_mocks WHERE skill = 'speaking' ORDER BY id LIMIT 2")
            .fetchall()
        ]
        for mock_id in speaking_ids:
            get_db().execute(
                """
                INSERT INTO ai_attempts
                    (user_id, ai_mock_id, submission_text, feedback_json, band_score)
                VALUES (?, ?, '[]', '{}', 5)
                """,
                (user_id, mock_id),
            )
        get_db().commit()
        next_mock_id = get_db().execute(
            "SELECT id FROM ai_mocks WHERE skill = 'speaking' ORDER BY id LIMIT 1 OFFSET 2"
        ).fetchone()["id"]
    assert client.get(f"/ai/speaking/{next_mock_id}").status_code == 200
