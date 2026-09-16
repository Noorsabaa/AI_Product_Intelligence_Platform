"""Validate every row before opening a write transaction. Append is the default."""
import hashlib
from fastapi import HTTPException
from services.import_preprocessing import read_export, infer_date_order, normalize_date, normalize_rating
from services.storage import database, active_run, metadata, set_metadata, now

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50000


def parse_csv(raw, date_order='auto'):
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, 'CSV exceeds the 10 MB limit.')
    source_rows = read_export(raw, MAX_ROWS)
    order = infer_date_order(source_rows, date_order)
    rows, errors = [], []
    for number, row in source_rows:
        try:
            app = (row.get('app_name') or 'Workspace').strip() or 'Workspace'
            content = (row.get('content') or '').strip()
            if None in row or not content:
                raise ValueError('Review content is required; check CSV quoting.')
            if len(app) > 120 or len(content) > 20000:
                raise ValueError('App name or review is too long (120 / 20,000 characters).')
            score, rating_missing = normalize_rating(row.get('score') or '')
            day = normalize_date(row.get('review_date') or '', order)
            context = {key: (row.get(key) or '').strip()[:200] for key in ('segment', 'service', 'customer_id', 'source')}
            rows.append({'app_name': app, 'content': content, 'score': score, 'rating_missing': rating_missing, 'review_date': day, **context})
        except (ValueError, TypeError, OverflowError, OSError) as exc:
            if len(errors) < 20:
                errors.append({'row': number, 'message': str(exc) or 'Invalid rating or date.'})
    if errors:
        raise HTTPException(422, {'message': 'Nothing imported. These rows need attention after automatic format conversion.', 'errors': errors})
    if not rows:
        raise HTTPException(422, 'The CSV has no review rows.')
    return rows


def import_rows(rows, filename, mode='append'):
    if mode not in ('append', 'replace'):
        raise HTTPException(422, 'Mode must be append or replace.')
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if active_run(conn):
            raise HTTPException(409, 'Analysis is running. Wait until it finishes before importing.')
        if mode == 'replace':
            conn.execute('DELETE FROM review_context')
            conn.execute('DELETE FROM discovered_topics')
            conn.execute('DELETE FROM review_analysis')
            conn.execute('DELETE FROM reviews')
            conn.execute('DELETE FROM apps')
            conn.execute('DELETE FROM insight_actions')
        # Compare natural keys too, so importing existing Google Play rows is idempotent.
        known = {(r[0].casefold(), r[1].strip(), r[2][:10], r[3], r[4], r[5], r[6]) for r in conn.execute(
            '''SELECT a.app_name,r.content,r.review_date,r.score,COALESCE(c.rating_missing,0),
                      COALESCE(c.customer_id,''),COALESCE(c.source,'')
               FROM reviews r JOIN apps a USING(app_id) LEFT JOIN review_context c USING(review_id)''')}
        apps = {r[1].casefold(): r[0] for r in conn.execute('SELECT app_id,app_name FROM apps')}
        inserted = 0
        for row in rows:
            key = (row['app_name'].casefold(), row['content'], row['review_date'], row['score'], row.get('rating_missing',0), row.get('customer_id') or '', row.get('source') or '')
            if key in known:
                continue
            if key[0] not in apps:
                package = 'csv:' + hashlib.sha256(key[0].encode()).hexdigest()[:24]
                apps[key[0]] = conn.execute('INSERT INTO apps(app_name,package_name) VALUES (?,?)',
                                           (row['app_name'], package)).lastrowid
            review_id = 'csv_' + hashlib.sha256(repr(key).encode()).hexdigest()
            conn.execute('''INSERT INTO reviews(review_id,app_id,content,score,review_date,scraped_at)
                VALUES (?,?,?,?,?,?)''', (review_id, apps[key[0]], row['content'], row['score'], row['review_date'], now()))
            conn.execute('INSERT INTO review_context VALUES (?,?,?,?,?,?)',
                         (review_id, *(row.get(k) or None for k in ('segment','service','customer_id','source')), row.get('rating_missing',0)))
            known.add(key)
            inserted += 1
        if inserted or mode == 'replace':
            set_metadata(conn, 'dataset_revision', int(metadata(conn, 'dataset_revision', '0')) + 1)
        duplicates = len(rows) - inserted
        conn.execute('INSERT INTO imports(filename,created_at,inserted,duplicates,mode) VALUES (?,?,?,?,?)',
                     (filename, now(), inserted, duplicates, mode))
        return {'inserted': inserted, 'duplicates': duplicates, 'mode': mode, 'total_rows': len(rows)}
