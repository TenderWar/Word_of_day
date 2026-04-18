-- Таблиця користувачів
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined_at TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Europe/Kyiv',
    notify_time TEXT NOT NULL DEFAULT '09:00',
    is_active INTEGER NOT NULL DEFAULT 1,
    current_word_index INTEGER NOT NULL DEFAULT 0
);

-- Таблиця сесій слів
CREATE TABLE IF NOT EXISTS word_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    date TEXT NOT NULL,
    word_viewed INTEGER NOT NULL DEFAULT 0,
    quiz_completed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, date)
);

-- Таблиця відповідей на тести
CREATE TABLE IF NOT EXISTS quiz_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    quiz_type TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    answered_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблиця кешу Gemini
CREATE TABLE IF NOT EXISTS gemini_cache (
    word TEXT PRIMARY KEY,
    content_json TEXT,
    quiz_en_to_uk_json TEXT,
    quiz_uk_to_en_json TEXT,
    created_at TEXT NOT NULL
);

-- Індекси для швидкого пошуку
CREATE INDEX IF NOT EXISTS idx_word_sessions_user_date ON word_sessions(user_id, date);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_user ON quiz_answers(user_id);
CREATE INDEX IF NOT EXISTS idx_users_active_time ON users(is_active, notify_time);
