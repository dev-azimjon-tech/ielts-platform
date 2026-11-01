"""Private Writing drafts, revision comparisons, and recoverable AI checks."""
import json
import math
import re
import secrets
from difflib import SequenceMatcher

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from .database import get_db

MAX_ESSAY_LENGTH = 50000
CRITERIA = (
    ('task_response_band', 'Task response'),
    ('coherence_band', 'Coherence and cohesion'),
    ('lexical_band', 'Vocabulary'),
    ('grammar_band', 'Grammar'),
)


def original_attempt(attempt_id):
    row = get_db().execute('''SELECT a.*,m.task_json,m.title FROM ai_attempts a
        JOIN ai_mocks m ON m.id=a.ai_mock_id
        WHERE a.id=? AND a.user_id=? AND m.skill='writing' ''',
        (attempt_id, current_user.id)).fetchone()
    if row is None:
        abort(404)
    return dict(row)


def versions(original):
    items = [dict(key='original', label='Original', essay=original['submission_text'],
                  band=original['band_score'], feedback=json.loads(original['feedback_json']),
                  created_at=original['completed_at'], id=None)]
    for number,row in enumerate(get_db().execute(
            'SELECT * FROM writing_revisions WHERE attempt_id=? ORDER BY id', (original['id'],)), 1):
        items.append(dict(key=str(row['id']), label=f'Revision {number}', essay=row['essay'],
                          band=row['band_score'], feedback=json.loads(row['feedback_json']),
                          created_at=row['created_at'], id=row['id']))
    return items


def get_draft(original, latest):
    db = get_db()
    db.execute('''INSERT OR IGNORE INTO writing_revision_drafts(attempt_id,essay,base_revision_id)
        VALUES(?,?,?)''', (original['id'], latest['essay'], latest['id']))
    db.commit()
    return db.execute('SELECT * FROM writing_revision_drafts WHERE attempt_id=?',
                      (original['id'],)).fetchone()


def save_draft(attempt_id, essay, expected_version):
    db = get_db()
    cursor = db.execute('''UPDATE writing_revision_drafts SET essay=?,version=version+1,saved_at=CURRENT_TIMESTAMP
        WHERE attempt_id=? AND version=?''', (essay, attempt_id, expected_version))
    db.commit()
    return expected_version + 1 if cursor.rowcount else None


def numeric_band(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 9 and math.isfinite(value):
        return float(value)
    return None


def compare_criteria(before, after):
    rows = []
    for key,label in CRITERIA:
        old, new = numeric_band(before.get(key)), numeric_band(after.get(key))
        rows.append({'label': label, 'before': old, 'after': new,
                     'change': round(new-old, 1) if old is not None and new is not None else None})
    return rows


def essay_changes(before, after):
    # A token includes its following whitespace so paragraph breaks survive rendering.
    old = re.findall(r'\S+\s*|\s+', before)
    new = re.findall(r'\S+\s*|\s+', after)
    if before == after:
        return {'before': [{'kind': 'same', 'text': before}], 'after': [{'kind': 'same', 'text': after}],
                'added': 0, 'removed': 0, 'available': True}
    if len(old) > 2000 or len(new) > 2000:
        return {'before': [{'kind': 'same', 'text': before}], 'after': [{'kind': 'same', 'text': after}],
                'available': False}
    left, right = [], []
    added = removed = 0
    for tag,i,j,k,l in SequenceMatcher(None, old, new, autojunk=True).get_opcodes():
        if i != j:
            text = ''.join(old[i:j])
            left.append({'kind': 'same' if tag == 'equal' else 'removed', 'text': text})
            if tag != 'equal':
                removed += len(text.split())
        if k != l:
            text = ''.join(new[k:l])
            right.append({'kind': 'same' if tag == 'equal' else 'added', 'text': text})
            if tag != 'equal':
                added += len(text.split())
    return {'before': left, 'after': right, 'added': added, 'removed': removed, 'available': True}


def replay_revision(token, attempt_id):
    row = get_db().execute('''SELECT r.id,r.attempt_id FROM writing_revision_submissions s
        JOIN writing_revisions r ON r.id=s.revision_id WHERE s.token=?''', (token,)).fetchone()
    if row and row['attempt_id'] != attempt_id:
        abort(400)
    return row['id'] if row else None


def revision_page(attempt_id):
    from .ai import _attempt_count, _limit
    from .ai_service import AIServiceError, evaluate_writing

    original = original_attempt(attempt_id)
    items = versions(original)
    latest = items[-1]
    draft = get_draft(original, latest)
    essay = draft['essay']
    token = request.form.get('submission_token') or secrets.token_urlsafe(24)
    if not 20 <= len(token) <= 128 or not re.fullmatch(r'[A-Za-z0-9_-]+', token):
        abort(400)
    status = 200
    if request.method == 'POST':
        action = request.form.get('action', 'check')
        if action not in ('check', 'save'):
            abort(400)
        replay = replay_revision(token, attempt_id)
        if action == 'check' and replay is not None:
            return redirect(url_for('learning.revise', attempt_id=attempt_id, revision=replay))
        essay = request.form.get('essay', '')
        if len(essay) > MAX_ESSAY_LENGTH:
            flash('Keep your essay below 50,000 characters. Your saved draft is unchanged.', 'error')
            status = 400
        else:
            try:
                expected = int(request.form.get('draft_version', draft['version']))
            except (ValueError, TypeError):
                abort(400)
            saved_version = save_draft(attempt_id, essay, expected)
            if saved_version is None:
                flash('Another tab saved a newer draft. Your text is still in the editor below. Copy it before reloading to choose which version to keep.', 'error')
                status = 409
            elif action == 'save':
                flash('Draft saved. No AI check was used.', 'success')
                return redirect(url_for('learning.revise', attempt_id=attempt_id))
            elif len(essay.split()) < 50:
                flash('Draft saved. Write at least 50 words before checking your revision.', 'error')
                status = 400
            elif _attempt_count('writing') >= _limit('writing'):
                flash('Draft saved. Your Writing AI check allowance has been used.', 'info')
            else:
                try:
                    feedback = evaluate_writing(json.loads(original['task_json'])['prompt'], essay, len(essay.split()))
                    band = numeric_band(feedback.get('overall_band')) if isinstance(feedback,dict) else None
                    if band is None:
                        raise AIServiceError('The checker returned an invalid band. Your draft is saved; try again.')
                    db = get_db()
                    db.execute('BEGIN IMMEDIATE')
                    # Recheck both replay identity and the shared allowance under the write lock.
                    replay = replay_revision(token, attempt_id)
                    if replay is not None:
                        db.commit()
                        return redirect(url_for('learning.revise', attempt_id=attempt_id, revision=replay))
                    if _attempt_count('writing') >= _limit('writing'):
                        db.rollback()
                        flash('Draft saved. Your last Writing AI check was used in another session.', 'info')
                    else:
                        cursor = db.execute('''INSERT INTO writing_revisions(attempt_id,essay,feedback_json,band_score)
                            VALUES(?,?,?,?)''', (attempt_id, essay, json.dumps(feedback), band))
                        revision_id = cursor.lastrowid
                        db.execute('INSERT INTO writing_revision_submissions VALUES(?,?)', (token, revision_id))
                        # A newer draft from another tab must survive the AI result returning.
                        db.execute('''UPDATE writing_revision_drafts SET base_revision_id=?,version=version+1
                            WHERE attempt_id=? AND version=?''', (revision_id, attempt_id, saved_version))
                        db.commit()
                        flash('Revision checked. Compare the feedback and changes below.', 'success')
                        return redirect(url_for('learning.revise', attempt_id=attempt_id, revision=revision_id))
                except AIServiceError as error:
                    flash(f'{error} Your draft is saved. No AI check was used.', 'error')
        draft = get_draft(original, latest)
    selected_key = request.args.get('revision', latest['key'])
    baseline_key = request.args.get('baseline', 'original')
    selected = next((v for v in items if v['key'] == selected_key), None)
    baseline = next((v for v in items if v['key'] == baseline_key), None)
    if selected is None or baseline is None:
        abort(404)
    remaining = max(0, _limit('writing') - _attempt_count('writing'))
    changes = essay_changes(baseline['essay'], selected['essay'])
    return render_template('learning/revise.html', original=original, task=json.loads(original['task_json']),
                           items=items, selected=selected, baseline=baseline, latest=latest,
                           essay=essay, draft=draft, conflict=status == 409, editor_version=expected if status == 409 else draft['version'], submission_token=token,
                           criteria=compare_criteria(baseline['feedback'], selected['feedback']), changes=changes,
                           band_change=round(selected['band']-baseline['band'], 1), remaining=remaining,
                           word_count=len(essay.split())), status


def draft_api(attempt_id):
    original = original_attempt(attempt_id)
    get_draft(original, versions(original)[-1])
    payload = request.get_json(silent=True)
    if (not isinstance(payload, dict) or not isinstance(payload.get('essay'), str)
            or len(payload['essay']) > MAX_ESSAY_LENGTH or type(payload.get('version')) is not int
            or payload['version'] < 0):
        abort(400)
    version = save_draft(attempt_id, payload['essay'], payload['version'])
    if version is None:
        return jsonify(error='Another tab saved a newer draft. Copy your current text before reloading.'), 409
    response = jsonify(version=version)
    response.headers['Cache-Control'] = 'private, no-store'
    return response
