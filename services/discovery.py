"""Open-set topic discovery: no category dictionary, no forced outlier assignment."""
import hashlib
import json
import os
import re
import uuid
from functools import lru_cache

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import HDBSCAN
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.preprocessing import normalize
from services.storage import database

EMBEDDING_MODEL = os.getenv('TOPIC_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
GENERIC_WORDS = {'app', 'application', 'really', 'just', 'use', 'using', 'used', 'like', 'please', 'im', 'ive', 'dont', 'did', 'does', 'great', 'good', 'bad', 'worst', 'best', 'new', 'old', 'makes', 'make'}


def clean_text(text, excluded=()):
    text = re.sub(r'https?://\S+|\b\S+@\S+\.\S+\b', ' ', text.casefold())
    for name in sorted(excluded, key=len, reverse=True):
        if name:
            text = re.sub(r'(?<!\w)' + re.escape(name.casefold()) + r'(?!\w)', ' ', text)
    return ' '.join(text.split())


@lru_cache(maxsize=1)
def embedding_model():
    try:
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        return SentenceTransformer(EMBEDDING_MODEL, local_files_only=True, device='cpu')
    except Exception as exc:
        raise RuntimeError('The semantic topic model is not available locally. Complete model setup or choose Lexical discovery. No categories were changed.') from exc


def cached_embeddings(texts, progress):
    hashes = [hashlib.sha256(text.encode()).hexdigest() for text in texts]
    with database() as conn:
        known = {r[0]: np.frombuffer(r[1], dtype=np.float32).copy() for r in conn.execute(
            'SELECT text_hash,vector FROM feature_cache WHERE model=?', (EMBEDDING_MODEL,))}
    missing = [(h, t) for h, t in zip(hashes, texts) if h not in known]
    if missing:
        model = embedding_model()
        for offset in range(0, len(missing), 64):
            batch = missing[offset:offset + 64]
            vectors = model.encode([t for _, t in batch], batch_size=32, normalize_embeddings=True, show_progress_bar=False)
            with database() as conn:
                for (key, _), vector in zip(batch, vectors):
                    known[key] = np.asarray(vector, dtype=np.float32)
                    conn.execute('INSERT OR REPLACE INTO feature_cache VALUES (?,?,?)',
                                 (key, EMBEDDING_MODEL, known[key].tobytes()))
            progress('Understanding review meaning', 40 + round(25 * min(offset + 64, len(missing)) / len(missing)))
    return np.stack([known[h] for h in hashes]), len(texts) - len(missing)


def match_topic_ids(new_topics, old_topics):
    """One-to-one overlap matching; do not merge unrelated historical identities."""
    if not new_topics or not old_topics:
        return
    old_members = [set(json.loads(t['member_ids'])) for t in old_topics]
    scores = np.zeros((len(new_topics), len(old_topics)))
    for i, new in enumerate(new_topics):
        members = set(new['member_ids'])
        for j, old in enumerate(old_members):
            scores[i, j] = len(members & old) / max(1, len(members | old))
    current, previous = linear_sum_assignment(-scores)
    for i, j in zip(current, previous):
        if scores[i, j] >= .5:
            new_topics[i]['id'] = old_topics[j]['id']
            new_topics[i]['custom_label'] = old_topics[j]['custom_label']


def discover_topics(rows, engine, previous_topics, excluded=(), progress=lambda *_: None):
    assignments = {r['review_id']: {'topic_id': None, 'strength': None,
        'reason': 'unsupported_language' if r['language'] != 'en' else 'insufficient_text'} for r in rows}
    grouped = {}
    for row in rows:
        text = clean_text(row['content'], excluded)
        if row['language'] == 'en' and len(re.findall(r'\b[a-z]{2,}\b', text)) >= 4:
            grouped.setdefault(text, []).append(row['review_id'])
            assignments[row['review_id']]['reason'] = 'no_coherent_group'
    texts = sorted(grouped)
    if len(texts) < 6:
        return [], assignments, {'distinct_texts': len(texts), 'cache_hits': 0, 'method': engine}
    # Deterministic fitting cap bounds local density-clustering memory. Unfitted text abstains.
    fit_texts = sorted(texts, key=lambda t: hashlib.sha256(t.encode()).hexdigest())[:10000]
    for text in set(texts) - set(fit_texts):
        for review_id in grouped[text]:
            assignments[review_id]['reason'] = 'discovery_capacity_limit'
    stopwords = sorted(set(ENGLISH_STOP_WORDS) | GENERIC_WORDS | {word.casefold() for name in excluded for word in name.split()})
    cache_hits = 0
    if engine == 'semantic':
        vectors, cache_hits = cached_embeddings(fit_texts, progress)
        from umap import UMAP
        reduced = UMAP(n_neighbors=min(15, len(fit_texts)-1), n_components=min(5, len(fit_texts)-2),
                       metric='cosine', random_state=42, n_jobs=1, low_memory=True).fit_transform(vectors)
    else:
        try:
            tfidf = TfidfVectorizer(stop_words=stopwords, ngram_range=(1, 2), sublinear_tf=True,
                                    max_features=12000, min_df=2).fit_transform(fit_texts)
        except ValueError:
            return [], assignments, {'distinct_texts': len(texts), 'cache_hits': 0, 'method': engine}
        if tfidf.shape[1] < 2:
            return [], assignments, {'distinct_texts': len(texts), 'cache_hits': 0, 'method': engine}
        vectors = tfidf
        reduced = TruncatedSVD(n_components=min(32, tfidf.shape[1] - 1, len(fit_texts) - 1), random_state=42).fit_transform(tfidf)
    if engine != 'semantic':
        reduced = normalize(reduced)
    progress('Discovering recurring categories', 72)
    min_size = max(3, min(10, round(len(fit_texts) ** .5 / 4)))
    clustering = HDBSCAN(min_cluster_size=min_size, min_samples=2, cluster_selection_method='eom',
                         allow_single_cluster=False, n_jobs=2, copy=True).fit(reduced)
    labels, strengths = clustering.labels_, clustering.probabilities_
    try:
        vectorizer = CountVectorizer(stop_words=stopwords, ngram_range=(1, 2), min_df=1, max_features=15000)
        words = vectorizer.fit_transform(fit_texts)
    except ValueError:
        return [], assignments, {'distinct_texts': len(texts), 'cache_hits': cache_hits, 'method': engine}
    features = vectorizer.get_feature_names_out()
    candidate_clusters = []
    for label in sorted(set(labels) - {-1}):
        indices = np.flatnonzero((labels == label) & (strengths >= .35))
        if len(indices) < 3:
            continue
        # Reject diffuse members even when the density algorithm gives them a label.
        if engine == 'semantic':
            centroid = normalize(np.mean(vectors[indices], axis=0, keepdims=True))[0]
            similarities = vectors[indices] @ centroid
            indices = indices[similarities >= .50]
            coherence = float(np.mean(similarities))
        else:
            centroid = normalize(np.asarray(vectors[indices].mean(axis=0)))[0]
            similarities = np.asarray(vectors[indices] @ centroid).ravel()
            indices = indices[similarities >= .24]
            coherence = float(np.mean(similarities))
        if len(indices) >= 3:
            candidate_clusters.append((indices, coherence))
    if not candidate_clusters:
        return [], assignments, {'distinct_texts': len(texts), 'cache_hits': cache_hits, 'method': engine}
    # Class-level TF-IDF describes the clusters; it does not decide their membership.
    counts = np.stack([np.asarray(words[indices].sum(axis=0)).ravel() for indices, _ in candidate_clusters])
    tf = counts / np.maximum(1, counts.sum(axis=1, keepdims=True))
    idf = np.log(1 + counts.sum(axis=1).mean() / np.maximum(1, counts.sum(axis=0)))
    topics = []
    for cluster_index, (indices, coherence) in enumerate(candidate_clusters):
        scores = tf[cluster_index] * idf
        ranked = sorted(range(len(features)), key=lambda i: -(scores[i] * (1.35 if ' ' in features[i] else 1)))
        keywords = []
        for feature_index in ranked:
            phrase = features[feature_index]
            if scores[feature_index] <= 0:
                break
            if not any({w.rstrip('s') for w in phrase.split()} & {w.rstrip('s') for w in k.split()} for k in keywords):
                keywords.append(phrase)
            if len(keywords) == 6:
                break
        label = ' / '.join(keywords[:2]).capitalize() or 'Unnamed cluster'
        member_ids = [rid for index in indices for rid in grouped[fit_texts[index]]]
        topics.append({'id': uuid.uuid4().hex[:20], 'label': label, 'keywords': keywords,
                       'custom_label': None, 'member_ids': member_ids, 'coherence': round(coherence, 4),
                       'model': EMBEDDING_MODEL if engine == 'semantic' else 'tfidf-svd-hdbscan',
                       '_indices': indices})
    match_topic_ids(topics, previous_topics)
    for topic in topics:
        for index in topic.pop('_indices'):
            for review_id in grouped[fit_texts[index]]:
                assignments[review_id] = {'topic_id': topic['id'], 'strength': round(float(strengths[index]), 4), 'reason': 'grouped'}
    return topics, assignments, {'distinct_texts': len(texts), 'fit_texts': len(fit_texts),
                                 'cache_hits': cache_hits, 'method': engine}
