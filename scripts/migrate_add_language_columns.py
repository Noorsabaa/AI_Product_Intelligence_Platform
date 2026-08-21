# scripts/migrate_add_language_columns.py
import sqlite3
from db.connection import get_connection

MIGRATION_STATEMENTS = [
    "ALTER TABLE reviews ADD COLUMN language TEXT;",
    "ALTER TABLE reviews ADD COLUMN detected_lang TEXT;",
    "ALTER TABLE reviews ADD COLUMN language_confidence REAL;",
    "ALTER TABLE reviews ADD COLUMN is_analyzable INTEGER;",
]

def migrate():
    conn = get_connection()
    for stmt in MIGRATION_STATEMENTS:
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