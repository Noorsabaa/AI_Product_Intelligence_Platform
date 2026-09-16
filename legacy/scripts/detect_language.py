# scripts/detect_language.py
import unicodedata
from fast_langdetect import detect
from db.connection import get_connection


def strip_symbols(text):
    """
    Returns a copy of text with emoji/symbols removed, keeping letters,
    marks, numbers, punctuation, and spaces (any script). Used only to
    decide analyzability and to feed the detector — never written back
    over the original `content` column.
    """
    if not text:
        return ""
    kept = [ch for ch in text if unicodedata.category(ch).startswith(("L", "M", "N", "P", "Z"))]
    cleaned = " ".join("".join(kept).split())
    has_letter = any(unicodedata.category(c).startswith("L") for c in cleaned)
    return cleaned if has_letter else ""


def classify_language(cleaned_text, confidence_threshold=0.7):
    result = detect(cleaned_text.replace("\n", " "))[0]
    detected_lang = result["lang"]
    confidence = result["score"]

    if detected_lang == "en":
        language = "en"
    elif confidence >= confidence_threshold:
        language = "other"
    else:
        language = "unknown"

    return language, detected_lang, confidence


def run_language_detection(batch_commit_size=500):
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute(
        "SELECT review_id, content FROM reviews WHERE language IS NULL"
    ).fetchall()
    print(f"Rows to process: {len(rows)}")

    processed = 0
    for review_id, content in rows:
        cleaned = strip_symbols(content)

        if not cleaned:
            cursor.execute(
                """
                UPDATE reviews
                SET is_analyzable = 0, language = 'unknown',
                    detected_lang = NULL, language_confidence = NULL
                WHERE review_id = ?
                """,
                (review_id,),
            )
        else:
            language, detected_lang, confidence = classify_language(cleaned)
            cursor.execute(
                """
                UPDATE reviews
                SET is_analyzable = 1, language = ?,
                    detected_lang = ?, language_confidence = ?
                WHERE review_id = ?
                """,
                (language, detected_lang, confidence, review_id),
            )

        processed += 1
        if processed % batch_commit_size == 0:
            conn.commit()
            print(f"Processed {processed}/{len(rows)}...")

    conn.commit()
    conn.close()
    print(f"Done. Total processed: {processed}")


if __name__ == "__main__":
    run_language_detection()