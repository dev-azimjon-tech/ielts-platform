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
