"""Shared scheduling and progress for private vocabulary reviews."""
from datetime import date, timedelta

from .database import get_db


def review_intervals(interval_days):
    """Return the same next intervals for button previews and saved ratings."""
    previous = max(0, interval_days or 0)
    return {
        "again": 0,
        "good": min(365, max(1, previous * 2)),
        "easy": min(365, max(4, previous * 3)),
    }


def review_summary(user_id, today=None):
    today = (today or date.today()).isoformat()
    row = get_db().execute(
        """SELECT COUNT(*) AS total,
            COALESCE(SUM(s.word_id IS NULL), 0) AS new,
            COALESCE(SUM(s.word_id IS NULL OR s.due_on <= :today), 0) AS due,
            COALESCE(SUM(s.due_on > :today), 0) AS scheduled,
            COALESCE(SUM(s.reviewed_on = :today), 0) AS reviewed_today,
            MIN(CASE WHEN s.due_on > :today THEN s.due_on END) AS next_due
        FROM vocabulary_words w
        LEFT JOIN vocabulary_schedule s ON s.word_id = w.id
        WHERE w.user_id = :user_id""",
        {"user_id": user_id, "today": today},
    ).fetchone()
    return dict(row)


def rating_options(interval_days, today=None):
    today = today or date.today()
    return [
        {
            "rating": rating,
            "days": days,
            "label": "Today" if not days else "Tomorrow" if days == 1 else f"In {days} days",
            "due_on": (today + timedelta(days=days)).isoformat(),
        }
        for rating, days in review_intervals(interval_days).items()
    ]


def record_rating(user_id, word_id, rating, today=None):
    """Schedule a due card once, even when two tabs submit ratings together.

    The read and update share a SQLite write transaction. A tab that arrives
    after another tab schedules the card cannot move it back to today.
    """
    if rating not in ('again', 'good', 'easy'):
        raise ValueError('Unknown vocabulary rating.')
    today = today or date.today()
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    try:
        word = db.execute('''SELECT w.id,s.interval_days,s.due_on FROM vocabulary_words w
            LEFT JOIN vocabulary_schedule s ON s.word_id=w.id
            WHERE w.id=? AND w.user_id=?''', (word_id,user_id)).fetchone()
        if word is None:
            db.rollback()
            return None
        if word['due_on'] and word['due_on'] > today.isoformat():
            db.commit()
            return {'status': 'already_scheduled', 'due_on': word['due_on']}
        interval = review_intervals(word['interval_days'])[rating]
        due_on = (today + timedelta(days=interval)).isoformat()
        db.execute('''INSERT INTO vocabulary_schedule(word_id,due_on,interval_days,reviewed_on)
            VALUES(?,?,?,?) ON CONFLICT(word_id) DO UPDATE SET due_on=excluded.due_on,
                interval_days=excluded.interval_days,reviewed_on=excluded.reviewed_on''',
            (word_id,due_on,interval,today.isoformat()))
        db.commit()
        return {'status': 'scheduled', 'due_on': due_on, 'interval_days': interval}
    except Exception:
        db.rollback()
        raise
