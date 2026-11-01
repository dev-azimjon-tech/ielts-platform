"""Scheduling decisions must be atomic across browser tabs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

from app.database import get_db
from app.models import User
from app.vocabulary_review import record_rating


def test_simultaneous_ratings_schedule_a_due_card_once(app):
    today = date.today()
    with app.app_context():
        user_id = User.create('Reviewer', 'reviewer@example.com', 'unused').id
        db = get_db()
        word_id = db.execute("INSERT INTO vocabulary_words(user_id,term,normalized_term,meaning) VALUES(?,'clear','clear','easy to understand')", (user_id,)).lastrowid
        db.commit()
    ready = Barrier(2)
    def rate(rating):
        with app.app_context():
            ready.wait(timeout=5)
            return record_rating(user_id,word_id,rating,today)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(rate, ('good','easy')))
    assert sorted(r['status'] for r in results) == ['already_scheduled','scheduled']
    scheduled = next(r for r in results if r['status']=='scheduled')
    with app.app_context():
        saved = get_db().execute('SELECT * FROM vocabulary_schedule WHERE word_id=?', (word_id,)).fetchone()
        assert saved['due_on'] == scheduled['due_on']
        assert saved['interval_days'] == scheduled['interval_days']
        # A stale Again action cannot undo the review performed in the other tab.
        assert record_rating(user_id,word_id,'again',today)['status'] == 'already_scheduled'
        assert record_rating(user_id+1,word_id,'again',today) is None
