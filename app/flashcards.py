"""Private vocabulary collections, flashcard study, and vocabulary quizzes."""

import json
import random
import secrets
import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from .database import get_db


flashcards_bp = Blueprint("flashcards", __name__, url_prefix="/flashcards")
MAX_QUIZ_QUESTIONS = 10


def _normalized(value):
    return " ".join(value.split()).casefold()


def _csrf_token():
    if "flashcards_csrf_token" not in session:
        session["flashcards_csrf_token"] = secrets.token_urlsafe(32)
    return session["flashcards_csrf_token"]


@flashcards_bp.context_processor
def flashcards_context():
    return {"flashcards_csrf_token": _csrf_token()}


@flashcards_bp.before_request
def protect_forms():
    if request.method == "POST" and current_user.is_authenticated:
        supplied = request.form.get("csrf_token", "")
        expected = session.get("flashcards_csrf_token", "")
        if not expected or not secrets.compare_digest(supplied.encode(), expected.encode()):
            abort(400, description="This form expired. Refresh the page and try again.")


def _words():
    return [dict(row) for row in get_db().execute(
        "SELECT id, term, meaning, example FROM vocabulary_words WHERE user_id = ? ORDER BY id DESC",
        (current_user.id,),
    ).fetchall()]


def _word_or_404(word_id):
    word = get_db().execute(
        "SELECT id, term, meaning, example FROM vocabulary_words WHERE id = ? AND user_id = ?",
        (word_id, current_user.id),
    ).fetchone()
    if word is None:
        abort(404)
    return dict(word)


def _render_library(values=None, status=200):
    from datetime import date
    from .vocabulary_review import review_summary

    words = _words()
    schedules = {row['word_id']: row['due_on'] for row in get_db().execute(
        "SELECT s.word_id, s.due_on FROM vocabulary_schedule s JOIN vocabulary_words w ON w.id=s.word_id WHERE w.user_id=?",
        (current_user.id,),
    )}
    today = date.today().isoformat()
    for word in words:
        due_on = schedules.get(word['id'])
        word['review_label'] = 'New · ready to review' if due_on is None else 'Due today' if due_on <= today else f'Next review: {due_on}'
    summary = review_summary(current_user.id)
    recent_quizzes = []
    for row in get_db().execute(
        """SELECT id, score, questions_json, completed_at FROM vocabulary_quizzes
        WHERE user_id = ? AND completed_at IS NOT NULL ORDER BY completed_at DESC, rowid DESC LIMIT 3""",
        (current_user.id,),
    ).fetchall():
        recent_quizzes.append({
            "id": row["id"], "score": row["score"],
            "total": len(json.loads(row["questions_json"])), "completed_at": row["completed_at"],
        })
    return render_template(
        "flashcards/index.html", words=words, values=values or {}, review_summary=summary,
        can_quiz=len({_normalized(word["meaning"]) for word in words}) >= 2,
        quiz_size=min(len(words), MAX_QUIZ_QUESTIONS), recent_quizzes=recent_quizzes,
    ), status


def _word_values():
    return {
        "term": " ".join(request.form.get("term", "").split()),
        "meaning": request.form.get("meaning", "").strip(),
        "example": request.form.get("example", "").strip(),
    }


def _validation_error(values):
    if not values["term"] or not values["meaning"]:
        return "Add both a word or phrase and its meaning."
    if len(values["term"]) > 100:
        return "Keep the word or phrase to 100 characters or fewer."
    if len(values["meaning"]) > 500:
        return "Keep the meaning to 500 characters or fewer."
    if len(values["example"]) > 1000:
        return "Keep the example to 1,000 characters or fewer."
    return None


@flashcards_bp.route("/")
@login_required
def index():
    return _render_library()


@flashcards_bp.route("/words", methods=("POST",))
@login_required
def add_word():
    values = _word_values()
    error = _validation_error(values)
    if error is None:
        db = get_db()
        try:
            db.execute(
                """INSERT INTO vocabulary_words (user_id, term, normalized_term, meaning, example)
                VALUES (?, ?, ?, ?, ?)""",
                (current_user.id, values["term"], _normalized(values["term"]), values["meaning"], values["example"]),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            error = "That word or phrase is already saved. Edit it to update its meaning."
        else:
            flash("Word saved. Your next flashcard is ready.", "success")
            return redirect(url_for("flashcards.index"))
    flash(error, "error")
    return _render_library(values, status=400)


@flashcards_bp.route("/words/<int:word_id>/edit", methods=("GET", "POST"))
@login_required
def edit_word(word_id):
    word = _word_or_404(word_id)
    values = word
    status = 200
    if request.method == "POST":
        values = _word_values()
        error = _validation_error(values)
        if error is None:
            db = get_db()
            try:
                db.execute(
                    """UPDATE vocabulary_words SET term = ?, normalized_term = ?, meaning = ?, example = ?
                    WHERE id = ? AND user_id = ?""",
                    (values["term"], _normalized(values["term"]), values["meaning"], values["example"], word_id, current_user.id),
                )
                if values["term"] != word["term"] or values["meaning"] != word["meaning"]:
                    db.execute("DELETE FROM vocabulary_schedule WHERE word_id = ?", (word_id,))
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                error = "Another card already has that word or phrase."
            else:
                flash("Your vocabulary card has been updated.", "success")
                return redirect(url_for("flashcards.index"))
        flash(error, "error")
        status = 400
    return render_template("flashcards/edit.html", word=word, values=values), status


@flashcards_bp.route("/words/<int:word_id>/delete", methods=("POST",))
@login_required
def delete_word(word_id):
    _word_or_404(word_id)
    db = get_db()
    db.execute("DELETE FROM vocabulary_words WHERE id = ? AND user_id = ?", (word_id, current_user.id))
    db.commit()
    flash("Word removed from your vocabulary.", "info")
    return redirect(url_for("flashcards.index"))


@flashcards_bp.route("/study")
@login_required
def study():
    words = _words()
    if not words:
        flash("Save your first word to start studying flashcards.", "info")
        return redirect(url_for("flashcards.index"))
    random.shuffle(words)
    return render_template(
        "flashcards/study.html", words=words,
        can_quiz=len({_normalized(word["meaning"]) for word in words}) >= 2,
    )


@flashcards_bp.route("/quiz/start", methods=("POST",))
@login_required
def start_quiz():
    words = _words()
    meanings = {}
    for word in words:
        meanings.setdefault(_normalized(word["meaning"]), word["meaning"])
    if len(meanings) < 2:
        flash("Save at least 2 words with different meanings to start a multiple-choice quiz.", "info")
        return redirect(url_for("flashcards.index"))

    # Preserve the vocabulary as it was when this quiz started.
    questions = []
    for word in random.sample(words, min(len(words), MAX_QUIZ_QUESTIONS)):
        other_meanings = [meaning for key, meaning in meanings.items() if key != _normalized(word["meaning"])]
        choices = random.sample(other_meanings, min(3, len(other_meanings))) + [word["meaning"]]
        random.shuffle(choices)
        questions.append({
            "term": word["term"], "choices": choices,
            "correct": choices.index(word["meaning"]), "example": word["example"],
        })
    quiz_id = secrets.token_urlsafe(24)
    db = get_db()
    db.execute(
        "INSERT INTO vocabulary_quizzes (id, user_id, questions_json) VALUES (?, ?, ?)",
        (quiz_id, current_user.id, json.dumps(questions, ensure_ascii=False)),
    )
    db.commit()
    return redirect(url_for("flashcards.quiz", quiz_id=quiz_id))


@flashcards_bp.route("/quiz/<quiz_id>", methods=("GET", "POST"))
@login_required
def quiz(quiz_id):
    db = get_db()
    quiz_row = db.execute(
        "SELECT * FROM vocabulary_quizzes WHERE id = ? AND user_id = ?", (quiz_id, current_user.id),
    ).fetchone()
    if quiz_row is None:
        abort(404)
    questions = json.loads(quiz_row["questions_json"])
    if quiz_row["completed_at"] is not None:
        return render_template(
            "flashcards/result.html", questions=questions,
            answers=json.loads(quiz_row["answers_json"]), score=quiz_row["score"],
            percentage=round(quiz_row["score"] / len(questions) * 100),
        )

    answers = {}
    if request.method == "POST":
        for number, question in enumerate(questions):
            raw_answer = request.form.get(f"question_{number}", "")
            try:
                answer = int(raw_answer)
            except ValueError:
                continue
            if 0 <= answer < len(question["choices"]):
                answers[str(number)] = answer
        if len(answers) == len(questions):
            score = sum(answers[str(number)] == question["correct"] for number, question in enumerate(questions))
            db.execute(
                """UPDATE vocabulary_quizzes SET answers_json = ?, score = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND completed_at IS NULL""",
                (json.dumps(answers), score, quiz_id, current_user.id),
            )
            db.commit()
            return redirect(url_for("flashcards.quiz", quiz_id=quiz_id))
        flash("Choose one answer for every word before checking your score.", "error")

    # The answer key and examples stay on the server until the quiz is submitted.
    public_questions = [{"term": question["term"], "choices": question["choices"]} for question in questions]
    return render_template(
        "flashcards/quiz.html", quiz_id=quiz_id, questions=public_questions, answers=answers,
    ), 400 if request.method == "POST" else 200
