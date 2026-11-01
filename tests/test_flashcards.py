import json

import pytest
from werkzeug.security import generate_password_hash

from app.database import get_db, init_db
from app.models import User


@pytest.fixture()
def student(app, client):
    with app.app_context():
        User.create("Vocabulary Student", "vocab@example.com", generate_password_hash("securepass"))
        User.create("Other Student", "other@example.com", generate_password_hash("securepass"))
    client.post("/auth/login", data={"email": "vocab@example.com", "password": "securepass"})
    client.get("/flashcards/")
    return client


def post(client, path, **data):
    with client.session_transaction() as session:
        token = session["flashcards_csrf_token"]
    return client.post(path, data={"csrf_token": token, **data})


def words(app):
    with app.app_context():
        return [dict(row) for row in get_db().execute("SELECT * FROM vocabulary_words ORDER BY id")]


def quiz_data(app, location):
    with app.app_context():
        return dict(get_db().execute(
            "SELECT * FROM vocabulary_quizzes WHERE id = ?", (location.rsplit("/", 1)[-1],)
        ).fetchone())


def add_words(client, count=4):
    for number in range(count):
        assert post(
            client, "/flashcards/words", term=f"Word {number}",
            meaning=f"Meaning {number}", example=f"Private example {number}",
        ).status_code == 302


def other_client(app):
    other = app.test_client()
    other.post("/auth/login", data={"email": "other@example.com", "password": "securepass"})
    other.get("/flashcards/")
    return other


def test_flashcards_require_login(client):
    for path in ("/flashcards/", "/flashcards/study", "/flashcards/quiz/unknown", "/flashcards/words/1/edit"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]
    for path in ("/flashcards/words", "/flashcards/quiz/start", "/flashcards/words/1/delete"):
        assert client.post(path).status_code == 302


def test_empty_collection_and_study_redirect(student):
    response = student.get("/flashcards/")
    assert b"Save your first word" in response.data
    assert b"2 words with different meanings" in response.data
    assert student.get("/flashcards/study").headers["Location"].endswith("/flashcards/")


def test_add_edit_delete_and_duplicate_validation(app, student):
    assert post(student, "/flashcards/words", term="  Resilient  ", meaning="  Able to recover  ", example="Stay resilient.").status_code == 302
    word = words(app)[0]
    assert word["term"] == "Resilient"
    assert word["meaning"] == "Able to recover"
    assert student.get("/flashcards/").data.count(b"Stay resilient.") == 1
    assert post(student, "/flashcards/words", term="RESILIENT", meaning="Another meaning").status_code == 400
    assert len(words(app)) == 1
    path = f"/flashcards/words/{word['id']}/edit"
    assert student.get(path).status_code == 200
    assert post(student, path, term="Adaptable", meaning="Able to change", example="").status_code == 302
    assert words(app)[0]["term"] == "Adaptable"
    assert post(student, f"/flashcards/words/{word['id']}/delete").status_code == 302
    assert words(app) == []


@pytest.mark.parametrize("data", [
    {"term": " ", "meaning": "Meaning"},
    {"term": "Word", "meaning": "\n "},
    {"term": "w" * 101, "meaning": "Meaning"},
    {"term": "Word", "meaning": "m" * 501},
    {"term": "Word", "meaning": "Meaning", "example": "e" * 1001},
])
def test_rejects_invalid_vocabulary_without_saving(app, student, data):
    assert post(student, "/flashcards/words", **data).status_code == 400
    assert words(app) == []


def test_unicode_duplicates_and_conflicting_edits(app, student):
    assert post(student, "/flashcards/words", term="Straße", meaning="A street").status_code == 302
    assert post(student, "/flashcards/words", term="STRASSE", meaning="Street").status_code == 400
    assert post(student, "/flashcards/words", term="Take   part", meaning="Participate").status_code == 302
    word_id = words(app)[1]["id"]
    assert post(student, f"/flashcards/words/{word_id}/edit", term="straße", meaning="Street").status_code == 400
    assert words(app)[1]["term"] == "Take part"


def test_vocabulary_is_private_between_students(app, student):
    add_words(student, 2)
    word_id = words(app)[0]["id"]
    other = other_client(app)
    assert b"Meaning 0" not in other.get("/flashcards/").data
    assert other.get("/flashcards/study").status_code == 302
    path = f"/flashcards/words/{word_id}"
    assert other.get(path + "/edit").status_code == 404
    assert post(other, path + "/edit", term="Changed", meaning="Changed").status_code == 404
    assert post(other, path + "/delete").status_code == 404
    assert len(words(app)) == 2
    # The same word is allowed in a different student's private collection.
    assert post(other, "/flashcards/words", term="Word 0", meaning="Different personal meaning").status_code == 302
    study = student.get("/flashcards/study")
    assert b"Private example 0" in study.data
    assert b"Different personal meaning" not in study.data


def test_forms_require_csrf_token(app, student):
    for token in (None, "wrong-token", "токен"):
        data = {"term": "Word", "meaning": "Meaning"}
        if token is not None:
            data["csrf_token"] = token
        assert student.post("/flashcards/words", data=data).status_code == 400
    assert words(app) == []
    assert student.post("/flashcards/quiz/start").status_code == 400


def test_saved_vocabulary_is_escaped_in_pages_and_study_data(student):
    term = '<img src=x onerror="alert(1)">'
    post(student, "/flashcards/words", term=term, meaning="</script><script>alert(1)</script>")
    library = student.get("/flashcards/").data
    assert term.encode() not in library
    assert b"&lt;img" in library
    study = student.get("/flashcards/study").data
    assert b"</script><script>alert(1)</script>" not in study
    assert b"\\u003c/script\\u003e" in study


def test_quiz_requires_distinct_meanings_and_supports_small_collections(app, student):
    post(student, "/flashcards/words", term="Large", meaning="Very big")
    post(student, "/flashcards/words", term="Huge", meaning=" very   BIG ")
    assert post(student, "/flashcards/quiz/start").headers["Location"].endswith("/flashcards/")
    post(student, "/flashcards/words", term="Tiny", meaning="Very small")
    location = post(student, "/flashcards/quiz/start").headers["Location"]
    questions = json.loads(quiz_data(app, location)["questions_json"])
    assert len(questions) == 3
    for question in questions:
        assert len(question["choices"]) == 2
        assert len({" ".join(choice.split()).casefold() for choice in question["choices"]}) == 2


def test_quiz_uses_only_own_words_with_unique_choices_and_ten_question_limit(app, student):
    add_words(student, 14)
    other = other_client(app)
    post(other, "/flashcards/words", term="Secret foreign word", meaning="Secret foreign meaning")
    location = post(student, "/flashcards/quiz/start").headers["Location"]
    questions = json.loads(quiz_data(app, location)["questions_json"])
    assert len(questions) == 10
    assert len({question["term"] for question in questions}) == 10
    for question in questions:
        assert len(question["choices"]) == len(set(question["choices"])) == 4
        assert question["choices"][question["correct"]].split()[-1] == question["term"].split()[-1]
        assert all(choice.startswith("Meaning ") for choice in question["choices"])
    response = student.get(location)
    assert response.status_code == 200
    assert b"Secret foreign" not in response.data
    assert b"Private example" not in response.data
    assert b'data-correct' not in response.data


def test_quiz_scores_on_server_and_keeps_results_on_resubmission(app, student):
    add_words(student)
    location = post(student, "/flashcards/quiz/start").headers["Location"]
    questions = json.loads(quiz_data(app, location)["questions_json"])
    answers = {f"question_{number}": str(q["correct"] if number < 2 else (q["correct"] + 1) % len(q["choices"])) for number, q in enumerate(questions)}
    assert post(student, location, **answers, score="999").status_code == 302
    saved = quiz_data(app, location)
    assert saved["score"] == 2
    assert saved["completed_at"] is not None
    result = student.get(location)
    assert b"50% correct" in result.data
    assert b"Correct meaning" in result.data
    assert b"Private example" in result.data
    post(student, location, **{f"question_{n}": str(q["correct"]) for n, q in enumerate(questions)})
    assert quiz_data(app, location)["score"] == 2
    assert quiz_data(app, location)["answers_json"] == saved["answers_json"]
    assert location.encode() in student.get("/flashcards/").data


def test_invalid_or_missing_answers_do_not_complete_quiz(app, student):
    add_words(student, 2)
    location = post(student, "/flashcards/quiz/start").headers["Location"]
    for answers in ({}, {"question_0": "0"}, {"question_0": "-1", "question_1": "99"}, {"question_0": "0", "question_1": "bad"}):
        assert post(student, location, **answers).status_code == 400
        saved = quiz_data(app, location)
        assert saved["score"] is None
        assert saved["completed_at"] is None


def test_quizzes_and_results_are_private(app, student):
    add_words(student, 2)
    location = post(student, "/flashcards/quiz/start").headers["Location"]
    other = other_client(app)
    assert other.get(location).status_code == 404
    assert post(other, location, question_0="0", question_1="0").status_code == 404
    questions = json.loads(quiz_data(app, location)["questions_json"])
    post(student, location, **{f"question_{n}": str(q["correct"]) for n, q in enumerate(questions)})
    assert other.get(location).status_code == 404
    assert location.encode() not in other.get("/flashcards/").data


def test_active_quiz_survives_word_edits_deletion_and_database_reinitialization(app, student):
    add_words(student, 2)
    location = post(student, "/flashcards/quiz/start").headers["Location"]
    questions = json.loads(quiz_data(app, location)["questions_json"])
    with app.app_context():
        init_db()
    assert len(words(app)) == 2
    assert json.loads(quiz_data(app, location)["questions_json"]) == questions
    word_id = words(app)[0]["id"]
    post(student, f"/flashcards/words/{word_id}/edit", term="Updated word", meaning="Updated meaning")
    for word in words(app):
        post(student, f"/flashcards/words/{word['id']}/delete")
    with app.app_context():
        init_db()
    assert student.get(location).status_code == 200
    post(student, location, **{f"question_{n}": str(q["correct"]) for n, q in enumerate(questions)})
    assert quiz_data(app, location)["score"] == 2
    assert b"100% correct" in student.get(location).data
    assert b"Updated meaning" not in student.get(location).data


def test_saving_unchanged_card_or_example_does_not_erase_review_progress(app, student):
    post(student, '/flashcards/words', term='Resilient', meaning='Able to recover', example='Stay resilient.')
    word = words(app)[0]
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO vocabulary_schedule VALUES(?,'2099-01-01',30,'2026-10-01')", (word['id'],))
        db.commit()
    path = f"/flashcards/words/{word['id']}/edit"
    for example in ('Stay resilient.', 'She stayed resilient during the exam.'):
        assert post(student, path, term=word['term'], meaning=word['meaning'], example=example).status_code == 302
        with app.app_context():
            schedule = get_db().execute('SELECT * FROM vocabulary_schedule WHERE word_id=?', (word['id'],)).fetchone()
            assert schedule['interval_days'] == 30 and schedule['due_on'] == '2099-01-01'
    assert post(student, path, term=word['term'], meaning='Recovering quickly from difficulty', example='').status_code == 302
    with app.app_context():
        assert get_db().execute('SELECT 1 FROM vocabulary_schedule WHERE word_id=?', (word['id'],)).fetchone() is None
