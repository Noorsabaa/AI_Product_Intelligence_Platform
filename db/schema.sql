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
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_app_id
ON reviews(app_id);

CREATE INDEX IF NOT EXISTS idx_reviews_review_date
ON reviews(review_date);