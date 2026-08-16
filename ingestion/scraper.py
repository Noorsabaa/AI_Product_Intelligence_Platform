# ingestion/scraper.py
import time
from datetime import datetime, timedelta, timezone

from google_play_scraper import reviews, Sort


def upsert_app(conn, app_name, package_name):
    """
    Insert an app if it does not already exist,
    then return its app_id.
    """
    conn.execute(
        """
        INSERT OR IGNORE INTO apps (app_name, package_name)
        VALUES (?, ?);
        """,
        (app_name, package_name)
    )
    conn.commit()

    result = conn.execute(
        """
        SELECT app_id
        FROM apps
        WHERE package_name = ?;
        """,
        (package_name,)
    ).fetchone()

    return result[0]


def scrape_and_store_reviews(
    conn,
    app_id,
    package_name,
    count=200,
    days_back=180,
    max_pages=100,
    max_reviews=20000,
):
    """
    Scrape Google Play reviews using pagination, stopping once
    reviews older than `days_back` days are reached.

    max_pages / max_reviews are safety backstops only — they
    should rarely be the actual reason the loop stops for a
    normal app.
    """
    cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)
    print(f"Target cutoff date: {cutoff_date.isoformat()}")

    continuation_token = None
    page_count = 0
    processed_reviews = 0
    inserted_reviews = 0
    reached_cutoff = False

    while continuation_token is not None or page_count == 0:

        if page_count >= max_pages:
            print("Safety limit hit: maximum page count reached.")
            break
        if processed_reviews >= max_reviews:
            print("Safety limit hit: maximum review count reached.")
            break

        page_count += 1
        print(f"Scraping page {page_count}...")

        result, continuation_token = reviews(
            package_name,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=count,
            continuation_token=continuation_token,
        )

        if not result:
            print("No more reviews returned.")
            break

        for review in result:
            review_date = review["at"]

            # This review (and everything after it in this page,
            # since it's sorted newest -> oldest) is past our window.
            if review_date < cutoff_date:
                reached_cutoff = True
                break

            review_id = review["reviewId"]
            content = review["content"]
            score = review["score"]
            thumbs_up_count = review["thumbsUpCount"]
            reply_content = review.get("replyContent")
            replied_at = review.get("repliedAt")
            app_version = review.get("appVersion")
            scraped_at = datetime.now(timezone.utc).isoformat()

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO reviews (
                    review_id, app_id, content, score, thumbs_up_count,
                    reply_content, replied_at, app_version,
                    review_date, scraped_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id, app_id, content, score, thumbs_up_count,
                    reply_content,
                    replied_at.isoformat() if replied_at else None,
                    app_version, review_date.isoformat(), scraped_at,
                )
            )

            if cursor.rowcount == 1:
                inserted_reviews += 1
            processed_reviews += 1

        conn.commit()
        print(
            f"Page {page_count}: {processed_reviews} reviews processed so far, "
            f"{inserted_reviews} new reviews inserted so far."
        )

        if reached_cutoff:
            print(f"Reached {days_back}-day cutoff. Stopping.")
            break
        if continuation_token is None:
            print("No more pages available (exhausted all reviews).")
            break

        time.sleep(1)

    print(f"Total reviews processed: {processed_reviews}")
    print(f"Total new reviews inserted: {inserted_reviews}")
    return inserted_reviews