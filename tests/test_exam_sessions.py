"""Exam clocks, private drafts, recovery, replay protection, and incomplete reports."""
import json

import pytest
from flask import template_rendered

from app.database import get_db
from app.models import User
from app.seed import seed_demo_content


@pytest.fixture()
def exam(app,client):
    with app.app_context():
        seed_demo_content()
        db=get_db()
        user=User.create('Exam student','exam@example.com','unused').id
        other=User.create('Other','other-exam@example.com','unused').id
        selected={skill:db.execute(f"SELECT id FROM {'mock_tests' if skill in ('listening','reading') else 'ai_mocks'} WHERE skill=? LIMIT 1",(skill,)).fetchone()[0] for skill in ('listening','reading','writing','speaking')}
    with client.session_transaction() as session:
        session['_user_id']=str(user)
        session['_fresh']=True
    client.get('/learn/exam')
    with client.session_transaction() as session: token=session['learning_csrf']
    assert client.post('/learn/exam',data={'csrf_token':token,**selected}).status_code==302
    with app.app_context(): sid=get_db().execute('SELECT id FROM exam_sessions WHERE user_id=?',(user,)).fetchone()[0]
    return {'id':sid,'user':user,'other':other,'selected':selected,'token':token}


def save(client,exam,stage,revision,draft):
    return client.post(f"/learn/exam/{exam['id']}/draft",json={'stage':stage,'revision':revision,'draft':draft},headers={'X-CSRF-Token':exam['token']})


def capture(app,client,path):
    contexts=[]
    def receiver(sender,template,context,**extra): contexts.append(context)
    with template_rendered.connected_to(receiver,app): response=client.get(path)
    assert response.status_code==200
    return contexts[-1]


def skip(client,exam,stage):
    return client.post(f"/learn/exam/{exam['id']}/skip",data={'csrf_token':exam['token'],'stage':stage})


def test_clock_does_not_start_next_section_until_opened(app,client,exam):
    first=capture(app,client,f"/mocks/{exam['selected']['listening']}")
    second=capture(app,client,f"/mocks/{exam['selected']['listening']}")
    assert first['exam_deadline']==second['exam_deadline']
    assert skip(client,exam,0).status_code==302
    with app.app_context():
        pending=get_db().execute('SELECT * FROM exam_section_state WHERE session_id=? AND stage=1',(exam['id'],)).fetchone()
        assert pending['started_at'] is None
    opened=capture(app,client,f"/mocks/{exam['selected']['reading']}")
    assert opened['exam_session']['stage']==1
    with app.app_context(): assert get_db().execute('SELECT started_at FROM exam_section_state WHERE session_id=? AND stage=1',(exam['id'],)).fetchone()[0]


def test_drafts_restore_and_reject_stale_tabs_wrong_stage_and_other_users(app,client,exam):
    client.get(f"/mocks/{exam['selected']['listening']}")
    draft={'question_1':'my answer'}
    response=save(client,exam,0,0,draft)
    assert response.status_code==200 and response.json['revision']==1
    restored=capture(app,client,f"/mocks/{exam['selected']['listening']}")
    assert restored['exam_draft']==draft
    assert save(client,exam,0,0,{'question_1':'stale answer'}).status_code==409
    assert save(client,exam,1,1,draft).status_code==409
    assert client.post(f"/learn/exam/{exam['id']}/draft",json={'stage':0,'revision':1,'draft':draft}).status_code==400
    with client.session_transaction() as session: session['_user_id']=str(exam['other'])
    assert save(client,exam,0,1,draft).status_code==404
    assert client.get(f"/learn/exam/{exam['id']}/report").status_code==404


def test_duplicate_submission_does_not_consume_second_attempt(app,client,exam):
    mid=exam['selected']['listening']
    identity={'_exam_session':exam['id'],'_exam_stage':0}
    assert client.post(f'/mocks/{mid}/submit',data=identity).status_code==302
    assert client.post(f'/mocks/{mid}/submit',data=identity).status_code==302
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM attempts WHERE user_id=?',(exam['user'],)).fetchone()[0]==1
        assert get_db().execute('SELECT stage FROM exam_sessions WHERE id=?',(exam['id'],)).fetchone()[0]==1


def test_ai_failure_keeps_essay_and_does_not_auto_retry(app,client,exam,monkeypatch):
    from app.ai_service import AIServiceError
    skip(client,exam,0); skip(client,exam,1)
    mid=exam['selected']['writing']
    client.get(f'/ai/writing/{mid}')
    with app.app_context():
        get_db().execute("UPDATE exam_section_state SET started_at='2000-01-01 00:00:00' WHERE session_id=? AND stage=2",(exam['id'],));get_db().commit()
    def unavailable(*args): raise AIServiceError('AI offline')
    monkeypatch.setattr('app.ai.evaluate_writing',unavailable)
    essay='Original saved response '*30
    response=client.post(f'/ai/writing/{mid}',data={'essay':essay,'_exam_session':exam['id'],'_exam_stage':2})
    assert response.status_code==200 and b'AI offline' in response.data
    assert b'"autoSubmit": false' in response.data
    recovered=capture(app,client,f'/ai/writing/{mid}')
    assert recovered['exam_draft']['essay']==essay and recovered['exam_auto_submit'] is False
    with app.app_context(): assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0]==0


def test_unscored_report_keeps_drafts_and_never_invents_overall_band(app,client,exam):
    skip(client,exam,0); skip(client,exam,1)
    assert save(client,exam,2,0,{'essay':'An incomplete essay.'}).status_code==200
    skip(client,exam,2); skip(client,exam,3)
    response=client.get(f"/learn/exam/{exam['id']}/report")
    assert response.status_code==200
    assert b'An incomplete essay.' in response.data
    assert b'Ended without a score.' in response.data
    assert b'Estimated overall band' not in response.data
    with app.app_context():
        e=get_db().execute('SELECT * FROM exam_sessions WHERE id=?',(exam['id'],)).fetchone()
        assert e['stage']==4 and e['completed_at']
        assert all(r['band'] is None for r in json.loads(e['results_json']))


def test_speaking_answers_recover_and_failed_scoring_can_retry(app,client,exam,monkeypatch):
    from app.ai_service import AIServiceError
    for stage in range(3): skip(client,exam,stage)
    mid=exam['selected']['speaking']
    turns=[{'part':1,'question':'Where do you live?','transcript':'I live near the mountains.'}]
    draft={'turns':turns,'index':1,'next':{'part':1,'question':'What do you like about it?','instruction':'Answer naturally','prep_seconds':0},'finished':False}
    assert save(client,exam,3,0,draft).status_code==200
    restored=capture(app,client,f'/ai/speaking/{mid}')
    assert restored['exam_draft']['turns']==turns
    def unavailable(*args): raise AIServiceError('Examiner unavailable')
    monkeypatch.setattr('app.ai.evaluate_speaking',unavailable)
    response=client.post(f'/ai/speaking/{mid}/complete',json={'turns':turns,'_exam_session':exam['id'],'_exam_stage':3})
    assert response.status_code==503
    recovered=capture(app,client,f'/ai/speaking/{mid}')
    assert recovered['exam_draft']['finished'] is True
    assert recovered['exam_draft']['turns']==turns
    assert save(client,exam,3,recovered['exam_revision'],{'turns':'bad data'}).status_code==400
