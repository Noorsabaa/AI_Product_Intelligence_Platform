"""Atomic discovery pipeline shared by the API and CLI."""
import hashlib
import json
import logging
import os
import uuid
from collections import Counter
from functools import lru_cache

from fastapi import HTTPException
from langdetect import DetectorFactory, detect_langs, LangDetectException
from services.storage import database, active_run, metadata, set_metadata, now
from services.discovery import discover_topics

DetectorFactory.seed = 0
LOGGER = logging.getLogger(__name__)
SENTIMENT_MODEL = os.getenv('SENTIMENT_MODEL', 'cardiffnlp/twitter-roberta-base-sentiment-latest')

@lru_cache(maxsize=12000)
def detect_language(text):
    if sum(c.isalpha() for c in text) < 12:
        return 'unknown'
    try:
        result = detect_langs(text[:3000])[0]
        return result.lang if result.prob >= .8 else 'unknown'
    except LangDetectException:
        return 'unknown'


def reserve_run(engine='semantic'):
    engine = {'local': 'lexical', 'transformer': 'semantic'}.get(engine, engine)
    if engine not in ('semantic', 'lexical'):
        raise HTTPException(422, 'Choose semantic or lexical discovery.')
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if active_run(conn):
            raise HTTPException(409, 'An analysis is already running.')
        total = conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
        if not total:
            raise HTTPException(422, 'Import feedback before running analysis.')
        run_id = uuid.uuid4().hex
        conn.execute('''INSERT INTO pipeline_runs(id,status,stage,total,started_at,engine)
                        VALUES (?,'queued','Queued',?,?,?)''', (run_id, total, now(), engine))
        return run_id


def update_run(run_id, **fields):
    allowed = {'status', 'stage', 'progress', 'processed', 'finished_at', 'error', 'summary'}
    if not fields.keys() <= allowed:
        raise ValueError('Unknown run fields')
    with database() as conn:
        conn.execute('UPDATE pipeline_runs SET ' + ','.join(f'{key}=?' for key in fields) + ' WHERE id=?',
                     (*fields.values(), run_id))


@lru_cache(maxsize=1)
def load_transformer():
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        tokenizer = AutoTokenizer.from_pretrained(SENTIMENT_MODEL, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL, local_files_only=True)
        return pipeline('sentiment-analysis', model=model, tokenizer=tokenizer, device=-1)
    except Exception as exc:
        raise RuntimeError('The English sentiment model is unavailable. Complete model setup or use Lexical discovery with rating signals. Published results are unchanged.') from exc


def text_sentiments(texts, progress):
    unique = sorted(set(texts))
    hashes = {text: hashlib.sha256(text.encode()).hexdigest() for text in unique}
    with database() as conn:
        known = dict(conn.execute('SELECT text_hash,label FROM sentiment_cache WHERE model=?', (SENTIMENT_MODEL,)))
    missing = [text for text in unique if hashes[text] not in known]
    if missing:
        model = load_transformer()
        for offset in range(0, len(missing), 16):
            batch = missing[offset:offset + 16]
            results = model(batch, truncation=True, max_length=512, batch_size=8)
            with database() as conn:
                for text, result in zip(batch, results):
                    label = result['label'].lower()
                    label = {'label_0': 'negative', 'label_1': 'neutral', 'label_2': 'positive'}.get(label, label)
                    if label not in ('negative', 'neutral', 'positive'):
                        raise RuntimeError('Unsupported sentiment model labels.')
                    known[hashes[text]] = label
                    conn.execute('INSERT OR REPLACE INTO sentiment_cache VALUES (?,?,?)', (hashes[text], SENTIMENT_MODEL, label))
            progress('Reading sentiment', 10 + round(25 * min(offset + 16, len(missing)) / len(missing)))
    return {text: known[key] for text, key in hashes.items()}, len(unique) - len(missing)


def run_pipeline(run_id):
    try:
        update_run(run_id, status='running', stage='Preparing feedback', progress=2)
        with database() as conn:
            rows = [dict(r) for r in conn.execute('''SELECT r.review_id,r.content,r.score,x.language,
                COALESCE(c.rating_missing,0) AS rating_missing FROM reviews r
                LEFT JOIN review_analysis x USING(review_id) LEFT JOIN review_context c USING(review_id)
                ORDER BY r.review_id''')]
            engine = conn.execute('SELECT engine FROM pipeline_runs WHERE id=?', (run_id,)).fetchone()[0]
            revision = metadata(conn, 'dataset_revision')
            previous_topics = [dict(r) for r in conn.execute('SELECT * FROM discovered_topics')]
            source_names = [r[0] for r in conn.execute('SELECT app_name FROM apps')]
        def progress(stage, percent):
            update_run(run_id, stage=stage, progress=percent)
        for index, row in enumerate(rows):
            row['language'] = row['language'] or detect_language(row['content'])
            if index % 200 == 0:
                progress('Identifying languages', 3 + round(6 * index / len(rows)))
        predictions, sentiment_cache_hits = ({}, 0)
        if engine == 'semantic':
            predictions, sentiment_cache_hits = text_sentiments([r['content'] for r in rows if r['language'] == 'en'], progress)
        for row in rows:
            if row['content'] in predictions:
                row.update(sentiment=predictions[row['content']], sentiment_method='text_model')
            elif not row['rating_missing']:
                row.update(sentiment='negative' if row['score'] <= 2 else 'neutral' if row['score'] == 3 else 'positive', sentiment_method='rating')
            else:
                row.update(sentiment=None, sentiment_method='unavailable')
        progress('Preparing category discovery', 38)
        topics, assignments, discovery = discover_topics(rows, engine, previous_topics, source_names, progress)
        topic_names = {t['id']: t['custom_label'] or t['label'] for t in topics}
        output = []
        for row in rows:
            match = assignments[row['review_id']]
            output.append((row['review_id'], row['language'], row['sentiment'], row['sentiment_method'],
                           topic_names.get(match['topic_id']), engine, '[]', run_id,
                           match['topic_id'], match['strength'], match['reason']))
        progress('Publishing categories and evidence', 94)
        summary = json.dumps({'version': 3, 'reviews': len(rows), 'categories': len(topics),
            'grouped': sum(bool(r[8]) for r in output), 'ungrouped': sum(not r[8] for r in output),
            'languages': dict(Counter(r['language'] for r in rows)),
            'sentiment_methods': dict(Counter(r['sentiment_method'] for r in rows)),
            'sentiment_cache_hits': sentiment_cache_hits, 'sentiment_model': SENTIMENT_MODEL if engine == 'semantic' else None,
            'discovery': discovery})
        with database() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if metadata(conn, 'dataset_revision') != revision:
                raise RuntimeError('Dataset changed during analysis. Run analysis again.')
            conn.execute('DELETE FROM review_analysis')
            conn.execute('DELETE FROM discovered_topics')
            conn.executemany('''INSERT INTO review_analysis(review_id,language,sentiment,sentiment_method,category,
                category_method,matched_terms,run_id,topic_id,topic_strength,analysis_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?)''', output)
            conn.executemany('INSERT INTO discovered_topics VALUES (?,?,?,?,?,?,?,?)',
                [(t['id'], t['label'], json.dumps(t['keywords']), t['custom_label'], t['model'], run_id,
                  json.dumps(t['member_ids']), t['coherence']) for t in topics])
            set_metadata(conn, 'published_revision', revision)
            set_metadata(conn, 'published_run', run_id)
            set_metadata(conn, 'pipeline_version', '3')
            conn.execute('''UPDATE pipeline_runs SET status='completed', stage='Complete', progress=100,
                processed=?, finished_at=?, summary=? WHERE id=?''', (len(rows), now(), summary, run_id))
    except Exception as exc:
        LOGGER.exception('Analysis failed for run %s', run_id)
        update_run(run_id, status='failed', finished_at=now(), error=str(exc), stage='Failed')


def latest_run():
    with database() as conn:
        row = conn.execute('SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 1').fetchone()
        return dict(row) if row else {'status': 'idle', 'stage': 'Ready to analyze', 'progress': 0, 'processed': 0, 'total': 0}
