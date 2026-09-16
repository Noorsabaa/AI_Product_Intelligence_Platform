"""Explicit one-time downloads. Normal analysis uses local files only."""
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from services.discovery import EMBEDDING_MODEL
from services.analysis import SENTIMENT_MODEL


def main():
    print('Downloading/caching the topic and English sentiment models. No feedback is uploaded.')
    SentenceTransformer(EMBEDDING_MODEL, device='cpu')
    AutoTokenizer.from_pretrained(SENTIMENT_MODEL)
    AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL)
    print('Models ready. Subsequent analysis uses this local cache.')


if __name__ == '__main__':
    main()
