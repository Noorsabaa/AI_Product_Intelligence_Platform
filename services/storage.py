"""Shared storage. Run state and published results live in the same database."""
from contextlib import contextmanager
from datetime import datetime, timezone
from db.connection import get_connection
from scripts.init_db import init_db


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def database():
    conn = get_connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize():
    init_db()
    with database() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS workspace_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, stage TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0, processed INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL,
                finished_at TEXT, error TEXT, engine TEXT NOT NULL, summary TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON pipeline_runs((1))
                WHERE status IN ('queued', 'running');
            CREATE TABLE IF NOT EXISTS review_analysis (
                review_id TEXT PRIMARY KEY REFERENCES reviews(review_id) ON DELETE CASCADE,
                language TEXT, sentiment TEXT, sentiment_method TEXT NOT NULL,
                category TEXT, category_method TEXT NOT NULL,
                matched_terms TEXT NOT NULL, run_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS insight_actions (
                id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'open',
                owner TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY, filename TEXT NOT NULL, created_at TEXT NOT NULL,
                inserted INTEGER NOT NULL, duplicates INTEGER NOT NULL, mode TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS discovered_topics (
                id TEXT PRIMARY KEY, label TEXT NOT NULL, keywords TEXT NOT NULL,
                custom_label TEXT, model TEXT NOT NULL, run_id TEXT NOT NULL,
                member_ids TEXT NOT NULL, coherence REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_context (
                review_id TEXT PRIMARY KEY REFERENCES reviews(review_id) ON DELETE CASCADE,
                segment TEXT, service TEXT, customer_id TEXT, source TEXT,
                rating_missing INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS feature_cache (
                text_hash TEXT NOT NULL, model TEXT NOT NULL, vector BLOB NOT NULL,
                PRIMARY KEY(text_hash, model)
            );
            CREATE TABLE IF NOT EXISTS sentiment_cache (
                text_hash TEXT NOT NULL, model TEXT NOT NULL, label TEXT NOT NULL,
                PRIMARY KEY(text_hash, model)
            );
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
                period_start TEXT NOT NULL, period_end TEXT NOT NULL,
                run_id TEXT NOT NULL, payload TEXT NOT NULL
            );
        """)
        columns = {row[1] for row in conn.execute('PRAGMA table_info(review_analysis)')}
        if 'rating_missing' not in {r[1] for r in conn.execute('PRAGMA table_info(review_context)')}:
            conn.execute('ALTER TABLE review_context ADD COLUMN rating_missing INTEGER NOT NULL DEFAULT 0')
        for name, kind in [('topic_id', 'TEXT'), ('topic_strength', 'REAL'), ('analysis_reason', 'TEXT')]:
            if name not in columns:
                conn.execute(f'ALTER TABLE review_analysis ADD COLUMN {name} {kind}')
        conn.execute('CREATE INDEX IF NOT EXISTS analysis_topic ON review_analysis(topic_id,sentiment)')
        # The old rule taxonomy is not presented as discovered categories during migration.
        if metadata(conn, 'pipeline_version') != '3':
            set_metadata(conn, 'published_revision', 'requires-v3-analysis')
        if not conn.execute("SELECT 1 FROM workspace_meta WHERE key='dataset_revision'").fetchone():
            conn.execute("INSERT INTO workspace_meta VALUES ('dataset_revision', '1')")


def recover_interrupted_runs():
    # Called once by the single-worker app on startup, never by request handlers.
    with database() as conn:
        conn.execute("""UPDATE pipeline_runs SET status='interrupted', stage='interrupted',
            finished_at=?, error='The server stopped during analysis. Run analysis again; the last published results are intact.'
            WHERE status IN ('queued', 'running')""", (now(),))


def active_run(conn):
    return conn.execute("SELECT * FROM pipeline_runs WHERE status IN ('queued','running')").fetchone()


def metadata(conn, key, default=None):
    row = conn.execute("SELECT value FROM workspace_meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_metadata(conn, key, value):
    conn.execute("INSERT INTO workspace_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
