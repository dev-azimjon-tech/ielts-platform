import json
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..database import get_db


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
VALID_SKILLS = {"reading", "listening"}
VALID_QUESTION_TYPES = {"multiple_choice", "tfng", "short_answer"}


def admin_required(view):
    """Allow only signed-in users who have the admin flag."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


def _get_mock(mock_id):
    row = get_db().execute(
        "SELECT * FROM mock_tests WHERE id = ?", (mock_id,)
    ).fetchone()
    if row is None:
        abort(404)
    return dict(row)


def _mock_with_content(mock_id):
    db = get_db()
    mock = _get_mock(mock_id)
    if mock["skill"] == "reading":
        content_rows = db.execute(
            """
            SELECT * FROM reading_passages
            WHERE mock_id = ?
            ORDER BY display_order, id
            """,
            (mock_id,),
        ).fetchall()
        content_key = "passage_id"
    else:
        content_rows = db.execute(
            """
            SELECT * FROM listening_scripts
            WHERE mock_id = ?
            ORDER BY display_order, id
            """,
            (mock_id,),
        ).fetchall()
        content_key = "listening_script_id"

    content = []
    for row in content_rows:
        section = dict(row)
        section["questions"] = []
        for question_row in db.execute(
            f"SELECT * FROM questions WHERE {content_key} = ? ORDER BY question_number",
            (row["id"],),
        ).fetchall():
            question = dict(question_row)
            question["options"] = json.loads(question["options_json"] or "[]")
            section["questions"].append(question)
        content.append(section)

    mock["content"] = content
    mock["question_count"] = sum(len(section["questions"]) for section in content)
    return mock


def _form_mock_values():
    skill = request.form.get("skill", "").strip().lower()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    time_limit = request.form.get("time_limit_minutes", "").strip()
    error = None

    if skill not in VALID_SKILLS:
        error = "Choose Reading or Listening."
    elif not title:
        error = "A mock title is required."
    elif len(title) > 140:
        error = "The title must be 140 characters or fewer."
    elif not description:
        error = "A short description is required."
    else:
        try:
            time_limit = int(time_limit)
        except ValueError:
            error = "Time limit must be a whole number."
        else:
            if time_limit < 1 or time_limit > 300:
                error = "Time limit must be between 1 and 300 minutes."

    return {
        "skill": skill,
        "title": title,
        "description": description,
        "time_limit_minutes": time_limit,
    }, error


def _content_values(mock):
    title = request.form.get("title", "").strip()
    text_field = "body" if mock["skill"] == "reading" else "script"
    body = request.form.get(text_field, "").strip()
    error = None
    if not title:
        error = "A passage or section title is required."
    elif not body:
        error = "Add the passage text or listening script."
    return {"title": title, "body": body}, error


def _question_values(mock):
    question_type = request.form.get("question_type", "").strip()
    prompt = request.form.get("prompt", "").strip()
    correct_answer = request.form.get("correct_answer", "").strip()
    explanation = request.form.get("explanation", "").strip()
    options = [
        line.strip()
        for line in request.form.get("options", "").splitlines()
        if line.strip()
    ]
    error = None

    if question_type not in VALID_QUESTION_TYPES:
        error = "Choose a supported question type."
    elif not prompt:
        error = "The question prompt is required."
    elif not correct_answer:
        error = "The correct answer is required."
    elif question_type == "multiple_choice":
        if len(options) < 2:
            error = "Multiple-choice questions need at least two options."
        elif correct_answer.upper() not in {
            chr(65 + index) for index in range(len(options))
        }:
            error = "For multiple choice, enter the correct option letter (A, B, C...)."
        else:
            correct_answer = correct_answer.upper()
    elif question_type == "tfng":
        options = ["TRUE", "FALSE", "NOT GIVEN"]
        if correct_answer.upper() not in set(options):
            error = "True/False/Not Given answers must be TRUE, FALSE, or NOT GIVEN."
        else:
            correct_answer = correct_answer.upper()
    else:
        options = []

    return {
        "question_type": question_type,
        "prompt": prompt,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": explanation or "Review the source text for the evidence.",
    }, error


@admin_bp.route("/")
@admin_required
def index():
    db = get_db()
    counts = {
        "users": db.execute("SELECT COUNT(*) AS value FROM users").fetchone()["value"],
        "premium_users": db.execute(
            "SELECT COUNT(*) AS value FROM users WHERE is_premium = 1"
        ).fetchone()["value"],
        "mocks": db.execute("SELECT COUNT(*) AS value FROM mock_tests").fetchone()["value"],
        "published_mocks": db.execute(
            "SELECT COUNT(*) AS value FROM mock_tests WHERE is_published = 1"
        ).fetchone()["value"],
        "attempts": db.execute("SELECT COUNT(*) AS value FROM attempts").fetchone()["value"],
    }
    recent_users = db.execute(
        """
        SELECT id, name, email, is_premium, is_admin, created_at
        FROM users ORDER BY id DESC LIMIT 8
        """
    ).fetchall()
    recent_attempts = db.execute(
        """
        SELECT a.score, a.total_points, a.completed_at, u.name, m.title, m.skill
        FROM attempts AS a
        JOIN users AS u ON u.id = a.user_id
        JOIN mock_tests AS m ON m.id = a.mock_id
        ORDER BY a.id DESC LIMIT 8
        """
    ).fetchall()
    return render_template(
        "admin/dashboard.html",
        counts=counts,
        recent_users=recent_users,
        recent_attempts=recent_attempts,
    )


@admin_bp.route("/mocks")
@admin_required
def mocks():
    db = get_db()
    rows = db.execute("SELECT * FROM mock_tests ORDER BY skill, id").fetchall()
    mocks = []
    for row in rows:
        mock = dict(row)
        if mock["skill"] == "reading":
            section_table = "reading_passages"
        else:
            section_table = "listening_scripts"
        mock["section_count"] = db.execute(
            f"SELECT COUNT(*) AS value FROM {section_table} WHERE mock_id = ?",
            (mock["id"],),
        ).fetchone()["value"]
        mock["question_count"] = db.execute(
            "SELECT COUNT(*) AS value FROM questions WHERE mock_id = ?",
            (mock["id"],),
        ).fetchone()["value"]
        mocks.append(mock)
    return render_template("admin/mocks.html", mocks=mocks)


@admin_bp.route("/mocks/new", methods=("GET", "POST"))
@admin_required
def new_mock():
    values = {
        "skill": "reading",
        "title": "",
        "description": "",
        "time_limit_minutes": 60,
    }
    if request.method == "POST":
        values, error = _form_mock_values()
        if error is None:
            db = get_db()
            cursor = db.execute(
                """
                INSERT INTO mock_tests
                    (skill, title, description, time_limit_minutes, is_published)
                VALUES (?, ?, ?, ?, 0)
                """,
                (
                    values["skill"],
                    values["title"],
                    values["description"],
                    values["time_limit_minutes"],
                ),
            )
            db.commit()
            flash("Draft mock created. Add its content before publishing.", "success")
            return redirect(url_for("admin.edit_mock", mock_id=cursor.lastrowid))
        flash(error, "error")
    return render_template("admin/mock_form.html", values=values, editing=False)


@admin_bp.route("/mocks/<int:mock_id>/edit-details", methods=("GET", "POST"))
@admin_required
def edit_mock_details(mock_id):
    mock = _get_mock(mock_id)
    values = mock.copy()
    if request.method == "POST":
        values, error = _form_mock_values()
        if error is None:
            db = get_db()
            db.execute(
                """
                UPDATE mock_tests
                SET skill = ?, title = ?, description = ?, time_limit_minutes = ?
                WHERE id = ?
                """,
                (
                    values["skill"],
                    values["title"],
                    values["description"],
                    values["time_limit_minutes"],
                    mock_id,
                ),
            )
            db.commit()
            flash("Mock details updated.", "success")
            return redirect(url_for("admin.edit_mock", mock_id=mock_id))
        flash(error, "error")
    return render_template(
        "admin/mock_form.html", values=values, editing=True, mock=mock
    )


@admin_bp.route("/mocks/<int:mock_id>/edit")
@admin_required
def edit_mock(mock_id):
    return render_template("admin/mock_edit.html", mock=_mock_with_content(mock_id))


@admin_bp.route("/mocks/<int:mock_id>/toggle-publish", methods=("POST",))
@admin_required
def toggle_publish(mock_id):
    mock = _get_mock(mock_id)
    db = get_db()
    if not mock["is_published"]:
        section_table = (
            "reading_passages" if mock["skill"] == "reading" else "listening_scripts"
        )
        section_count = db.execute(
            f"SELECT COUNT(*) AS value FROM {section_table} WHERE mock_id = ?",
            (mock_id,),
        ).fetchone()["value"]
        question_count = db.execute(
            "SELECT COUNT(*) AS value FROM questions WHERE mock_id = ?",
            (mock_id,),
        ).fetchone()["value"]
        if section_count == 0 or question_count == 0:
            flash("Add at least one passage/section and one question before publishing.", "error")
            return redirect(url_for("admin.edit_mock", mock_id=mock_id))

    new_state = 0 if mock["is_published"] else 1
    db.execute("UPDATE mock_tests SET is_published = ? WHERE id = ?", (new_state, mock_id))
    db.commit()
    flash("Mock is now published." if new_state else "Mock moved back to draft.", "success")
    return redirect(url_for("admin.edit_mock", mock_id=mock_id))


@admin_bp.route("/mocks/<int:mock_id>/content/new", methods=("GET", "POST"))
@admin_required
def new_content(mock_id):
    mock = _get_mock(mock_id)
    values = {"title": "", "body": ""}
    if request.method == "POST":
        values, error = _content_values(mock)
        if error is None:
            db = get_db()
            if mock["skill"] == "reading":
                table = "reading_passages"
                text_column = "body"
            else:
                table = "listening_scripts"
                text_column = "script"
            next_order = db.execute(
                f"SELECT COALESCE(MAX(display_order), 0) + 1 AS value FROM {table} WHERE mock_id = ?",
                (mock_id,),
            ).fetchone()["value"]
            db.execute(
                f"INSERT INTO {table} (mock_id, title, {text_column}, display_order) VALUES (?, ?, ?, ?)",
                (mock_id, values["title"], values["body"], next_order),
            )
            db.commit()
            flash("Content section added. You can now add its questions.", "success")
            return redirect(url_for("admin.edit_mock", mock_id=mock_id))
        flash(error, "error")
    return render_template("admin/content_form.html", mock=mock, values=values, editing=False)


@admin_bp.route("/mocks/<int:mock_id>/content/<int:content_id>/edit", methods=("GET", "POST"))
@admin_required
def edit_content(mock_id, content_id):
    mock = _get_mock(mock_id)
    db = get_db()
    if mock["skill"] == "reading":
        table = "reading_passages"
        text_column = "body"
    else:
        table = "listening_scripts"
        text_column = "script"
    row = db.execute(
        f"SELECT * FROM {table} WHERE id = ? AND mock_id = ?", (content_id, mock_id)
    ).fetchone()
    if row is None:
        abort(404)
    values = {"title": row["title"], "body": row[text_column]}
    if request.method == "POST":
        values, error = _content_values(mock)
        if error is None:
            db.execute(
                f"UPDATE {table} SET title = ?, {text_column} = ? WHERE id = ? AND mock_id = ?",
                (values["title"], values["body"], content_id, mock_id),
            )
            db.commit()
            flash("Content section updated.", "success")
            return redirect(url_for("admin.edit_mock", mock_id=mock_id))
        flash(error, "error")
    return render_template("admin/content_form.html", mock=mock, values=values, editing=True)


@admin_bp.route("/mocks/<int:mock_id>/content/<int:content_id>/questions/new", methods=("GET", "POST"))
@admin_required
def new_question(mock_id, content_id):
    mock = _get_mock(mock_id)
    db = get_db()
    if mock["skill"] == "reading":
        content_table = "reading_passages"
        content_key = "passage_id"
    else:
        content_table = "listening_scripts"
        content_key = "listening_script_id"
    content = db.execute(
        f"SELECT * FROM {content_table} WHERE id = ? AND mock_id = ?",
        (content_id, mock_id),
    ).fetchone()
    if content is None:
        abort(404)

    values = {
        "question_type": "multiple_choice",
        "prompt": "",
        "options": [],
        "correct_answer": "",
        "explanation": "",
    }
    if request.method == "POST":
        values, error = _question_values(mock)
        if error is None:
            question_number = db.execute(
                "SELECT COALESCE(MAX(question_number), 0) + 1 AS value FROM questions WHERE mock_id = ?",
                (mock_id,),
            ).fetchone()["value"]
            db.execute(
                f"""
                INSERT INTO questions
                    (mock_id, {content_key}, question_number, question_type,
                     prompt, options_json, correct_answer, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mock_id,
                    content_id,
                    question_number,
                    values["question_type"],
                    values["prompt"],
                    json.dumps(values["options"]),
                    values["correct_answer"],
                    values["explanation"],
                ),
            )
            db.commit()
            flash(f"Question {question_number} added.", "success")
            return redirect(url_for("admin.edit_mock", mock_id=mock_id))
        flash(error, "error")
    return render_template(
        "admin/question_form.html", mock=mock, content=content, values=values
    )


@admin_bp.route("/questions/<int:question_id>/edit", methods=("GET", "POST"))
@admin_required
def edit_question(question_id):
    db = get_db()
    question = db.execute(
        "SELECT * FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    if question is None:
        abort(404)
    question = dict(question)
    mock = _get_mock(question["mock_id"])
    if mock["skill"] == "reading":
        content_table = "reading_passages"
    else:
        content_table = "listening_scripts"
    content_id = (
        question["passage_id"]
        if mock["skill"] == "reading"
        else question["listening_script_id"]
    )
    content = db.execute(
        f"SELECT * FROM {content_table} WHERE id = ? AND mock_id = ?",
        (content_id, mock["id"]),
    ).fetchone()
    if content is None:
        abort(404)

    values = {
        "question_type": question["question_type"],
        "prompt": question["prompt"],
        "options": json.loads(question["options_json"] or "[]"),
        "correct_answer": question["correct_answer"],
        "explanation": question["explanation"],
    }
    if request.method == "POST":
        values, error = _question_values(mock)
        if error is None:
            db.execute(
                """
                UPDATE questions
                SET question_type = ?, prompt = ?, options_json = ?,
                    correct_answer = ?, explanation = ?
                WHERE id = ?
                """,
                (
                    values["question_type"],
                    values["prompt"],
                    json.dumps(values["options"]),
                    values["correct_answer"],
                    values["explanation"],
                    question_id,
                ),
            )
            db.commit()
            flash("Question updated.", "success")
            return redirect(url_for("admin.edit_mock", mock_id=mock["id"]))
        flash(error, "error")
    return render_template(
        "admin/question_form.html",
        mock=mock,
        content=content,
        values=values,
        editing=True,
    )


@admin_bp.route("/questions/<int:question_id>/delete", methods=("POST",))
@admin_required
def delete_question(question_id):
    db = get_db()
    row = db.execute(
        "SELECT mock_id FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    if row is None:
        abort(404)
    db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    db.commit()
    flash("Question deleted.", "success")
    return redirect(url_for("admin.edit_mock", mock_id=row["mock_id"]))


@admin_bp.route("/users")
@admin_required
def users():
    rows = get_db().execute(
        """
        SELECT id, name, email, is_premium, is_admin, created_at
        FROM users ORDER BY id DESC
        """
    ).fetchall()
    return render_template("admin/users.html", users=rows)


@admin_bp.route("/users/<int:user_id>/toggle-premium", methods=("POST",))
@admin_required
def toggle_premium(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    new_state = 0 if user["is_premium"] else 1
    db.execute("UPDATE users SET is_premium = ? WHERE id = ?", (new_state, user_id))
    db.commit()
    flash(
        f"{user['name']} now has premium access."
        if new_state
        else f"Premium access removed from {user['name']}.",
        "success",
    )
    return redirect(url_for("admin.users"))
