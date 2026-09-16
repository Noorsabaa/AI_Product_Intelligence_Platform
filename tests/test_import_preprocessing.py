import csv
import io
from datetime import datetime

import pytest
from fastapi import HTTPException
from services.imports import parse_csv


def export(dates, delimiter=',', encoding='utf-8', headers=None):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, delimiter=delimiter)
    writer.writerow(headers or [' Reviews ', 'Review Date', 'Star Rating'])
    for index, day in enumerate(dates):
        writer.writerow([f'Customer {index}: café support, slow; still waiting\nPlease respond.', day, '2.0'])
    return stream.getvalue().encode(encoding)


@pytest.mark.parametrize('delimiter,encoding', [(',', 'utf-8-sig'), (';', 'cp1252'), ('\t', 'utf-16'), ('|', 'utf-8')])
def test_export_variations_preserve_text(delimiter, encoding):
    rows = parse_csv(export(['8/3/2026', '8/13/2026'], delimiter, encoding))
    assert [r['review_date'] for r in rows] == ['2026-08-03', '2026-08-13']
    assert rows[0]['score'] == 2
    assert rows[0]['content'] == 'Customer 0: café support, slow; still waiting\nPlease respond.'


def test_infers_day_first_from_whole_file():
    rows = parse_csv(export(['3/8/2026', '13/8/2026']))
    assert [r['review_date'] for r in rows] == ['2026-08-03', '2026-08-13']


def test_ambiguous_dates_require_choice_without_reformatting():
    raw = export(['8/3/2026', '9/4/2026'])
    with pytest.raises(HTTPException) as error:
        parse_csv(raw)
    assert error.value.detail['code'] == 'ambiguous_date_order'
    assert parse_csv(raw, 'mdy')[0]['review_date'] == '2026-08-03'
    assert parse_csv(raw, 'dmy')[0]['review_date'] == '2026-03-08'


def test_mixed_locale_evidence_requires_choice_for_ambiguous_rows():
    raw = export(['8/13/2026', '13/8/2026', '8/3/2026'])
    with pytest.raises(HTTPException):
        parse_csv(raw)
    assert [r['review_date'] for r in parse_csv(raw, 'mdy')] == ['2026-08-13', '2026-08-13', '2026-08-03']
    assert len(parse_csv(export(['8/13/2026', '13/8/2026']))) == 2


@pytest.mark.parametrize('value,expected', [
    ('2026-08-03', '2026-08-03'),
    ('2026/8/3', '2026-08-03'),
    ('2026.8.3', '2026-08-03'),
    ('2026-08-03T01:00:00+05:00', '2026-08-02'),
    ('8/13/2026 14:30:00', '2026-08-13'),
    ('13.8.2026', '2026-08-13'),
    ('13-8-2026', '2026-08-13'),
    ('3 Aug 2026', '2026-08-03'),
    ('August 3, 2026', '2026-08-03'),
    ('3-Aug-2026', '2026-08-03'),
    (str((datetime(2026, 8, 3) - datetime(1899, 12, 30)).days) + '.5', '2026-08-03'),
    ('1785715200', '2026-08-03'),
    ('1785715200000', '2026-08-03'),
])
def test_date_normalization(value, expected):
    assert parse_csv(export([value]))[0]['review_date'] == expected


def test_excel_separator_directive_and_blank_rows():
    raw = b'sep=;\r\nFeedback;Created At;Rating\r\n\r\n;;\r\nHelpful staff;2026-01-01;5 stars\r\n'
    rows = parse_csv(raw)
    assert len(rows) == 1 and rows[0]['score'] == 5


@pytest.mark.parametrize('rating,expected', [('5/5', 5), ('4 out of 5', 4), ('1.00', 1), ('', 3)])
def test_rating_formats_and_missing_flag(rating, expected):
    rows = parse_csv(f'Feedback,Date,Rating\nHelpful,2026-01-01,{rating}'.encode())
    assert rows[0]['score'] == expected
    assert rows[0]['rating_missing'] == int(not rating)


@pytest.mark.parametrize('raw', [
    b'Feedback,Review,Date\nHello,Other,2026-01-01',
    b'Reviews,Date\nHello,31/2/2026',
    b'Reviews,Date\nHello,8/3/26',
    b'Reviews,Date,Rating\nHello,2026-01-01,4.5',
    b'Reviews,Date\nHello,2026-01-01,unexpected',
    b'Reviews,Date\n\x00,2026-01-01',
])
def test_invalid_values_are_not_silently_changed(raw):
    with pytest.raises(HTTPException):
        parse_csv(raw)
