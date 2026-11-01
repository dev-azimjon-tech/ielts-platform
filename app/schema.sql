CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    is_premium INTEGER NOT NULL DEFAULT 0,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mock_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill TEXT NOT NULL CHECK (skill IN ('reading', 'listening')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    time_limit_minutes INTEGER NOT NULL,
    is_published INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reading_passages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mock_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (mock_id) REFERENCES mock_tests (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS listening_scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mock_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    script TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (mock_id) REFERENCES mock_tests (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mock_id INTEGER NOT NULL,
    passage_id INTEGER,
    listening_script_id INTEGER,
    question_number INTEGER NOT NULL,
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    options_json TEXT,
    correct_answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    FOREIGN KEY (mock_id) REFERENCES mock_tests (id) ON DELETE CASCADE,
    FOREIGN KEY (passage_id) REFERENCES reading_passages (id) ON DELETE CASCADE,
    FOREIGN KEY (listening_script_id) REFERENCES listening_scripts (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mock_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    total_points INTEGER NOT NULL,
    answers_json TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (mock_id) REFERENCES mock_tests (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_mocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill TEXT NOT NULL CHECK (skill IN ('speaking', 'writing')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    task_json TEXT NOT NULL,
    time_limit_minutes INTEGER NOT NULL,
    is_published INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ai_mock_id INTEGER NOT NULL,
    submission_text TEXT NOT NULL,
    transcript TEXT NOT NULL DEFAULT '',
    feedback_json TEXT NOT NULL,
    band_score REAL NOT NULL,
    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (ai_mock_id) REFERENCES ai_mocks (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vocabulary_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    term TEXT NOT NULL,
    normalized_term TEXT NOT NULL,
    meaning TEXT NOT NULL,
    example TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, normalized_term),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vocabulary_quizzes (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    questions_json TEXT NOT NULL,
    answers_json TEXT,
    score INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vocabulary_user ON vocabulary_words(user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_vocabulary_quizzes_user ON vocabulary_quizzes(user_id, completed_at DESC);

CREATE INDEX IF NOT EXISTS idx_attempts_user_mock ON attempts(user_id, mock_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user_recent ON attempts(user_id, completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_attempts_user_mock ON ai_attempts(user_id, ai_mock_id);
CREATE INDEX IF NOT EXISTS idx_ai_attempts_user_recent ON ai_attempts(user_id, completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_questions_mock_number ON questions(mock_id, question_number);
CREATE INDEX IF NOT EXISTS idx_reading_passages_mock ON reading_passages(mock_id, display_order);
CREATE INDEX IF NOT EXISTS idx_listening_scripts_mock ON listening_scripts(mock_id, display_order);

-- Learning tools are additive so existing accounts and results remain intact.
CREATE TABLE IF NOT EXISTS mistake_reviews (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
 answer TEXT NOT NULL, is_correct INTEGER NOT NULL, reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id, question_id)
);
CREATE TABLE IF NOT EXISTS vocabulary_schedule (
 word_id INTEGER PRIMARY KEY REFERENCES vocabulary_words(id) ON DELETE CASCADE,
 due_on TEXT NOT NULL DEFAULT CURRENT_DATE, interval_days INTEGER NOT NULL DEFAULT 0,
 reviewed_on TEXT
);
CREATE TABLE IF NOT EXISTS study_plans (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 target_band REAL NOT NULL, exam_date TEXT NOT NULL, daily_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS study_tasks (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 task_date TEXT NOT NULL, task_key TEXT NOT NULL, PRIMARY KEY(user_id, task_date, task_key)
);
CREATE TABLE IF NOT EXISTS writing_revisions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER NOT NULL REFERENCES ai_attempts(id) ON DELETE CASCADE,
 essay TEXT NOT NULL, feedback_json TEXT NOT NULL, band_score REAL NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS teacher_profiles (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, invite_code TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS teacher_students (
 teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 PRIMARY KEY(teacher_id, student_id), CHECK(teacher_id != student_id)
);
CREATE TABLE IF NOT EXISTS assignments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL CHECK(kind IN ('mock','ai')), mock_id INTEGER NOT NULL,
 due_on TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS teacher_comments (
 assignment_id INTEGER PRIMARY KEY REFERENCES assignments(id) ON DELETE CASCADE,
 comment TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exam_sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 mocks_json TEXT NOT NULL, results_json TEXT NOT NULL DEFAULT '[]',
 stage INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 stage_started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS speaking_recordings (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 ai_mock_id INTEGER NOT NULL REFERENCES ai_mocks(id) ON DELETE CASCADE,
 attempt_id INTEGER REFERENCES ai_attempts(id) ON DELETE CASCADE,
 mime_type TEXT NOT NULL, audio BLOB NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS study_days (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_date TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    PRIMARY KEY (user_id, task_date)
);

CREATE TABLE IF NOT EXISTS exam_section_state (
    session_id INTEGER NOT NULL REFERENCES exam_sessions(id) ON DELETE CASCADE,
    stage INTEGER NOT NULL,
    started_at TEXT,
    draft_json TEXT NOT NULL DEFAULT '{}',
    revision INTEGER NOT NULL DEFAULT 0,
    saved_at TEXT,
    PRIMARY KEY(session_id, stage)
);

CREATE TABLE IF NOT EXISTS writing_revision_drafts (
    attempt_id INTEGER PRIMARY KEY REFERENCES ai_attempts(id) ON DELETE CASCADE,
    essay TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 0,
    base_revision_id INTEGER REFERENCES writing_revisions(id) ON DELETE SET NULL,
    saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS writing_revision_submissions (
    token TEXT PRIMARY KEY,
    revision_id INTEGER NOT NULL REFERENCES writing_revisions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_speaking_recordings_user_attempt ON speaking_recordings(user_id, attempt_id);

CREATE TABLE IF NOT EXISTS assignment_tracking (
    assignment_id INTEGER PRIMARY KEY REFERENCES assignments(id) ON DELETE CASCADE,
    minimum_attempt_id INTEGER NOT NULL DEFAULT 0,
    cancelled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS assignment_submissions (
    assignment_id INTEGER PRIMARY KEY REFERENCES assignments(id) ON DELETE CASCADE,
    attempt_id INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    feedback_version INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_assignments_teacher_student ON assignments(teacher_id,student_id,due_on);
CREATE INDEX IF NOT EXISTS idx_assignments_student ON assignments(student_id,due_on);

CREATE TABLE IF NOT EXISTS assignment_creation_tokens (
    token TEXT PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attempt_snapshots (
    attempt_id INTEGER PRIMARY KEY REFERENCES attempts(id) ON DELETE CASCADE,
    questions_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mistake_retries (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL,
    answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS ai_writing_submission_tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ai_mock_id INTEGER NOT NULL REFERENCES ai_mocks(id) ON DELETE CASCADE,
    attempt_id INTEGER NOT NULL UNIQUE REFERENCES ai_attempts(id) ON DELETE CASCADE
);
