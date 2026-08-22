# scripts/run_categorization.py
from sentence_transformers import SentenceTransformer, util
from db.connection import get_connection

MODEL = "all-MiniLM-L6-v2"

CATEGORY_DESCRIPTIONS = {
    "Performance & Stability": "The app is slow, laggy, freezes, or crashes.",
    "Login & Authentication": "Problems signing in, logging in, passwords, or two-factor authentication.",
    "Core Functionality Failure": "The app's main feature does not work, such as sending messages, saving tasks, or loading content.",
    "UI/UX & Navigation": "The interface is confusing, ugly, hard to navigate, or a redesign is disliked.",
    "Missing or Limited Features": "A feature is missing on mobile compared to desktop, or a requested feature does not exist.",
    "Compatibility & Device Support": "The app does not work on a specific phone, Android version, or device.",
    "Data & Sync Issues": "Data is lost, not saved, or does not sync properly across devices.",
    "Notifications & Alerts": "Notifications are not received, delayed, or push alerts do not work.",
    "Billing, Subscription & Account Management": "Problems with billing, subscription charges, refunds, or cancelling a plan.",
    "Other / General Feedback": "General comments, praise, or feedback that does not fit another category.",
}

def run_categorization(batch_size=64, commit_every=1000):
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT review_id, content FROM reviews
        WHERE is_analyzable = 1 AND language != 'other'
          AND sentiment IN ('negative', 'neutral')
          AND category IS NULL
    """).fetchall()
    print(f"Rows to process: {len(rows)}")
    if not rows:
        conn.close()
        return

    model = SentenceTransformer(MODEL)
    labels = list(CATEGORY_DESCRIPTIONS.keys())
    label_texts = list(CATEGORY_DESCRIPTIONS.values())
    label_embeddings = model.encode(label_texts, convert_to_tensor=True)

    processed = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = [r[1] for r in batch]
        review_embeddings = model.encode(texts, convert_to_tensor=True, batch_size=batch_size)
        similarities = util.cos_sim(review_embeddings, label_embeddings)

        for (review_id, _), sim_row in zip(batch, similarities):
            best_idx = int(sim_row.argmax())
            cursor.execute(
                "UPDATE reviews SET category = ?, category_confidence = ? WHERE review_id = ?",
                (labels[best_idx], float(sim_row[best_idx]), review_id),
            )

        processed += len(batch)
        if processed % commit_every < batch_size or processed == len(rows):
            conn.commit()
            print(f"Processed {processed}/{len(rows)}")

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    run_categorization()