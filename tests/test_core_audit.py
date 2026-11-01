"""Regression coverage for authentication, immutable reviews, and admin edits."""
import json

import pytest
from flask import template_rendered
from flask.testing import FlaskClient
from werkzeug.security import generate_password_hash

from app import create_app
from app.database import get_db
from app.models import User
from app.seed import seed_demo_content


@pytest.fixture()
def users(app,client):
    with app.app_context():
        seed_demo_content()
        student=User.create('Audit learner','audit@example.com',generate_password_hash('securepass')).id
        admin=User.create('Audit admin','audit-admin@example.com',generate_password_hash('securepass'),is_admin=True).id
    with client.session_transaction() as session:
        session['_user_id']=str(student);session['_fresh']=True
    client.get('/learn/')
    return student,admin


def csrf(client):
    client.get('/auth/login')
    with client.session_transaction() as session:return session['app_csrf_token']


def test_csrf_is_required_for_auth_mock_and_ai_requests(app,users):
    raw=FlaskClient(app,app.response_class)
    for path,data in [('/auth/register',{'name':'Unwanted','email':'unwanted@example.com','password':'securepass','confirm_password':'securepass'}),
                      ('/auth/login',{'email':'audit@example.com','password':'securepass'}),
                      ('/mocks/1/submit',{}),('/ai/speaking/1/complete',{})]:
        assert raw.post(path,data=data).status_code==400
    token=csrf(raw)
    assert raw.post('/auth/login',data={'email':'audit@example.com','password':'securepass','csrf_token':'wrong'}).status_code==400
    foreign=FlaskClient(app,app.response_class)
    assert foreign.post('/auth/login',data={'email':'audit@example.com','password':'securepass','csrf_token':token}).status_code==400
    response=raw.post('/auth/login',data={'email':'audit@example.com','password':'securepass','csrf_token':token})
    assert response.status_code==302
    assert raw.post('/auth/logout').status_code==400
    response=raw.post('/ai/speaking/1/complete',json={'turns':[]})
    assert response.status_code==400 and response.json['error']


def test_login_resumes_local_destination_and_discards_previous_session_state(app,users):
    raw=FlaskClient(app,app.response_class)
    token=csrf(raw)
    with raw.session_transaction() as session:
        session['flashcards_csrf_token']='old-account-token'
        session['vocabulary_review_cursor:999']=123
    response=raw.post('/auth/login?next=/learn/plan',data={'email':'audit@example.com','password':'securepass','csrf_token':token})
    assert response.location=='/learn/plan'
    with raw.session_transaction() as session:
        assert session['_user_id']==str(users[0])
        assert 'flashcards_csrf_token' not in session and 'vocabulary_review_cursor:999' not in session
        assert session.get('app_csrf_token')!=token


@pytest.mark.parametrize('target',['https://example.com/','//example.com/','/\\example.com/','/path\nheader'])
def test_login_does_not_redirect_outside_platform(app,users,target):
    raw=FlaskClient(app,app.response_class)
    token=csrf(raw)
    response=raw.post('/auth/login',data={'email':'audit@example.com','password':'securepass','csrf_token':token,'next':target})
    assert response.status_code==302 and response.location=='/dashboard'


@pytest.mark.parametrize('value',['','dev-only-change-this-secret','replace-this-with-a-long-random-value'])
def test_unconfigured_apps_do_not_share_a_public_session_signing_key(tmp_path,monkeypatch,value):
    monkeypatch.setenv('SECRET_KEY',value)
    first=create_app({'DATABASE':str(tmp_path/'first.sqlite3')})
    second=create_app({'DATABASE':str(tmp_path/'second.sqlite3')})
    assert first.secret_key and first.secret_key!=second.secret_key
    assert first.secret_key!='dev-only-change-this-secret'


def capture(app,client,path):
    contexts=[]
    def receiver(sender,template,context,**extra):contexts.append(context)
    with template_rendered.connected_to(receiver,app):response=client.get(path)
    assert response.status_code==200
    return response,contexts[-1]


def question(app):
    with app.app_context():
        return dict(get_db().execute("SELECT q.* FROM questions q JOIN mock_tests m ON m.id=q.mock_id WHERE m.skill='reading' ORDER BY q.id LIMIT 1").fetchone())


def test_frozen_review_survives_question_edit_and_deletion(app,client,users):
    q=question(app)
    assert client.post(f'/mocks/{q["mock_id"]}/submit',data={f'question_{q["id"]}':'incorrect'}).status_code==200
    with app.app_context():
        db=get_db();aid=db.execute('SELECT MAX(id) FROM attempts').fetchone()[0]
        db.execute('DELETE FROM questions WHERE id=?',(q['id'],));db.commit()
    _,data=capture(app,client,f'/learn/results/{aid}')
    frozen=next(item for item in data['questions'] if item['id']==q['id'])
    assert frozen['correct_answer']==q['correct_answer'] and frozen['prompt']==q['prompt']
    _,data=capture(app,client,'/learn/mistakes')
    assert any(item['id']==q['id'] for item in data['items'])
    with client.session_transaction() as session:token=session['learning_csrf']
    response=client.post('/learn/mistakes',data={'csrf_token':token,'question_id':q['id'],'attempt_id':aid,'answer':q['correct_answer']})
    assert response.status_code==302
    _,data=capture(app,client,'/learn/mistakes')
    assert next(item for item in data['items'] if item['id']==q['id'])['review']['is_correct']==1


def test_later_missed_mock_clears_prior_successful_retry_badge(app,client,users):
    q=question(app);path=f'/mocks/{q["mock_id"]}/submit'
    client.post(path,data={f'question_{q["id"]}':'incorrect'})
    with app.app_context():first=get_db().execute('SELECT MAX(id) FROM attempts').fetchone()[0]
    with client.session_transaction() as session:token=session['learning_csrf']
    client.post('/learn/mistakes',data={'csrf_token':token,'question_id':q['id'],'attempt_id':first,'answer':q['correct_answer']})
    client.post(path,data={f'question_{q["id"]}':'incorrect again'})
    _,data=capture(app,client,'/learn/mistakes')
    item=next(item for item in data['items'] if item['id']==q['id'])
    assert item['review'] is None and item['source_attempt_id']!=first
    assert client.post('/learn/mistakes',data={'csrf_token':token,'question_id':q['id'],'attempt_id':first,'answer':q['correct_answer']}).status_code==409


def admin_post(client,users,path,data):
    with client.session_transaction() as session:session['_user_id']=str(users[1]);session['_fresh']=True
    client.get('/admin/')
    with client.session_transaction() as session:token=session['admin_csrf_token']
    return client.post(path,data={'csrf_token':token,**data})


def test_admin_cannot_convert_a_populated_mock_to_another_skill(app,client,users):
    q=question(app)
    response=admin_post(client,users,f'/admin/mocks/{q["mock_id"]}/edit-details',dict(skill='listening',title='Changed type',description='Description',time_limit_minutes=30))
    assert response.status_code==200 and b'Create a new mock' in response.data
    with app.app_context():assert get_db().execute('SELECT skill FROM mock_tests WHERE id=?',(q['mock_id'],)).fetchone()[0]=='reading'


def test_admin_rejects_unrenderable_multiple_choice_and_legacy_admin_premium(app,client,users):
    q=question(app)
    response=admin_post(client,users,f'/admin/mocks/{q["mock_id"]}/content/{q["passage_id"]}/questions/new',
        dict(question_type='multiple_choice',prompt='Too many choices',correct_answer='A',options='\n'.join(f'Choice {i}' for i in range(27)),explanation='Explanation'))
    assert response.status_code==200 and b'between 2 and 26' in response.data
    assert admin_post(client,users,f'/admin/users/{users[1]}/toggle-premium',{}).status_code==400


def test_mock_submission_rechecks_quota_under_write_lock(app,client,users,monkeypatch):
    q=question(app)
    def consume_last_checks(*args):
        db=get_db()
        db.executemany("INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,0,40,'{}')",[(users[0],q['mock_id'])]*10)
        db.commit()
    monkeypatch.setattr('app.exam_sessions.save_submission_draft',consume_last_checks)
    response=client.post(f'/mocks/{q["mock_id"]}/submit',data={})
    assert response.status_code==302
    with app.app_context():assert get_db().execute('SELECT COUNT(*) FROM attempts WHERE user_id=?',(users[0],)).fetchone()[0]==10


def test_unicode_answers_remain_distinguishable():
    from app.mocks import _normalise_answer
    assert _normalise_answer(' École ') == _normalise_answer('école')
    assert _normalise_answer('école') != _normalise_answer('cole')
    assert _normalise_answer('東京') != _normalise_answer('大阪')


def test_admin_preserves_legacy_review_before_editing_a_question(app,client,users):
    q=question(app)
    with app.app_context():
        db=get_db()
        aid=db.execute('INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,0,1,?)',
                       (users[0],q['mock_id'],json.dumps({str(q['id']):'wrong'}))).lastrowid
        db.commit()
    response=admin_post(client,users,f'/admin/questions/{q["id"]}/edit',dict(question_type='short_answer',prompt='Changed prompt',correct_answer='Changed answer',explanation='Changed explanation'))
    assert response.status_code==302
    with app.app_context():
        db=get_db()
        snapshot=json.loads(db.execute('SELECT questions_json FROM attempt_snapshots WHERE attempt_id=?',(aid,)).fetchone()[0])
        assert snapshot[0]['prompt']==q['prompt'] and snapshot[0]['correct_answer']==q['correct_answer']
        assert db.execute('SELECT score FROM attempts WHERE id=?',(aid,)).fetchone()[0]==0
