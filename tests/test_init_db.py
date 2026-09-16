import sqlite3
from pathlib import Path

import db.connection as connection
import scripts.init_db as initializer


REQUIRED_COLUMNS = {
    "language",
    "detected_lang",
    "language_confidence",
    "is_analyzable",
    "sentiment",
    "sentiment_confidence",
    "category",
    "category_confidence",
}
REQUIRED_VIEWS = {
    "reviews_trend_window",
    "reviews_categorized_confident",
}


def initialize_database(path, monkeypatch):
    monkeypatch.setattr(connection, "DB_PATH", path)
    monkeypatch.setattr(initializer, "get_connection", connection.get_connection)
    initializer.init_db()


def inspect_database(path):
    conn = sqlite3.connect(path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}
    views = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'view'"
        )
    }
    review_count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    conn.close()
    return columns, views, review_count


def test_init_db_creates_complete_schema(tmp_path, monkeypatch):
    database = str(tmp_path / "fresh.db")

    initialize_database(database, monkeypatch)

    columns, views, review_count = inspect_database(database)
    assert REQUIRED_COLUMNS <= columns
    assert REQUIRED_VIEWS <= views
    assert review_count == 0


def test_init_db_upgrades_legacy_database(tmp_path, monkeypatch):
    database = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(database)
    conn.executescript(
        """
        CREATE TABLE apps (
            app_id INTEGER PRIMARY KEY,
            app_name TEXT NOT NULL UNIQUE,
            package_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE reviews (
            review_id TEXT PRIMARY KEY,
            app_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            score INTEGER NOT NULL,
            thumbs_up_count INTEGER NOT NULL DEFAULT 0,
            reply_content TEXT,
            replied_at TIMESTAMP,
            app_version TEXT,
            review_date TIMESTAMP NOT NULL,
            scraped_at TIMESTAMP NOT NULL,
            FOREIGN KEY (app_id) REFERENCES apps(app_id)
        );
        INSERT INTO apps VALUES (1, 'Legacy', 'legacy');
        INSERT INTO reviews VALUES (
            'r1', 1, 'Old review', 3, 0, NULL, NULL, NULL,
            date('now'), datetime('now')
        );
        """
    )
    conn.commit()
    conn.close()

    initialize_database(database, monkeypatch)

    columns, views, review_count = inspect_database(database)
    assert REQUIRED_COLUMNS <= columns
    assert REQUIRED_VIEWS <= views
    assert review_count == 1
