import json

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .ai_service import (
    AIServiceError,
    evaluate_speaking,
    evaluate_writing,
    generate_next_speaking_question,
    transcribe_audio,
)
from .database import get_db


ai_bp = Blueprint("ai", __name__, url_prefix="/ai")
FREE_LIMITS = {"speaking": 2, "writing": 2}
PREMIUM_LIMITS = {"speaking": 10, "writing": 10}


def _load_ai_mock(mock_id, required_skill=None):
    row = get_db().execute(
        "SELECT * FROM ai_mocks WHERE id = ? AND is_published = 1", (mock_id,)
    ).fetchone()
    if row is None or (required_skill and row["skill"] != required_skill):
        abort(404)
    mock = dict(row)
    mock["task"] = json.loads(mock["task_json"])
    return mock


def _attempt_count(skill):
    row = get_db().execute(
        """
        SELECT COUNT(*) AS count
        FROM ai_attempts AS a
        JOIN ai_mocks AS m ON m.id = a.ai_mock_id
        WHERE a.user_id = ? AND m.skill = ?
        """,
        (current_user.id, skill),
    ).fetchone()
    return row["count"]


def _limit(skill):
    return PREMIUM_LIMITS[skill] if current_user.is_premium else FREE_LIMITS[skill]


def _check_access(skill):
    attempts = _attempt_count(skill)
    limit = _limit(skill)
    if attempts >= limit:
        if current_user.is_premium:
            flash(
                f"You have completed all {limit} premium {skill} AI mocks.",
                "info",
            )
        else:
            flash(
                f"You have used both free {skill} AI mocks. Upgrade to premium for {PREMIUM_LIMITS[skill]} mocks.",
                "info",
            )
        return False
    return True


def _speaking_plan(task):
    plan = []
    for part in task.get("parts", []):
        for prompt in part.get("questions", []):
            plan.append(
                {
                    "part": part["part"],
                    "title": part["title"],
                    "instruction": part["instruction"],
                    "question": prompt,
                    "prep_seconds": part.get("prep_seconds", 0),
                }
            )
    return plan


@ai_bp.route("/")
@login_required
def index():
    rows = get_db().execute(
        "SELECT * FROM ai_mocks WHERE is_published = 1 ORDER BY skill, id"
    ).fetchall()
    mocks = []
    for row in rows:
        mock = dict(row)
        mock["attempts"] = _attempt_count(mock["skill"])
        mock["limit"] = _limit(mock["skill"])
        mock["remaining"] = max(mock["limit"] - mock["attempts"], 0)
        mock["locked"] = mock["attempts"] >= mock["limit"]
        mocks.append(mock)
    return render_template(
        "ai/index.html",
        mocks=mocks,
        speaking_attempts=_attempt_count("speaking"),
        writing_attempts=_attempt_count("writing"),
        speaking_limit=_limit("speaking"),
        writing_limit=_limit("writing"),
    )


@ai_bp.route("/speaking/<int:mock_id>")
@login_required
def speaking(mock_id):
    mock = _load_ai_mock(mock_id, "speaking")
    if not _check_access("speaking"):
        return redirect(url_for("ai.index"))
    plan = _speaking_plan(mock["task"])
    if not plan:
        abort(404)
    return render_template(
        "ai/speaking.html",
        mock=mock,
        plan=plan,
        attempt_count=_attempt_count("speaking"),
        limit=_limit("speaking"),
    )


@ai_bp.route("/speaking/<int:mock_id>/turn", methods=("POST",))
@login_required
def speaking_turn(mock_id):
    mock = _load_ai_mock(mock_id, "speaking")
    if not _check_access("speaking"):
        return jsonify({"error": "This Speaking mock is no longer available for your plan."}), 403

    audio = request.files.get("audio")
    if audio is None:
        return jsonify({"error": "Please record an answer before continuing."}), 400
    try:
        plan = _speaking_plan(mock["task"])
        plan_index = int(request.form.get("plan_index", "0"))
        if plan_index < 0 or plan_index >= len(plan):
            return jsonify({"error": "That Speaking question is not valid."}), 400
        history = json.loads(request.form.get("history", "[]"))
        if not isinstance(history, list) or len(history) > len(plan):
            return jsonify({"error": "The Speaking session data is invalid."}), 400
        current_plan = plan[plan_index]
        transcript = transcribe_audio(audio)
        displayed_question = request.form.get("question", "").strip() or current_plan["question"]
        current_turn = {
            "part": current_plan["part"],
            "question": displayed_question,
            "transcript": transcript,
        }
        updated_history = history + [current_turn]
        next_plan = plan[plan_index + 1] if plan_index + 1 < len(plan) else None
        if next_plan is None:
            return jsonify(
                {
                    "transcript": transcript,
                    "finished": True,
                    "turns": updated_history,
                }
            )
        next_question = generate_next_speaking_question(
            displayed_question, next_plan, updated_history
        )
        return jsonify(
            {
                "transcript": transcript,
                "finished": False,
                "turns": updated_history,
                "next": {
                    **next_plan,
                    "question": next_question["question"],
                    "examiner_note": next_question["examiner_note"],
                },
            }
        )
    except (AIServiceError, ValueError, json.JSONDecodeError) as error:
        return jsonify({"error": str(error)}), 503 if isinstance(error, AIServiceError) else 400


@ai_bp.route("/speaking/<int:mock_id>/complete", methods=("POST",))
@login_required
def complete_speaking(mock_id):
    mock = _load_ai_mock(mock_id, "speaking")
    if not _check_access("speaking"):
        return jsonify({"error": "This Speaking mock is no longer available for your plan."}), 403
    try:
        payload = request.get_json(silent=True) or {}
        turns = payload.get("turns", [])
        if not isinstance(turns, list) or not turns or len(turns) > 20:
            return jsonify({"error": "Please complete the Speaking answers first."}), 400
        feedback = evaluate_speaking(turns)
        band_score = float(feedback["overall_band"])
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO ai_attempts
                (user_id, ai_mock_id, submission_text, transcript, feedback_json, band_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                mock_id,
                json.dumps(turns, ensure_ascii=False),
                "\n\n".join(
                    f"Part {turn['part']}: {turn['transcript']}" for turn in turns
                ),
                json.dumps(feedback, ensure_ascii=False),
                band_score,
            ),
        )
        db.commit()
        return jsonify({"redirect": url_for("ai.result", attempt_id=cursor.lastrowid)})
    except AIServiceError as error:
        return jsonify({"error": str(error)}), 503
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": f"The Speaking answers could not be saved: {error}"}), 400


@ai_bp.route("/writing/<int:mock_id>", methods=("GET", "POST"))
@login_required
def writing(mock_id):
    mock = _load_ai_mock(mock_id, "writing")
    if not _check_access("writing"):
        return redirect(url_for("ai.index"))
    essay = request.form.get("essay", "") if request.method == "POST" else ""
    word_count = len(essay.split())
    if request.method == "POST":
        if word_count < 50:
            flash("Please write at least 50 words before asking the AI checker to review your essay.", "error")
        else:
            try:
                feedback = evaluate_writing(mock["task"]["prompt"], essay, word_count)
                db = get_db()
                cursor = db.execute(
                    """
                    INSERT INTO ai_attempts
                        (user_id, ai_mock_id, submission_text, feedback_json, band_score)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        current_user.id,
                        mock_id,
                        essay,
                        json.dumps(feedback, ensure_ascii=False),
                        float(feedback["overall_band"]),
                    ),
                )
                db.commit()
                return redirect(url_for("ai.result", attempt_id=cursor.lastrowid))
            except AIServiceError as error:
                flash(str(error), "error")
    return render_template(
        "ai/writing.html",
        mock=mock,
        essay=essay,
        word_count=word_count,
        attempt_count=_attempt_count("writing"),
        limit=_limit("writing"),
    )


@ai_bp.route("/results/<int:attempt_id>")
@login_required
def result(attempt_id):
    row = get_db().execute(
        """
        SELECT a.*, m.title, m.skill, m.task_json
        FROM ai_attempts AS a
        JOIN ai_mocks AS m ON m.id = a.ai_mock_id
        WHERE a.id = ? AND a.user_id = ?
        """,
        (attempt_id, current_user.id),
    ).fetchone()
    if row is None:
        abort(404)
    result_data = dict(row)
    result_data["feedback"] = json.loads(result_data.pop("feedback_json"))
    result_data["turns"] = json.loads(result_data["submission_text"]) if row["skill"] == "speaking" else []
    return render_template("ai/result.html", result=result_data)
