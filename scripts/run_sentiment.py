# scripts/run_sentiment.py
from transformers import pipeline
from db.connection import get_connection

MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"

def run_sentiment(batch_size=32, commit_every=200):
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT review_id, content FROM reviews
        WHERE is_analyzable = 1 AND language != 'other' AND sentiment IS NULL
    """).fetchall()
    print(f"Rows to process: {len(rows)}")

    if not rows:
        conn.close()
        print("No sentiment work pending.")
        return

    clf = pipeline("sentiment-analysis", model=MODEL, tokenizer=MODEL)

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

        for (review_id, _), result in zip(batch, results):
            if result is None:
                continue
            label = result["label"].lower()
            score = result["score"]
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