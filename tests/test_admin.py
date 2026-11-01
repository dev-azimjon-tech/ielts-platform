from werkzeug.security import generate_password_hash

from app.database import get_db
from app.models import User


def login(client, email, password="securepass"):
    return client.post(
        "/auth/login", data={"email": email, "password": password}
    )



def admin_post(client, path, **kwargs):
    client.get('/admin/')
    with client.session_transaction() as session:
        token = session.get('admin_csrf_token', '')
    data = dict(kwargs.pop('data', {}))
    data['csrf_token'] = token
    return client.post(path, data=data, **kwargs)


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

    response = admin_post(client,
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

    admin_post(client,
        f"/admin/mocks/{mock_id}/content/new",
        data={"title": "Managed passage", "body": "A passage for students."},
    )
    with app.app_context():
        content_id = get_db().execute(
            "SELECT id FROM reading_passages WHERE mock_id = ?", (mock_id,)
        ).fetchone()["id"]
    admin_post(client,
        f"/admin/mocks/{mock_id}/content/{content_id}/questions/new",
        data={
            "question_type": "multiple_choice",
            "prompt": "What is this?",
            "options": "A passage\nA script",
            "correct_answer": "A",
            "explanation": "The source says passage.",
        },
    )

    response = admin_post(client, f"/admin/mocks/{mock_id}/toggle-publish")
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

    assert admin_post(client, f"/admin/users/{student_id}/toggle-premium").status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT is_premium FROM users WHERE id = ?", (student_id,)
        ).fetchone()["is_premium"] == 1


def setup_admin(app, client):
    with app.app_context():
        admin = User.create('Admin', 'admin@example.com', generate_password_hash('securepass'), is_admin=True)
    login(client, 'admin@example.com')
    client.get('/admin/')
    return admin.id


def test_user_search_filters_and_pagination(app, client):
    setup_admin(app, client)
    with app.app_context():
        db = get_db()
        db.executemany('INSERT INTO users (name, email, password_hash, is_premium) VALUES (?, ?, ?, ?)',
                       [(f'Student {n}', f'student{n}@example.com', 'unused', n % 2) for n in range(25)])
        db.execute("INSERT INTO users (name, email, password_hash) VALUES ('100%_Learner', 'literal@example.com', 'unused')")
        db.commit()
    response = client.get('/admin/users?role=student&plan=premium')
    assert response.status_code == 200
    assert b'student23@example.com' in response.data
    assert b'student24@example.com' not in response.data
    assert b'Admin account' not in response.data
    assert b'1\xe2\x80\x9312 of 12 results' in response.data
    response = client.get('/admin/users?q=100%25_')
    assert b'literal@example.com' in response.data
    assert b'student0@example.com' not in response.data
    response = client.get('/admin/users?role=student&page=2')
    assert b'21\xe2\x80\x9326 of 26 results' in response.data
    assert b'role=student' in response.data
    for page in ('-5', 'oops', '999999999999999999999999'):
        assert client.get('/admin/users?page=' + page).status_code == 200
    assert b'No users found' in client.get('/admin/users?q=missing-person').data
    assert client.get('/admin/users?q=%27+OR+1=1+--').status_code == 200


def test_mock_search_filters_counts_and_pagination(app, client):
    setup_admin(app, client)
    with app.app_context():
        db = get_db()
        db.executemany("INSERT INTO mock_tests (skill,title,description,time_limit_minutes,is_published) VALUES ('reading',?, 'Description',60,0)",
                       [(f'Draft {n}',) for n in range(22)])
        db.execute("INSERT INTO mock_tests (skill,title,description,time_limit_minutes,is_published) VALUES ('listening','Live listening','Description',40,1)")
        mock_id = db.execute("SELECT id FROM mock_tests WHERE title = 'Draft 0'").fetchone()[0]
        db.execute("INSERT INTO reading_passages (mock_id,title,body) VALUES (?, 'Passage','Text')", (mock_id,))
        db.executemany("INSERT INTO questions (mock_id,question_number,question_type,prompt,correct_answer,explanation) VALUES (?,?,'short_answer','Prompt','Answer','Explanation')", [(mock_id,1),(mock_id,2)])
        db.commit()
    response = client.get('/admin/mocks?skill=listening&status=published')
    assert b'Live listening' in response.data and b'Draft 0' not in response.data
    response = client.get('/admin/mocks?q=Draft+0&status=draft')
    assert b'1 passages' in response.data and b'2 questions' in response.data
    response = client.get('/admin/mocks?status=draft&page=2')
    assert b'21\xe2\x80\x9322 of 22 results' in response.data
    assert b'status=draft' in response.data
    assert b'No mocks found' in client.get('/admin/mocks?q=nonexistent').data
    assert client.get('/admin/mocks?skill=invalid&status=invalid&page=wrong').status_code == 200


def test_overview_includes_ai_and_aggregate_vocabulary_without_private_words(app, client):
    admin_id = setup_admin(app, client)
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO ai_mocks (skill,title,description,task_json,time_limit_minutes,is_published) VALUES ('writing','Writing activity','Description','{}',40,1)")
        mock_id = db.execute('SELECT id FROM ai_mocks').fetchone()[0]
        db.execute("INSERT INTO ai_attempts (user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES (?,?,'Private essay','{}',7.5)", (admin_id,mock_id))
        db.execute("INSERT INTO vocabulary_words (user_id,term,normalized_term,meaning) VALUES (?,'Private word','private word','Private meaning')", (admin_id,))
        db.commit()
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Writing activity' in response.data
    assert b'7.5/9' in response.data
    assert b'1 vocabulary cards' in response.data
    assert b'1 AI mocks live' in response.data
    assert b'Private word' not in response.data and b'Private essay' not in response.data


def test_admin_forms_require_tokens_and_premium_updates_are_idempotent(app, client):
    admin_id = setup_admin(app, client)
    with app.app_context():
        student_id = User.create('Student','student@example.com','unused').id
    path = f'/admin/users/{student_id}/premium'
    for token in ('', 'invalid', '\u0442\u043e\u043a\u0435\u043d'):
        assert client.post(path, data={'premium':'1','csrf_token':token}).status_code == 400
    for _ in range(2):
        response = admin_post(client, path, data={'premium':'1', 'q':'Student', 'role':'student', 'page':'2'})
        assert response.status_code == 302
        assert 'q=Student' in response.headers['Location']
    with app.app_context():
        assert get_db().execute('SELECT is_premium FROM users WHERE id = ?', (student_id,)).fetchone()[0] == 1
    assert admin_post(client, path, data={'premium':'bogus'}).status_code == 400
    assert admin_post(client, f'/admin/users/{admin_id}/premium', data={'premium':'1'}).status_code == 400
    assert admin_post(client, '/admin/users/99999/premium', data={'premium':'1'}).status_code == 404
    assert client.post('/admin/mocks/new', data={'title':'Unprotected'}).status_code == 400
    assert admin_post(client, path, data={'premium':'0'}).status_code == 302
    with app.app_context():
        assert get_db().execute('SELECT is_premium FROM users WHERE id = ?', (student_id,)).fetchone()[0] == 0
