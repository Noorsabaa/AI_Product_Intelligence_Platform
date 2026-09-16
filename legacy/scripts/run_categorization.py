# scripts/run_categorization.py
from db.connection import get_connection

MODEL = "all-MiniLM-L6-v2"
CATEGORY_CONFIDENCE_THRESHOLD = 0.7
KEYWORD_ROUTING_CONFIDENCE = 0.85
SECONDARY_CATEGORY_CONFIDENCE_THRESHOLD = 0.7
MIN_CATEGORY_TEXT_LENGTH = 10
_model = None
_label_embeddings = None

CATEGORY_KEYWORDS = {
    "Billing, Subscription & Account Management": (
        "charged", "subscription", "billing", "refund", "cancel"
    ),
    "Login & Authentication": (
        "sign in", "login", "password", "authentication", "authent", "ログイン"
    ),
    "Notifications & Alerts": (
        "notification", "push alert", "alerts arrive", "not at all"
    ),
    "Data & Sync Issues": (
        "sync", "synchron", "data is lost", "not saved"
    ),
    "Compatibility & Device Support": (
        "samsung", "android phone", "device", "compatibility"
    ),
    "Core Functionality Failure": (
        "messages will not send", "main feature", "does not work", "no funciona"
    ),
    "Missing or Limited Features": (
        "missing", "desktop features", "feature does not exist"
    ),
    "Performance & Stability": (
        "slow", "freezes", "crash", "crashing", "stability", "laggy"
    ),
    "UI/UX & Navigation": (
        "interface", "layout", "navigate", "privacy controls", "confusing"
    ),
}

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


def get_model_and_labels():
    global _model, _label_embeddings
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL)
        label_texts = list(CATEGORY_DESCRIPTIONS.values())
        _label_embeddings = _model.encode(label_texts, convert_to_tensor=True)
    return _model, _label_embeddings


def classify_by_keyword(text):
    matches = classify_by_keywords(text)
    return matches[0] if matches else None


def classify_by_keywords(text):
    normalized = text.casefold()
    matches = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword.casefold() in normalized for keyword in keywords):
            matches.append(category)
    return matches

def run_categorization(batch_size=64, commit_every=1000):
    from sentence_transformers import util

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE reviews
        SET category = NULL
        WHERE category IS NOT NULL
          AND category_confidence < ?
        """,
        (CATEGORY_CONFIDENCE_THRESHOLD,),
    )

    rows = cursor.execute("""
        SELECT review_id, content FROM reviews
        WHERE is_analyzable = 1
          AND sentiment IN ('negative', 'neutral')
            AND length(trim(content)) >= ?
          AND category IS NULL
        """, (MIN_CATEGORY_TEXT_LENGTH,)).fetchall()
    print(f"Rows to process: {len(rows)}")
    if not rows:
        conn.close()
        return

    model, label_embeddings = get_model_and_labels()
    labels = list(CATEGORY_DESCRIPTIONS.keys())

    processed = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        unresolved = []
        for review_id, text in batch:
            categories = classify_by_keywords(text)
            if categories:
                cursor.execute(
                    """
                    UPDATE reviews
                    SET category = ?, category_confidence = ?,
                        secondary_category = ?, secondary_category_confidence = ?
                    WHERE review_id = ?
                    """,
                    (
                        categories[0], KEYWORD_ROUTING_CONFIDENCE,
                        categories[1] if len(categories) > 1 else None,
                        KEYWORD_ROUTING_CONFIDENCE if len(categories) > 1 else None,
                        review_id,
                    ),
                )
            else:
                unresolved.append((review_id, text))

        if unresolved:
            texts = [r[1] for r in unresolved]
            review_embeddings = model.encode(texts, convert_to_tensor=True, batch_size=batch_size)
            similarities = util.cos_sim(review_embeddings, label_embeddings)
            for (review_id, _), sim_row in zip(unresolved, similarities):
                ranked_indices = sim_row.argsort(descending=True)
                best_idx = int(ranked_indices[0])
                best_score = float(sim_row[best_idx])
                secondary_idx = int(ranked_indices[1])
                secondary_score = float(sim_row[secondary_idx])
                if best_score < CATEGORY_CONFIDENCE_THRESHOLD:
                    cursor.execute(
                        """
                        UPDATE reviews
                        SET category = NULL, category_confidence = ?,
                            secondary_category = NULL,
                            secondary_category_confidence = NULL
                        WHERE review_id = ?
                        """,
                        (best_score, review_id),
                    )
                    continue
                cursor.execute(
                    """
                    UPDATE reviews
                    SET category = ?, category_confidence = ?,
                        secondary_category = ?, secondary_category_confidence = ?
                    WHERE review_id = ?
                    """,
                    (
                        labels[best_idx], best_score,
                        labels[secondary_idx] if secondary_score >= SECONDARY_CATEGORY_CONFIDENCE_THRESHOLD else None,
                        secondary_score if secondary_score >= SECONDARY_CATEGORY_CONFIDENCE_THRESHOLD else None,
                        review_id,
                    ),
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