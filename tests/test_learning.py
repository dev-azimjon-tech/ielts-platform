import io
import json
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash
from app.database import get_db
from app.models import User
from app.seed import seed_demo_content

@pytest.fixture()
def setup(app,client):
    with app.app_context():
        seed_demo_content()
        one=User.create('Learner','learn@example.com',generate_password_hash('password123'))
        two=User.create('Teacher','teacher@example.com',generate_password_hash('password123'))
        ids=(one.id,two.id)
    with client.session_transaction() as s: s['_user_id']=str(ids[0]); s['_fresh']=True
    client.get('/learn/')
    return ids

def post(client,path,data=None):
    with client.session_transaction() as s: token=s['learning_csrf']
    return client.post(path,data={'csrf_token':token,**(data or {})})

def switch(client,user):
    with client.session_transaction() as s: s['_user_id']=str(user); s['_fresh']=True

def test_tools_render_and_csrf(client,setup):
    for path in ('/learn/','/learn/mistakes','/learn/review','/learn/plan','/learn/progress','/learn/exam','/learn/teachers'):
        assert client.get(path).status_code==200,path
    assert client.post('/learn/teachers',data={'action':'create'}).status_code==400

def test_notebook_ownership_and_retry(app,client,setup):
    with app.app_context():
        db=get_db(); q=db.execute('SELECT * FROM questions LIMIT 1').fetchone(); qid=q['id']; answer=q['correct_answer']
        db.execute('INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,0,1,?)',(setup[0],q['mock_id'],json.dumps({str(qid):'wrong'}))); db.commit()
    assert b'wrong' in client.get('/learn/mistakes').data
    assert post(client,'/learn/mistakes',{'question_id':qid,'answer':answer}).status_code==302
    assert b'Correct' in client.get('/learn/mistakes').data
    switch(client,setup[1]); assert post(client,'/learn/mistakes',{'question_id':qid,'answer':answer}).status_code==404

def test_spaced_review_persists_and_protects_owner(app,client,setup):
    with app.app_context():
        db=get_db(); wid=db.execute("INSERT INTO vocabulary_words(user_id,term,normalized_term,meaning) VALUES(?,'learn','learn','gain knowledge')",(setup[0],)).lastrowid; db.commit()
    assert b'gain knowledge' in client.get('/learn/review').data
    post(client,'/learn/review',{'word_id':wid,'rating':'good'})
    assert b'All caught up' in client.get('/learn/review').data
    with app.app_context(): assert get_db().execute('SELECT due_on FROM vocabulary_schedule WHERE word_id=?',(wid,)).fetchone()[0]==(date.today()+timedelta(days=1)).isoformat()
    switch(client,setup[1]); assert post(client,'/learn/review',{'word_id':wid,'rating':'again'}).status_code==404

def test_plan_validation_and_persistence(app,client,setup):
    post(client,'/learn/plan',{'target_band':'nan','exam_date':date.today().isoformat(),'daily_minutes':30})
    with app.app_context(): assert get_db().execute('SELECT * FROM study_plans').fetchone() is None
    post(client,'/learn/plan',{'target_band':'7.5','exam_date':(date.today()+timedelta(days=60)).isoformat(),'daily_minutes':45})
    assert b'Target band 7.5' in client.get('/learn/plan').data
    post(client,'/learn/plan',{'task_key':'vocabulary'})
    assert b'Completed' in client.get('/learn/plan').data

def test_teacher_requires_student_consent_and_revocation(app,client,setup):
    switch(client,setup[1]); post(client,'/learn/teachers',{'action':'create'})
    assert client.get(f'/learn/students/{setup[0]}').status_code==404
    with app.app_context(): code=get_db().execute('SELECT invite_code FROM teacher_profiles').fetchone()[0]
    switch(client,setup[0]); post(client,'/learn/teachers',{'action':'join','code':code})
    switch(client,setup[1]); assert client.get(f'/learn/students/{setup[0]}').status_code==200
    with app.app_context(): mid=get_db().execute('SELECT id FROM mock_tests LIMIT 1').fetchone()[0]
    assert post(client,f'/learn/students/{setup[0]}',{'mock':f'mock:{mid}','due_on':date.today().isoformat(),'note':'Read carefully'}).status_code==302
    switch(client,setup[0]); assert b'Read carefully' in client.get('/learn/teachers').data
    post(client,'/learn/teachers',{'action':'leave','teacher_id':setup[1]})
    switch(client,setup[1]); assert client.get(f'/learn/students/{setup[0]}').status_code==404

def test_exam_sequence_and_combined_report(app,client,setup,monkeypatch):
    monkeypatch.setattr('app.ai.evaluate_writing',lambda *a:{'overall_band':6.5})
    monkeypatch.setattr('app.ai.evaluate_speaking',lambda *a:{'overall_band':7})
    with app.app_context():
        db=get_db(); choices={s:db.execute(f"SELECT id FROM {'mock_tests' if s in ('reading','listening') else 'ai_mocks'} WHERE skill=? LIMIT 1",(s,)).fetchone()[0] for s in ('listening','reading','writing','speaking')}
    assert post(client,'/learn/exam',choices).status_code==302
    assert client.get('/learn/exam/continue').location.endswith(f"/mocks/{choices['listening']}")
    for skill in ('listening','reading'):
        response=client.get(f"/mocks/{choices[skill]}"); assert b'data-exam-deadline' in response.data
        response=client.post(f"/mocks/{choices[skill]}/submit",data={}); assert response.location.endswith('/learn/exam/continue')
    response=client.post(f"/ai/writing/{choices['writing']}",data={'essay':'word '*60}); assert response.location.endswith('/learn/exam/continue')
    response=client.post(f"/ai/speaking/{choices['speaking']}/complete",json={'turns':[{'part':1,'question':'Hello','transcript':'Hello there'}]}); assert response.json['redirect'].endswith('/learn/exam/continue')
    assert b'estimated overall band' in client.get('/learn/exam').data
    with app.app_context():
        e=get_db().execute('SELECT * FROM exam_sessions').fetchone(); assert e['stage']==4 and e['completed_at']; assert len(json.loads(e['results_json']))==4

def test_revision_comparison_allowance_and_privacy(app,client,setup,monkeypatch):
    monkeypatch.setattr('app.ai_service.evaluate_writing',lambda *a:{'overall_band':7,'feedback':'Clearer','improvements':[]})
    with app.app_context():
        db=get_db(); mid=db.execute("SELECT id FROM ai_mocks WHERE skill='writing' LIMIT 1").fetchone()[0]
        aid=db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'Original essay','{}',6)",(setup[0],mid)).lastrowid; db.commit()
    assert post(client,f'/learn/writing/{aid}/revise',{'essay':'improved '*60}).status_code==302
    assert b'+1.0' in client.get(f'/learn/writing/{aid}/revise').data
    post(client,f'/learn/writing/{aid}/revise',{'essay':'improved '*60})
    with app.app_context(): assert get_db().execute('SELECT COUNT(*) FROM writing_revisions').fetchone()[0]==1
    switch(client,setup[1]); assert client.get(f'/learn/writing/{aid}/revise').status_code==404

def test_recording_owner_access_and_saved_transcript(app,client,setup,monkeypatch):
    monkeypatch.setattr('app.ai.transcribe_audio',lambda audio:'My spoken answer')
    monkeypatch.setattr('app.ai.generate_next_speaking_question',lambda *a:{'question':'Next question','examiner_note':''})
    with app.app_context(): mid=get_db().execute("SELECT id FROM ai_mocks WHERE skill='speaking' LIMIT 1").fetchone()[0]
    response=client.post(f'/ai/speaking/{mid}/turn',data={'audio':(io.BytesIO(b'audio-bytes'),'answer.webm','audio/webm'),'plan_index':'0','history':'[]'})
    assert response.status_code==200
    rid=response.json['turns'][0]['recording_id']; assert client.get(f'/ai/recordings/{rid}').data==b'audio-bytes'
    switch(client,setup[1]); assert client.get(f'/ai/recordings/{rid}').status_code==404


def test_again_cycles_through_due_cards_and_progress_matches_library(app, client, setup):
    with app.app_context():
        db = get_db()
        word_ids = []
        for term in ('apple', 'bridge', 'cloud'):
            word_ids.append(db.execute(
                'INSERT INTO vocabulary_words(user_id,term,normalized_term,meaning) VALUES(?,?,?,?)',
                (setup[0], term, term, f'Meaning of {term}'),
            ).lastrowid)
        db.commit()
    for word_id, term in zip(word_ids, ('apple', 'bridge', 'cloud')):
        response = client.get('/learn/review')
        assert f'<h2>{term}</h2>'.encode() in response.data
        post(client, '/learn/review', {'word_id': word_id, 'rating': 'again'})
    assert b'<h2>apple</h2>' in client.get('/learn/review').data
    library = client.get('/flashcards/')
    assert b'Review due cards (3)' in library.data
    assert b'3 reviewed today' in library.data
    assert b'0 new' in library.data


def test_review_preview_matches_saved_due_date_and_replayed_rating_is_safe(app, client, setup):
    today = date.today()
    with app.app_context():
        db = get_db()
        wid = db.execute(
            "INSERT INTO vocabulary_words(user_id,term,normalized_term,meaning) VALUES(?,'advanced','advanced','far along')",
            (setup[0],),
        ).lastrowid
        db.execute('INSERT INTO vocabulary_schedule VALUES(?,?,?,?)',
                   (wid, (today - timedelta(days=2)).isoformat(), 200, None))
        db.commit()
    response = client.get('/learn/review')
    assert b'In 365 days' in response.data
    post(client, '/learn/review', {'word_id': wid, 'rating': 'easy'})
    expected = (today + timedelta(days=365)).isoformat()
    assert expected.encode() in client.get('/learn/review').data
    post(client, '/learn/review', {'word_id': wid, 'rating': 'again'})
    with app.app_context():
        scheduled = get_db().execute('SELECT * FROM vocabulary_schedule WHERE word_id=?', (wid,)).fetchone()
        assert scheduled['due_on'] == expected
        assert scheduled['interval_days'] == 365
    switch(client, setup[1])
    assert b'Add your first word' in client.get('/learn/review').data
    assert b'Review due cards (0)' in client.get('/flashcards/').data
