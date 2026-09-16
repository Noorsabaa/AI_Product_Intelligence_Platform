# scripts/run_sentiment.py
from db.connection import get_connection

# XLM-R supports the multilingual reviews accepted by language detection.
MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
FALLBACK_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
RATING_FALLBACK_CONFIDENCE = 0.85
_classifier = None
_active_model_name = None


def get_classifier():
    global _classifier, _active_model_name
    if _classifier is None:
        from transformers import pipeline

        try:
            _classifier = pipeline(
                "sentiment-analysis", model=MODEL, tokenizer=MODEL,
                local_files_only=True,
            )
            _active_model_name = MODEL
        except Exception:
            # Do not block the API when an optional multilingual model is unavailable.
            _classifier = pipeline(
                "sentiment-analysis", model=FALLBACK_MODEL,
                tokenizer=FALLBACK_MODEL, local_files_only=True,
            )
            _active_model_name = FALLBACK_MODEL
    return _classifier


def calibrate_sentiment(label, confidence, score):
    if confidence < RATING_FALLBACK_CONFIDENCE:
        if score == 3:
            return "neutral"
        if score <= 2 and label == "positive":
            return "negative"
        if score >= 4 and label == "negative":
            return "positive"
    return label

def run_sentiment(batch_size=32, commit_every=200):
    conn = get_connection()
    cursor = conn.cursor()
    clf = get_classifier()

    if _active_model_name == FALLBACK_MODEL:
        cursor.execute(
            """
            UPDATE reviews
            SET sentiment = NULL, sentiment_confidence = NULL
            WHERE language IS NOT NULL AND language != 'en'
            """
        )
        language_filter = "AND language = 'en'"
        print("Multilingual model unavailable; processing English reviews only.")
    else:
        language_filter = ""

    rows = cursor.execute(f"""
        SELECT review_id, content, score FROM reviews
        WHERE is_analyzable = 1 AND sentiment IS NULL
        {language_filter}
    """).fetchall()
    print(f"Rows to process: {len(rows)}")

    if not rows:
        conn.close()
        print("No sentiment work pending.")
        return

    processed = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = [r[1] for r in batch]

        try:
            results = clf(texts, truncation=True, max_length=512)
        except Exception as e:
            print(f"Batch failed ({e}), falling back to per-row processing...")
            results = []
            for text in texts:
                try:
                    results.append(clf(text, truncation=True, max_length=512)[0])
                except Exception as row_err:
                    print(f"  Skipping unprocessable row: {row_err}")
                    results.append(None)

        for (review_id, _, rating), result in zip(batch, results):
            if result is None:
                continue
            score = result["score"]
            label = calibrate_sentiment(
                result["label"].lower(), score, rating
            )
            cursor.execute(
                "UPDATE reviews SET sentiment = ?, sentiment_confidence = ? WHERE review_id = ?",
                (label, score, review_id),
            )

        processed += len(batch)
        if processed % commit_every < batch_size or processed == len(rows):
            conn.commit()
            print(f"Processed {processed}/{len(rows)}")

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    run_sentiment()