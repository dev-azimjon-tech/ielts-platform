"""Deterministic daily practice suggestions and saved daily sessions."""
import json
from datetime import date, timedelta

from flask import url_for

from .database import get_db
from .vocabulary_review import review_summary
from .progress_analytics import valid_score_rows

SKILLS = ('listening', 'reading', 'writing', 'speaking')


def skill_gaps(rows, target):
    values = {skill: [] for skill in SKILLS}
    for row in valid_score_rows(rows):
        values[row['skill']].append(row['band'])
    return [
        {'skill': skill,
         'average': round(sum(values[skill][-5:]) / len(values[skill][-5:]), 1) if values[skill] else None,
         'count': len(values[skill]),
         'gap': max(0, target - sum(values[skill][-5:]) / len(values[skill][-5:])) if values[skill] else None}
        for skill in SKILLS
    ]


def build_day(on_date, settings, gaps, vocabulary, missed_count):
    target = settings['target_band']
    minutes = settings['daily_minutes']
    exam_date = date.fromisoformat(settings['exam_date']) if settings.get('exam_date') else None
    days_left = (exam_date - on_date).days if exam_date else None
    phase = ('Set a goal' if days_left is None else 'Refresh your goal' if days_left < 0
             else 'Exam day' if days_left == 0 else 'Final review' if days_left <= 7
             else 'Build consistency' if days_left > 30 else 'Focused practice')
    # Two days in three favour the largest target gap; the third keeps all skills in rotation.
    rotation = on_date.toordinal() % 4
    order = SKILLS[rotation:] + SKILLS[:rotation]
    ranked = sorted(gaps, key=lambda item: (
        -(target + 1 if item['average'] is None else item['gap']), order.index(item['skill'])))
    focus = ranked[0] if on_date.toordinal() % 3 else next(item for item in gaps if item['skill'] == order[0])
    skill = focus['skill']
    reason = (f'No {skill.capitalize()} score yet. Use this session to establish a baseline.'
              if focus['average'] is None else
              f'Your recent {skill.capitalize()} average is {focus["average"]:.1f}; target band is {target:g}.')
    if focus['gap'] == 0:
        reason += ' Maintain this skill while working towards your overall goal.'
    # Near the exam, more of the budget goes to recall and reflection.
    review_share = .30 if days_left is not None and 0 <= days_left <= 7 else .20
    vocab_minutes = max(2, int(minutes * review_share))
    reflection_minutes = max(2, int(minutes * review_share))
    practice_minutes = minutes - vocab_minutes - reflection_minutes
    tasks = [
        {'key': 'vocabulary', 'title': 'Review vocabulary due today' if vocabulary['due'] else 'Add useful vocabulary' if not vocabulary['total'] else 'Recall your saved vocabulary',
         'minutes': vocab_minutes, 'reason': f'{vocabulary["due"]} cards are currently due.' if vocabulary['due'] else 'Save a few useful words and their meanings.' if not vocabulary['total'] else 'Your scheduled reviews are caught up. Practise recall without changing the schedule.',
         'url': url_for('learning.review') if vocabulary['due'] else url_for('flashcards.index') if not vocabulary['total'] else url_for('flashcards.study')},
        {'key': 'mistakes', 'title': 'Revisit your mistakes' if missed_count else 'Reflect on your practice',
         'minutes': reflection_minutes, 'reason': f'{missed_count} missed questions to revisit. Explain the answer in your own words.' if missed_count else 'Review feedback from a saved result, or note one thing to improve in your next session.',
         'url': url_for('learning.notebook') if missed_count else url_for('learning.progress')},
        {'key': 'practice', 'title': f'Practise {skill}', 'minutes': practice_minutes,
         'reason': reason, 'url': url_for('learning.plan_practice', skill=skill)},
    ]
    if phase == 'Exam day':
        tasks[2]['title'] = f'Light {skill} warm-up'
        tasks[2]['reason'] = 'Review a familiar example and your approach to this skill. Keep this session light.'
    return {'date': on_date.isoformat(), 'phase': phase, 'focus': skill,
            'minutes': minutes, 'target_band': target, 'exam_date': settings.get('exam_date'), 'tasks': tasks}


def planning_context(user_id, rows, missed_count, today=None):
    today = today or date.today()
    db = get_db()
    saved = db.execute('SELECT * FROM study_plans WHERE user_id=?', (user_id,)).fetchone()
    settings = dict(saved) if saved else {'target_band': 7.0, 'exam_date': None, 'daily_minutes': 30}
    gaps = skill_gaps(rows, settings['target_band'])
    vocabulary = review_summary(user_id, today)
    current = db.execute('SELECT plan_json FROM study_days WHERE user_id=? AND task_date=?',
                         (user_id, today.isoformat())).fetchone()
    if current:
        daily = json.loads(current['plan_json'])
    else:
        daily = build_day(today, settings, gaps, vocabulary, missed_count)
        db.execute('INSERT OR IGNORE INTO study_days VALUES(?,?,?)',
                   (user_id, today.isoformat(), json.dumps(daily)))
        db.commit()
        # A second tab may have created the session first.
        daily = json.loads(db.execute('SELECT plan_json FROM study_days WHERE user_id=? AND task_date=?',
                                     (user_id, today.isoformat())).fetchone()[0])
    # Older saved sessions used a direct library link, which could become locked
    # after their last check. Upgrade that action without changing session tasks.
    if daily.get('focus') in SKILLS:
        destination = url_for('learning.plan_practice',skill=daily['focus'])
        upgraded = False
        for task in daily['tasks']:
            if task.get('key')=='practice' and task.get('url')!=destination:
                task['url'] = destination
                upgraded = True
        if upgraded:
            db.execute('UPDATE study_days SET plan_json=? WHERE user_id=? AND task_date=?',
                       (json.dumps(daily),user_id,today.isoformat()))
            db.commit()
    exam_date = date.fromisoformat(settings['exam_date']) if settings['exam_date'] else None
    week = [daily]
    for offset in range(1, 7):
        day = today + timedelta(days=offset)
        if exam_date and day > exam_date:
            break
        week.append(build_day(day, settings, gaps, vocabulary, missed_count))
    return {'saved': saved, 'daily': daily, 'week': week, 'gaps': gaps,
            'days': (exam_date - today).days if exam_date else None}


def practice_destination(user_id, skill):
    """Keep plan actions useful after an allowance is exhausted.

    Count persisted attempts directly, including all Writing revisions. Scores
    omitted from analytics still count against the original practice allowance.
    """
    from .ai import FREE_LIMITS as AI_FREE_LIMITS, PREMIUM_LIMITS
    from .mocks import FREE_LIMITS as MOCK_FREE_LIMITS

    if skill not in SKILLS:
        raise ValueError('Unknown practice skill.')
    db = get_db()
    user = db.execute('SELECT is_premium FROM users WHERE id=?', (user_id,)).fetchone()
    if user is None:
        raise ValueError('Unknown student.')
    ai_skill = skill in ('writing','speaking')
    library = url_for('ai.index') if ai_skill else url_for('mocks.index',skill=skill)
    if user['is_premium'] and not ai_skill:
        return library
    attempts_table, mocks_table, mock_column = ('ai_attempts','ai_mocks','ai_mock_id') if ai_skill else ('attempts','mock_tests','mock_id')
    count = db.execute(f'''SELECT COUNT(*) FROM {attempts_table} a JOIN {mocks_table} m ON m.id=a.{mock_column}
        WHERE a.user_id=? AND m.skill=?''', (user_id,skill)).fetchone()[0]
    if skill == 'writing':
        count += db.execute('''SELECT COUNT(*) FROM writing_revisions r
            JOIN ai_attempts a ON a.id=r.attempt_id WHERE a.user_id=?''', (user_id,)).fetchone()[0]
    limit = (PREMIUM_LIMITS[skill] if user['is_premium'] else AI_FREE_LIMITS[skill]) if ai_skill else MOCK_FREE_LIMITS[skill]
    if count < limit:
        return library
    latest = db.execute(f'''SELECT a.id FROM {attempts_table} a JOIN {mocks_table} m ON m.id=a.{mock_column}
        WHERE a.user_id=? AND m.skill=? ORDER BY a.completed_at DESC,a.id DESC LIMIT 1''', (user_id,skill)).fetchone()
    if latest is None:
        return url_for('learning.progress',skill=skill)
    endpoint = 'learning.revise' if skill == 'writing' else 'ai.result' if ai_skill else 'learning.mock_result'
    return url_for(endpoint,attempt_id=latest['id'])
