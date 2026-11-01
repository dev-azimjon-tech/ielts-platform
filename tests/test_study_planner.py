"""Study recommendations must respect budgets and keep ongoing sessions stable."""
from datetime import date, timedelta
import json

from app.database import get_db
from app.models import User
from app.study_planner import build_day, planning_context, skill_gaps


def test_day_budget_and_final_week_adjustment(app):
    day = date(2026, 11, 2)
    rows = [{'skill': skill, 'band': band} for skill, band in
            [('listening', 7), ('reading', 5), ('writing', 6), ('speaking', 6.5)]]
    gaps = skill_gaps(rows, 7)
    with app.test_request_context():
        for minutes in (10, 30, 45, 240):
            settings = {'target_band': 7, 'daily_minutes': minutes,
                        'exam_date': (day + timedelta(days=60)).isoformat()}
            early = build_day(day, settings, gaps, {'due': 0, 'total': 0}, 0)
            settings['exam_date'] = (day + timedelta(days=3)).isoformat()
            late = build_day(day, settings, gaps, {'due': 5, 'total': 5}, 2)
            for daily in (early, late):
                assert sum(task['minutes'] for task in daily['tasks']) == minutes
                assert all(task['minutes'] > 0 for task in daily['tasks'])
            assert late['tasks'][0]['minutes'] >= early['tasks'][0]['minutes']
            assert late['phase'] == 'Final review'
            assert early['tasks'][0]['url'].endswith('/flashcards/')
            assert late['tasks'][0]['url'].endswith('/learn/review')
        settings['exam_date'] = day.isoformat()
        exam_day = build_day(day, settings, gaps, {'due': 0, 'total': 0}, 0)
        assert exam_day['phase'] == 'Exam day'
        assert 'warm-up' in exam_day['tasks'][2]['title']


def test_recent_five_scores_determine_target_gap_and_priority(app):
    # This date is a priority day, rather than the every-third-day rotation.
    day = next(date(2026, 11, d) for d in range(1, 10) if date(2026, 11, d).toordinal() % 3)
    rows = [{'skill': 'reading', 'band': 1}] * 10
    rows += [{'skill': 'reading', 'band': 8}] * 5
    rows += [{'skill': skill, 'band': band} for skill, band in
             [('listening', 7), ('writing', 5), ('speaking', 6.5)]]
    gaps = skill_gaps(rows, 7)
    assert next(item for item in gaps if item['skill'] == 'reading')['average'] == 8
    with app.test_request_context():
        result = build_day(day, {'target_band': 7, 'daily_minutes': 30, 'exam_date': None},
                           gaps, {'due': 0, 'total': 0}, 0)
        assert result['focus'] == 'writing'
        assert '5.0' in result['tasks'][2]['reason']
        assert 'target band is 7' in result['tasks'][2]['reason']


def test_daily_snapshot_stays_fixed_and_week_stops_at_exam(app):
    today = date.today()
    with app.test_request_context():
        student = User.create('Planner', 'planner@example.com', 'unused')
        db = get_db()
        db.execute('INSERT INTO study_plans VALUES(?,?,?,?)',
                   (student.id, 7, (today + timedelta(days=2)).isoformat(), 30))
        db.commit()
        first = planning_context(student.id, [], 0, today)
        assert len(first['week']) == 3
        assert first['week'][-1]['phase'] == 'Exam day'
        changed = planning_context(student.id, [{'skill': 'writing', 'band': 1}], 50, today)
        assert changed['daily'] == first['daily']
        assert changed['gaps'] != first['gaps']
        tomorrow = planning_context(student.id, [], 0, today + timedelta(days=1))
        assert tomorrow['daily']['date'] != first['daily']['date']


def test_goal_changes_preserve_started_session_and_undo_is_private(app, client):
    with app.app_context():
        one = User.create('One', 'one@example.com', 'unused').id
        two = User.create('Two', 'two@example.com', 'unused').id
    with client.session_transaction() as session:
        session['_user_id'] = str(one)
        session['_fresh'] = True
    assert client.get('/learn/plan').status_code == 200
    with client.session_transaction() as session:
        token = session['learning_csrf']
    def post(data):
        return client.post('/learn/plan', data={'csrf_token': token, **data})
    post({'task_key': 'practice'})
    post({'target_band': '8', 'exam_date': (date.today() + timedelta(days=30)).isoformat(), 'daily_minutes': '60'})
    with app.app_context():
        db = get_db()
        saved = db.execute('SELECT * FROM study_plans WHERE user_id=?', (one,)).fetchone()
        daily = json.loads(db.execute('SELECT plan_json FROM study_days WHERE user_id=?', (one,)).fetchone()[0])
        assert saved['daily_minutes'] == 60
        assert daily['minutes'] == 30
        assert db.execute('SELECT COUNT(*) FROM study_tasks WHERE user_id=?', (one,)).fetchone()[0] == 1
    with client.session_transaction() as session:
        session['_user_id'] = str(two)
    post({'task_key': 'practice', 'action': 'undo'})
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM study_tasks WHERE user_id=?', (one,)).fetchone()[0] == 1
    with client.session_transaction() as session:
        session['_user_id'] = str(one)
    post({'task_key': 'practice', 'action': 'undo'})
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM study_tasks WHERE user_id=?', (one,)).fetchone()[0] == 0
    assert post({'task_key': 'invented'}).status_code == 400


def test_plan_destination_uses_free_review_when_checks_run_out(app):
    from app.seed import seed_demo_content
    from app.study_planner import practice_destination
    with app.test_request_context():
        seed_demo_content()
        user=User.create('Budget planner','budget-planner@example.com','unused').id
        other=User.create('Another planner','another-planner@example.com','unused').id
        db=get_db()
        writing=db.execute("SELECT id FROM ai_mocks WHERE skill='writing' LIMIT 1").fetchone()[0]
        speaking=db.execute("SELECT id FROM ai_mocks WHERE skill='speaking' LIMIT 1").fetchone()[0]
        reading=db.execute("SELECT id FROM mock_tests WHERE skill='reading' LIMIT 1").fetchone()[0]
        assert practice_destination(user,'writing').endswith('/ai/')
        writing_attempt=db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'essay','{}',6)",(user,writing)).lastrowid
        db.execute("INSERT INTO writing_revisions(attempt_id,essay,feedback_json,band_score) VALUES(?,'revised essay','{}',7)",(writing_attempt,))
        for _ in range(2):
            speaking_attempt=db.execute("INSERT INTO ai_attempts(user_id,ai_mock_id,submission_text,feedback_json,band_score) VALUES(?,?,'[]','{}',6)",(user,speaking)).lastrowid
        for _ in range(10):
            reading_attempt=db.execute("INSERT INTO attempts(user_id,mock_id,score,total_points,answers_json) VALUES(?,?,1,2,'{}')",(user,reading)).lastrowid
        db.commit()
        assert practice_destination(user,'writing').endswith(f'/learn/writing/{writing_attempt}/revise')
        assert practice_destination(user,'speaking').endswith(f'/ai/results/{speaking_attempt}')
        assert practice_destination(user,'reading').endswith(f'/learn/results/{reading_attempt}')
        assert practice_destination(other,'writing').endswith('/ai/')
        db.execute('UPDATE users SET is_premium=1 WHERE id=?',(user,));db.commit()
        assert practice_destination(user,'reading').endswith('/mocks/?skill=reading')
        assert practice_destination(user,'writing').endswith('/ai/')


def test_existing_daily_snapshot_gets_safe_action_without_replacing_tasks(app):
    with app.test_request_context():
        user=User.create('Legacy planner','legacy-planner@example.com','unused').id
        first=planning_context(user,[],0)
        original=json.loads(json.dumps(first['daily']))
        old=json.loads(json.dumps(original))
        next(t for t in old['tasks'] if t['key']=='practice')['url']='/ai/'
        get_db().execute('UPDATE study_days SET plan_json=? WHERE user_id=? AND task_date=?',
                         (json.dumps(old),user,date.today().isoformat()))
        get_db().commit()
        upgraded=planning_context(user,[],0)['daily']
        assert upgraded==original
        assert next(t for t in upgraded['tasks'] if t['key']=='practice')['url'].startswith('/learn/practice/')
