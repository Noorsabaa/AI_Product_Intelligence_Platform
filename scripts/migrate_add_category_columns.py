# scripts/migrate_add_category_columns.py
from db.connection import get_connection

STATEMENTS = [
    "ALTER TABLE reviews ADD COLUMN category TEXT;",
    "ALTER TABLE reviews ADD COLUMN category_confidence REAL;",
]

def migrate():
    conn = get_connection()
    for stmt in STATEMENTS:
        try:
            conn.execute(stmt)
        except Exception as e:
            if "duplicate column name" in str(e):
                print(f"Skipping (already applied): {stmt}")
            else:
                raise
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()