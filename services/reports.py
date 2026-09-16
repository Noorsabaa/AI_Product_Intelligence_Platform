"""Immutable, quantitative performance reports; never engineering recommendations."""
import csv
import html
import io
import json
import uuid
from fastapi import HTTPException
from services.intelligence import _load, dashboard_from_rows
from services.storage import database, now


def narrative(data):
    s = data['summary']
    paragraphs = [f"Of {s['total']:,} feedback records in this period, {s['analyzed']:,} have a sentiment result: {s['positive']:,} positive, {s['negative']:,} negative and {s['neutral']:,} neutral. These are feedback records, not verified service failures or unique customers."]
    ranked = sorted(data['categories'], key=lambda c: -c['negative'])
    if ranked and ranked[0]['negative']:
        top = ranked[0]
        paragraphs.append(f"Among the discovered categories, {top['label']} accounts for the most negative feedback: {top['negative']:,} reviews, or {top['complaint_share']}% of all negative reviews. {top['negative_rate']}% of feedback within that category is negative.")
    rising = [c for c in data['categories'] if c['is_rising']]
    if rising:
        paragraphs.append('Categories with a supported rise in their share of feedback include ' + ', '.join(c['label'] for c in rising[:3]) + '. Growth compares the latest seven days with the previous 28 days and adjusts for total analyzed feedback volume.')
    else:
        paragraphs.append('No category meets the supported rising-signal threshold in this period. This does not establish that service performance is unchanged; feedback coverage and history may be insufficient.')
    for field, noun in [('services', 'service'), ('segments', 'customer segment')]:
        if data[field]:
            top = data[field][0]
            paragraphs.append(f"Of records with a supplied {noun}, {top['name']} has the most negative reviews ({top['negative']:,} of {top['total']:,} records). This comparison excludes records without that metadata and is not normalized by the number of service users.")
    paragraphs.append(f"{s['ungrouped_negative']:,} negative reviews remain outside a coherent category. They are included in overall sentiment totals and available as ungrouped evidence. Automatically extracted category names are descriptive phrases, not verified service names.")
    return paragraphs


def create_report(days=90, title=''):
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        rows, scope, topics = _load(conn, days)
        if scope['needs_analysis']:
            raise HTTPException(409, 'Analyze the current dataset before saving a performance report.')
        data = dashboard_from_rows(rows, scope, topics)
        if not data['summary']['analyzed']:
            raise HTTPException(422, 'There is no analyzed feedback in this period.')
        report_id = uuid.uuid4().hex
        created = now()
        title = title.strip() or f"Feedback performance · {scope['start']} to {scope['end']}"
        data.update({'id': report_id, 'title': title, 'created_at': created, 'narrative': narrative(data),
            'methodology': {
                'complaints': 'Negative feedback only. Neutral is counted separately.',
                'categories': 'Discovered from distinct review text; uncertain or unsupported text is not forced into a category.',
                'priority': 'Volume: 45 × sqrt(category negative / all negative). Concentration: 30 × smoothed category negative rate. Growth: up to 25 for a supported rise in share of all analyzed feedback.',
                'limits': 'Feedback is a sample. No revenue impact, root cause, unique-customer count or operational service failure is inferred from review volume.'},
            'evidence': [{k: v for k, v in row.items() if k not in ('customer_id',)} for row in rows]})
        conn.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?)',
            (report_id, title, created, scope['start'], scope['end'], scope['published_run']['id'], json.dumps(data, ensure_ascii=False)))
        return {key: data[key] for key in ('id', 'title', 'created_at')}


def get_report(report_id):
    with database() as conn:
        row = conn.execute('SELECT payload FROM reports WHERE id=?', (report_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Report not found.')
    return json.loads(row[0])


def csv_feedback(rows):
    stream = io.StringIO()
    fields = ['review_id', 'review_date', 'content', 'score', 'sentiment', 'sentiment_method', 'category', 'language', 'service', 'segment', 'source']
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')) else value) for key, value in row.items()})
    return '\ufeff' + stream.getvalue()


def render_html(report):
    escape = lambda value: html.escape(str(value))
    s, scope = report['summary'], report['scope']
    cells = ''.join(f'<div><strong>{s[key]:,}</strong><span>{label}</span></div>' for key, label in [('analyzed','Analyzed'),('positive','Positive'),('negative','Negative'),('neutral','Neutral')])
    paragraphs = ''.join(f'<p>{escape(p)}</p>' for p in report['narrative'])
    rows = ''.join(f"<tr><td>{escape(c['label'])}</td><td>{c['negative']}</td><td>{c['complaint_share']}%</td><td>{c['negative_rate']}%</td><td>{c['priority_score']}/100</td></tr>" for c in report['categories'] if c['negative'])
    methods = ''.join(f'<p><b>{escape(key.capitalize())}.</b> {escape(value)}</p>' for key,value in report['methodology'].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(report['title'])}</title><style>
+body{{font:15px/1.65 Arial,sans-serif;background:#f6f2e9;color:#332e28;margin:0}}main{{max-width:900px;margin:40px auto;background:#fffdf8;padding:48px;border:1px solid #ddd5c7}}h1{{font:36px Georgia,serif;margin:15px 0}}h2{{font:24px Georgia,serif;margin-top:36px}}small{{color:#70685d}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:28px 0;border-block:1px solid #ddd5c7;padding:20px 0}}.kpis strong{{display:block;font-size:30px;font-weight:500}}.kpis span{{font-size:12px;color:#70685d}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #ddd5c7;padding:12px 8px}}th{{font-size:11px}}footer{{margin-top:40px;border-top:1px solid #ddd5c7;padding-top:15px}}@media print{{body{{background:white}}main{{margin:0;border:0;padding:0}}tr{{break-inside:avoid}}}}@media(max-width:600px){{main{{margin:0;padding:20px}}.kpis{{grid-template-columns:1fr 1fr}}table{{font-size:11px}}}}
+</style></head><body><main><small>SAVED PERFORMANCE REPORT · {escape(report['created_at'][:10])}</small><h1>{escape(report['title'])}</h1><p>{escape(scope['start'])} — {escape(scope['end'])} · Snapshot of analysis {escape(scope['published_run']['id'][:8])}</p><div class="kpis">{cells}</div><h2>Performance summary</h2>{paragraphs}<h2>Complaint categories</h2><table><thead><tr><th>Discovered category</th><th>Negative reviews</th><th>Share of complaints</th><th>Negative rate</th><th>Priority</th></tr></thead><tbody>{rows}</tbody></table><h2>How to read this report</h2>{methods}<footer><small>Frozen at generation time. Later imports, category renames and reanalysis do not change this report. {s['ungrouped_negative']:,} negative reviews were ungrouped. Sentiment methods: {escape(json.dumps(s['sentiment_methods']))}.</small></footer></main></body></html>'''.replace('\n+', '\n')
