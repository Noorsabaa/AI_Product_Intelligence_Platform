# scripts/migrate_add_sentiment_columns.py
import sqlite3
from db.connection import get_connection

STATEMENTS = [
    "ALTER TABLE reviews ADD COLUMN sentiment TEXT;",
    "ALTER TABLE reviews ADD COLUMN sentiment_confidence REAL;",
]

def migrate():
    conn = get_connection()
    for stmt in STATEMENTS:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Skipping (already applied): {stmt}")
            else:
                raise
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()