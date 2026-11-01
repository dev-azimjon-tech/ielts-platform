import json
import re
import unicodedata

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .database import get_db
from .practice_resources import OFFICIAL_RESOURCES


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
    is_reading = mock["skill"] == "reading"
    content_table = "reading_passages" if is_reading else "listening_scripts"
    mock["steps"] = [
        dict(row)
        for row in db.execute(
            f"SELECT * FROM {content_table} WHERE mock_id = ? ORDER BY display_order, id",
            (mock_id,),
        ).fetchall()
    ]
    columns = (
        "id, passage_id, listening_script_id, question_number, "
        "question_type, prompt, options_json"
    )
    if include_answers:
        columns += ", correct_answer, explanation"
    mock["questions"] = []
    questions_by_step = {}
    for row in db.execute(
        f"SELECT {columns} FROM questions WHERE mock_id = ? ORDER BY question_number",
        (mock_id,),
    ).fetchall():
        question = dict(row)
        question["options"] = json.loads(question.pop("options_json") or "[]")
        mock["questions"].append(question)
        parent_id = question["passage_id" if is_reading else "listening_script_id"]
        questions_by_step.setdefault(parent_id, []).append(question)

    for step in mock["steps"]:
        step["questions"] = questions_by_step.get(step["id"], [])
        step["start_question"] = (
            step["questions"][0]["question_number"] if step["questions"] else None
        )
        step["end_question"] = (
            step["questions"][-1]["question_number"] if step["questions"] else None
        )
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
    answer = unicodedata.normalize('NFKC', answer).strip().casefold().replace('_', ' ')
    answer = re.sub(r"[^\w: @.]+", " ", answer)
    return re.sub(r"\s+", " ", answer).strip()


def _check_access(mock, attempts=None):
    limit = FREE_LIMITS[mock["skill"]]
    if attempts is None:
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
    skill = request.args.get("skill", "all")
    if skill != "all" and skill not in FREE_LIMITS:
        skill = "all"
    counts = {
        row["skill"]: row["completed"]
        for row in get_db().execute(
            """
            SELECT m.skill, COUNT(*) AS completed
            FROM attempts AS a JOIN mock_tests AS m ON m.id = a.mock_id
            WHERE a.user_id = ? GROUP BY m.skill
            """,
            (current_user.id,),
        )
    }
    rows = get_db().execute(
        "SELECT * FROM mock_tests WHERE is_published = 1 ORDER BY skill, id"
    ).fetchall()
    mocks = []
    for row in rows:
        mock = dict(row)
        if skill != "all" and mock["skill"] != skill:
            continue
        mock["attempts"] = counts.get(mock["skill"], 0)
        mock["limit"] = FREE_LIMITS[mock["skill"]]
        mock["remaining"] = max(mock["limit"] - mock["attempts"], 0)
        mocks.append(mock)
    return render_template(
        "mocks/index.html",
        mocks=mocks,
        selected_skill=skill,
        official_resources=[
            resource for resource in OFFICIAL_RESOURCES
            if skill == "all" or skill in resource["skills"]
        ],
    )


@mocks_bp.route("/<int:mock_id>")
@login_required
def take(mock_id):
    mock = _load_mock(mock_id)
    attempts = _attempt_count(mock["skill"])
    if not _check_access(mock, attempts):
        return redirect(url_for("mocks.index"))
    return render_template(
        "mocks/take.html",
        mock=mock,
        exam_mode=True,
        listening_scripts=(
            [step["script"] for step in mock["steps"]]
            if mock["skill"] == "listening" else []
        ),
    )


@mocks_bp.route("/<int:mock_id>/submit", methods=("POST",))
@login_required
def submit(mock_id):
    from .exam_sessions import submission_redirect
    replay = submission_redirect('mock', mock_id)
    if replay:
        return redirect(replay)
    mock = _load_mock(mock_id, include_answers=True)
    if not _check_access(mock):
        return redirect(url_for("mocks.index"))

    if not mock['questions']:
        abort(400, 'This mock has no questions to submit.')
    answers = {}
    score = 0
    result_questions = []
    for question in mock["questions"]:
        answer = request.form.get(f"question_{question['id']}", "").strip()
        if len(answer) > 500:
            abort(400, "Keep each answer below 500 characters.")
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

    from .exam_sessions import save_submission_draft
    if save_submission_draft('mock', mock_id, {f'question_{key}':value for key,value in answers.items()}) is False:
        abort(409, 'A newer exam draft exists. Copy your answers before reloading this section.')
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    replay = submission_redirect('mock', mock_id)
    if replay:
        db.commit()
        return redirect(replay)
    if not _check_access(mock):
        db.rollback()
        return redirect(url_for("mocks.index"))
    cursor = db.execute(
        """
        INSERT INTO attempts (user_id, mock_id, score, total_points, answers_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (current_user.id, mock_id, score, len(mock["questions"]), json.dumps(answers)),
    )
    db.execute("INSERT INTO attempt_snapshots(attempt_id,questions_json) VALUES(?,?)",
               (cursor.lastrowid, json.dumps(result_questions, ensure_ascii=False)))
    from .learning import complete_exam_section
    from .main import _estimated_band
    if complete_exam_section("mock", mock_id, cursor.lastrowid, _estimated_band(score,len(mock["questions"]),mock["skill"])):
        return redirect(url_for("learning.exam_continue"))
    db.commit()

    return render_template(
        "mocks/result.html",
        mock=mock,
        score=score,
        total=len(mock["questions"]),
        questions=result_questions,
    )
