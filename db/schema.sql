CREATE TABLE IF NOT EXISTS apps (
    app_id INTEGER PRIMARY KEY,
    app_name TEXT NOT NULL UNIQUE,
    package_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    app_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    thumbs_up_count INTEGER NOT NULL DEFAULT 0 CHECK (thumbs_up_count >= 0),
    reply_content TEXT,
    replied_at TIMESTAMP,
    app_version TEXT,
    review_date TIMESTAMP NOT NULL,
    scraped_at TIMESTAMP NOT NULL,
    language TEXT,
    detected_lang TEXT,
    language_confidence REAL,
    is_analyzable INTEGER,
    sentiment TEXT,
    sentiment_confidence REAL,
    category TEXT,
    category_confidence REAL,
    secondary_category TEXT,
    secondary_category_confidence REAL,
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_app_id
ON reviews(app_id);

CREATE INDEX IF NOT EXISTS idx_reviews_review_date
ON reviews(review_date);

CREATE VIEW IF NOT EXISTS reviews_trend_window AS
SELECT r.*
FROM reviews r
WHERE r.is_analyzable = 1
    AND r.review_date >= date('now', '-180 days');

CREATE VIEW IF NOT EXISTS reviews_categorized_confident AS
SELECT *
FROM reviews_trend_window
WHERE category IS NOT NULL
    AND category_confidence >= 0.7;