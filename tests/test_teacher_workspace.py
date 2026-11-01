"""Hand-ins, reviews, class actions, and revocable teacher access."""
import json
from datetime import date, timedelta

import pytest
from flask import template_rendered

from app.database import get_db
from app.models import User
from app.seed import seed_demo_content


@pytest.fixture()
def classroom(app,client):
    with app.app_context():
        seed_demo_content()
        ids={name:User.create(name,f'{name.lower()}@example.com','unused').id for name in ('Teacher','Learner','Second','Stranger')}
        db=get_db()
        db.execute("INSERT INTO teacher_profiles VALUES(?,'class-code')",(ids['Teacher'],))
        for name in ('Learner','Second'):
            db.execute('INSERT INTO teacher_students VALUES(?,?)',(ids['Teacher'],ids[name]))
        reading=db.execute("SELECT id FROM mock_tests WHERE skill='reading' LIMIT 1").fetchone()[0]
        writing=db.execute("SELECT id FROM ai_mocks WHERE skill='writing' LIMIT 1").fetchone()[0]
        speaking=db.execute("SELECT id FROM ai_mocks WHERE skill='speaking' LIMIT 1").fetchone()[0]
        db.commit()
    switch(client,ids['Teacher'])
    client.get('/learn/teachers')
    with client.session_transaction() as session:token=session['learning_csrf']
    return {**ids,'reading':reading,'writing':writing,'speaking':speaking,'csrf':token}


def switch(client,user):
    with client.session_transaction() as session:
        session['_user_id']=str(user)
        session['_fresh']=True


def post(client,classroom,path,**data):
    return client.post(path,data={'csrf_token':classroom['csrf'],**data})


def assign(app,client,c,kind='mock',mock=None):
    mock=mock or c['reading']
    response=post(client,c,f'/learn/students/{c["Learner"]}',mock=f'{kind}:{mock}',due_on=date.today().isoformat(),note='Explain your reasoning.')
    assert response.status_code==302
    with app.app_context():return get_db().execute('SELECT MAX(id) FROM assignments').fetchone()[0]


def result(app,c,kind='mock',mock=None,user=None,essay='A private response.'):
    with app.app_context():
        db=get_db()
        if kind=='mock':
            aid=db.execute("INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,1,2,'{}')",(user or c['Learner'],mock or c['reading'])).lastrowid
        else:
            aid=db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,?,'{}',6.5)",(user or c['Learner'],mock or c['writing'],essay)).lastrowid
        db.commit()
        return aid


def capture(app,client,path):
    contexts=[]
    def receiver(sender,template,context,**extra):contexts.append(context)
    with template_rendered.connected_to(receiver,app):response=client.get(path)
    assert response.status_code==200
    return response,contexts[-1]


def test_explicit_handin_does_not_share_unsubmitted_essays(app,client,classroom):
    c=classroom
    assignment=assign(app,client,c,'ai',c['writing'])
    aid=result(app,c,'ai',essay='My deliberately private unsubmitted essay.')
    response,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['submission'] is None and b'deliberately private' not in response.data
    switch(client,c['Learner'])
    response,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert len(data['candidates'])==1 and b'Hand in result' in response.data
    assert post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=aid).status_code==302
    switch(client,c['Teacher'])
    response,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['status']=='submitted'
    assert b'My deliberately private unsubmitted essay.' in response.data
    assert response.headers['Cache-Control']=='private, no-store'


def test_review_and_resubmission_reject_stale_feedback(app,client,classroom):
    c=classroom;assignment=assign(app,client,c)
    first=result(app,c)
    switch(client,c['Learner'])
    post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=first)
    switch(client,c['Teacher'])
    post(client,c,f'/learn/assignments/{assignment}',action='review',submission_version=1,comment='Good start. Explain the last answer.')
    switch(client,c['Learner'])
    response,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['status']=='reviewed' and b'Good start.' in response.data
    # Repeating the same hand-in does not clear a completed review.
    post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=first)
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['version']==1 and data['assignment']['status']=='reviewed'
    second=result(app,c)
    post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=second)
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['status']=='submitted' and data['assignment']['earlier_feedback']
    switch(client,c['Teacher'])
    stale=post(client,c,f'/learn/assignments/{assignment}',action='review',submission_version=1,comment='Stale feedback')
    assert stale.status_code==409 and b'Stale feedback' in stale.data
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['comment']=='Good start. Explain the last answer.' and data['assignment']['status']=='submitted'
    post(client,c,f'/learn/assignments/{assignment}',action='review',submission_version=2,comment='Your new result is clearer.')
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['status']=='reviewed'


def test_ownership_csrf_and_revocation_apply_to_all_assignment_actions(app,client,classroom):
    c=classroom;assignment=assign(app,client,c)
    switch(client,c['Stranger'])
    assert client.get(f'/learn/assignments/{assignment}').status_code==404
    assert post(client,c,f'/learn/assignments/{assignment}',action='cancel').status_code==404
    switch(client,c['Learner'])
    assert post(client,c,f'/learn/assignments/{assignment}',action='review',comment='Pretend to be teacher').status_code==403
    assert client.post(f'/learn/assignments/{assignment}',data={'action':'submit'}).status_code==400
    post(client,c,'/learn/teachers',action='leave',teacher_id=c['Teacher'])
    switch(client,c['Teacher'])
    assert client.get(f'/learn/students/{c["Learner"]}').status_code==404
    assert client.get(f'/learn/assignments/{assignment}').status_code==404
    assert post(client,c,f'/learn/assignments/{assignment}',action='review',comment='No longer authorised').status_code==404


def test_existing_wrong_mock_and_other_users_attempts_cannot_be_handed_in(app,client,classroom):
    c=classroom
    previous=result(app,c)
    assignment=assign(app,client,c)
    other=result(app,c,user=c['Second'])
    with app.app_context():
        wrong_mock=get_db().execute("SELECT id FROM mock_tests WHERE skill='reading' AND id!=? LIMIT 1",(c['reading'],)).fetchone()[0]
    wrong=result(app,c,mock=wrong_mock)
    switch(client,c['Learner'])
    for aid in (previous,other,wrong):
        assert post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=aid).status_code==400
    # An unknown result cannot be handed in either.
    with app.app_context():
        maximum=get_db().execute('SELECT COALESCE(MAX(id),0) FROM attempts').fetchone()[0]
    assert post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=maximum+100).status_code==400
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['candidates']==[]


def test_batch_assignment_is_atomic_and_overdue_cancel_restore_states(app,client,classroom):
    c=classroom
    response=post(client,c,'/learn/teacher/assign',student_ids=[c['Learner'],c['Stranger']],mock=f'mock:{c["reading"]}',due_on=date.today().isoformat())
    assert response.status_code==404
    with app.app_context():assert get_db().execute('SELECT COUNT(*) FROM assignments').fetchone()[0]==0
    response=post(client,c,'/learn/teacher/assign',student_ids=[c['Learner'],c['Second']],mock=f'mock:{c["reading"]}',due_on=date.today().isoformat())
    assert response.status_code==302
    with app.app_context():
        db=get_db();assert db.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]==2
        assignment=db.execute('SELECT id FROM assignments WHERE student_id=?',(c['Learner'],)).fetchone()[0]
        db.execute('UPDATE assignments SET due_on=? WHERE id=?',((date.today()-timedelta(days=1)).isoformat(),assignment));db.commit()
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['status']=='overdue'
    post(client,c,f'/learn/assignments/{assignment}',action='cancel')
    switch(client,c['Learner'])
    assert client.get(f'/learn/assignments/{assignment}/start').status_code==302
    assert post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=123).status_code==400
    switch(client,c['Teacher'])
    post(client,c,f'/learn/assignments/{assignment}',action='restore')
    post(client,c,f'/learn/assignments/{assignment}',action='update',due_on=(date.today()+timedelta(days=2)).isoformat(),note='Updated instructions')
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['status']=='pending' and data['assignment']['note']=='Updated instructions'


def test_rotating_invitation_does_not_remove_connected_students(app,client,classroom):
    c=classroom
    post(client,c,'/learn/teachers',action='rotate')
    with app.app_context():
        db=get_db();new_code=db.execute('SELECT invite_code FROM teacher_profiles WHERE user_id=?',(c['Teacher'],)).fetchone()[0]
        assert new_code!='class-code'
        assert db.execute('SELECT COUNT(*) FROM teacher_students WHERE teacher_id=?',(c['Teacher'],)).fetchone()[0]==2
    switch(client,c['Stranger'])
    post(client,c,'/learn/teachers',action='join',code='class-code')
    with app.app_context():assert get_db().execute('SELECT 1 FROM teacher_students WHERE teacher_id=? AND student_id=?',(c['Teacher'],c['Stranger'])).fetchone() is None
    post(client,c,'/learn/teachers',action='join',code=new_code)
    switch(client,c['Teacher'])
    assert client.get(f'/learn/students/{c["Stranger"]}').status_code==200


def test_teacher_cannot_listen_to_private_speaking_audio(app,client,classroom):
    c=classroom;assignment=assign(app,client,c,'ai',c['speaking'])
    turns=[{'part':1,'question':'Where do you live?','transcript':'I live near a river.','recording_id':'student-private-audio'}]
    aid=result(app,c,'ai',c['speaking'],essay=json.dumps(turns))
    with app.app_context():
        db=get_db();db.execute("INSERT INTO speaking_recordings VALUES('student-private-audio',?,?,?,'audio/webm',?,CURRENT_TIMESTAMP)",(c['Learner'],c['speaking'],aid,b'voice'));db.commit()
    switch(client,c['Learner'])
    post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=aid)
    switch(client,c['Teacher'])
    response,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert b'I live near a river.' in response.data and b'Where do you live?' in response.data
    assert b'student-private-audio' not in response.data and b'<audio' not in response.data
    assert client.get('/ai/recordings/student-private-audio').status_code==404


def test_assignment_filters_class_counts_and_roster_pagination(app,client,classroom):
    c=classroom
    post(client,c,'/learn/teacher/assign',student_ids=[c['Learner'],c['Second']],mock=f'mock:{c["reading"]}',due_on=date.today().isoformat())
    with app.app_context():
        db=get_db();assignment=db.execute('SELECT id FROM assignments WHERE student_id=?',(c['Learner'],)).fetchone()[0]
        for i in range(12):
            user=User.create(f'Extra {i:02}',f'extra-{i}@example.com','unused').id
            db.execute('INSERT INTO teacher_students VALUES(?,?)',(c['Teacher'],user))
        db.commit()
    aid=result(app,c)
    switch(client,c['Learner'])
    post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=aid)
    switch(client,c['Teacher'])
    response,data=capture(app,client,'/learn/teachers?status=submitted')
    assert data['counts']['submitted']==1 and data['counts']['pending']==1
    assert len(data['teaching'])==1 and data['teaching'][0]['student_id']==c['Learner']
    assert len(data['students'])==12 and data['roster_pages']['pages']==2
    assert b'status=submitted' in response.data and b'students_page=2' in response.data
    _,data=capture(app,client,'/learn/teachers?students_page=9999')
    assert len(data['students'])==2 and data['roster_pages']['page']==2
    _,data=capture(app,client,'/learn/teachers?q=Second')
    assert len(data['students'])==1 and data['students'][0]['id']==c['Second']


def test_batch_creation_retry_is_idempotent_and_stale_handin_is_safe(app,client,classroom):
    c=classroom
    request_data=dict(student_ids=[c['Learner'],c['Second']],mock=f'mock:{c["reading"]}',due_on=date.today().isoformat(),request_token='unique_batch_request_token_123')
    assert post(client,c,'/learn/teacher/assign',**request_data).status_code==302
    assert post(client,c,'/learn/teacher/assign',**request_data).status_code==302
    with app.app_context():
        db=get_db();assert db.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]==2
        assignment=db.execute('SELECT id FROM assignments WHERE student_id=?',(c['Learner'],)).fetchone()[0]
    first=result(app,c);second=result(app,c)
    switch(client,c['Learner'])
    post(client,c,f'/learn/assignments/{assignment}',action='submit',submission_version=0,attempt_id=second)
    post(client,c,f'/learn/assignments/{assignment}',action='submit',submission_version=0,attempt_id=first)
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['attempt_id']==second and data['assignment']['version']==1


def test_malformed_submission_versions_do_not_bypass_conflict_protection(app,client,classroom):
    c=classroom;assignment=assign(app,client,c)
    first=result(app,c);second=result(app,c)
    switch(client,c['Learner'])
    post(client,c,f'/learn/assignments/{assignment}',action='submit',submission_version=0,attempt_id=first)
    for malformed in ('invalid','', '-1'):
        response=post(client,c,f'/learn/assignments/{assignment}',action='submit',submission_version=malformed,attempt_id=second)
        assert response.status_code==400
    switch(client,c['Teacher'])
    post(client,c,f'/learn/assignments/{assignment}',action='review',submission_version=1,comment='Keep this feedback.')
    for malformed in ('invalid','', '-1'):
        response=post(client,c,f'/learn/assignments/{assignment}',action='review',submission_version=malformed,comment='Do not save malformed feedback.')
        assert response.status_code==400
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert data['assignment']['attempt_id']==first and data['assignment']['version']==1
    assert data['assignment']['comment']=='Keep this feedback.'


def test_review_requires_a_real_handed_in_result(app,client,classroom):
    c=classroom;assignment=assign(app,client,c)
    response=post(client,c,f'/learn/assignments/{assignment}',action='review',submission_version=0,comment='There is no result yet.')
    assert response.status_code==400
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM teacher_comments WHERE assignment_id=?',(assignment,)).fetchone()[0]==0
    aid=result(app,c)
    switch(client,c['Learner'])
    post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=aid)
    with app.app_context():
        db=get_db();db.execute('DELETE FROM attempts WHERE id=?',(aid,));db.commit()
    switch(client,c['Teacher'])
    assert post(client,c,f'/learn/assignments/{assignment}',action='review',submission_version=1,comment='Deleted result').status_code==400


def test_handin_chooser_loads_metadata_without_private_essay_bodies(app,client,classroom):
    c=classroom;assignment=assign(app,client,c,'ai',c['writing'])
    result(app,c,'ai',essay='A long unfinished response. '*1000)
    switch(client,c['Learner'])
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    assert len(data['candidates'])==1
    assert set(data['candidates'][0].keys())=={'id','completed_at','band_score'}


def test_roster_attempt_counts_include_both_skills_without_other_users(app,client,classroom):
    c=classroom
    result(app,c);result(app,c,'ai')
    result(app,c,user=c['Second'])
    for _ in range(3):result(app,c,user=c['Stranger'])
    _,data=capture(app,client,'/learn/teachers')
    counts={student['id']:student['attempts'] for student in data['students']}
    assert counts=={c['Learner']:2,c['Second']:1}


def test_teacher_review_preserves_questions_and_answers_from_submission(app,client,classroom):
    c=classroom;assignment=assign(app,client,c)
    with app.app_context():
        original=dict(get_db().execute('SELECT * FROM questions WHERE mock_id=? ORDER BY question_number LIMIT 1',(c['reading'],)).fetchone())
    switch(client,c['Learner'])
    with client.session_transaction() as session:app_csrf=session['app_csrf_token']
    response=client.post(f'/mocks/{c["reading"]}/submit',data={f'question_{original["id"]}':original['correct_answer']},headers={'X-CSRF-Token':app_csrf})
    assert response.status_code==200
    with app.app_context():
        db=get_db();aid=db.execute('SELECT MAX(id) FROM attempts WHERE user_id=?',(c['Learner'],)).fetchone()[0]
        assert db.execute('SELECT 1 FROM attempt_snapshots WHERE attempt_id=?',(aid,)).fetchone()
        db.execute("UPDATE questions SET prompt='Edited after submission',correct_answer='changed',explanation='New explanation' WHERE id=?",(original['id'],))
        db.commit()
    post(client,c,f'/learn/assignments/{assignment}',action='submit',attempt_id=aid)
    switch(client,c['Teacher'])
    _,data=capture(app,client,f'/learn/assignments/{assignment}')
    question=next(q for q in data['submission']['review'] if q['id']==original['id'])
    assert question['prompt']==original['prompt'] and question['explanation']==original['explanation']
    assert question['answer']==original['correct_answer'] and question['correct'] is True
