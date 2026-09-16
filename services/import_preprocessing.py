"""Normalize spreadsheet exports without guessing ambiguous calendar dates."""
import csv
import io
import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException


ALIASES = {
    'content': ('content', 'review', 'reviews', 'review_text', 'review_content', 'feedback', 'feedback_text', 'comment', 'comments', 'text', 'body', 'message'),
    'review_date': ('review_date', 'date', 'created_at', 'created_on', 'created_date', 'submitted_at', 'submission_date', 'timestamp', 'datetime', 'feedback_date'),
    'score': ('score', 'rating', 'stars', 'star_rating', 'review_rating'),
    'service': ('service', 'service_name', 'product', 'product_name'),
    'segment': ('segment', 'customer_segment', 'plan', 'plan_name'),
    'customer_id': ('customer_id', 'customer', 'user_id', 'account_id'),
    'source': ('source', 'channel', 'feedback_source'),
    'app_name': ('app_name',),
}
HEADER_MAP = {alias: name for name, aliases in ALIASES.items() for alias in aliases}
NUMERIC_DATE = re.compile(r'^(\d{1,2})([/.-])(\d{1,2})\2(\d{4})(?P<time>(?:[ T].*)?)$')


def read_export(raw, max_rows):
    try:
        if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
            text = raw.decode('utf-16')
        else:
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('cp1252')
        if any(ord(c) < 32 and c not in '\t\r\n' for c in text):
            raise ValueError('Binary content')
        text = text.lstrip('\ufeff\r\n')
        delimiter = None
        first, _, rest = text.partition('\n')
        if re.fullmatch(r'sep=[,;\t|]', first.strip(), re.IGNORECASE):
            delimiter, text = first.strip()[4], rest
        if not text.strip():
            raise HTTPException(422, 'The file is empty. Choose an export containing feedback rows.')
        if delimiter is None:
            # Headers have a consistent structure even if later rows are malformed.
            delimiter = csv.Sniffer().sniff(text.splitlines()[0], delimiters=',;\t|').delimiter
        reader = csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True)
        original = next(reader)
        headers = [re.sub(r'[^\w]+', '_', h.strip().casefold()).strip('_') for h in original]
        headers = [HEADER_MAP.get(h, h) for h in headers]
        if len(set(headers)) != len(headers):
            raise HTTPException(422, 'Multiple columns identify the same field. Keep one feedback, date, and rating column each.')
        missing = {'content', 'review_date'} - set(headers)
        if missing:
            raise HTTPException(422, 'Could not identify a feedback and date column. Recognized names include Review, Reviews, Feedback, Content, Date, Review Date, and Created At.')
        rows = []
        for values in reader:
            if not any(value.strip() for value in values):
                continue
            if len(rows) >= max_rows:
                raise HTTPException(413, 'Use at most 50,000 reviews per import.')
            row = dict(zip(headers, values))
            if len(values) > len(headers):
                row[None] = values[len(headers):]
            rows.append((reader.line_num, row))
        return rows
    except (UnicodeError, csv.Error, ValueError, StopIteration) as exc:
        raise HTTPException(422, 'Could not read this CSV. Supported exports use commas, semicolons, tabs, or pipes with UTF-8, Windows-1252, or BOM-marked UTF-16 text.') from exc


def infer_date_order(rows, requested='auto'):
    if requested not in ('auto', 'mdy', 'dmy'):
        raise HTTPException(422, 'Date order must be auto, mdy, or dmy.')
    evidence, ambiguous = set(), []
    for _, row in rows:
        value = (row.get('review_date') or '').strip()
        match = NUMERIC_DATE.fullmatch(value)
        if not match:
            continue
        a, b = int(match[1]), int(match[3])
        if 12 < a <= 31 and 1 <= b <= 12:
            evidence.add('dmy')
        elif 12 < b <= 31 and 1 <= a <= 12:
            evidence.add('mdy')
        elif 1 <= a <= 12 and 1 <= b <= 12 and a != b:
            ambiguous.append(value)
    if requested != 'auto':
        return requested
    if ambiguous and len(evidence) != 1:
        raise HTTPException(422, {
            'code': 'ambiguous_date_order',
            'message': f'Dates such as {ambiguous[0]} could mean month/day or day/month. Choose how to read these dates below; no file changes are needed.',
            'example': ambiguous[0],
        })
    return next(iter(evidence)) if len(evidence) == 1 else 'mdy'


def normalize_date(value, order):
    value = value.strip()
    if not value:
        raise ValueError('A feedback date is missing.')
    numeric = NUMERIC_DATE.fullmatch(value)
    if numeric:
        a, b, year = int(numeric[1]), int(numeric[3]), int(numeric[4])
        # An unambiguous row is safe even in exports combining different locales.
        row_order = 'dmy' if a > 12 else 'mdy' if b > 12 else order
        day, month = (a, b) if row_order == 'dmy' else (b, a)
        value = f'{year:04d}-{month:02d}-{day:02d}{numeric["time"]}'
    # Year-first spreadsheet dates are unambiguous.
    value = re.sub(r'^(\d{4})[/\.](\d{1,2})[/\.](\d{1,2})(?=$|[ T])',
                   lambda m: f'{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}', value)
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        parsed = None
        if re.fullmatch(r'\d{5}(?:\.\d+)?', value):
            parsed = datetime(1899, 12, 30) + timedelta(days=float(value))
        elif re.fullmatch(r'\d{10}|\d{13}', value):
            parsed = datetime.fromtimestamp(int(value) / (1000 if len(value) == 13 else 1), timezone.utc)
        else:
            cleaned = re.sub(r'\s+', ' ', value.replace(',', '').replace('-', ' '))
            for fmt in ('%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y'):
                try:
                    parsed = datetime.strptime(cleaned, fmt)
                    break
                except ValueError:
                    pass
        if parsed is None:
            raise ValueError(f'Cannot recognize date "{value}". Use a calendar date with a four-digit year.')
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc)
    day = parsed.date()
    if day > datetime.now(timezone.utc).date():
        raise ValueError('Review date cannot be in the future.')
    return day.isoformat()


def normalize_rating(value):
    value = value.strip()
    if not value:
        return 3, 1  # Existing storage uses a separate flag for missing ratings.
    match = re.fullmatch(r'([1-5])(?:\.0+)?(?:\s*(?:/\s*5|out of 5|stars?))?', value, re.IGNORECASE)
    if not match:
        raise ValueError('Rating must be a whole number from 1 to 5, or blank.')
    return int(match[1]), 0
