"""Consent-based teaching with explicit hand-ins and versioned review status."""
import json
import math
import re
import secrets
from collections import Counter
from datetime import date, timedelta

from flask import abort, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user

from .database import get_db
from .main import _estimated_band

STATUSES = {'pending': 'Pending', 'overdue': 'Overdue', 'submitted': 'Awaiting review',
            'reviewed': 'Reviewed', 'cancelled': 'Cancelled'}
ASSIGNMENT_SELECT = '''SELECT a.*,u.name AS student_name,t.name AS teacher_name,c.comment,
    COALESCE(m.title,am.title,'Unavailable practice') AS title,COALESCE(m.skill,am.skill) AS skill,
    COALESCE(m.is_published,am.is_published,0) AS available,
    x.minimum_attempt_id,COALESCE(x.cancelled,0) AS cancelled,
    s.attempt_id,s.version,s.submitted_at,s.reviewed_at,s.feedback_version
    FROM assignments a JOIN users u ON u.id=a.student_id JOIN users t ON t.id=a.teacher_id
    JOIN teacher_students link ON link.teacher_id=a.teacher_id AND link.student_id=a.student_id
    LEFT JOIN mock_tests m ON a.kind='mock' AND m.id=a.mock_id
    LEFT JOIN ai_mocks am ON a.kind='ai' AND am.id=a.mock_id
    LEFT JOIN teacher_comments c ON c.assignment_id=a.id
    LEFT JOIN assignment_tracking x ON x.assignment_id=a.id
    LEFT JOIN assignment_submissions s ON s.assignment_id=a.id'''


def private_page(template, **data):
    response = make_response(render_template(template, statuses=STATUSES, assignment_token=secrets.token_urlsafe(24), **data))
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def connected(student_id):
    if not get_db().execute('SELECT 1 FROM teacher_students WHERE teacher_id=? AND student_id=?',
                             (current_user.id,student_id)).fetchone():
        abort(404)


def assignment_data(row):
    item = dict(row)
    if item['cancelled']:
        status = 'cancelled'
    elif item['version']:
        status = 'reviewed' if item['reviewed_at'] and item['feedback_version'] == item['version'] else 'submitted'
    else:
        status = 'overdue' if item['due_on'] < date.today().isoformat() else 'pending'
    item['status'] = status
    item['late'] = bool(item['submitted_at'] and item['submitted_at'][:10] > item['due_on'])
    item['earlier_feedback'] = bool(item['comment'] and item['feedback_version'] != item['version'])
    return item


def assignment_or_404(assignment_id):
    row = get_db().execute(ASSIGNMENT_SELECT + ' WHERE a.id=? AND (a.teacher_id=? OR a.student_id=?)',
                            (assignment_id,current_user.id,current_user.id)).fetchone()
    if not row:
        abort(404)
    return assignment_data(row)


def choices():
    return get_db().execute("""SELECT 'mock' kind,id,title,skill FROM mock_tests WHERE is_published=1
        AND EXISTS(SELECT 1 FROM questions q WHERE q.mock_id=mock_tests.id)
        UNION ALL SELECT 'ai',id,title,skill FROM ai_mocks WHERE is_published=1 ORDER BY skill,title""").fetchall()


def paginate(items, key, endpoint, **route_args):
    total = len(items)
    pages = max(1, math.ceil(total/12))
    page = min(max(1,request.args.get(key,1,type=int) or 1),pages)
    params = {k:v for k,v in request.args.items() if k not in route_args}
    def link(number):
        return url_for(endpoint, **{**params,**route_args,key:number})
    return items[(page-1)*12:page*12], {'page':page,'pages':pages,'total':total,
           'previous':link(page-1) if page>1 else None,'next':link(page+1) if page<pages else None}


def filter_status(items, key):
    status = request.args.get(key,'all')
    status = status if status in STATUSES else 'all'
    return [a for a in items if status=='all' or a['status']==status], status


def create_assignments(student_ids):
    if not student_ids or len(student_ids)>100:
        abort(400,'Choose between 1 and 100 connected students.')
    try:
        kind,raw = request.form.get('mock','').split(':')
        mock_id = int(raw)
        due = date.fromisoformat(request.form.get('due_on',''))
        if kind not in ('mock','ai') or not date.today() <= due <= date.today()+timedelta(days=1825):
            raise ValueError()
    except ValueError:
        abort(400,'Choose a published practice and a due date within five years.')
    note = request.form.get('note','').strip()
    if len(note)>1000:
        abort(400,'Keep instructions below 1,000 characters.')
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    token = request.form.get('request_token') or secrets.token_urlsafe(24)
    if not 20 <= len(token) <= 128 or not re.fullmatch(r'[A-Za-z0-9_-]+',token):
        abort(400)
    existing = db.execute('SELECT teacher_id FROM assignment_creation_tokens WHERE token=?',(token,)).fetchone()
    if existing:
        if existing[0] != current_user.id:
            abort(400)
        db.commit()
        flash('These assignments were already created.','info')
        return
    placeholders = ','.join('?' for _ in student_ids)
    enrolled = {r[0] for r in db.execute(f'SELECT student_id FROM teacher_students WHERE teacher_id=? AND student_id IN ({placeholders})',
                                        [current_user.id,*student_ids])}
    if enrolled != set(student_ids):
        abort(404)
    table = 'mock_tests' if kind=='mock' else 'ai_mocks'
    if not db.execute(f'SELECT 1 FROM {table} WHERE id=? AND is_published=1',(mock_id,)).fetchone():
        abort(404)
    if kind=='mock' and not db.execute('SELECT 1 FROM questions WHERE mock_id=?',(mock_id,)).fetchone():
        abort(400,'Choose a mock with questions.')
    attempts_table = 'attempts' if kind=='mock' else 'ai_attempts'
    mock_column = 'mock_id' if kind=='mock' else 'ai_mock_id'
    for student_id in student_ids:
        baseline = db.execute(f'SELECT COALESCE(MAX(id),0) FROM {attempts_table} WHERE user_id=? AND {mock_column}=?',
                              (student_id,mock_id)).fetchone()[0]
        cursor = db.execute('INSERT INTO assignments(teacher_id,student_id,kind,mock_id,due_on,note) VALUES(?,?,?,?,?,?)',
                            (current_user.id,student_id,kind,mock_id,due.isoformat(),note))
        db.execute('INSERT INTO assignment_tracking(assignment_id,minimum_attempt_id) VALUES(?,?)',(cursor.lastrowid,baseline))
    db.execute('INSERT INTO assignment_creation_tokens(token,teacher_id) VALUES(?,?)',(token,current_user.id))
    db.commit()
    flash(f'Practice assigned to {len(student_ids)} student(s).','success')


def workspace():
    db = get_db()
    if request.method=='POST':
        action = request.form.get('action')
        if action=='create':
            db.execute('INSERT OR IGNORE INTO teacher_profiles VALUES(?,?)',(current_user.id,secrets.token_urlsafe(10)))
        elif action=='rotate':
            db.execute('UPDATE teacher_profiles SET invite_code=? WHERE user_id=?',(secrets.token_urlsafe(10),current_user.id))
            flash('Invitation code replaced. Existing student connections stay active.','success')
        elif action=='join':
            teacher = db.execute('SELECT user_id FROM teacher_profiles WHERE invite_code=?',(request.form.get('code','').strip(),)).fetchone()
            if not teacher or teacher[0]==current_user.id:
                flash('Check the teacher invitation code.','error')
                return redirect(url_for('learning.teachers'))
            db.execute('INSERT OR IGNORE INTO teacher_students VALUES(?,?)',(teacher[0],current_user.id))
            flash('Teacher connected. You can now view their assignments.','success')
        elif action=='leave':
            db.execute('DELETE FROM teacher_students WHERE teacher_id=? AND student_id=?',
                       (request.form.get('teacher_id',type=int),current_user.id))
            flash('Teacher access revoked.','info')
        elif action=='remove':
            db.execute('DELETE FROM teacher_students WHERE teacher_id=? AND student_id=?',
                       (current_user.id,request.form.get('student_id',type=int)))
            flash('Student connection removed.','info')
        else:
            abort(400)
        db.commit()
        return redirect(url_for('learning.teachers'))
    profile = db.execute('SELECT * FROM teacher_profiles WHERE user_id=?',(current_user.id,)).fetchone()
    teachers = db.execute('SELECT u.id,u.name FROM teacher_students t JOIN users u ON t.teacher_id=u.id WHERE t.student_id=?',
                          (current_user.id,)).fetchall()
    teaching = [assignment_data(r) for r in db.execute(ASSIGNMENT_SELECT+' WHERE a.teacher_id=? ORDER BY a.due_on,a.id DESC',(current_user.id,))]
    mine = [assignment_data(r) for r in db.execute(ASSIGNMENT_SELECT+' WHERE a.student_id=? ORDER BY a.due_on,a.id DESC',(current_user.id,))]
    roster = [dict(r) for r in db.execute('''SELECT u.id,u.name,p.attempts,p.last_practice
        FROM teacher_students t JOIN users u ON u.id=t.student_id
        LEFT JOIN (SELECT user_id,COUNT(*) AS attempts,MAX(completed_at) AS last_practice FROM
          (SELECT a.user_id,a.completed_at FROM attempts a
             JOIN teacher_students members ON members.student_id=a.user_id WHERE members.teacher_id=?
           UNION ALL
           SELECT a.user_id,a.completed_at FROM ai_attempts a
             JOIN teacher_students members ON members.student_id=a.user_id WHERE members.teacher_id=?)
          GROUP BY user_id) p ON p.user_id=u.id
        WHERE t.teacher_id=? ORDER BY u.name,u.id''',(current_user.id,current_user.id,current_user.id))]
    attention = Counter((a['student_id'],a['status']) for a in teaching)
    for student in roster:
        student['awaiting'] = attention[(student['id'],'submitted')]
        student['overdue'] = attention[(student['id'],'overdue')]
    search = request.args.get('q','').strip()[:100]
    filtered_roster = [s for s in roster if search.casefold() in s['name'].casefold()]
    students,roster_pages = paginate(filtered_roster,'students_page','learning.teachers')
    filtered,teacher_status = filter_status(teaching,'status')
    teaching_page,teaching_pages = paginate(filtered,'assignments_page','learning.teachers')
    filtered,my_status = filter_status(mine,'my_status')
    my_page,my_pages = paginate(filtered,'my_page','learning.teachers')
    return private_page('learning/teachers.html',profile=profile,teachers=teachers,students=students,
                        roster_pages=roster_pages,student_count=len(roster),search=search,teaching=teaching_page,
                        teaching_pages=teaching_pages,teacher_status=teacher_status,counts=Counter(a['status'] for a in teaching),
                        assigned=my_page,my_pages=my_pages,my_status=my_status,choices=choices(),today=date.today().isoformat())


def student_page(student_id):
    from .learning import history
    from .progress_analytics import summarize
    connected(student_id)
    if request.method=='POST':
        if 'assignment_id' in request.form:
            item = assignment_or_404(request.form.get('assignment_id',type=int))
            if item['student_id']!=student_id or item['teacher_id']!=current_user.id:
                abort(404)
            return assignment_action(item,default_action='review')
        create_assignments([student_id])
        return redirect(url_for('learning.student',student_id=student_id))
    assignments = [assignment_data(r) for r in get_db().execute(ASSIGNMENT_SELECT+' WHERE a.teacher_id=? AND a.student_id=? ORDER BY a.due_on,a.id DESC',
                                                               (current_user.id,student_id))]
    filtered,status = filter_status(assignments,'status')
    tasks,pagination = paginate(filtered,'page','learning.student',student_id=student_id)
    rows = history(student_id)
    return private_page('learning/student.html',student=get_db().execute('SELECT id,name FROM users WHERE id=?',(student_id,)).fetchone(),
                        assigned=tasks,pagination=pagination,status=status,stats=summarize(rows),rows=list(reversed(rows))[:20],
                        choices=choices(),today=date.today().isoformat())


def attempt_source(item):
    return ('attempts','mock_id') if item['kind']=='mock' else ('ai_attempts','ai_mock_id')


def candidate_attempts(item):
    table,column = attempt_source(item)
    scores = 'score,total_points' if item['kind']=='mock' else 'band_score'
    # The chooser needs scores and dates, never every saved essay or answer set.
    return get_db().execute(f'''SELECT id,completed_at,{scores} FROM {table} WHERE user_id=? AND {column}=?
        AND id>? AND completed_at>=? ORDER BY completed_at DESC,id DESC''',
        (item['student_id'],item['mock_id'],item['minimum_attempt_id'] or 0,item['created_at'])).fetchall()


def eligible_attempt(item, attempt_id):
    table,column = attempt_source(item)
    return get_db().execute(f'''SELECT 1 FROM {table} WHERE id=? AND user_id=? AND {column}=?
        AND id>? AND completed_at>=?''', (attempt_id,item['student_id'],item['mock_id'],
        item['minimum_attempt_id'] or 0,item['created_at'])).fetchone() is not None


def submitted_attempt(item):
    if not item['attempt_id']:
        return None
    table,column = attempt_source(item)
    return get_db().execute(f'SELECT * FROM {table} WHERE id=? AND user_id=? AND {column}=?',
                            (item['attempt_id'],item['student_id'],item['mock_id'])).fetchone()


def expected_submission_version(default):
    raw = request.form.get('submission_version')
    if raw is None:
        return default
    try:
        version = int(raw)
    except (TypeError,ValueError):
        abort(400,'Choose a valid submission version.')
    if version < 0:
        abort(400,'Choose a valid submission version.')
    return version


def submission_detail(item):
    row = submitted_attempt(item)
    if not row:
        return None
    submission = dict(row)
    if item['kind']=='mock':
        from .mock_results import load_attempt_questions
        submission['review'] = [{**question,'answer':question['submitted_answer'],'correct':question['is_correct']}
                                for question in load_attempt_questions(row)]
        submission['band'] = _estimated_band(row['score'],row['total_points'],item['skill'])
    else:
        submission['feedback'] = json.loads(row['feedback_json'])
        try:
            turns = json.loads(row['submission_text']) if item['skill']=='speaking' else []
        except (ValueError,TypeError):
            turns = []
        submission['turns'] = [turn for turn in turns if isinstance(turn,dict)] if isinstance(turns,list) else []
        submission['band'] = row['band_score']
    return submission


def assignment_action(item, default_action=None):
    action = request.form.get('action',default_action)
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    item = assignment_or_404(item['id'])
    teacher = item['teacher_id']==current_user.id
    if action=='submit' and not teacher:
        if item['cancelled']:
            abort(400,'This assignment is cancelled.')
        attempt_id = request.form.get('attempt_id',type=int)
        if not eligible_attempt(item,attempt_id):
            abort(400,'Choose your own completed result from this assigned practice.')
        expected = expected_submission_version(item['version'] or 0)
        if expected != (item['version'] or 0) and attempt_id != item['attempt_id']:
            db.rollback()
            flash('A newer result is already handed in. Open the assignment before replacing it.','error')
            return redirect(url_for('learning.assignment',assignment_id=item['id']))
        db.execute('''INSERT INTO assignment_submissions(assignment_id,attempt_id) VALUES(?,?)
            ON CONFLICT(assignment_id) DO UPDATE SET attempt_id=excluded.attempt_id,
              version=assignment_submissions.version+1,submitted_at=CURRENT_TIMESTAMP,reviewed_at=NULL
            WHERE assignment_submissions.attempt_id!=excluded.attempt_id''',(item['id'],attempt_id))
        flash('Result handed in. Your teacher can review its answers and feedback.','success')
    elif teacher and action=='review':
        comment = request.form.get('comment','').strip()
        if not comment or len(comment)>3000:
            abort(400,'Write feedback between 1 and 3,000 characters.')
        expected = expected_submission_version(item['version'] or 0)
        current = item
        if current['cancelled']:
            abort(400,'Restore this assignment before reviewing it.')
        if not current['version'] or submitted_attempt(current) is None:
            abort(400,'The student must hand in a result before it can be reviewed.')
        if expected != (current['version'] or 0):
            db.rollback()
            flash('The student handed in a newer result. Review that submission before saving feedback.','error')
            return private_page('learning/assignment.html',assignment=current,is_teacher=True,
                                submission=submission_detail(current),candidates=[],today=date.today().isoformat(),
                                review_draft=comment), 409
        db.execute('INSERT INTO teacher_comments VALUES(?,?) ON CONFLICT(assignment_id) DO UPDATE SET comment=excluded.comment',
                   (item['id'],comment))
        db.execute('UPDATE assignment_submissions SET feedback_version=version,reviewed_at=CURRENT_TIMESTAMP WHERE assignment_id=?',(item['id'],))
        flash('Feedback saved for the student.','success')
    elif teacher and action in ('cancel','restore'):
        db.execute('''INSERT INTO assignment_tracking(assignment_id,cancelled) VALUES(?,?)
            ON CONFLICT(assignment_id) DO UPDATE SET cancelled=excluded.cancelled''',(item['id'],int(action=='cancel')))
    elif teacher and action=='update':
        try:
            due = date.fromisoformat(request.form.get('due_on',''))
            if due.isoformat()!=item['due_on'] and not date.today()<=due<=date.today()+timedelta(days=1825):
                raise ValueError()
        except ValueError:
            abort(400,'Choose a valid future due date within five years.')
        note = request.form.get('note','').strip()
        if len(note)>1000:
            abort(400,'Keep instructions below 1,000 characters.')
        db.execute('UPDATE assignments SET due_on=?,note=? WHERE id=?',(due.isoformat(),note,item['id']))
        flash('Assignment updated.','success')
    else:
        abort(403)
    db.commit()
    return redirect(url_for('learning.assignment',assignment_id=item['id']))


def assignment_page(assignment_id):
    item = assignment_or_404(assignment_id)
    if request.method=='POST':
        return assignment_action(item)
    teacher = item['teacher_id']==current_user.id
    candidates = [] if teacher or item['cancelled'] else candidate_attempts(item)
    return private_page('learning/assignment.html',assignment=item,is_teacher=teacher,
                        submission=submission_detail(item),candidates=candidates,today=date.today().isoformat())
