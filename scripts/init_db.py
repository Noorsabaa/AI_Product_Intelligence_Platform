from db.connection import get_connection
from pathlib import Path
import sqlite3


DERIVED_COLUMNS = (
    ("language", "TEXT"),
    ("detected_lang", "TEXT"),
    ("language_confidence", "REAL"),
    ("is_analyzable", "INTEGER"),
    ("sentiment", "TEXT"),
    ("sentiment_confidence", "REAL"),
    ("category", "TEXT"),
    ("category_confidence", "REAL"),
    ("secondary_category", "TEXT"),
    ("secondary_category_confidence", "REAL"),
)


def init_db():
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    schema_sql = schema_path.read_text()

    conn = get_connection()
    try:
        conn.executescript(schema_sql)

        # Add columns for databases created before the derived fields were
        # included in db/schema.sql.
        for column_name, column_type in DERIVED_COLUMNS:
            try:
                conn.execute(
                    f"ALTER TABLE reviews ADD COLUMN {column_name} {column_type}"
                )
            except sqlite3.OperationalError as error:
                if "duplicate column name" not in str(error):
                    raise

        conn.execute("DROP VIEW IF EXISTS reviews_categorized_confident")
        conn.execute("DROP VIEW IF EXISTS reviews_trend_window")
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()