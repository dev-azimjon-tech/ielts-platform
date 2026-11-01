"""Private, filterable progress summaries from saved practice attempts."""
import json
import math
from datetime import date, timedelta

from flask import url_for

from .database import get_db

SKILLS = ('listening', 'reading', 'writing', 'speaking')
CRITERIA = {
    'writing': [('task_response_band', 'Task response'), ('coherence_band', 'Coherence'),
                ('lexical_band', 'Vocabulary'), ('grammar_band', 'Grammar')],
    'speaking': [('fluency_band', 'Fluency'), ('lexical_band', 'Vocabulary'),
                 ('grammar_band', 'Grammar'), ('pronunciation_band', 'Pronunciation estimate')],
}


def valid_score_rows(rows):
    """Exclude malformed legacy scores from arithmetic and chart coordinates."""
    return [row for row in rows if row.get('skill') in SKILLS
            and isinstance(row.get('band'), (int, float)) and not isinstance(row['band'], bool)
            and 0 <= row['band'] <= 9 and math.isfinite(row['band'])]


def _json_object(value):
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def summarize(rows, target=None):
    rows = valid_score_rows(rows)
    stats = []
    for skill in SKILLS:
        attempts = [r for r in rows if r['skill'] == skill]
        values = [r['band'] for r in attempts]
        recent, previous = values[-5:], values[-10:-5]
        average = sum(recent) / len(recent) if recent else None
        stats.append({
            'skill': skill, 'count': len(values), 'average': round(average, 1) if recent else None,
            'latest': values[-1] if values else None, 'best': max(values) if values else None,
            'recent_count': len(recent),
            'change': round(average - sum(previous) / 5, 1) if len(values) >= 10 else None,
            'latest_change': round(values[-1] - values[-2], 1) if len(values) > 1 else None,
            'gap': round(max(0, target - average), 1) if target is not None and recent else None,
        })
    return stats


def trend_series(rows, selected_skill):
    rows = valid_score_rows(rows)
    series = []
    for skill in SKILLS:
        if selected_skill != 'all' and selected_skill != skill:
            continue
        attempts = [r for r in rows if r['skill'] == skill][-30:]
        points = []
        for index, attempt in enumerate(attempts):
            points.append({**attempt, 'x': round(46 + index * 540 / max(1, len(attempts)-1), 2),
                           'y': round(164 - attempt['band'] / 9 * 144, 2),
                           'url': url_for('ai.result' if attempt['kind'] == 'ai' else 'learning.mock_result', attempt_id=attempt['id'])})
        series.append({'skill': skill, 'points': points,
                       'path': ' '.join(f'{p["x"]},{p["y"]}' for p in points)})
    return series


def question_accuracy(user_id, cutoff, selected_skill):
    from .mock_results import load_attempt_questions, load_question_snapshots

    # Grade against the submitted snapshot, not an administrator's later edits.
    # Latest answers count once per original question, including saved blanks.
    attempts = get_db().execute('''SELECT a.*,m.skill FROM attempts a
        JOIN mock_tests m ON m.id=a.mock_id WHERE a.user_id=?
        AND (? IS NULL OR a.completed_at>=?) AND (?='all' OR m.skill=?)
        ORDER BY a.completed_at,a.id''', (user_id,cutoff,cutoff,selected_skill,selected_skill)).fetchall()
    snapshots = load_question_snapshots(attempts)
    latest = {}
    for attempt in attempts:
        answers = _json_object(attempt['answers_json'])
        if not answers:
            continue
        for question in load_attempt_questions(attempt,snapshots=snapshots):
            if str(question['id']) in answers:
                latest[(attempt['mock_id'],question['id'])] = {**question,'skill':attempt['skill']}
    groups = {}
    for question in latest.values():
        key = (question['skill'],question['question_type'])
        group = groups.setdefault(key, {'skill':question['skill'], 'kind':question['question_type'],
                                        'correct':0, 'total':0})
        group['total'] += 1
        group['correct'] += int(question['is_correct'])
    for group in groups.values():
        group['accuracy'] = round(group['correct'] / group['total'] * 100)
        group['missed'] = group['total'] - group['correct']
    return sorted(groups.values(), key=lambda g: (g['accuracy'], -g['total'],g['skill'],g['kind']))


def criterion_averages(user_id, cutoff, selected_skill):
    rows = get_db().execute('''SELECT m.skill,a.feedback_json FROM ai_attempts a JOIN ai_mocks m ON m.id=a.ai_mock_id
        WHERE a.user_id=? AND (? IS NULL OR a.completed_at>=?) AND (?='all' OR m.skill=?)
        ORDER BY a.completed_at DESC,a.id DESC''', (user_id,cutoff,cutoff,selected_skill,selected_skill))
    recent = {'writing': [], 'speaking': []}
    for row in rows:
        if len(recent[row['skill']]) < 5:
            recent[row['skill']].append(_json_object(row['feedback_json']))
    groups = []
    for skill, fields in CRITERIA.items():
        if selected_skill not in ('all',skill):
            continue
        criteria = []
        for field,label in fields:
            values = [feedback.get(field) for feedback in recent[skill]]
            values = [float(v) for v in values if isinstance(v,(int,float)) and not isinstance(v,bool) and 0 <= v <= 9 and math.isfinite(v)]
            if values:
                criteria.append({'label': label, 'average': round(sum(values)/len(values),1), 'count': len(values)})
        if criteria:
            groups.append({'skill': skill, 'criteria': sorted(criteria,key=lambda c:c['average'])})
    return groups


def progress_data(user_id, rows, skill='all', period='all', page=1, today=None):
    today = today or date.today()
    rows = valid_score_rows(rows)
    cutoff = (today-timedelta(days=int(period)-1)).isoformat() if period != 'all' else None
    filtered = [r for r in rows if (skill == 'all' or r['skill'] == skill)
                and (cutoff is None or r['completed_at'][:10] >= cutoff)]
    plan = get_db().execute('SELECT target_band FROM study_plans WHERE user_id=?',(user_id,)).fetchone()
    target = plan['target_band'] if plan else None
    stats = [s for s in summarize(filtered,target) if skill == 'all' or s['skill'] == skill]
    pages = max(1, math.ceil(len(filtered)/20))
    page = min(max(1,page),pages)
    accuracy = question_accuracy(user_id,cutoff,skill)
    criteria = criterion_averages(user_id,cutoff,skill)
    suggestions = []
    missing = next((s for s in stats if not s['count']),None)
    if missing:
        s = missing['skill']
        suggestions.append({'title': f'Establish your {s.capitalize()} baseline', 'copy': 'Complete a practice mock to see a score and trend for this skill.',
                            'url': url_for('ai.index') if s in CRITERIA else url_for('mocks.index',skill=s)})
    gap = max((s for s in stats if s['gap'] is not None and s['gap'] > 0), key=lambda s:s['gap'], default=None)
    if gap:
        s = gap['skill']
        suggestions.append({'title': f'Close your {s.capitalize()} target gap',
                            'copy': f'Your recent average is {gap["gap"]} below your target band. Plan a focused session.',
                            'url': url_for('learning.plan')})
    weakest = next((g for g in accuracy if g['missed']),None)
    if weakest:
        suggestions.append({'title': f'Revisit {weakest["skill"]} {weakest["kind"].replace("_"," ")}',
                            'copy': f'{weakest["missed"]} of {weakest["total"]} latest question answers need another look.',
                            'url': url_for('learning.notebook',skill=weakest['skill'])})
    if criteria:
        weakest_criterion = min([(g['skill'],c) for g in criteria for c in g['criteria']],key=lambda pair:pair[1]['average'])
        s,c = weakest_criterion
        suggestions.append({'title': f'Work on {s} {c["label"].lower()}', 'copy': f'Your recent criterion average is {c["average"]}/9. Open a result and review its specific feedback.', 'url': next((url_for('ai.result',attempt_id=r['id']) for r in reversed(filtered) if r['skill']==s),url_for('ai.index'))})
    if not suggestions:
        suggestions.append({'title': 'Keep a regular practice routine', 'copy': 'Use your study plan to choose the next focused session.', 'url':url_for('learning.plan')})
    return dict(stats=stats,target=target,total=len(filtered),rows=list(reversed(filtered))[(page-1)*20:page*20],
                page=page,pages=pages,series=trend_series(filtered,skill),accuracy=accuracy,criteria=criteria,
                suggestions=suggestions,skill=skill,period=period)
