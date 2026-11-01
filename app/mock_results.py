"""Frozen question reviews for new attempts and a legacy fallback."""
import json

from .database import get_db


def load_question_snapshots(attempts):
    """Batch review lookups so history pages do not query once per attempt."""
    ids = [attempt['id'] for attempt in attempts]
    snapshots = {}
    for offset in range(0,len(ids),500):
        batch = ids[offset:offset+500]
        placeholders = ','.join('?' for _ in batch)
        for row in get_db().execute(f'SELECT attempt_id,questions_json FROM attempt_snapshots WHERE attempt_id IN ({placeholders})',batch):
            snapshots[row['attempt_id']] = row['questions_json']
    return snapshots


def load_attempt_questions(attempt, snapshots=None):
    if snapshots is None:
        row = get_db().execute('SELECT questions_json FROM attempt_snapshots WHERE attempt_id=?',
                                (attempt['id'],)).fetchone()
        serialized = row['questions_json'] if row else None
    else:
        serialized = snapshots.get(attempt['id'])
    if serialized is not None:
        return json.loads(serialized)
    from .mocks import _normalise_answer
    try:
        answers = json.loads(attempt['answers_json'])
    except (ValueError,TypeError):
        return []
    if not isinstance(answers,dict):
        return []
    questions = []
    for q in get_db().execute('SELECT * FROM questions WHERE mock_id=? ORDER BY question_number', (attempt['mock_id'],)):
        if str(q['id']) not in answers:
            continue
        answer = answers.get(str(q['id']), '')
        questions.append({**dict(q), 'options': json.loads(q['options_json'] or '[]'),
                          'submitted_answer': answer or 'Not answered',
                          'is_correct': _normalise_answer(answer) == _normalise_answer(q['correct_answer'])})
    return questions


def freeze_legacy_reviews(mock_id):
    """Retain the current legacy review before an admin edits it; scores stay intact.

    This helper participates in its caller's write transaction.
    """
    db = get_db()
    attempts = db.execute('''SELECT a.* FROM attempts a LEFT JOIN attempt_snapshots s ON s.attempt_id=a.id
        WHERE a.mock_id=? AND s.attempt_id IS NULL''',(mock_id,)).fetchall()
    for attempt in attempts:
        questions = load_attempt_questions(attempt)
        db.execute('INSERT OR IGNORE INTO attempt_snapshots VALUES(?,?)',
                   (attempt['id'],json.dumps(questions,ensure_ascii=False)))
