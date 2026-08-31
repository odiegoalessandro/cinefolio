PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE CHECK (length(username) BETWEEN 3 AND 30),
    display_name TEXT NOT NULL CHECK (length(display_name) BETWEEN 1 AND 80),
    bio TEXT NOT NULL DEFAULT '' CHECK (length(bio) <= 500),
    password_hash TEXT NOT NULL,
    avatar_url TEXT NOT NULL DEFAULT '',
    banner_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    tmdb_id INTEGER NOT NULL UNIQUE CHECK (tmdb_id > 0),
    title TEXT NOT NULL,
    original_title TEXT NOT NULL DEFAULT '',
    release_year INTEGER CHECK (release_year IS NULL OR release_year BETWEEN 1888 AND 2200),
    poster_path TEXT NOT NULL DEFAULT '',
    backdrop_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_movies (
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('WATCHING', 'WATCHED', 'PLAN_TO_WATCH', 'DROPPED')),
    rating REAL CHECK (rating IS NULL OR (rating >= 0 AND rating <= 10)),
    review TEXT CHECK (review IS NULL OR length(review) <= 5000),
    favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
    watched_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, movie_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_movies_status ON user_movies(user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_movies_favorite ON user_movies(user_id, favorite);
CREATE INDEX IF NOT EXISTS idx_user_movies_watched_at ON user_movies(user_id, watched_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
