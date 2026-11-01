import json
import re
import secrets
from io import BytesIO

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for, send_file, make_response, g
from flask_login import current_user, login_required

from .ai_service import (
    AIServiceError,
    evaluate_speaking,
    evaluate_writing,
    generate_next_speaking_question,
    transcribe_audio,
    validated_band,
)
from .database import get_db


ai_bp = Blueprint("ai", __name__, url_prefix="/ai")
FREE_LIMITS = {"speaking": 2, "writing": 2}
PREMIUM_LIMITS = {"speaking": 10, "writing": 10}


def _load_ai_mock(mock_id, required_skill=None):
    row = get_db().execute(
        "SELECT * FROM ai_mocks WHERE id = ? AND is_published = 1", (mock_id,)
    ).fetchone()
    if row is None or (required_skill and row["skill"] != required_skill):
        abort(404)
    mock = dict(row)
    mock["task"] = json.loads(mock["task_json"])
    return mock


def _attempt_count(skill):
    row = get_db().execute(
        """
        SELECT COUNT(*) AS count
        FROM ai_attempts AS a
        JOIN ai_mocks AS m ON m.id = a.ai_mock_id
        WHERE a.user_id = ? AND m.skill = ?
        """,
        (current_user.id, skill),
    ).fetchone()
    count = row["count"]
    if skill == "writing":
        count += get_db().execute("SELECT COUNT(*) FROM writing_revisions r JOIN ai_attempts a ON a.id=r.attempt_id WHERE a.user_id=?",(current_user.id,)).fetchone()[0]
    return count


def _limit(skill):
    return PREMIUM_LIMITS[skill] if current_user.is_premium else FREE_LIMITS[skill]


def _check_access(skill):
    attempts = _attempt_count(skill)
    limit = _limit(skill)
    if attempts >= limit:
        if current_user.is_premium:
            flash(
                f"You have completed all {limit} premium {skill} AI mocks.",
                "info",
            )
        else:
            flash(
                f"You have used both free {skill} AI mocks. Upgrade to premium for {PREMIUM_LIMITS[skill]} mocks.",
                "info",
            )
        return False
    return True


def _speaking_plan(task):
    plan = []
    for part in task.get("parts", []):
        for prompt in part.get("questions", []):
            plan.append(
                {
                    "part": part["part"],
                    "title": part["title"],
                    "instruction": part["instruction"],
                    "question": prompt,
                    "prep_seconds": part.get("prep_seconds", 0),
                }
            )
    return plan


@ai_bp.route("/")
@login_required
def index():
    counts = {
        row["skill"]: row["completed"]
        for row in get_db().execute(
            """
            SELECT m.skill, COUNT(*) AS completed
            FROM ai_attempts AS a JOIN ai_mocks AS m ON m.id = a.ai_mock_id
            WHERE a.user_id = ? GROUP BY m.skill
            """,
            (current_user.id,),
        )
    }
    counts["writing"] = _attempt_count("writing")
    rows = get_db().execute(
        "SELECT * FROM ai_mocks WHERE is_published = 1 ORDER BY skill, id"
    ).fetchall()
    mocks = []
    for row in rows:
        mock = dict(row)
        mock["attempts"] = counts.get(mock["skill"], 0)
        mock["limit"] = _limit(mock["skill"])
        mock["remaining"] = max(mock["limit"] - mock["attempts"], 0)
        mock["locked"] = mock["attempts"] >= mock["limit"]
        mocks.append(mock)
    return render_template(
        "ai/index.html",
        mocks=mocks,
        speaking_attempts=counts.get("speaking", 0),
        writing_attempts=counts.get("writing", 0),
        speaking_limit=_limit("speaking"),
        writing_limit=_limit("writing"),
    )


@ai_bp.route("/speaking/<int:mock_id>")
@login_required
def speaking(mock_id):
    mock = _load_ai_mock(mock_id, "speaking")
    if not _check_access("speaking"):
        return redirect(url_for("ai.index"))
    plan = _speaking_plan(mock["task"])
    if not plan:
        abort(404)
    return render_template(
        "ai/speaking.html",
        mock=mock,
        plan=plan,
        attempt_count=_attempt_count("speaking"),
        limit=_limit("speaking"),
    )


def _validated_turns(value, *, maximum=20, allow_empty=False):
    if not isinstance(value, list) or len(value) > maximum or (not value and not allow_empty):
        raise ValueError('Please complete valid Speaking answers first.')
    turns, recording_ids = [], []
    for turn in value:
        if (not isinstance(turn, dict) or type(turn.get('part')) is not int or turn['part'] not in (1,2,3)
                or not isinstance(turn.get('question'), str) or not turn['question'].strip() or len(turn['question']) > 4000
                or not isinstance(turn.get('transcript'), str) or not turn['transcript'].strip() or len(turn['transcript']) > 20000):
            raise ValueError('The Speaking answers are invalid. Please reload your saved answers.')
        item = {key:turn[key] for key in ('part','question','transcript')}
        if turn.get('recording_id') is not None:
            rid = turn['recording_id']
            if not isinstance(rid,str) or not rid or len(rid)>128 or rid in recording_ids:
                raise ValueError('Each recorded answer needs a valid unique recording.')
            recording_ids.append(rid)
            item['recording_id'] = rid
        turns.append(item)
    return turns


def _speaking_recordings(turns, mock_id):
    ids = [turn['recording_id'] for turn in turns if 'recording_id' in turn]
    if not ids:
        return {}
    placeholders = ','.join('?' for _ in ids)
    records = {row['id']:row for row in get_db().execute(
        f'SELECT id,attempt_id FROM speaking_recordings WHERE user_id=? AND ai_mock_id=? AND id IN ({placeholders})',
        (current_user.id,mock_id,*ids))}
    if set(ids) != set(records):
        raise ValueError('A recording is unavailable for this Speaking practice. Please check your saved answers.')
    return records


def _completed_speaking_redirect(turns, records):
    if not turns or len(records)!=len(turns):
        return None
    attempts = {row['attempt_id'] for row in records.values()}
    if len(attempts)!=1 or None in attempts:
        return None
    attempt_id = next(iter(attempts))
    row = get_db().execute('SELECT submission_text FROM ai_attempts WHERE id=? AND user_id=?',
                           (attempt_id,current_user.id)).fetchone()
    if row and json.loads(row['submission_text']) == turns:
        return url_for('ai.result',attempt_id=attempt_id)
    return None


@ai_bp.route("/speaking/<int:mock_id>/turn", methods=("POST",))
@login_required
def speaking_turn(mock_id):
    from .exam_sessions import submission_redirect
    replay = submission_redirect('ai', mock_id)
    if replay:
        return jsonify({"redirect": replay})
    mock = _load_ai_mock(mock_id, "speaking")
    if not _check_access("speaking"):
        return jsonify({"error": "This Speaking mock is no longer available for your plan."}), 403

    audio = request.files.get("audio")
    if audio is None:
        return jsonify({"error": "Please record an answer before continuing."}), 400
    try:
        plan = _speaking_plan(mock["task"])
        plan_index = int(request.form.get("plan_index", "0"))
        if plan_index < 0 or plan_index >= len(plan):
            return jsonify({"error": "That Speaking question is not valid."}), 400
        history = _validated_turns(json.loads(request.form.get("history", "[]")),maximum=len(plan),allow_empty=True)
        if len(history) != plan_index:
            return jsonify({"error": "The Speaking question does not match your saved answers."}), 400
        _speaking_recordings(history, mock_id)
        current_plan = plan[plan_index]
        audio_data = audio.read()
        audio.stream.seek(0)
        mime = (audio.mimetype or "audio/webm").split(";")[0]
        if mime not in {"audio/webm","audio/ogg","audio/mp4","audio/wav"}:
            return jsonify({"error":"Unsupported recording format."}), 400
        if not audio_data or len(audio_data) > 15 * 1024 * 1024:
            return jsonify({"error":"Record an answer under 15 MB before continuing."}), 400
        displayed_question = request.form.get("question", "").strip() or current_plan["question"]
        if len(displayed_question) > 4000:
            return jsonify(error='Keep the question below 4,000 characters.'), 400
        transcript = transcribe_audio(audio)
        if not isinstance(transcript,str) or not transcript.strip():
            raise AIServiceError('The recording could not be transcribed. Please try again.')
        if len(transcript) > 20000:
            return jsonify(error='This answer is too long. Record a shorter response.'), 400
        recording_id = secrets.token_urlsafe(24)
        current_turn = {
            "part": current_plan["part"],
            "question": displayed_question,
            "transcript": transcript,
            "recording_id": recording_id,
        }
        updated_history = history + [current_turn]
        next_plan = plan[plan_index + 1] if plan_index + 1 < len(plan) else None
        from .learning import exam_expired
        if next_plan is None or exam_expired("ai", mock_id):
            _save_recording(recording_id, mock_id, mime, audio_data)
            return jsonify(
                {
                    "transcript": transcript,
                    "finished": True,
                    "turns": updated_history,
                }
            )
        notice = None
        try:
            next_question = generate_next_speaking_question(displayed_question, next_plan, updated_history)
        except AIServiceError:
            # A generated follow-up must not discard an already transcribed answer.
            next_question = {'question': next_plan['question'], 'examiner_note': ''}
            notice = 'The AI examiner is unavailable. Continuing with the planned question.'
        _save_recording(recording_id, mock_id, mime, audio_data)
        return jsonify(
            {
                "transcript": transcript,
                "finished": False,
                "notice": notice,
                "turns": updated_history,
                "next": {
                    **next_plan,
                    "question": next_question["question"],
                    "examiner_note": next_question["examiner_note"],
                },
            }
        )
    except (AIServiceError, ValueError, json.JSONDecodeError) as error:
        return jsonify({"error": str(error)}), 503 if isinstance(error, AIServiceError) else 400


@ai_bp.route("/speaking/<int:mock_id>/complete", methods=("POST",))
@login_required
def complete_speaking(mock_id):
    from .exam_sessions import submission_redirect
    replay = submission_redirect('ai', mock_id)
    if replay:
        return jsonify({"redirect": replay})
    mock = _load_ai_mock(mock_id, "speaking")
    try:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error":"Send a JSON object with your Speaking answers."}), 400
        turns = _validated_turns(payload.get("turns"))
        records = _speaking_recordings(turns, mock_id)
        replay = _completed_speaking_redirect(turns, records)
        if replay:
            return jsonify({'redirect': replay})
        if any(record['attempt_id'] is not None for record in records.values()):
            return jsonify({'error':'These recordings already belong to another saved result.'}), 400
        if not _check_access("speaking"):
            return jsonify({"error": "This Speaking mock is no longer available for your plan."}), 403
        from .exam_sessions import save_submission_draft
        saved = save_submission_draft('ai', mock_id, {'turns':turns,'index':min(len(turns)-1,19),'finished':True})
        if saved is False:
            return jsonify({'error':'Another tab saved newer answers. Copy your current answers before reloading.'}), 409
        feedback = evaluate_speaking(turns)
        band_score = validated_band(feedback)
        db = get_db()
        db.execute('BEGIN IMMEDIATE')
        replay = submission_redirect('ai', mock_id)
        if replay:
            db.commit()
            return jsonify({'redirect': replay})
        records = _speaking_recordings(turns, mock_id)
        replay = _completed_speaking_redirect(turns, records)
        if replay:
            db.commit()
            return jsonify({'redirect':replay})
        if any(record['attempt_id'] is not None for record in records.values()):
            db.rollback()
            return jsonify(error='A recording was already saved with another result. Open Speaking history to review it.'), 400
        if _attempt_count('speaking') >= _limit('speaking'):
            db.rollback()
            return jsonify(error='Your last Speaking AI check was used in another session. Your answers remain saved.',exam_revision=getattr(g,'exam_saved_revision',None)), 403
        cursor = db.execute(
            """
            INSERT INTO ai_attempts
                (user_id, ai_mock_id, submission_text, transcript, feedback_json, band_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                mock_id,
                json.dumps(turns, ensure_ascii=False),
                "\n\n".join(
                    f"Part {turn['part']}: {turn['transcript']}" for turn in turns
                ),
                json.dumps(feedback, ensure_ascii=False),
                band_score,
            ),
        )
        for turn in turns:
            db.execute("UPDATE speaking_recordings SET attempt_id=? WHERE id=? AND user_id=? AND ai_mock_id=? AND attempt_id IS NULL",(cursor.lastrowid,turn.get("recording_id",""),current_user.id,mock_id))
        from .learning import complete_exam_section
        in_exam=complete_exam_section("ai",mock_id,cursor.lastrowid,band_score)
        db.commit()
        return jsonify({"redirect": url_for("learning.exam_continue") if in_exam else url_for("ai.result", attempt_id=cursor.lastrowid)})
    except AIServiceError as error:
        return jsonify(error=str(error), exam_revision=getattr(g,'exam_saved_revision',None)), 503
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": f"The Speaking answers could not be saved: {error}"}), 400


def _writing_submission_token():
    token = request.form.get('submission_token') or secrets.token_urlsafe(24)
    if not 20 <= len(token) <= 128 or not re.fullmatch(r'[A-Za-z0-9_-]+',token):
        abort(400, 'Invalid Writing submission token.')
    return token


def _writing_replay(token, mock_id):
    row = get_db().execute('SELECT user_id,ai_mock_id,attempt_id FROM ai_writing_submission_tokens WHERE token=?',
                           (token,)).fetchone()
    if row:
        if row['user_id'] != current_user.id or row['ai_mock_id'] != mock_id:
            abort(400, 'This submission belongs to a different Writing task.')
        return url_for('ai.result',attempt_id=row['attempt_id'])
    return None


@ai_bp.route("/writing/<int:mock_id>", methods=("GET", "POST"))
@login_required
def writing(mock_id):
    from .exam_sessions import submission_redirect
    submission_token = _writing_submission_token()
    if request.method == 'POST':
        replay = submission_redirect('ai', mock_id)
        if replay:
            return redirect(replay)
        replay = _writing_replay(submission_token,mock_id)
        if replay:
            return redirect(replay)
    mock = _load_ai_mock(mock_id, "writing")
    if not _check_access("writing"):
        return redirect(url_for("ai.index"))
    essay = request.form.get("essay", "") if request.method == "POST" else ""
    word_count = len(essay.split())
    if request.method == "POST":
        from .exam_sessions import save_submission_draft
        if len(essay) > 50000:
            abort(400, 'Keep your essay below 50,000 characters.')
        saved = save_submission_draft('ai', mock_id, {'essay':essay})
        if saved is False:
            flash('Another tab saved a newer response. Your submitted text is preserved below; copy it before reloading.', 'error')
            return render_template('ai/writing.html',mock=mock,essay=essay,word_count=word_count,
                                   attempt_count=_attempt_count('writing'),limit=_limit('writing'),submission_token=submission_token,exam_submission_conflict=True), 409
        if word_count < 50:
            flash("Please write at least 50 words before asking the AI checker to review your essay.", "error")
        else:
            try:
                feedback = evaluate_writing(mock["task"]["prompt"], essay, word_count)
                band_score = validated_band(feedback)
                db = get_db()
                db.execute('BEGIN IMMEDIATE')
                replay = submission_redirect('ai', mock_id)
                if replay:
                    db.commit()
                    return redirect(replay)
                replay = _writing_replay(submission_token,mock_id)
                if replay:
                    db.commit()
                    return redirect(replay)
                if _attempt_count('writing') >= _limit('writing'):
                    db.rollback()
                    flash('Your last Writing AI check was used in another session. Your response is preserved below.', 'info')
                    return render_template('ai/writing.html', mock=mock, essay=essay, word_count=word_count,
                                           attempt_count=_attempt_count('writing'), limit=_limit('writing'),submission_token=submission_token)
                cursor = db.execute(
                    """
                    INSERT INTO ai_attempts
                        (user_id, ai_mock_id, submission_text, feedback_json, band_score)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        current_user.id,
                        mock_id,
                        essay,
                        json.dumps(feedback, ensure_ascii=False),
                        band_score,
                    ),
                )
                db.execute('INSERT INTO ai_writing_submission_tokens VALUES(?,?,?,?)',
                           (submission_token,current_user.id,mock_id,cursor.lastrowid))
                from .learning import complete_exam_section
                if complete_exam_section("ai",mock_id,cursor.lastrowid,band_score):
                    return redirect(url_for("learning.exam_continue"))
                db.commit()
                return redirect(url_for("ai.result", attempt_id=cursor.lastrowid))
            except AIServiceError as error:
                flash(str(error), "error")
    return render_template(
        "ai/writing.html",
        mock=mock,
        submission_token=submission_token,
        essay=essay,
        word_count=word_count,
        attempt_count=_attempt_count("writing"),
        limit=_limit("writing"),
    )


@ai_bp.route("/results/<int:attempt_id>")
@login_required
def result(attempt_id):
    row = get_db().execute(
        """
        SELECT a.*, m.title, m.skill, m.task_json
        FROM ai_attempts AS a
        JOIN ai_mocks AS m ON m.id = a.ai_mock_id
        WHERE a.id = ? AND a.user_id = ?
        """,
        (attempt_id, current_user.id),
    ).fetchone()
    if row is None:
        abort(404)
    result_data = dict(row)
    result_data["feedback"] = json.loads(result_data.pop("feedback_json"))
    try:
        result_data["turns"] = json.loads(result_data["submission_text"]) if row["skill"] == "speaking" else []
    except (ValueError, TypeError):
        result_data["turns"] = []
    speaking_review = None
    if row['skill'] == 'speaking':
        from .speaking_review import answer_review
        speaking_review = answer_review(row)
    response = make_response(render_template("ai/result.html", result=result_data, speaking_review=speaking_review))
    if speaking_review is not None:
        response.headers['Cache-Control'] = 'private, no-store'
    return response


def _save_recording(recording_id,mock_id,mime,data):
    db=get_db()
    # Retain old uploads while a resumable exam still references them.
    stale = {row['id']:row['user_id'] for row in db.execute("SELECT id,user_id FROM speaking_recordings WHERE attempt_id IS NULL AND created_at < datetime('now','-1 day')")}
    if stale:
        referenced = set()
        for row in db.execute("SELECT s.draft_json,e.user_id FROM exam_section_state s JOIN exam_sessions e ON e.id=s.session_id WHERE e.completed_at IS NULL"):
            try:
                draft = json.loads(row['draft_json'])
                turns = draft.get('turns', []) if isinstance(draft, dict) else []
                referenced.update(turn['recording_id'] for turn in turns if isinstance(turn,dict) and isinstance(turn.get('recording_id'),str) and stale.get(turn['recording_id']) == row['user_id'])
            except (ValueError, TypeError):
                continue
        db.executemany('DELETE FROM speaking_recordings WHERE id=?', ((rid,) for rid in set(stale) - referenced))
    db.execute('INSERT INTO speaking_recordings(id,user_id,ai_mock_id,mime_type,audio) VALUES(?,?,?,?,?)',(recording_id,current_user.id,mock_id,mime,data))
    db.commit()

@ai_bp.route('/recordings/<recording_id>')
@login_required
def recording(recording_id):
    r=get_db().execute('SELECT * FROM speaking_recordings WHERE id=? AND user_id=?',(recording_id,current_user.id)).fetchone()
    if not r: abort(404)
    from .speaking_review import AUDIO_EXTENSIONS
    extension = AUDIO_EXTENSIONS.get(r['mime_type'].split(';')[0], 'bin')
    response=send_file(BytesIO(r['audio']),mimetype=r['mime_type'],conditional=True,
                       as_attachment=request.args.get('download') == '1',
                       download_name=f"speaking-{r['attempt_id'] or 'practice'}-{recording_id[:8]}.{extension}")
    response.headers['Cache-Control']='private, no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response
