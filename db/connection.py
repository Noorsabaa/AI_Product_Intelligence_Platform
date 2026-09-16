import sqlite3
import os
from pathlib import Path
from contextvars import ContextVar

DB_PATH = Path(os.environ.get("INTELLIGENCE_DB", Path(__file__).resolve().parent.parent / "data" / "reviews.db"))
WORKSPACE_PATH = ContextVar('workspace_database', default=None)


def get_connection():
    path = WORKSPACE_PATH.get() or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn
