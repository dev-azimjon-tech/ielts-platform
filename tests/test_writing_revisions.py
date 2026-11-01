"""Writing revisions keep drafts private, preserve edits, and consume checks once."""
import json

import pytest
from flask import template_rendered

from app.ai_service import AIServiceError
from app.database import get_db
from app.models import User
from app.seed import seed_demo_content
from app.writing_revisions import essay_changes


ORIGINAL = 'Students benefit from regular practice. ' * 12
EDITED = 'Students benefit from thoughtful practice with detailed feedback. ' * 12
FEEDBACK = dict(overall_band=7, task_response_band=7, coherence_band=7.5,
                lexical_band=6.5, grammar_band=7, feedback='Your examples are clearer.',
                strengths=['Relevant examples'], improvements=['Vary sentence structure'])


@pytest.fixture()
def writing(app, client):
    with app.app_context():
        seed_demo_content()
        first = User.create('Writer', 'writer@example.com', 'unused').id
        other = User.create('Other writer', 'other-writer@example.com', 'unused').id
        db = get_db()
        mock_id = db.execute("SELECT id FROM ai_mocks WHERE skill='writing' LIMIT 1").fetchone()[0]
        attempt = db.execute('''INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score)
            VALUES(?,?,?,?,6)''', (first, mock_id, ORIGINAL, json.dumps({**FEEDBACK,'overall_band':6,'grammar_band':5}))).lastrowid
        db.commit()
    with client.session_transaction() as session:
        session['_user_id'] = str(first)
        session['_fresh'] = True
    client.get(f'/learn/writing/{attempt}/revise')
    with client.session_transaction() as session:
        token = session['learning_csrf']
    return dict(user=first, other=other, mock=mock_id, attempt=attempt, csrf=token,
                path=f'/learn/writing/{attempt}/revise', api=f'/learn/writing/{attempt}/draft')


def post(client, writing, **data):
    return client.post(writing['path'], data={'csrf_token':writing['csrf'],**data})


def save(client, writing, text, version):
    return client.post(writing['api'], json={'essay':text,'version':version},
                       headers={'X-CSRF-Token':writing['csrf']})


def context(app, client, path):
    contexts = []
    def capture(sender, template, context, **extra):
        contexts.append(context)
    with template_rendered.connected_to(capture, app):
        response = client.get(path)
    assert response.status_code == 200
    return response, contexts[-1]


def test_draft_save_is_free_private_and_restores_even_empty_essay(app, client, writing):
    response = save(client, writing, 'Unfinished thoughts', 0)
    assert response.json['version'] == 1
    _, data = context(app, client, writing['path'])
    assert data['essay'] == 'Unfinished thoughts' and data['remaining'] == 1
    assert save(client, writing, '', 1).status_code == 200
    _, data = context(app, client, writing['path'])
    assert data['essay'] == ''
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM writing_revisions').fetchone()[0] == 0
    assert client.post(writing['api'], json={'essay':'no csrf','version':2}).status_code == 400
    with client.session_transaction() as session:
        session['_user_id'] = str(writing['other'])
    assert client.get(writing['path']).status_code == 404
    assert save(client, writing, 'Forbidden', 2).status_code == 404


def test_conflicting_tab_does_not_overwrite_newer_draft(app, client, writing):
    save(client, writing, 'New draft in first tab', 0)
    assert save(client, writing, 'Stale second tab', 0).status_code == 409
    response = post(client, writing, essay='Stale second tab', draft_version=0, action='save')
    assert response.status_code == 409
    assert b'Stale second tab' in response.data
    assert b'value="0"' in response.data
    _, data = context(app, client, writing['path'])
    assert data['essay'] == 'New draft in first tab'


def test_successful_check_is_idempotent_and_defaults_to_latest(app, client, writing, monkeypatch):
    calls = []
    def evaluate(*args):
        calls.append(args)
        return FEEDBACK
    monkeypatch.setattr('app.ai_service.evaluate_writing', evaluate)
    submission = dict(essay=EDITED, draft_version=0, submission_token='same_submission_token_12345')
    response = post(client, writing, **submission)
    assert response.status_code == 302
    replay = post(client, writing, **submission)
    assert replay.status_code == 302 and replay.location == response.location
    assert len(calls) == 1
    response, data = context(app, client, writing['path'])
    assert data['essay'] == EDITED and data['selected']['label'] == 'Revision 1'
    assert data['remaining'] == 0 and data['band_change'] == 1
    assert b'+1.0' in response.data
    assert next(c for c in data['criteria'] if c['label']=='Grammar')['change'] == 2
    assert calls[0][1] == EDITED
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM writing_revisions').fetchone()[0] == 1
    # The allowance can be exhausted while draft saving remains available.
    assert save(client, writing, 'Next draft', data['draft']['version']).status_code == 200


def test_failed_ai_check_keeps_draft_and_retry_uses_one_check(app, client, writing, monkeypatch):
    def unavailable(*args):
        raise AIServiceError('Local model is offline.')
    monkeypatch.setattr('app.ai_service.evaluate_writing', unavailable)
    token = 'retry_submission_token_123456'
    response = post(client, writing, essay=EDITED, draft_version=0, submission_token=token)
    assert response.status_code == 200 and b'No AI check was used' in response.data
    _, data = context(app, client, writing['path'])
    assert data['essay'] == EDITED and data['remaining'] == 1
    monkeypatch.setattr('app.ai_service.evaluate_writing', lambda *args: FEEDBACK)
    response = post(client, writing, essay=EDITED, draft_version=data['draft']['version'], submission_token=token)
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM writing_revisions').fetchone()[0] == 1


def test_newer_edits_survive_feedback_returning(app, client, writing, monkeypatch):
    newer = 'More work written while the AI was checking.'
    def evaluate(*args):
        db = get_db()
        db.execute('UPDATE writing_revision_drafts SET essay=?,version=version+1 WHERE attempt_id=?',
                   (newer,writing['attempt']))
        db.commit()
        return FEEDBACK
    monkeypatch.setattr('app.ai_service.evaluate_writing', evaluate)
    assert post(client, writing, essay=EDITED, draft_version=0).status_code == 302
    _, data = context(app, client, writing['path'])
    assert data['essay'] == newer
    assert data['selected']['essay'] == EDITED


def test_shared_allowance_is_rechecked_after_ai_finishes(app, client, writing, monkeypatch):
    def evaluate(*args):
        db = get_db()
        db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'essay','{}',6)",
                   (writing['user'],writing['mock']))
        db.commit()
        return FEEDBACK
    monkeypatch.setattr('app.ai_service.evaluate_writing', evaluate)
    response = post(client, writing, essay=EDITED, draft_version=0)
    assert response.status_code == 200 and b'used in another session' in response.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM writing_revisions').fetchone()[0] == 0


def test_comparison_versions_are_scoped_and_diff_escapes_html(app, client, writing):
    with app.app_context():
        db = get_db()
        revision = db.execute('INSERT INTO writing_revisions(attempt_id,essay,feedback_json,band_score) VALUES(?,?,?,?)',
                              (writing['attempt'], '<script>alert("bad")</script> A new paragraph.', json.dumps(FEEDBACK),7)).lastrowid
        second = db.execute('INSERT INTO writing_revisions(attempt_id,essay,feedback_json,band_score) VALUES(?,?,?,?)',
                            (writing['attempt'], 'A clearer new paragraph.', json.dumps(FEEDBACK),7.5)).lastrowid
        db.commit()
    response, data = context(app, client, writing['path']+f'?baseline={revision}&revision={second}')
    assert data['baseline']['key'] == str(revision) and data['selected']['key'] == str(second)
    assert data['band_change'] == .5
    assert b'&lt;script&gt;' in response.data and b'<script>alert(' not in response.data
    assert b'<del>' in response.data and b'<ins>' in response.data
    assert client.get(writing['path']+'?revision=999999').status_code == 404
    before,after = 'One\n\nold paragraph.', 'One\n\nnew paragraph.'
    changes = essay_changes(before,after)
    assert ''.join(s['text'] for s in changes['before']) == before
    assert ''.join(s['text'] for s in changes['after']) == after
    assert changes['removed'] == 1 and changes['added'] == 1
    assert essay_changes('word '*2001, 'changed '*2001)['available'] is False


def test_invalid_or_short_essays_do_not_use_ai_checks(app, client, writing, monkeypatch):
    def unexpected(*args):
        raise AssertionError('AI must not be called')
    monkeypatch.setattr('app.ai_service.evaluate_writing', unexpected)
    assert post(client, writing, essay='Short draft', draft_version=0).status_code == 400
    _, data = context(app, client, writing['path'])
    assert data['essay'] == 'Short draft'
    assert save(client, writing, 'x'*50001, data['draft']['version']).status_code == 400
    assert client.post(writing['api'],json={'essay':'a','version':True},headers={'X-CSRF-Token':writing['csrf']}).status_code == 400
    assert data['remaining'] == 1


def test_ordinary_writing_check_cannot_overspend_allowance_used_by_revision(app, client, writing, monkeypatch):
    def evaluate(*args):
        db = get_db()
        db.execute('INSERT INTO writing_revisions(attempt_id,essay,feedback_json,band_score) VALUES(?,?,?,7)',
                   (writing['attempt'], EDITED, json.dumps(FEEDBACK)))
        db.commit()
        return FEEDBACK
    monkeypatch.setattr('app.ai.evaluate_writing', evaluate)
    response = client.post(f'/ai/writing/{writing["mock"]}', data={'essay': EDITED})
    assert response.status_code == 200 and b'used in another session' in response.data
    assert EDITED.encode() in response.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM ai_attempts WHERE user_id=?',(writing['user'],)).fetchone()[0] == 1
        assert get_db().execute('SELECT COUNT(*) FROM writing_revisions').fetchone()[0] == 1
