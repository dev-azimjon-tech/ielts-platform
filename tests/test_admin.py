from werkzeug.security import generate_password_hash

from app.database import get_db
from app.models import User


def login(client, email, password="securepass"):
    return client.post(
        "/auth/login", data={"email": email, "password": password}
    )


def test_admin_routes_are_protected(app, client):
    with app.app_context():
        User.create(
            "Site Admin",
            "admin@example.com",
            generate_password_hash("securepass"),
            is_admin=True,
        )
        User.create(
            "Student",
            "student@example.com",
            generate_password_hash("securepass"),
        )

    assert client.get("/admin/").status_code == 302
    login(client, "student@example.com")
    assert client.get("/admin/").status_code == 403
    client.post("/auth/logout")
    login(client, "admin@example.com")
    assert client.get("/admin/").status_code == 200
    assert b"Platform overview" in client.get("/admin/").data


def test_admin_can_build_and_publish_a_mock(app, client):
    with app.app_context():
        User.create(
            "Site Admin",
            "admin@example.com",
            generate_password_hash("securepass"),
            is_admin=True,
        )
    login(client, "admin@example.com")

    response = client.post(
        "/admin/mocks/new",
        data={
            "skill": "reading",
            "title": "Managed Reading Mock",
            "description": "A test created in the admin panel.",
            "time_limit_minutes": "60",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        mock_id = get_db().execute(
            "SELECT id FROM mock_tests WHERE title = ?", ("Managed Reading Mock",)
        ).fetchone()["id"]

    client.post(
        f"/admin/mocks/{mock_id}/content/new",
        data={"title": "Managed passage", "body": "A passage for students."},
    )
    with app.app_context():
        content_id = get_db().execute(
            "SELECT id FROM reading_passages WHERE mock_id = ?", (mock_id,)
        ).fetchone()["id"]
    client.post(
        f"/admin/mocks/{mock_id}/content/{content_id}/questions/new",
        data={
            "question_type": "multiple_choice",
            "prompt": "What is this?",
            "options": "A passage\nA script",
            "correct_answer": "A",
            "explanation": "The source says passage.",
        },
    )

    response = client.post(f"/admin/mocks/{mock_id}/toggle-publish")
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT is_published FROM mock_tests WHERE id = ?", (mock_id,)
        ).fetchone()["is_published"] == 1
    assert client.get(f"/mocks/{mock_id}").status_code == 200


def test_admin_can_toggle_premium_access(app, client):
    with app.app_context():
        User.create(
            "Site Admin",
            "admin@example.com",
            generate_password_hash("securepass"),
            is_admin=True,
        )
        student = User.create(
            "Student",
            "student@example.com",
            generate_password_hash("securepass"),
        )
        student_id = student.id
    login(client, "admin@example.com")

    assert client.post(f"/admin/users/{student_id}/toggle-premium").status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT is_premium FROM users WHERE id = ?", (student_id,)
        ).fetchone()["is_premium"] == 1
