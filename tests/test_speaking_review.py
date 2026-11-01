"""Playback, history, downloads, and deletion must preserve ownership and results."""
import json

import pytest
from flask import template_rendered

from app.database import get_db
from app.models import User
from app.seed import seed_demo_content


@pytest.fixture()
def speaking(app, client):
    with app.app_context():
        seed_demo_content()
        user = User.create('Speaker', 'speaker@example.com', 'unused').id
        other = User.create('Other', 'other-speaker@example.com', 'unused', is_admin=True).id
        db = get_db()
        mid = db.execute("SELECT id FROM ai_mocks WHERE skill='speaking' ORDER BY id LIMIT 1").fetchone()[0]
        turns = [{'part':1,'question':'Where do you live?','transcript':'I live near a beautiful mountain.','recording_id':'owned-audio'},
                 {'part':2,'question':'Describe a memorable trip.','transcript':'We visited an ancient castle.','recording_id':'owned-mp4'},
                 {'part':3,'question':'Why do people travel?','transcript':'Travel brings people together.'}]
        aid = db.execute('''INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,transcript,feedback_json,band_score)
            VALUES(?,?,?,?,?,7)''', (user,mid,json.dumps(turns),'mountain ancient castle',json.dumps({'overall_band':7,'strengths':[],'improvements':[]}),)).lastrowid
        db.execute("INSERT INTO speaking_recordings VALUES('owned-audio',?,?,?,'audio/webm',?,CURRENT_TIMESTAMP)",
                   (user,mid,aid,b'0123456789audio'))
        db.execute("INSERT INTO speaking_recordings VALUES('owned-mp4',?,?,?,'audio/mp4',?,CURRENT_TIMESTAMP)",
                   (user,mid,aid,b'mp4-audio'))
        other_aid = db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'[]','{}',3)",(other,mid)).lastrowid
        db.execute("INSERT INTO speaking_recordings VALUES('other-audio',?,?,?,'audio/webm',?,CURRENT_TIMESTAMP)",
                   (other,mid,other_aid,b'private other audio'))
        db.commit()
    with client.session_transaction() as session:
        session['_user_id']=str(user)
        session['_fresh']=True
    client.get('/learn/speaking')
    with client.session_transaction() as session:
        csrf=session['learning_csrf']
    return dict(user=user,other=other,mock=mid,attempt=aid,other_attempt=other_aid,csrf=csrf)


def capture(app,client,path):
    contexts=[]
    def receiver(sender,template,context,**extra):contexts.append(context)
    with template_rendered.connected_to(receiver,app):response=client.get(path)
    assert response.status_code==200
    return response,contexts[-1]


def test_result_has_native_playback_transcripts_and_navigation(app,client,speaking):
    response,context=capture(app,client,f'/ai/results/{speaking["attempt"]}')
    review=context['speaking_review']
    assert review['audio_count']==2 and len(review['turns'])==3
    assert review['parts']==[1,2,3]
    assert response.data.count(b'<audio controls preload="none"')==2
    assert b'autoplay' not in response.data
    assert b'I live near a beautiful mountain.' in response.data
    assert b'Loop this answer' in response.data and b'Playback speed' in response.data
    assert b'Download recording' in response.data and b'Permanently delete recording' in response.data
    assert b'Audio was not saved for this older answer' in response.data
    assert client.get('/learn/speaking').status_code==200
    assert response.headers['Cache-Control']=='private, no-store'
    practice=client.get(f'/ai/speaking/{speaking["mock"]}')
    assert b'not stored as audio' not in practice.data and b'saved privately for playback' in practice.data


def test_download_range_mime_type_and_owner_authorization(client,speaking):
    response=client.get('/ai/recordings/owned-mp4?download=1')
    assert response.data==b'mp4-audio' and response.mimetype=='audio/mp4'
    assert 'attachment' in response.headers['Content-Disposition'] and '.m4a' in response.headers['Content-Disposition']
    assert response.headers['Cache-Control']=='private, no-store'
    response=client.get('/ai/recordings/owned-audio',headers={'Range':'bytes=0-3'})
    assert response.status_code==206 and response.data==b'0123'
    assert response.headers['Content-Range'].startswith('bytes 0-3/')
    assert client.get('/ai/recordings/other-audio?download=1').status_code==404
    with client.session_transaction() as session:session['_user_id']=str(speaking['other'])
    # Even an admin cannot read another student's private recordings.
    assert client.get('/ai/recordings/owned-audio').status_code==404
    assert client.get(f'/ai/results/{speaking["attempt"]}').status_code==404


def test_deleting_audio_requires_csrf_and_keeps_transcript_and_score(app,client,speaking):
    path='/learn/speaking/recordings/owned-audio/delete'
    assert client.post(path,data={'attempt_id':speaking['attempt']}).status_code==400
    assert client.post(path,data={'attempt_id':speaking['other_attempt'],'csrf_token':speaking['csrf']}).status_code==404
    response=client.post(path,data={'attempt_id':speaking['attempt'],'csrf_token':speaking['csrf']})
    assert response.status_code==302
    assert client.get('/ai/recordings/owned-audio').status_code==404
    response=client.get(f'/ai/results/{speaking["attempt"]}')
    assert b'Audio is no longer available for this answer' in response.data
    assert b'I live near a beautiful mountain.' in response.data
    assert b'/ai/recordings/owned-audio' not in response.data
    with app.app_context():
        attempt=get_db().execute('SELECT * FROM ai_attempts WHERE id=?',(speaking['attempt'],)).fetchone()
        assert attempt['band_score']==7 and json.loads(attempt['submission_text'])[0]['transcript'].startswith('I live')
        assert get_db().execute("SELECT COUNT(*) FROM speaking_recordings WHERE id='owned-mp4'").fetchone()[0]==1


def test_delete_cannot_target_another_users_recording(client,speaking):
    assert client.post('/learn/speaking/recordings/other-audio/delete',data={'attempt_id':speaking['other_attempt'],'csrf_token':speaking['csrf']}).status_code==404
    assert client.get('/ai/recordings/owned-audio').status_code==200


def test_history_search_audio_filters_and_pagination_are_private(app,client,speaking):
    with app.app_context():
        db=get_db()
        for _ in range(13):
            db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,transcript,feedback_json,band_score) VALUES(?,?,'[]','Literal 100% phrase','{}',5)",(speaking['user'],speaking['mock']))
        db.commit()
    _,data=capture(app,client,'/learn/speaking')
    assert data['total']==14 and len(data['attempts'])==12 and data['pages']==2
    _,data=capture(app,client,'/learn/speaking?audio=with')
    assert data['total']==1 and data['attempts'][0]['id']==speaking['attempt']
    _,data=capture(app,client,'/learn/speaking?audio=without&page=99')
    assert data['total']==13 and len(data['attempts'])==1 and data['page']==2
    response,data=capture(app,client,'/learn/speaking?q=100%25&audio=without')
    assert data['total']==13 and b'audio=without' in response.data and b'page=2' in response.data
    _,data=capture(app,client,'/learn/speaking?q=mountain')
    assert data['total']==1
    _,data=capture(app,client,'/learn/speaking?q=_')
    assert data['total']==0  # Search metacharacters are literal.
    _,data=capture(app,client,'/learn/speaking?audio=invalid&page=wrong')
    assert data['availability']=='all' and data['page']==1


def test_forged_or_mismatched_recording_references_do_not_render(app,client,speaking):
    with app.app_context():
        db=get_db()
        turns=[{'part':1,'question':'Forged link','transcript':'Only my text','recording_id':'other-audio'}]
        aid=db.execute('INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,?,\'{}\',6)',
                       (speaking['user'],speaking['mock'],json.dumps(turns))).lastrowid
        db.commit()
    response,data=capture(app,client,f'/ai/results/{aid}')
    assert data['speaking_review']['audio_count']==0 and b'/ai/recordings/other-audio' not in response.data
    assert b'Only my text' in response.data
    assert data['speaking_review']['neighbours']['older']==speaking['attempt']


def test_duplicate_audio_references_only_offer_one_answer_player(app,client,speaking):
    with app.app_context():
        db=get_db()
        turns=[{'part':1,'question':f'Question {i}','transcript':'Text','recording_id':'owned-audio'} for i in range(2)]
        db.execute('UPDATE ai_attempts SET submission_text=? WHERE id=?',(json.dumps(turns),speaking['attempt']));db.commit()
    response,data=capture(app,client,f'/ai/results/{speaking["attempt"]}')
    assert data['speaking_review']['audio_count']==1
    assert response.data.count(b'<audio controls preload="none"')==1


def test_older_unstructured_submission_still_shows_saved_transcript(app,client,speaking):
    with app.app_context():
        db=get_db()
        aid=db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,transcript,feedback_json,band_score) VALUES(?,?,'legacy answer','An older saved transcript.','{}',6)",
                       (speaking['user'],speaking['mock'])).lastrowid
        db.commit()
    response,data=capture(app,client,f'/ai/results/{aid}')
    assert b'An older saved transcript.' in response.data
    assert data['speaking_review']['audio_count']==0
    assert b'<audio' not in response.data
