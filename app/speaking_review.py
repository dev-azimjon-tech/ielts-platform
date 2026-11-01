"""Private Speaking history and metadata for saved answer playback."""
import json
import math

from flask import abort, flash, redirect, render_template, request, url_for, make_response
from flask_login import current_user

from .database import get_db

AUDIO_EXTENSIONS = {'audio/webm': 'webm', 'audio/ogg': 'ogg', 'audio/mp4': 'm4a',
                    'audio/wav': 'wav', 'audio/x-wav': 'wav'}


def format_size(size):
    return f'{size / (1024 * 1024):.1f} MB' if size >= 1024 * 1024 else f'{max(1, math.ceil(size / 1024))} KB' if size else '0 KB'


def answer_review(attempt):
    """A client-provided recording reference is usable only on its owning result."""
    records = {row['id']: dict(row) for row in get_db().execute(
        '''SELECT id,mime_type,length(audio) AS bytes FROM speaking_recordings
        WHERE user_id=? AND attempt_id=?''', (current_user.id, attempt['id']))}
    try:
        raw_turns = json.loads(attempt['submission_text'])
    except (ValueError, TypeError):
        raw_turns = []
    turns, seen, parts = [], set(), []
    for number,raw in enumerate(raw_turns if isinstance(raw_turns, list) else [], 1):
        if not isinstance(raw, dict):
            continue
        part = raw.get('part')
        part = part if type(part) is int and 1 <= part <= 3 else 'Practice'
        if part not in parts:
            parts.append(part)
        transcript = raw.get('transcript', '')
        transcript = transcript if isinstance(transcript, str) else ''
        recording_id = raw.get('recording_id')
        recording = records.get(recording_id) if isinstance(recording_id, str) and recording_id not in seen else None
        if recording:
            seen.add(recording_id)
        turns.append({'number': number, 'part': part, 'question': raw.get('question', ''),
                      'transcript': transcript, 'word_count': len(transcript.split()),
                      'recording': recording, 'had_recording': bool(recording_id)})
    neighbours = {}
    for name, operator, direction in [('older', '<', 'DESC'), ('newer', '>', 'ASC')]:
        row = get_db().execute(f'''SELECT a.id FROM ai_attempts a JOIN ai_mocks m ON m.id=a.ai_mock_id
            WHERE a.user_id=? AND m.skill='speaking' AND
            (a.completed_at {operator} ? OR (a.completed_at=? AND a.id {operator} ?))
            ORDER BY a.completed_at {direction},a.id {direction} LIMIT 1''',
            (current_user.id, attempt['completed_at'], attempt['completed_at'], attempt['id'])).fetchone()
        neighbours[name] = row['id'] if row else None
    return {'turns': turns, 'parts': parts, 'audio_count': len(seen),
            'storage': format_size(sum(records[rid]['bytes'] for rid in seen)), 'neighbours': neighbours}


def history_page():
    search = request.args.get('q', '').strip()[:150]
    availability = request.args.get('audio', 'all')
    if availability not in ('all', 'with', 'without'):
        availability = 'all'
    pattern = '%' + search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    source = '''FROM ai_attempts a JOIN ai_mocks m ON m.id=a.ai_mock_id
        LEFT JOIN (SELECT attempt_id,COUNT(*) AS audio_count,SUM(length(audio)) AS bytes
          FROM speaking_recordings WHERE user_id=? AND attempt_id IS NOT NULL GROUP BY attempt_id) r ON r.attempt_id=a.id
        WHERE a.user_id=? AND m.skill='speaking'
          AND (m.title LIKE ? ESCAPE '\\' OR a.transcript LIKE ? ESCAPE '\\')'''
    args = [current_user.id, current_user.id, pattern, pattern]
    if availability == 'with':
        source += ' AND COALESCE(r.audio_count,0)>0'
    elif availability == 'without':
        source += ' AND COALESCE(r.audio_count,0)=0'
    db = get_db()
    total = db.execute('SELECT COUNT(*) ' + source, args).fetchone()[0]
    pages = max(1, math.ceil(total / 12))
    page = min(max(1, request.args.get('page', 1, type=int) or 1), pages)
    rows = db.execute('''SELECT a.id,a.completed_at,a.band_score,m.title,COALESCE(r.audio_count,0) AS audio_count,
        COALESCE(r.bytes,0) AS bytes ''' + source + ' ORDER BY a.completed_at DESC,a.id DESC LIMIT 12 OFFSET ?',
        [*args, (page-1)*12]).fetchall()
    response = make_response(render_template('learning/speaking.html', attempts=[{**dict(r), 'storage': format_size(r['bytes'])} for r in rows],
                           search=search, availability=availability, total=total, page=page, pages=pages))
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def delete_recording(recording_id):
    attempt_id = request.form.get('attempt_id', type=int)
    db = get_db()
    recording = db.execute('''SELECT r.id FROM speaking_recordings r JOIN ai_attempts a ON a.id=r.attempt_id
        JOIN ai_mocks m ON m.id=a.ai_mock_id WHERE r.id=? AND r.user_id=? AND a.user_id=?
        AND r.attempt_id=? AND m.skill='speaking' ''',
        (recording_id, current_user.id, current_user.id, attempt_id)).fetchone()
    if recording is None:
        abort(404)
    db.execute('DELETE FROM speaking_recordings WHERE id=? AND user_id=?', (recording_id, current_user.id))
    db.commit()
    flash('Recording deleted. Your transcript, scores, and feedback are still saved.', 'success')
    return redirect(url_for('ai.result', attempt_id=attempt_id) + '#speaking-answers')
