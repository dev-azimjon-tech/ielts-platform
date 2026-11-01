"""Regression cases for malformed AI inputs, quota races, and exam recovery."""
import io
import json
from types import SimpleNamespace

import pytest

from app.database import get_db
from app.models import User
from app.seed import seed_demo_content


@pytest.fixture()
def candidate(app, client):
    with app.app_context():
        seed_demo_content()
        user = User.create('AI audit', 'audit-ai@example.com', 'unused').id
        other = User.create('Other', 'audit-ai-other@example.com', 'unused').id
        db = get_db()
        ids = {s:db.execute(f"SELECT id FROM {'mock_tests' if s in ('listening','reading') else 'ai_mocks'} WHERE skill=? LIMIT 1",(s,)).fetchone()[0]
               for s in ('listening','reading','writing','speaking')}
    with client.session_transaction() as session:
        session['_user_id'] = str(user)
        session['_fresh'] = True
    return dict(user=user, other=other, ids=ids)


def turns(recording_id=None):
    result = {'part':1,'question':'Where do you live?','transcript':'I live in a village near the mountains.'}
    if recording_id:
        result['recording_id'] = recording_id
    return [result]


@pytest.mark.parametrize('payload', [[1], {'turns':[None]}, {'turns':['words']}, {'turns':[{'part':True,'question':'Q','transcript':'A'}]}, {'turns':[{'part':1,'question':'Q','transcript':42}]}])
def test_malformed_speaking_payload_is_rejected_before_ai(app, client, candidate, monkeypatch, payload):
    def unexpected(*args):
        raise AssertionError('Malformed submissions must not reach the AI')
    monkeypatch.setattr('app.ai.evaluate_speaking',unexpected)
    response = client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json=payload)
    assert response.status_code == 400
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0] == 0


def test_speaking_quota_is_rechecked_after_model_returns(app, client, candidate, monkeypatch):
    def evaluate(*args):
        db = get_db()
        for _ in range(2):
            db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'[]','{}',6)",
                       (candidate['user'],candidate['ids']['speaking']))
        db.commit()
        return {'overall_band':7}
    monkeypatch.setattr('app.ai.evaluate_speaking',evaluate)
    response = client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json={'turns':turns()})
    assert response.status_code == 403
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0] == 2


@pytest.mark.parametrize('band', [float('nan'),float('inf'),-1,10,True,'7',None])
def test_invalid_model_band_never_reaches_results(app, client, candidate, monkeypatch, band):
    monkeypatch.setattr('app.ai.evaluate_speaking',lambda *a:{'overall_band':band})
    monkeypatch.setattr('app.ai.evaluate_writing',lambda *a:{'overall_band':band})
    response = client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json={'turns':turns()})
    assert response.status_code == 503
    response = client.post(f'/ai/writing/{candidate["ids"]["writing"]}',data={'essay':'thoughtful words '*60})
    assert response.status_code == 200 and b'invalid band' in response.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0] == 0


def test_replayed_recorded_result_does_not_use_another_check(app, client, candidate, monkeypatch):
    calls=[]
    monkeypatch.setattr('app.ai.evaluate_speaking',lambda *a:calls.append(a) or {'overall_band':7})
    with app.app_context():
        db=get_db()
        db.execute("INSERT INTO speaking_recordings(id,user_id,ai_mock_id,mime_type,audio) VALUES('audit-recording',?,?,'audio/webm',?)",
                   (candidate['user'],candidate['ids']['speaking'],b'voice'))
        db.commit()
    payload={'turns':turns('audit-recording')}
    first=client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json=payload)
    second=client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json['redirect']==second.json['redirect'] and len(calls)==1
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0] == 1


def test_foreign_recording_and_wrong_question_history_do_not_reach_ai(app, client, candidate, monkeypatch):
    with app.app_context():
        db=get_db()
        db.execute("INSERT INTO speaking_recordings(id,user_id,ai_mock_id,mime_type,audio) VALUES('foreign-audio',?,?,'audio/webm',?)",
                   (candidate['other'],candidate['ids']['speaking'],b'voice'))
        db.commit()
    def unexpected(*a):raise AssertionError('Invalid answers must not be processed')
    monkeypatch.setattr('app.ai.evaluate_speaking',unexpected)
    monkeypatch.setattr('app.ai.transcribe_audio',unexpected)
    assert client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json={'turns':turns('foreign-audio')}).status_code==400
    response=client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/turn',data={'audio':(io.BytesIO(b'voice'),'answer.webm','audio/webm'),'history':'[]','plan_index':'2'})
    assert response.status_code==400


def test_model_response_contract_rejects_missing_or_invalid_criteria(app, monkeypatch):
    from app.ai_service import AIServiceError,evaluate_writing
    valid=dict(overall_band=7,task_response_band=7,coherence_band=7,lexical_band=7,grammar_band=7,
               strengths=['Good examples'],improvements=['Expand conclusion'],feedback='Clear structure')
    output={'value':valid}
    fake=SimpleNamespace(chat=lambda **kw:{'message':{'content':json.dumps(output['value'])}})
    monkeypatch.setattr('app.ai_service._ollama_client',lambda:fake)
    with app.app_context():
        assert evaluate_writing('Prompt','essay',50)['overall_band']==7
        for bad in ({'overall_band':7},{**valid,'grammar_band':True},{**valid,'lexical_band':float('nan')},{**valid,'strengths':'wrong type'},[valid]):
            output['value']=bad
            with pytest.raises(AIServiceError,match='invalid feedback'):
                evaluate_writing('Prompt','essay',50)


def test_stale_exam_writing_submit_cannot_replace_newer_saved_draft(app, client, candidate, monkeypatch):
    client.get('/learn/exam')
    with client.session_transaction() as session:csrf=session['learning_csrf']
    client.post('/learn/exam',data={'csrf_token':csrf,**candidate['ids']})
    with app.app_context():sid=get_db().execute('SELECT id FROM exam_sessions').fetchone()[0]
    for stage in (0,1):client.post(f'/learn/exam/{sid}/skip',data={'csrf_token':csrf,'stage':stage})
    client.get(f'/ai/writing/{candidate["ids"]["writing"]}')
    newer='Newer saved essay '*30
    response=client.post(f'/learn/exam/{sid}/draft',json={'stage':2,'revision':0,'draft':{'essay':newer}},headers={'X-CSRF-Token':csrf})
    assert response.status_code==200
    def unexpected(*a):raise AssertionError('A stale draft must not be scored')
    monkeypatch.setattr('app.ai.evaluate_writing',unexpected)
    response=client.post(f'/ai/writing/{candidate["ids"]["writing"]}',data={'essay':'Old tab essay '*30,'_exam_session':sid,'_exam_stage':2,'_exam_revision':0})
    assert response.status_code==409 and b'data-exam-conflict="true"' in response.data
    assert b'Old tab essay' in response.data
    with app.app_context():
        draft=get_db().execute('SELECT draft_json FROM exam_section_state WHERE session_id=? AND stage=2',(sid,)).fetchone()[0]
        assert json.loads(draft)['essay']==newer


def test_orphan_cleanup_keeps_audio_referenced_by_unfinished_exam(app, client, candidate, monkeypatch):
    with app.app_context():
        db=get_db()
        for rid in ('active-exam-audio','abandoned-audio'):
            db.execute("INSERT INTO speaking_recordings(id,user_id,ai_mock_id,mime_type,audio,created_at) VALUES(?, ?,?,'audio/webm',?,'2000-01-01 00:00:00')",
                       (rid,candidate['user'],candidate['ids']['speaking'],b'voice'))
        selected=[{'kind':'mock' if s in ('listening','reading') else 'ai','id':mid,'skill':s,'minutes':20} for s,mid in candidate['ids'].items()]
        sid=db.execute('INSERT INTO exam_sessions(user_id,mocks_json) VALUES(?,?)',(candidate['user'],json.dumps(selected))).lastrowid
        db.execute('INSERT INTO exam_section_state(session_id,stage,draft_json) VALUES(?,?,?)',(sid,3,json.dumps({'turns':turns('active-exam-audio')})))
        db.commit()
    monkeypatch.setattr('app.ai.transcribe_audio',lambda *a:'A clear answer')
    monkeypatch.setattr('app.ai.generate_next_speaking_question',lambda *a:{'question':'Next','examiner_note':''})
    response=client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/turn',data={'audio':(io.BytesIO(b'voice'),'answer.webm','audio/webm'),'history':'[]','plan_index':'0'})
    assert response.status_code==200
    with app.app_context():
        assert get_db().execute("SELECT id FROM speaking_recordings WHERE id='active-exam-audio'").fetchone()
        assert get_db().execute("SELECT id FROM speaking_recordings WHERE id='abandoned-audio'").fetchone() is None


def test_initial_writing_submission_token_prevents_duplicate_checks(app,client,candidate,monkeypatch):
    calls=[]
    monkeypatch.setattr('app.ai.evaluate_writing',lambda *a:calls.append(a) or {'overall_band':7})
    payload={'essay':'A careful writing response '*30,'submission_token':'initial_writing_check_123456789'}
    first=client.post(f'/ai/writing/{candidate["ids"]["writing"]}',data=payload)
    replay=client.post(f'/ai/writing/{candidate["ids"]["writing"]}',data=payload)
    assert first.status_code==replay.status_code==302 and first.location==replay.location
    assert len(calls)==1
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0]==1
        other_mock=get_db().execute("SELECT id FROM ai_mocks WHERE skill='writing' AND id!=? LIMIT 1",(candidate['ids']['writing'],)).fetchone()[0]
    assert client.post(f'/ai/writing/{other_mock}',data=payload).status_code==400
    with client.session_transaction() as session:session['_user_id']=str(candidate['other'])
    assert client.post(f'/ai/writing/{candidate["ids"]["writing"]}',data=payload).status_code==400


@pytest.mark.parametrize('bad',[float('inf'),float('nan'),-1,10,'7',True])
def test_legacy_exam_invalid_bands_are_unavailable_not_report_errors(bad):
    from app.exam_sessions import report
    item={'results_json':json.dumps([{'band':0},{'band':7},{'band':8},{'band':bad}]),'mocks_json':'[]'}
    result=report(item)
    assert result['overall'] is None and result['scored_count']==3
    assert result['results'][0]['band']==0 and result['results'][3]['band'] is None
    item['results_json']=json.dumps([{'band':0},{'band':7},{'band':8},{'band':9}])
    assert report(item)['overall']==6


def test_failed_speaking_check_reports_revision_for_safe_retry(app,client,candidate,monkeypatch):
    from app.ai_service import AIServiceError
    client.get('/learn/exam')
    with client.session_transaction() as session:csrf=session['learning_csrf']
    client.post('/learn/exam',data={'csrf_token':csrf,**candidate['ids']})
    with app.app_context():sid=get_db().execute('SELECT id FROM exam_sessions').fetchone()[0]
    for stage in (0,1,2):client.post(f'/learn/exam/{sid}/skip',data={'csrf_token':csrf,'stage':stage})
    client.get(f'/ai/speaking/{candidate["ids"]["speaking"]}')
    def unavailable(*args):raise AIServiceError('Offline')
    monkeypatch.setattr('app.ai.evaluate_speaking',unavailable)
    payload={'turns':turns(),'_exam_session':sid,'_exam_stage':3,'_exam_revision':0}
    first=client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json=payload)
    assert first.status_code==503 and first.json['exam_revision']==1
    monkeypatch.setattr('app.ai.evaluate_speaking',lambda *a:{'overall_band':7})
    payload['_exam_revision']=first.json['exam_revision']
    retry=client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/complete',json=payload)
    assert retry.status_code==200
    with app.app_context():assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0]==1


def test_transcribed_answer_survives_followup_model_failure(app,client,candidate,monkeypatch):
    from app.ai_service import AIServiceError
    monkeypatch.setattr('app.ai.transcribe_audio',lambda audio:'My answer was transcribed successfully.')
    def unavailable(*args):raise AIServiceError('Ollama unavailable')
    monkeypatch.setattr('app.ai.generate_next_speaking_question',unavailable)
    response=client.post(f'/ai/speaking/{candidate["ids"]["speaking"]}/turn',data={
        'audio':(io.BytesIO(b'voice'),'answer.webm','audio/webm'),'history':'[]','plan_index':'0'})
    assert response.status_code==200 and response.json['finished'] is False
    assert response.json['notice'] and response.json['next']['question']
    turn=response.json['turns'][0]
    assert turn['transcript']=='My answer was transcribed successfully.'
    assert client.get('/ai/recordings/'+turn['recording_id']).status_code==200


def test_recording_claimed_during_scoring_does_not_create_another_result(app,client,candidate,monkeypatch):
    mid=candidate['ids']['speaking']
    with app.app_context():
        db=get_db();db.execute("INSERT INTO speaking_recordings(id,user_id,ai_mock_id,mime_type,audio) VALUES('race-audio',?,?,'audio/webm',?)",(candidate['user'],mid,b'voice'));db.commit()
    def evaluate(*args):
        db=get_db()
        aid=db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'[]','{}',6)",(candidate['user'],mid)).lastrowid
        db.execute("UPDATE speaking_recordings SET attempt_id=? WHERE id='race-audio'",(aid,));db.commit()
        return {'overall_band':7}
    monkeypatch.setattr('app.ai.evaluate_speaking',evaluate)
    response=client.post(f'/ai/speaking/{mid}/complete',json={'turns':turns('race-audio')})
    assert response.status_code==400
    with app.app_context():assert get_db().execute('SELECT COUNT(*) FROM ai_attempts').fetchone()[0]==1
