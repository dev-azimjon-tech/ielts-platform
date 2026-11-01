"""Progress filters, denominators, comparisons, and private saved results."""
import json
from datetime import date, timedelta

import pytest
from flask import template_rendered

from app.database import get_db
from app.models import User
from app.seed import seed_demo_content


@pytest.fixture()
def students(app,client):
    with app.app_context():
        seed_demo_content()
        first=User.create('Progress','progress@example.com','unused').id
        second=User.create('Other','other@example.com','unused').id
    with client.session_transaction() as session:
        session['_user_id']=str(first)
        session['_fresh']=True
    return first,second


def capture_progress(app,client,path):
    contexts=[]
    def capture(sender,template,context,**extra):
        contexts.append(context)
    with template_rendered.connected_to(capture,app):
        response=client.get(path)
    assert response.status_code==200
    return response,contexts[-1]


def test_recent_comparison_filters_and_target_gap(app,client,students):
    today=date.today()
    with app.app_context():
        db=get_db()
        mid=db.execute("SELECT id FROM ai_mocks WHERE skill='writing' LIMIT 1").fetchone()[0]
        for i in range(10):
            db.execute('''INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score,completed_at)
              VALUES(?,?,'essay','{}',?,?)''',(students[0],mid,5 if i<5 else 7,(today-timedelta(days=40 if i<5 else 1)).isoformat()+' 12:00:00'))
        db.execute('INSERT INTO study_plans VALUES(?,?,?,?)',(students[0],8,(today+timedelta(days=50)).isoformat(),30))
        db.commit()
    response,data=capture_progress(app,client,'/learn/progress?skill=writing')
    stat=data['stats'][0]
    assert stat['average']==7 and stat['change']==2 and stat['gap']==1 and stat['count']==10
    assert b'previous five' in response.data
    assert len(data['series'])==1 and data['series'][0]['skill']=='writing'
    _,data=capture_progress(app,client,'/learn/progress?skill=writing&period=30')
    assert data['stats'][0]['count']==5 and data['stats'][0]['change'] is None
    assert data['total']==5
    _,data=capture_progress(app,client,'/learn/progress?skill=reading&period=30')
    assert data['total']==0 and data['accuracy']==[]


def test_question_accuracy_uses_latest_distinct_answers_and_keeps_blanks(app,client,students):
    with app.app_context():
        db=get_db()
        questions=db.execute("SELECT q.* FROM questions q JOIN mock_tests m ON m.id=q.mock_id WHERE m.skill='reading' ORDER BY q.id LIMIT 2").fetchall()
        first,second=questions
        for uid,answers in [(students[0],{str(first['id']):'incorrect'}),
                            (students[0],{str(first['id']):first['correct_answer'],str(second['id']):''}),
                            (students[1],{str(first['id']):'other user wrong'})]:
            db.execute('INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,0,2,?)',
                       (uid,first['mock_id'],json.dumps(answers)))
        db.commit()
    response,data=capture_progress(app,client,'/learn/progress?skill=reading')
    assert sum(group['total'] for group in data['accuracy'])==2
    assert sum(group['correct'] for group in data['accuracy'])==1
    assert sum(group['missed'] for group in data['accuracy'])==1
    assert b'Review mistakes' in response.data
    _,data=capture_progress(app,client,'/learn/progress?skill=speaking')
    assert data['accuracy']==[]


def test_criteria_ignore_missing_invalid_values_and_other_users(app,client,students):
    with app.app_context():
        db=get_db()
        mid=db.execute("SELECT id FROM ai_mocks WHERE skill='speaking' LIMIT 1").fetchone()[0]
        for uid,feedback in [(students[0],{'grammar_band':6,'fluency_band':7}),
                             (students[0],{'grammar_band':8,'fluency_band':True,'lexical_band':99}),
                             (students[1],{'grammar_band':1,'fluency_band':1})]:
            db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'[]',?,7)",(uid,mid,json.dumps(feedback)))
        db.commit()
    response,data=capture_progress(app,client,'/learn/progress?skill=speaking')
    criteria={item['label']:item for item in data['criteria'][0]['criteria']}
    assert criteria['Grammar']['average']==7 and criteria['Grammar']['count']==2
    assert criteria['Fluency']['average']==7 and criteria['Fluency']['count']==1
    assert 'Vocabulary' not in criteria
    assert b'2 attempts' in response.data
    assert b'/ai/results/' in response.data


def test_history_pagination_and_invalid_filters(app,client,students):
    with app.app_context():
        db=get_db()
        mid=db.execute("SELECT id FROM mock_tests WHERE skill='reading' LIMIT 1").fetchone()[0]
        for _ in range(23):
            db.execute("INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,20,40,'{}')",(students[0],mid))
        db.commit()
    response,data=capture_progress(app,client,'/learn/progress?skill=reading&period=30')
    assert len(data['rows'])==20 and data['pages']==2
    assert b'period=30' in response.data and b'page=2' in response.data
    _,second=capture_progress(app,client,'/learn/progress?skill=reading&period=30&page=9999')
    assert len(second['rows'])==3 and second['page']==2
    assert {r['id'] for r in data['rows']}.isdisjoint({r['id'] for r in second['rows']})
    assert len(data['series'][0]['points'])==23
    assert b'viewBox="0 0 620 202"' in response.data
    _,fallback=capture_progress(app,client,'/learn/progress?skill=invalid&period=-1&page=wrong')
    assert fallback['skill']=='all' and fallback['period']=='all' and fallback['page']==1
    with client.session_transaction() as session:
        session['_user_id']=str(students[1])
    _,private=capture_progress(app,client,'/learn/progress')
    assert private['total']==0 and all(not s['points'] for s in private['series'])


def test_non_object_or_invalid_legacy_feedback_does_not_break_progress(app,client,students):
    with app.app_context():
        db=get_db()
        mid=db.execute("SELECT id FROM ai_mocks WHERE skill='speaking' LIMIT 1").fetchone()[0]
        for feedback in ('[]','"old feedback"','{invalid', '{"grammar_band": 6.5}'):
            db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'[]',?,6)",
                       (students[0],mid,feedback))
        db.commit()
    _,data=capture_progress(app,client,'/learn/progress?skill=speaking')
    assert data['total']==4
    assert data['criteria'][0]['criteria']==[{'label':'Grammar','average':6.5,'count':1}]


def test_invalid_legacy_bands_cannot_poison_summaries_or_plans(app):
    from app.progress_analytics import summarize, trend_series
    from app.study_planner import skill_gaps
    valid=dict(skill='writing',band=6.5,kind='ai',id=1,completed_at='2026-10-30 12:00:00')
    rows=[valid,*[{**valid,'band':bad} for bad in (float('inf'),float('nan'),-1,10,True,'7')]]
    with app.test_request_context():
        summary=next(s for s in summarize(rows,7) if s['skill']=='writing')
        assert summary['count']==1 and summary['average']==6.5
        chart=trend_series(rows,'writing')[0]
        assert len(chart['points'])==1 and chart['points'][0]['y']>0
        gap=next(s for s in skill_gaps(rows,7) if s['skill']=='writing')
        assert gap['count']==1 and gap['average']==6.5


def test_question_accuracy_uses_frozen_submitted_questions_after_admin_changes(app,client,students):
    with app.app_context():
        db=get_db()
        q=dict(db.execute("SELECT q.* FROM questions q JOIN mock_tests m ON m.id=q.mock_id WHERE m.skill='reading' LIMIT 1").fetchone())
        answers={str(q['id']):q['correct_answer']}
        aid=db.execute('INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,1,1,?)',
                       (students[0],q['mock_id'],json.dumps(answers))).lastrowid
        snapshot={**q,'options':json.loads(q['options_json'] or '[]'),
                  'submitted_answer':q['correct_answer'],'is_correct':True}
        db.execute('INSERT INTO attempt_snapshots(attempt_id,questions_json) VALUES(?,?)',(aid,json.dumps([snapshot])))
        db.execute("UPDATE questions SET correct_answer='changed by admin',question_type='new_type' WHERE id=?",(q['id'],))
        db.commit()
    _,data=capture_progress(app,client,'/learn/progress?skill=reading')
    assert data['accuracy']==[{'skill':'reading','kind':q['question_type'],'correct':1,'total':1,'accuracy':100,'missed':0}]
    with app.app_context():
        get_db().execute('DELETE FROM questions WHERE id=?',(q['id'],));get_db().commit()
    _,data=capture_progress(app,client,'/learn/progress?skill=reading')
    assert data['accuracy'][0]['correct']==1 and data['accuracy'][0]['kind']==q['question_type']
