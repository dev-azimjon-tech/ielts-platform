"""Private study tools and consent-based teacher relationships."""
import json
import math
import secrets
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from .database import get_db
from .main import _estimated_band
from .mocks import _normalise_answer

learning_bp = Blueprint('learning', __name__, url_prefix='/learn')
SKILLS = ('listening', 'reading', 'writing', 'speaking')

@learning_bp.app_context_processor
def context():
    if 'learning_csrf' not in session:
        session['learning_csrf'] = secrets.token_urlsafe(32)
    return {'learning_csrf': session['learning_csrf']}

@learning_bp.before_request
def protect():
    if request.method == 'POST':
        expected = session.get('learning_csrf', '')
        if not expected or not secrets.compare_digest((request.headers.get('X-CSRF-Token', '') if request.is_json else request.form.get('csrf_token', '')).encode(), expected.encode()):
            abort(400, 'Refresh this page and try again.')

def history(user_id):
    rows = get_db().execute('''SELECT a.id, m.title, m.skill, a.score, a.total_points, a.completed_at, 'mock' AS kind
        FROM attempts a JOIN mock_tests m ON a.mock_id=m.id WHERE a.user_id=?
        UNION ALL SELECT a.id, m.title, m.skill, a.band_score, 9, a.completed_at, 'ai'
        FROM ai_attempts a JOIN ai_mocks m ON a.ai_mock_id=m.id WHERE a.user_id=?
        ORDER BY 6, 1''', (user_id,user_id)).fetchall()
    return [{**dict(r), 'band': float(r['score']) if r['kind']=='ai' else _estimated_band(r['score'],r['total_points'],r['skill'])} for r in rows]

def mistakes(user_id):
    from .mock_results import load_attempt_questions, load_question_snapshots
    db = get_db()
    latest = {}
    attempts = db.execute('''SELECT a.*,m.skill,m.title FROM attempts a JOIN mock_tests m ON m.id=a.mock_id
        WHERE a.user_id=? ORDER BY a.completed_at,a.id''',(user_id,)).fetchall()
    snapshots = load_question_snapshots(attempts)
    for attempt in attempts:
        try:
            answered = json.loads(attempt['answers_json'])
        except (ValueError,TypeError):
            continue
        if not isinstance(answered,dict):
            continue
        for question in load_attempt_questions(attempt,snapshots=snapshots):
            if str(question['id']) not in answered:
                continue
            latest[question['id']] = {**question,'mock_id':attempt['mock_id'],'skill':attempt['skill'],
                                      'title':attempt['title'],'source_attempt_id':attempt['id'],
                                      'source_completed_at':attempt['completed_at']}
    reviews = {(row['attempt_id'],row['question_id']): row for row in db.execute(
        'SELECT * FROM mistake_retries WHERE user_id=?',(user_id,))}
    legacy = {row['question_id']:row for row in db.execute('SELECT * FROM mistake_reviews WHERE user_id=?',(user_id,))}
    items = []
    for question in latest.values():
        if question['is_correct']:
            continue
        review = reviews.get((question['source_attempt_id'],question['id']))
        older = legacy.get(question['id'])
        if review is None and older and older['reviewed_at'] > question['source_completed_at']:
            review = older
        items.append({**question,'answer':question['submitted_answer'],'review':review})
    return sorted(items,key=lambda q:(q['skill'],q['title'],q['question_number']))

@learning_bp.route('/')
@login_required
def index():
    return render_template('learning/index.html')

@learning_bp.route('/mistakes', methods=['GET','POST'])
@login_required
def notebook():
    items = mistakes(current_user.id)
    if request.method == 'POST':
        qid = request.form.get('question_id', type=int)
        q = next((q for q in items if q['id']==qid), None)
        if q is None: abort(404)
        source = request.form.get('attempt_id',q['source_attempt_id'],type=int)
        if source != q['source_attempt_id']:
            abort(409, 'A newer mock result replaced this review. Reload the notebook and try again.')
        answer = request.form.get('answer','').strip()
        if len(answer)>2000:
            abort(400, 'Keep your answer below 2,000 characters.')
        correct = _normalise_answer(answer)==_normalise_answer(q['correct_answer'])
        get_db().execute('''INSERT INTO mistake_retries(user_id,attempt_id,question_id,answer,is_correct) VALUES(?,?,?,?,?)
          ON CONFLICT(user_id,attempt_id,question_id) DO UPDATE SET answer=excluded.answer,is_correct=excluded.is_correct,reviewed_at=CURRENT_TIMESTAMP''', (current_user.id,q['source_attempt_id'],qid,answer,int(correct)))
        get_db().commit()
        flash('Correct — this question is marked practised.' if correct else 'Try again, then open the explanation for help.', 'success' if correct else 'info')
        return redirect(url_for('learning.notebook', skill=request.form.get('skill','all')))
    skill=request.args.get('skill','all')
    filtered=[q for q in items if skill=='all' or q['skill']==skill]
    return render_template('learning/mistakes.html', items=filtered, skill=skill)

@learning_bp.route('/review', methods=['GET', 'POST'])
@login_required
def review():
    from .vocabulary_review import rating_options, review_summary

    db = get_db()
    today = date.today()
    cursor_key = f"vocabulary_review_cursor:{current_user.id}"
    if request.method == 'POST':
        word_id = request.form.get('word_id', type=int)
        rating = request.form.get('rating')
        if rating not in ('again', 'good', 'easy'):
            abort(400)
        from .vocabulary_review import record_rating
        result = record_rating(current_user.id, word_id, rating, today)
        if result is None:
            abort(404)
        if result['status'] == 'already_scheduled':
            flash('This card is already scheduled for a later day.', 'info')
        else:
            session[cursor_key] = word_id
            flash('Card will return after the other due cards.' if rating == 'again'
                  else f"Next review: {result['due_on']}.", 'info' if rating == 'again' else 'success')
        return redirect(url_for('learning.review'))

    # Cycle through due cards so an Again rating cannot trap the learner on one card.
    word = db.execute(
        """SELECT w.*, s.interval_days, s.due_on FROM vocabulary_words w
        LEFT JOIN vocabulary_schedule s ON s.word_id = w.id
        WHERE w.user_id = ? AND (s.due_on IS NULL OR s.due_on <= ?)
        ORDER BY CASE WHEN w.id > ? THEN 0 ELSE 1 END, w.id LIMIT 1""",
        (current_user.id, today.isoformat(), session.get(cursor_key, 0)),
    ).fetchone()
    summary = review_summary(current_user.id, today)
    return render_template(
        'learning/review.html', word=word, due=summary['due'], summary=summary,
        options=rating_options(word['interval_days'], today) if word else [],
    )

@learning_bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan():
    from .study_planner import planning_context

    db = get_db()
    today = date.today()
    if request.method == 'POST' and 'task_key' not in request.form:
        try:
            target = float(request.form.get('target_band', ''))
            exam = date.fromisoformat(request.form.get('exam_date', ''))
            minutes = int(request.form.get('daily_minutes', ''))
            if (not math.isfinite(target) or not 1 <= target <= 9 or target * 2 != int(target * 2)
                    or not today <= exam <= today + timedelta(days=1825) or not 10 <= minutes <= 240):
                raise ValueError()
        except (ValueError, OverflowError):
            flash('Choose a band from 1–9 in half steps, a future exam date within five years, and 10–240 minutes.', 'error')
            return redirect(url_for('learning.plan'))
        db.execute("""INSERT INTO study_plans VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
            target_band=excluded.target_band, exam_date=excluded.exam_date, daily_minutes=excluded.daily_minutes""",
            (current_user.id, target, exam.isoformat(), minutes))
        started = db.execute('SELECT 1 FROM study_tasks WHERE user_id=? AND task_date=? LIMIT 1',
                             (current_user.id, today.isoformat())).fetchone()
        if not started:
            db.execute('DELETE FROM study_days WHERE user_id=? AND task_date=?', (current_user.id, today.isoformat()))
        db.commit()
        flash('Goal saved. Your started session is preserved; new settings apply tomorrow.' if started
              else 'Goal saved. Today’s tasks now use your new settings.', 'success')
        return redirect(url_for('learning.plan'))

    planning = planning_context(current_user.id, history(current_user.id), len(mistakes(current_user.id)), today)
    tasks = planning['daily']['tasks']
    if request.method == 'POST':
        key = request.form['task_key']
        if key not in {task['key'] for task in tasks}:
            abort(400)
        action = request.form.get('action', 'complete')
        if action == 'complete':
            db.execute('INSERT OR IGNORE INTO study_tasks VALUES(?,?,?)', (current_user.id, today.isoformat(), key))
        elif action == 'undo':
            db.execute('DELETE FROM study_tasks WHERE user_id=? AND task_date=? AND task_key=?',
                       (current_user.id, today.isoformat(), key))
        else:
            abort(400)
        db.commit()
        return redirect(url_for('learning.plan'))
    done = {row[0] for row in db.execute('SELECT task_key FROM study_tasks WHERE user_id=? AND task_date=?',
                                        (current_user.id, today.isoformat()))}
    completed_minutes = sum(task['minutes'] for task in tasks if task['key'] in done)
    return render_template('learning/plan.html', plan=planning['saved'], tasks=tasks, done=done,
                           today=today.isoformat(), days=planning['days'], daily=planning['daily'],
                           week=planning['week'], gaps=planning['gaps'], completed_minutes=completed_minutes)


def daily_tasks(user_id):
    from .study_planner import planning_context
    return planning_context(user_id, history(user_id), len(mistakes(user_id)))['daily']['tasks']

@learning_bp.route('/practice/<skill>')
@login_required
def plan_practice(skill):
    from .study_planner import practice_destination
    if skill not in SKILLS:
        abort(404)
    return redirect(practice_destination(current_user.id, skill))


@learning_bp.route('/progress')
@login_required
def progress():
    from .progress_analytics import progress_data

    skill = request.args.get('skill', 'all')
    period = request.args.get('period', 'all')
    if skill not in ('all', *SKILLS):
        skill = 'all'
    if period not in ('all', '30', '90'):
        period = 'all'
    data = progress_data(current_user.id, history(current_user.id), skill, period,
                         request.args.get('page', 1, type=int) or 1)
    return render_template('learning/progress.html', **data)

@learning_bp.route('/speaking')
@login_required
def speaking_history():
    from .speaking_review import history_page
    return history_page()


@learning_bp.route('/speaking/recordings/<recording_id>/delete', methods=['POST'])
@login_required
def delete_speaking_recording(recording_id):
    from .speaking_review import delete_recording
    return delete_recording(recording_id)


@learning_bp.route('/teachers', methods=['GET', 'POST'])
@login_required
def teachers():
    from .teacher_workspace import workspace
    return workspace()


@learning_bp.route('/teacher/assign', methods=['POST'])
@login_required
def teacher_assign():
    from .teacher_workspace import create_assignments
    try:
        students = sorted({int(value) for value in request.form.getlist('student_ids')})
    except ValueError:
        abort(400)
    create_assignments(students)
    return redirect(url_for('learning.teachers'))


@learning_bp.route('/students/<int:student_id>', methods=['GET', 'POST'])
@login_required
def student(student_id):
    from .teacher_workspace import student_page
    return student_page(student_id)

@learning_bp.route('/results/<int:attempt_id>')
@login_required
def mock_result(attempt_id):
    db=get_db(); a=db.execute('SELECT * FROM attempts WHERE id=? AND user_id=?',(attempt_id,current_user.id)).fetchone()
    if not a: abort(404)
    mock=db.execute('SELECT * FROM mock_tests WHERE id=?',(a['mock_id'],)).fetchone()
    from .mock_results import load_attempt_questions
    questions = load_attempt_questions(a)
    return render_template('mocks/result.html',mock=mock,score=a['score'],total=a['total_points'],questions=questions)

@learning_bp.route('/assignments/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def assignment(assignment_id):
    from .teacher_workspace import assignment_page
    return assignment_page(assignment_id)


@learning_bp.route('/assignments/<int:assignment_id>/start')
@login_required
def assignment_start(assignment_id):
    from .teacher_workspace import assignment_or_404
    item = assignment_or_404(assignment_id)
    if item['student_id'] != current_user.id:
        abort(403)
    if item['cancelled'] or not item['available']:
        flash('This assignment is currently unavailable for practice.', 'info')
        return redirect(url_for('learning.assignment', assignment_id=assignment_id))
    return redirect(url_for('mocks.take' if item['kind']=='mock' else 'ai.'+item['skill'],mock_id=item['mock_id']))

@learning_bp.route('/writing/<int:attempt_id>/revise', methods=['GET', 'POST'])
@login_required
def revise(attempt_id):
    from .writing_revisions import revision_page
    return revision_page(attempt_id)


@learning_bp.route('/writing/<int:attempt_id>/draft', methods=['POST'])
@login_required
def writing_revision_draft(attempt_id):
    from .writing_revisions import draft_api
    return draft_api(attempt_id)

from .exam_sessions import active_exam, exam_section, complete_exam_section, exam_expired

@learning_bp.route('/exam',methods=['GET','POST'])
@login_required
def exam():
    from .mocks import _check_access as mock_access
    from .ai import _check_access as ai_access
    db=get_db(); e=active_exam()
    if request.method=='POST':
        if request.form.get('action')=='cancel':
            if e:
                db.execute('UPDATE exam_sessions SET completed_at=CURRENT_TIMESTAMP WHERE id=?',(e['id'],)); db.commit()
            return redirect(url_for('learning.exam'))
        if not e:
            selected=[]
            for skill in SKILLS:
                kind='mock' if skill in ('reading','listening') else 'ai'; table='mock_tests' if kind=='mock' else 'ai_mocks'
                m=db.execute(f'SELECT * FROM {table} WHERE id=? AND skill=? AND is_published=1',(request.form.get(skill,type=int),skill)).fetchone()
                if not m: abort(400,'Choose a published mock for every skill.')
                if not (mock_access(dict(m)) if kind=='mock' else ai_access(skill)):
                    return redirect(url_for('learning.exam'))
                if kind=='mock' and not db.execute('SELECT 1 FROM questions WHERE mock_id=?',(m['id'],)).fetchone(): abort(400,'Choose mocks with questions.')
                selected.append(dict(kind=kind,id=m['id'],skill=skill,minutes=m['time_limit_minutes']))
            db.execute('BEGIN IMMEDIATE')
            if active_exam():
                db.commit()
                return redirect(url_for('learning.exam_continue'))
            created = db.execute('INSERT INTO exam_sessions(user_id,mocks_json) VALUES(?,?)',(current_user.id,json.dumps(selected)))
            db.execute('INSERT INTO exam_section_state(session_id,stage) VALUES(?,0)',(created.lastrowid,))
            db.commit(); e=active_exam()
        return redirect(url_for('learning.exam_continue'))
    choices={s:db.execute(f"SELECT * FROM {'mock_tests' if s in ('reading','listening') else 'ai_mocks'} WHERE skill=? AND is_published=1",(s,)).fetchall() for s in SKILLS}
    sessions=[]
    for row in db.execute('SELECT * FROM exam_sessions WHERE user_id=? AND completed_at IS NOT NULL ORDER BY id DESC LIMIT 10',(current_user.id,)):
        from .exam_sessions import report
        sessions.append(report(row))
    return render_template('learning/exam.html',choices=choices,active=e,active_sections=json.loads(e['mocks_json']) if e else [],sessions=sessions)

@learning_bp.route('/exam/continue')
@login_required
def exam_continue():
    e=active_exam()
    if not e: return redirect(url_for('learning.exam'))
    item=json.loads(e['mocks_json'])[e['stage']]
    return redirect(url_for('mocks.take' if item['kind']=='mock' else 'ai.'+item['skill'],mock_id=item['id']))

@learning_bp.app_context_processor
def exam_context():
    from .exam_sessions import deadline, now, section_state
    if not current_user.is_authenticated or request.endpoint not in ('mocks.take', 'ai.writing', 'ai.speaking'):
        return {'exam_session': None}
    exam = exam_section('mock' if request.endpoint == 'mocks.take' else 'ai', request.view_args.get('mock_id'))
    if not exam:
        return {'exam_session': None}
    state = section_state(exam, start=True)
    return {'exam_session': exam, 'exam_deadline': deadline(exam, state).isoformat(),
            'exam_server_now': now().isoformat(), 'exam_draft': json.loads(state['draft_json']),
            'exam_revision': state['revision'], 'exam_auto_submit': request.method == 'GET' and now() < deadline(exam, state)}


@learning_bp.route('/exam/<int:session_id>/draft', methods=['GET', 'POST'])
@login_required
def exam_draft(session_id):
    from flask import jsonify
    from .exam_sessions import section_state
    exam = get_db().execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (session_id, current_user.id)).fetchone()
    if not exam:
        abort(404)
    if request.method == 'GET':
        from .exam_sessions import now
        response = jsonify(serverNow=now().isoformat(), stage=exam['stage'], completed=bool(exam['completed_at']))
        response.headers['Cache-Control'] = 'private, no-store'
        return response
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or type(payload.get('stage')) is not int or type(payload.get('revision')) is not int or payload['revision'] < 0:
        abort(400)
    if exam['completed_at'] or payload.get('stage') != exam['stage']:
        return jsonify(error='This section has already ended. Open Session details to continue.'), 409
    state = section_state(exam, start=True)
    draft = payload.get('draft')
    item = json.loads(exam['mocks_json'])[exam['stage']]
    if not isinstance(draft, dict) or len(json.dumps(draft)) > 250000:
        abort(400)
    if item['skill'] == 'writing':
        if not isinstance(draft.get('essay', ''), str) or len(draft.get('essay','')) > 50000:
            abort(400)
        draft = {'essay': draft.get('essay','')}
    elif item['kind'] == 'mock':
        if not all(isinstance(k,str) and k.startswith('question_') and isinstance(v,str) and len(v)<=500 for k,v in draft.items()):
            abort(400)
    else:
        turns = draft.get('turns', [])
        if (not isinstance(turns, list) or len(turns) > 20
                or any(not isinstance(turn, dict) or not isinstance(turn.get('question'), str)
                       or not isinstance(turn.get('transcript'), str) for turn in turns)
                or type(draft.get('index', 0)) is not int or not 0 <= draft.get('index', 0) < 20
                or ('next' in draft and (not isinstance(draft['next'], dict) or not isinstance(draft['next'].get('question'), str)))):
            abort(400)
    cursor = get_db().execute("""UPDATE exam_section_state SET draft_json=?,revision=revision+1,saved_at=CURRENT_TIMESTAMP
        WHERE session_id=? AND stage=? AND revision=?
        AND EXISTS (SELECT 1 FROM exam_sessions e WHERE e.id=exam_section_state.session_id AND e.stage=exam_section_state.stage AND e.completed_at IS NULL)""", (json.dumps(draft),session_id,exam['stage'],payload.get('revision')))
    get_db().commit()
    if not cursor.rowcount:
        return jsonify(error='Another tab saved a newer draft. Reload this page before continuing.'), 409
    return jsonify(revision=state['revision']+1)


@learning_bp.route('/exam/<int:session_id>/skip', methods=['POST'])
@login_required
def exam_skip(session_id):
    exam = active_exam()
    if not exam or exam['id'] != session_id:
        abort(404)
    if request.form.get('stage', type=int) != exam['stage']:
        return redirect(url_for('learning.exam_continue'))
    item = json.loads(exam['mocks_json'])[exam['stage']]
    complete_exam_section(item['kind'],item['id'],None,None,status='unscored')
    flash('Section ended without a score. Its saved draft is available in the report.', 'info')
    return redirect(url_for('learning.exam_continue'))


@learning_bp.route('/exam/<int:session_id>/report')
@login_required
def exam_report(session_id):
    from .exam_sessions import report
    exam = get_db().execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?',(session_id,current_user.id)).fetchone()
    if not exam:
        abort(404)
    drafts = {r['stage']:json.loads(r['draft_json']) for r in get_db().execute('SELECT stage,draft_json FROM exam_section_state WHERE session_id=?',(session_id,))}
    questions = {}
    for stage,item in enumerate(json.loads(exam['mocks_json'])):
        if item['kind'] == 'mock':
            questions[stage] = [{**dict(q), 'answer': drafts.get(stage,{}).get(f'question_{q["id"]}','')}
                                for q in get_db().execute('SELECT id,question_number,prompt FROM questions WHERE mock_id=? ORDER BY question_number',(item['id'],))]
    return render_template('learning/exam_report.html', exam=report(exam), drafts=drafts, draft_questions=questions)
