import hashlib
import io
import csv
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from db.connection import get_connection
from ingestion.scraper import upsert_app


router = APIRouter()

REQUIRED_COLUMNS = {"app_name", "content", "review_date", "score"}


def make_review_id(app_name, content, review_date):
    raw = f"{app_name}|{content}|{review_date}"
    return "csv_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@router.post("/csv")
async def ingest_csv(file: UploadFile = File(...)):

    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "File must be a .csv")

    raw = await file.read()
    text = raw.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise HTTPException(
            400,
            f"CSV must contain columns: {sorted(REQUIRED_COLUMNS)}. "
            f"Found: {reader.fieldnames}",
        )

    conn = get_connection()
    cursor = conn.cursor()

    inserted = 0
    skipped = 0
    app_id_cache = {}

    for row in reader:

        app_name = row["app_name"].strip()
        content = row["content"].strip()
        review_date = row["review_date"].strip()

        if not content or not review_date:
            skipped += 1
            continue

        try:
            score = int(row["score"])

            if not (1 <= score <= 5):
                raise ValueError

        except (ValueError, TypeError):
            skipped += 1
            continue

        if app_name not in app_id_cache:

            package_name = f"csv:{app_name.lower().replace(' ', '_')}"

            app_id_cache[app_name] = upsert_app(
                conn,
                app_name,
                package_name
            )

        app_id = app_id_cache[app_name]

        review_id = make_review_id(
            app_name,
            content,
            review_date
        )

        scraped_at = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """
            INSERT OR IGNORE INTO reviews (
                review_id,
                app_id,
                content,
                score,
                thumbs_up_count,
                review_date,
                scraped_at
            )
            VALUES (?, ?, ?, ?, 0, ?, ?)
            """,
            (
                review_id,
                app_id,
                content,
                score,
                review_date,
                scraped_at,
            ),
        )

        if cursor.rowcount == 1:
            inserted += 1

    conn.commit()
    conn.close()

    return {
        "inserted": inserted,
        "skipped": skipped,
        "note": "Run the pipeline (cleaning, sentiment, categorization) to process these new rows.",
    }