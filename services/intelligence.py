"""One-company feedback analysis. Every numerator has an explicit denominator."""
import json
import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from services.storage import database, metadata


def _load(conn, days=90, topic_id='', sentiment='', search='', segment='', service=''):
    published = metadata(conn, 'pipeline_version') == '3'
    stats = conn.execute("SELECT COUNT(*),MIN(date(review_date)),MAX(date(review_date)) FROM reviews WHERE date(review_date)<=date('now')").fetchone()
    dataset_total = conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
    end = stats[2] or date.today().isoformat()
    start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat() if days else stats[1] or end
    run_id = metadata(conn, 'published_run')
    run = conn.execute('SELECT * FROM pipeline_runs WHERE id=?', (run_id,)).fetchone() if published else None
    topics = [dict(t) for t in conn.execute('SELECT * FROM discovered_topics')] if published else []
    query = '''SELECT r.review_id,r.content,date(r.review_date) AS review_date,
        CASE WHEN COALESCE(c.rating_missing,0)=1 THEN NULL ELSE r.score END AS score,
        x.sentiment,x.sentiment_method,x.language,x.topic_id,x.topic_strength,x.analysis_reason,
        COALESCE(t.custom_label,t.label) AS category,t.keywords,c.segment,c.service,c.customer_id,c.source
        FROM reviews r LEFT JOIN review_analysis x ON x.review_id=r.review_id AND ?
        LEFT JOIN discovered_topics t ON t.id=x.topic_id LEFT JOIN review_context c USING(review_id)
        WHERE date(r.review_date) BETWEEN ? AND ?'''
    params = [int(published), start, end]
    if topic_id == 'ungrouped':
        query += ' AND x.topic_id IS NULL'
    elif topic_id:
        query += ' AND x.topic_id=?'
        params.append(topic_id)
    if sentiment:
        query += " AND COALESCE(x.sentiment,'pending')=?"
        params.append(sentiment)
    if search:
        query += ' AND instr(lower(r.content),lower(?))>0'
        params.append(search)
    for column, value in [('segment', segment), ('service', service)]:
        if value:
            query += f' AND c.{column}=?'
            params.append(value)
    query += ' ORDER BY r.review_date DESC,r.review_id'
    rows = [dict(row) for row in conn.execute(query, params)]
    scope = {'start': start, 'end': end, 'days': days, 'dataset_total': dataset_total,
             'invalid_dates': dataset_total - stats[0], 'published_run': dict(run) if run else None,
             'needs_analysis': not published or metadata(conn, 'dataset_revision') != metadata(conn, 'published_revision')}
    return rows, scope, topics


def load_scope(days=90, topic_id='', sentiment='', search='', segment='', service=''):
    with database() as conn:
        conn.execute('BEGIN')
        return _load(conn, days, topic_id, sentiment, search, segment, service)


def priority_categories(rows, topics, scope):
    analyzed = [r for r in rows if r['sentiment']]
    groups = defaultdict(list)
    for row in analyzed:
        if row['topic_id']:
            groups[row['topic_id']].append(row)
    negative_total = sum(r['sentiment'] == 'negative' for r in analyzed)
    overall_rate = negative_total / max(1, len(analyzed))
    end = date.fromisoformat(scope['end'])
    recent_start, baseline_start = (end - timedelta(days=6)).isoformat(), (end - timedelta(days=34)).isoformat()
    recent_total = sum(r['review_date'] >= recent_start for r in analyzed)
    baseline_total = sum(baseline_start <= r['review_date'] < recent_start for r in analyzed)
    history = min((r['review_date'] for r in analyzed), default=scope['end']) <= baseline_start
    enough_history = history and scope['start'] <= baseline_start and recent_total >= 10 and baseline_total >= 20
    definitions = {t['id']: t for t in topics}
    result = []
    for topic_id, evidence in groups.items():
        definition = definitions[topic_id]
        counts = Counter(r['sentiment'] for r in evidence)
        negative = counts['negative']
        recent = sum(r['sentiment'] == 'negative' and r['review_date'] >= recent_start for r in evidence)
        baseline = sum(r['sentiment'] == 'negative' and baseline_start <= r['review_date'] < recent_start for r in evidence)
        recent_share, baseline_share = recent / max(1, recent_total), baseline / max(1, baseline_total)
        growth_ratio = max(0, recent_share / baseline_share - 1) if baseline_share else (2 if recent >= 5 else 0)
        volume = 45 * math.sqrt(negative / max(1, negative_total))
        severity = 30 * (negative + 5 * overall_rate) / (len(evidence) + 5)
        growth = 25 * min(2, growth_ratio) / 2 if enough_history and recent >= 5 else 0
        score = round(volume + severity + growth) if negative else 0
        result.append({'id': topic_id, 'label': definition['custom_label'] or definition['label'],
            'auto_label': definition['label'], 'keywords': json.loads(definition['keywords']),
            'total': len(evidence), 'positive': counts['positive'], 'neutral': counts['neutral'], 'negative': negative,
            'complaint_share': round(negative / max(1, negative_total) * 100, 1),
            'negative_rate': round(negative / len(evidence) * 100, 1), 'priority_score': score,
            'priority': 'High' if score >= 65 else 'Medium' if score >= 40 else 'Low',
            'score_parts': {'volume': round(volume, 1), 'concentration': round(severity, 1), 'growth': round(growth, 1)},
            'recent_negative': recent, 'baseline_negative': baseline, 'recent_total': recent_total, 'baseline_total': baseline_total,
            'change_pp': round((recent_share - baseline_share) * 100, 1) if enough_history else None,
            'has_baseline': enough_history, 'is_rising': enough_history and recent >= 5 and growth_ratio >= 1,
            'unique_texts': len({r['content'].strip().casefold() for r in evidence}), 'coherence': definition['coherence']})
    return sorted(result, key=lambda t: (-t['priority_score'], -t['negative'], t['label']))


def trend_series(rows, scope, topic_id=''):
    start, end = date.fromisoformat(scope['start']), date.fromisoformat(scope['end'])
    daily = (end - start).days < 35
    current = start if daily else start - timedelta(days=start.weekday())
    buckets = {}
    while current <= end:
        buckets[current.isoformat()] = {'date': current.isoformat(), 'total': 0, 'negative': 0, 'positive': 0, 'neutral': 0, 'denominator': 0}
        current += timedelta(days=1 if daily else 7)
    for row in rows:
        if not row['sentiment']:
            continue
        d = date.fromisoformat(row['review_date'])
        bucket = buckets[(d if daily else d - timedelta(days=d.weekday())).isoformat()]
        bucket['denominator'] += 1
        if (not topic_id or row['topic_id'] == topic_id or topic_id == 'ungrouped' and not row['topic_id']):
            bucket['total'] += 1
            bucket[row['sentiment']] += 1
    for bucket in buckets.values():
        bucket['negative_share'] = round(bucket['negative'] / max(1, bucket['denominator']) * 100, 2)
        bucket['total_share'] = round(bucket['total'] / max(1, bucket['denominator']) * 100, 2)
    return list(buckets.values()), 'day' if daily else 'week'


def breakdown(rows, field):
    groups = defaultdict(list)
    for row in rows:
        if row[field] and row['sentiment']:
            groups[row[field]].append(row)
    return sorted([{'name': key, 'total': len(group), 'negative': sum(r['sentiment'] == 'negative' for r in group),
                    'negative_rate': round(sum(r['sentiment'] == 'negative' for r in group) / len(group) * 100, 1)}
                   for key, group in groups.items()], key=lambda r: (-r['negative'], r['name']))


def dashboard_from_rows(rows, scope, topics, chart_topic=''):
    analyzed = [r for r in rows if r['sentiment']]
    sentiments = Counter(r['sentiment'] for r in analyzed)
    categories = priority_categories(rows, topics, scope)
    trends, granularity = trend_series(rows, scope, chart_topic)
    return {'scope': scope, 'summary': {'total': len(rows), 'analyzed': len(analyzed),
        'positive': sentiments['positive'], 'negative': sentiments['negative'], 'neutral': sentiments['neutral'],
        'grouped': sum(bool(r['topic_id']) for r in analyzed), 'ungrouped': sum(not r['topic_id'] for r in analyzed),
        'ungrouped_negative': sum(not r['topic_id'] and r['sentiment'] == 'negative' for r in analyzed),
        'sentiment_methods': dict(Counter(r['sentiment_method'] for r in analyzed)),
        'languages': dict(Counter(r['language'] or 'unknown' for r in rows)),
        'unique_texts': len({r['content'].strip().casefold() for r in rows}),
        'known_customers': len({r['customer_id'] for r in rows if r['customer_id']}),
        'customer_coverage': sum(bool(r['customer_id']) for r in rows),
        'segment_coverage': sum(bool(r['segment']) for r in rows), 'service_coverage': sum(bool(r['service']) for r in rows)},
        'categories': categories, 'trends': trends, 'granularity': granularity,
        'segments': breakdown(rows, 'segment'), 'services': breakdown(rows, 'service')}


def dashboard(days=90, topic_id=''):
    rows, scope, topics = load_scope(days)
    return dashboard_from_rows(rows, scope, topics, topic_id)
