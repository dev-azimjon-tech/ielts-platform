from werkzeug.security import generate_password_hash
from flask import template_rendered

from app.database import get_db
from app.models import User
from app.seed import seed_demo_content


def test_dashboard_shows_band_scores_instead_of_raw_marks(app, client):
    with app.app_context():
        seed_demo_content()
        User.create(
            "Band Student",
            "bands@example.com",
            generate_password_hash("securepass"),
        )
        user_id = User.get_by_email("bands@example.com").id
        reading_id = get_db().execute(
            "SELECT id FROM mock_tests WHERE skill = 'reading' ORDER BY id LIMIT 1"
        ).fetchone()["id"]
        listening_id = get_db().execute(
            "SELECT id FROM mock_tests WHERE skill = 'listening' ORDER BY id LIMIT 1"
        ).fetchone()["id"]
        get_db().executemany(
            """
            INSERT INTO attempts (user_id, mock_id, score, total_points, answers_json)
            VALUES (?, ?, ?, 40, '{}')
            """,
            [(user_id, reading_id, 39), (user_id, listening_id, 38)],
        )
        get_db().commit()

    client.post(
        "/auth/login",
        data={"email": "bands@example.com", "password": "securepass"},
    )
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Overall average band" in response.data
    assert b"Average estimated IELTS band" in response.data
    assert b"8.8 <small>/ 9" in response.data
    assert b"9.0</strong><span>/ 9" in response.data
    assert b"8.5</strong><span>/ 9" in response.data
    assert b"correct answers" not in response.data


def test_grouped_dashboard_preserves_attempt_weights_and_user_isolation(app, client):
    with app.app_context():
        seed_demo_content()
        student = User.create("Student", "weighted@example.com", generate_password_hash("securepass"))
        other = User.create("Other", "other@example.com", generate_password_hash("securepass"))
        db = get_db()
        reading_id = db.execute("SELECT id FROM mock_tests WHERE skill = 'reading' LIMIT 1").fetchone()["id"]
        speaking_id = db.execute("SELECT id FROM ai_mocks WHERE skill = 'speaking' LIMIT 1").fetchone()["id"]
        db.executemany(
            "INSERT INTO attempts (user_id, mock_id, score, total_points, answers_json) VALUES (?, ?, ?, 40, '{}')",
            [(student.id, reading_id, 39), (student.id, reading_id, 39), (student.id, reading_id, 30), (other.id, reading_id, 0)],
        )
        db.execute(
            "INSERT INTO ai_attempts (user_id, ai_mock_id, submission_text, feedback_json, band_score) VALUES (?, ?, 'answer', '{}', 6.5)",
            (student.id, speaking_id),
        )
        db.commit()

    client.post('/auth/login', data={'email': 'weighted@example.com', 'password': 'securepass'})
    contexts = []
    def capture(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(capture, app):
        assert client.get('/dashboard').status_code == 200

    context = contexts[-1]
    stats = {stat['key']: stat for stat in context['skill_stats']}
    assert context['completed_mocks'] == 4
    assert context['overall_average_band'] == 7.9
    assert stats['reading']['average_band'] == 8.3
    assert stats['reading']['completed'] == 3
    assert stats['speaking']['average_band'] == 6.5
