import json
import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .database import get_db


mocks_bp = Blueprint("mocks", __name__, url_prefix="/mocks")

FREE_LIMITS = {"reading": 10, "listening": 10}


def _load_mock(mock_id, include_answers=False):
    db = get_db()
    mock_row = db.execute(
        "SELECT * FROM mock_tests WHERE id = ? AND is_published = 1", (mock_id,)
    ).fetchone()
    if mock_row is None:
        abort(404)

    mock = dict(mock_row)
    mock["passages"] = [
        dict(row)
        for row in db.execute(
            "SELECT * FROM reading_passages WHERE mock_id = ? ORDER BY display_order",
            (mock_id,),
        ).fetchall()
    ]
    mock["listening_scripts"] = [
        dict(row)
        for row in db.execute(
            "SELECT * FROM listening_scripts WHERE mock_id = ? ORDER BY display_order",
            (mock_id,),
        ).fetchall()
    ]
    mock["questions"] = []
    for row in db.execute(
        "SELECT * FROM questions WHERE mock_id = ? ORDER BY question_number",
        (mock_id,),
    ).fetchall():
        question = dict(row)
        question["options"] = json.loads(question["options_json"] or "[]")
        if not include_answers:
            question.pop("correct_answer", None)
            question.pop("explanation", None)
        mock["questions"].append(question)

    if mock["skill"] == "reading":
        mock["steps"] = mock["passages"]
    else:
        mock["steps"] = mock["listening_scripts"]

    for step in mock["steps"]:
        step["questions"] = [
            question
            for question in mock["questions"]
            if (
                question.get("passage_id") == step["id"]
                if mock["skill"] == "reading"
                else question.get("listening_script_id") == step["id"]
            )
        ]
        step["start_question"] = step["questions"][0]["question_number"]
        step["end_question"] = step["questions"][-1]["question_number"]
    return mock


def _attempt_count(skill):
    row = get_db().execute(
        """
        SELECT COUNT(*) AS count
        FROM attempts AS a
        JOIN mock_tests AS m ON m.id = a.mock_id
        WHERE a.user_id = ? AND m.skill = ?
        """,
        (current_user.id, skill),
    ).fetchone()
    return row["count"]


def _normalise_answer(answer):
    answer = answer or ""
    answer = answer.strip().lower()
    answer = re.sub(r"[^a-z0-9: @.]+", " ", answer)
    return re.sub(r"\s+", " ", answer).strip()


def _check_access(mock):
    limit = FREE_LIMITS[mock["skill"]]
    attempts = _attempt_count(mock["skill"])
    if not current_user.is_premium and attempts >= limit:
        flash(
            f"You have used all {limit} free {mock['skill']} mocks. Premium access will be available soon.",
            "info",
        )
        return False
    return True


@mocks_bp.route("/")
@login_required
def index():
    rows = get_db().execute(
        "SELECT * FROM mock_tests WHERE is_published = 1 ORDER BY skill, id"
    ).fetchall()
    mocks = []
    for row in rows:
        mock = dict(row)
        mock["attempts"] = _attempt_count(mock["skill"])
        mock["limit"] = FREE_LIMITS[mock["skill"]]
        mock["remaining"] = max(mock["limit"] - mock["attempts"], 0)
        mocks.append(mock)
    return render_template("mocks/index.html", mocks=mocks)


@mocks_bp.route("/<int:mock_id>")
@login_required
def take(mock_id):
    mock = _load_mock(mock_id)
    if not _check_access(mock):
        return redirect(url_for("mocks.index"))
    return render_template(
        "mocks/take.html",
        mock=mock,
        attempt_count=_attempt_count(mock["skill"]),
        remaining=max(FREE_LIMITS[mock["skill"]] - _attempt_count(mock["skill"]), 0),
    )


@mocks_bp.route("/<int:mock_id>/submit", methods=("POST",))
@login_required
def submit(mock_id):
    mock = _load_mock(mock_id, include_answers=True)
    if not _check_access(mock):
        return redirect(url_for("mocks.index"))

    answers = {}
    score = 0
    result_questions = []
    for question in mock["questions"]:
        answer = request.form.get(f"question_{question['id']}", "").strip()
        answers[str(question["id"])] = answer
        is_correct = _normalise_answer(answer) == _normalise_answer(
            question["correct_answer"]
        )
        if is_correct:
            score += 1
        result_questions.append(
            {
                **question,
                "submitted_answer": answer or "Not answered",
                "is_correct": is_correct,
            }
        )

    db = get_db()
    db.execute(
        """
        INSERT INTO attempts (user_id, mock_id, score, total_points, answers_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (current_user.id, mock_id, score, len(mock["questions"]), json.dumps(answers)),
    )
    db.commit()

    return render_template(
        "mocks/result.html",
        mock=mock,
        score=score,
        total=len(mock["questions"]),
        questions=result_questions,
    )
