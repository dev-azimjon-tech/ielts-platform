from flask import Blueprint, redirect, render_template, url_for
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


def _average_band(bands):
    return round(sum(bands) / len(bands), 1) if bands else 0.0


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


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

    for skill in free_limits:
        is_ai_skill = skill in {"speaking", "writing"}
        if is_ai_skill:
            rows = db.execute(
                """
                SELECT band_score
                FROM ai_attempts AS a
                JOIN ai_mocks AS m ON m.id = a.ai_mock_id
                WHERE a.user_id = ? AND m.skill = ?
                """,
                (current_user.id, skill),
            ).fetchall()
            practice_url = url_for("ai.index")
            bands = [round(float(row["band_score"]), 1) for row in rows]
        else:
            rows = db.execute(
                """
                SELECT score, total_points
                FROM attempts AS a
                JOIN mock_tests AS m ON m.id = a.mock_id
                WHERE a.user_id = ? AND m.skill = ?
                """,
                (current_user.id, skill),
            ).fetchall()
            practice_url = url_for("mocks.index")
            bands = [
                _estimated_band(row["score"], row["total_points"], skill)
                for row in rows
            ]

        completed = len(bands)
        average_band = _average_band(bands)
        limit = premium_limits[skill] if current_user.is_premium else free_limits[skill]
        skill_stats.append(
            {
                "key": skill,
                "name": skill_names[skill],
                "icon": skill_icons[skill],
                "limit": limit,
                "completed": completed,
                "remaining": max(limit - completed, 0),
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

    regular_attempts = db.execute(
        """
        SELECT a.score, a.total_points, m.skill
        FROM attempts AS a
        JOIN mock_tests AS m ON m.id = a.mock_id
        WHERE a.user_id = ?
        """,
        (current_user.id,),
    ).fetchall()
    ai_attempts = db.execute(
        """
        SELECT a.band_score, m.skill
        FROM ai_attempts
        AS a JOIN ai_mocks AS m ON m.id = a.ai_mock_id
        WHERE a.user_id = ?
        """,
        (current_user.id,),
    ).fetchall()
    all_bands = [
        _estimated_band(row["score"], row["total_points"], row["skill"])
        for row in regular_attempts
    ] + [round(float(row["band_score"]), 1) for row in ai_attempts]

    return render_template(
        "dashboard.html",
        skill_stats=skill_stats,
        recent_attempts=recent_attempts,
        completed_mocks=completed_mocks,
        overall_average_band=_average_band(all_bands),
        free_remaining=sum(
            max(free_limits[stat["key"]] - stat["completed"], 0)
            for stat in skill_stats
        ),
    )
