"""Persisted exam section clocks, drafts, and result transitions."""
import json
import math
from datetime import datetime, timedelta, timezone

from flask import abort, g, request, url_for
from flask_login import current_user

from .database import get_db

SKILLS = ('listening', 'reading', 'writing', 'speaking')


def now():
    return datetime.now(timezone.utc)


def active_exam():
    return get_db().execute('SELECT * FROM exam_sessions WHERE user_id=? AND completed_at IS NULL ORDER BY id DESC LIMIT 1',
                            (current_user.id,)).fetchone()


def exam_section(kind, mock_id):
    exam = active_exam()
    if not exam or exam['stage'] >= 4:
        return None
    item = json.loads(exam['mocks_json'])[exam['stage']]
    return exam if item['kind'] == kind and item['id'] == mock_id else None


def section_state(exam, start=False):
    db = get_db()
    state = db.execute('SELECT * FROM exam_section_state WHERE session_id=? AND stage=?',
                       (exam['id'], exam['stage'])).fetchone()
    if state is None:
        # Existing sessions retain their original clock on migration.
        db.execute('INSERT OR IGNORE INTO exam_section_state(session_id,stage,started_at) VALUES(?,?,?)',
                   (exam['id'], exam['stage'], exam['stage_started_at']))
    if start:
        db.execute('UPDATE exam_section_state SET started_at=CURRENT_TIMESTAMP WHERE session_id=? AND stage=? AND started_at IS NULL',
                   (exam['id'], exam['stage']))
    db.commit()
    return db.execute('SELECT * FROM exam_section_state WHERE session_id=? AND stage=?',
                      (exam['id'], exam['stage'])).fetchone()


def deadline(exam, state):
    if not state['started_at']:
        return None
    item = json.loads(exam['mocks_json'])[exam['stage']]
    return datetime.strptime(state['started_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc) + timedelta(minutes=item['minutes'])


def exam_expired(kind, mock_id):
    exam = exam_section(kind, mock_id)
    if not exam:
        return False
    end = deadline(exam, section_state(exam))
    return end is not None and now() >= end


def submission_redirect(kind, mock_id):
    """Recognize a replay from a rendered section before spending an allowance."""
    payload = request.get_json(silent=True) if request.is_json else request.form
    payload = payload or {}
    if not isinstance(payload, dict) and request.is_json:
        abort(400, 'Send a JSON object for this request.')
    session_id = payload.get('_exam_session')
    if session_id is None:
        return None
    try:
        session_id, stage = int(session_id), int(payload.get('_exam_stage'))
    except (TypeError, ValueError):
        abort(400)
    exam = get_db().execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?',
                            (session_id, current_user.id)).fetchone()
    if not exam or not 0 <= stage < 4:
        abort(404)
    item = json.loads(exam['mocks_json'])[stage]
    if item['kind'] != kind or item['id'] != mock_id:
        abort(400)
    if exam['completed_at'] or exam['stage'] != stage:
        return url_for('learning.exam_continue') if not exam['completed_at'] else url_for('learning.exam_report', session_id=exam['id'])
    return None


def complete_exam_section(kind, mock_id, attempt_id, band, status='scored'):
    # Caller holds its SQLite write transaction when saving an attempt.
    exam = exam_section(kind, mock_id)
    if not exam:
        return False
    state = get_db().execute('SELECT * FROM exam_section_state WHERE session_id=? AND stage=?',
                             (exam['id'],exam['stage'])).fetchone()
    end = deadline(exam,state) if state else None
    overtime = bool(end and (getattr(g, 'exam_submitted_at', None) or now()) > end)
    results = json.loads(exam['results_json'])
    results.append({'kind': kind, 'id': attempt_id, 'skill': SKILLS[exam['stage']], 'band': band,
                    'status': status, 'overtime': overtime, 'completed_at': now().isoformat()})
    cursor = get_db().execute('''UPDATE exam_sessions SET results_json=?,stage=stage+1,stage_started_at=CURRENT_TIMESTAMP,
        completed_at=CASE WHEN stage=3 THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=? AND stage=? AND completed_at IS NULL''',
        (json.dumps(results), exam['id'], exam['stage']))
    if cursor.rowcount and exam['stage'] < 3:
        get_db().execute('INSERT OR IGNORE INTO exam_section_state(session_id,stage) VALUES(?,?)',
                         (exam['id'], exam['stage'] + 1))
    get_db().commit()
    return bool(cursor.rowcount)


def report(exam):
    stored = json.loads(exam['results_json'])
    results = []
    for record in stored if isinstance(stored,list) else []:
        item = dict(record) if isinstance(record,dict) else {'status':'unavailable'}
        value = item.get('band')
        valid = isinstance(value,(int,float)) and not isinstance(value,bool) and 0 <= value <= 9 and math.isfinite(value)
        item['band'] = value if valid else None
        results.append(item)
    scored = [r for r in results if r.get('band') is not None]
    complete = len(results) == 4
    average = sum(r['band'] for r in scored) / 4 if len(scored) == 4 else None
    return {**dict(exam), 'results': results, 'sections': json.loads(exam['mocks_json']),
            'complete': complete, 'scored_count': len(scored), 'overtime': any(r.get('overtime') for r in results),
            'overall': math.floor(average * 2 + .5) / 2 if average is not None else None}


def save_submission_draft(kind, mock_id, draft):
    """Save submitted content without overwriting newer work from another tab."""
    exam = exam_section(kind, mock_id)
    if not exam:
        return None
    g.exam_submitted_at = now()
    section_state(exam, start=True)
    payload = request.get_json(silent=True) if request.is_json else request.form
    supplied = (payload or {}).get('_exam_revision')
    try:
        expected = int(supplied) if supplied is not None else None
        if expected is not None and (expected < 0 or isinstance(supplied, bool)):
            raise ValueError()
    except (TypeError, ValueError):
        abort(400, 'Invalid exam draft version.')
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    state = db.execute('SELECT revision FROM exam_section_state WHERE session_id=? AND stage=?',
                       (exam['id'], exam['stage'])).fetchone()
    expected = state['revision'] if expected is None else expected
    cursor = db.execute('''UPDATE exam_section_state SET draft_json=?,revision=revision+1,saved_at=CURRENT_TIMESTAMP
        WHERE session_id=? AND stage=? AND revision=? AND EXISTS
        (SELECT 1 FROM exam_sessions e WHERE e.id=exam_section_state.session_id
          AND e.user_id=? AND e.stage=exam_section_state.stage AND e.completed_at IS NULL)''',
        (json.dumps(draft), exam['id'], exam['stage'], expected, current_user.id))
    db.commit()
    if cursor.rowcount:
        g.exam_saved_revision = expected + 1
    return bool(cursor.rowcount)
