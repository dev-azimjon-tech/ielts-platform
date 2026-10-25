from werkzeug.security import generate_password_hash

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
