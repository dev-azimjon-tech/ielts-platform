import json

from flask import Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..database import get_db


main_bp = Blueprint("main", __name__)


# These are the standard practice-score boundaries used to estimate IELTS
# bands from a 40-question Listening or Academic Reading mock.
LISTENING_BAND_BOUNDARIES = (
    (39, 9.0),
    (37, 8.5),
    (35, 8.0),
    (32, 7.5),
    (30, 7.0),
    (27, 6.5),
    (23, 6.0),
    (18, 5.5),
    (16, 5.0),
    (13, 4.5),
    (10, 4.0),
    (8, 3.5),
    (6, 3.0),
    (4, 2.5),
    (2, 2.0),
    (1, 1.0),
)

READING_BAND_BOUNDARIES = (
    (39, 9.0),
    (37, 8.5),
    (35, 8.0),
    (33, 7.5),
    (30, 7.0),
    (27, 6.5),
    (23, 6.0),
    (19, 5.5),
    (15, 5.0),
    (13, 4.5),
    (10, 4.0),
    (8, 3.5),
    (6, 3.0),
    (4, 2.5),
    (2, 2.0),
    (1, 1.0),
)


def _estimated_band(score, total_points, skill):
    """Convert a mock mark into an estimated IELTS band score."""
    if not total_points:
        return 0.0

    # Scale shorter admin-created practice tests to the IELTS 40-mark scale.
    mark = round(float(score) / float(total_points) * 40)
    boundaries = (
        READING_BAND_BOUNDARIES
        if skill == "reading"
        else LISTENING_BAND_BOUNDARIES
    )
    for minimum_mark, band in boundaries:
        if mark >= minimum_mark:
            return band
    return 0.0


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/guide")
def guide():
    from ..platform_guide import GUIDE_CHAPTERS

    with current_app.open_resource("static/media/platform-guide.json") as manifest_file:
        manifest = json.load(manifest_file)
    timings = {chapter["id"]: chapter for chapter in manifest["chapters"]}
    chapters = [{**chapter, "start": timings[chapter["id"]]["start"]} for chapter in GUIDE_CHAPTERS]
    seconds = round(manifest["duration"])
    return render_template("guide.html", chapters=chapters, duration=f"{seconds // 60}:{seconds % 60:02d}")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    free_limits = {"reading": 10, "listening": 10, "speaking": 2, "writing": 2}
    premium_limits = {"reading": 10, "listening": 10, "speaking": 10, "writing": 10}
    skill_names = {
        "reading": "Reading",
        "listening": "Listening",
        "speaking": "Speaking",
        "writing": "Writing",
    }
    skill_icons = {"reading": "R", "listening": "L", "speaking": "S", "writing": "W"}
    skill_stats = []
    # Aggregate equal marks in SQLite so the dashboard does not load the
    # student's full answer history or rescan it for every skill.
    summaries = db.execute(
        """
        SELECT m.skill, a.score, a.total_points, COUNT(*) AS completed
        FROM attempts AS a JOIN mock_tests AS m ON m.id = a.mock_id
        WHERE a.user_id = ? GROUP BY m.skill, a.score, a.total_points
        UNION ALL
        SELECT m.skill, a.band_score AS score, 9 AS total_points, COUNT(*) AS completed
        FROM ai_attempts AS a JOIN ai_mocks AS m ON m.id = a.ai_mock_id
        WHERE a.user_id = ? GROUP BY m.skill, a.band_score
        """,
        (current_user.id, current_user.id),
    ).fetchall()
    skill_totals = {skill: {"completed": 0, "band_total": 0.0} for skill in free_limits}
    for row in summaries:
        band = (
            float(row["score"]) if row["skill"] in {"speaking", "writing"}
            else _estimated_band(row["score"], row["total_points"], row["skill"])
        )
        totals = skill_totals[row["skill"]]
        totals["completed"] += row["completed"]
        totals["band_total"] += band * row["completed"]

    revisions = db.execute("SELECT COUNT(*) FROM writing_revisions r JOIN ai_attempts a ON a.id=r.attempt_id WHERE a.user_id=?", (current_user.id,)).fetchone()[0]
    for skill in free_limits:
        is_ai_skill = skill in {"speaking", "writing"}
        practice_url = url_for("ai.index") if is_ai_skill else url_for("mocks.index", skill=skill)
        totals = skill_totals[skill]
        completed = totals["completed"]
        average_band = round(totals["band_total"] / completed, 1) if completed else 0.0
        limit = premium_limits[skill] if current_user.is_premium else free_limits[skill]
        skill_stats.append(
            {
                "key": skill,
                "name": skill_names[skill],
                "icon": skill_icons[skill],
                "limit": limit,
                "completed": completed,
                "remaining": max(limit - completed - (revisions if skill == "writing" else 0), 0),
                "average_band": average_band,
                "band_percent": round(average_band / 9 * 100),
                "practice_url": practice_url,
                "available": True,
                "unlimited": current_user.is_premium and not is_ai_skill,
            }
        )

    recent_attempts = db.execute(
        """
        SELECT a.score, a.total_points, a.completed_at, m.title, m.skill
        FROM attempts AS a
        JOIN mock_tests AS m ON m.id = a.mock_id
        WHERE a.user_id = ?
        UNION ALL
        SELECT a.band_score AS score, 9 AS total_points, a.completed_at, m.title, m.skill
        FROM ai_attempts AS a
        JOIN ai_mocks AS m ON m.id = a.ai_mock_id
        WHERE a.user_id = ?
        ORDER BY completed_at DESC
        LIMIT 6
        """,
        (current_user.id, current_user.id),
    ).fetchall()
    recent_attempts = [
        {
            **dict(attempt),
            "band_score": round(
                float(attempt["score"])
                if attempt["skill"] in {"speaking", "writing"}
                else _estimated_band(
                    attempt["score"], attempt["total_points"], attempt["skill"]
                ),
                1,
            ),
        }
        for attempt in recent_attempts
    ]
    completed_mocks = sum(stat["completed"] for stat in skill_stats)

    band_total = sum(totals["band_total"] for totals in skill_totals.values())

    return render_template(
        "dashboard.html",
        skill_stats=skill_stats,
        recent_attempts=recent_attempts,
        completed_mocks=completed_mocks,
        overall_average_band=round(band_total / completed_mocks, 1) if completed_mocks else 0.0,
        free_remaining=sum(
            max(free_limits[stat["key"]] - stat["completed"] - (revisions if stat["key"] == "writing" else 0), 0)
            for stat in skill_stats
        ),
    )
