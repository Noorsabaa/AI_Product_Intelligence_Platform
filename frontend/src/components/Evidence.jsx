import { useEffect, useState } from 'react';
import { request, apiUrl } from '../api';
import { Modal, ReviewCard, Empty } from './ui';
import Icon from './Icon';
import { number } from '../format';
export default function Evidence({ category, days, runId, reportId, onClose, onRenamed }) {
  const [sentiment, setSentiment] = useState('negative');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [label, setLabel] = useState(category.label);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      const params = new URLSearchParams({
        days,
        topic_id: category.id,
        sentiment,
        search,
        page,
        ...(!reportId && runId ? { run_id: runId } : {}),
      });
      request(`${reportId ? `/reports/${reportId}` : '/dashboard'}/reviews?${params}`, {
        signal: controller.signal,
      })
        .then((r) => {
          setResult(r);
          setError('');
        })
        .catch((e) => {
          if (e.name !== 'AbortError') setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [days, category.id, sentiment, search, page, runId, reportId]);
  async function rename() {
    setSaving(true);
    try {
      await request(`/dashboard/categories/${category.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label }),
      });
      onRenamed();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }
  function filter(setter, value) {
    setter(value);
    setPage(1);
  }
  return (
    <Modal title={category.label} onClose={onClose} wide>
      <div className="evidence-intro">
        <p>
          {reportId
            ? 'Evidence preserved with this report.'
            : 'Every review behind this category is available here.'}{' '}
          Negative reviews drive complaint volume; all sentiment supplies the concentration
          denominator.
        </p>
        {category.score_parts && (
          <div className="score-explainer">
            <strong>Priority {category.priority_score}/100</strong>
            <span>Volume {category.score_parts.volume}/45</span>
            <span>Concentration {category.score_parts.concentration}/30</span>
            <span>Growth {category.score_parts.growth}/25</span>
          </div>
        )}
        {category.keywords && (
          <p className="muted">Extracted terms: {category.keywords.join(', ')}.</p>
        )}
        {!reportId && category.id !== 'ungrouped' && (
          <details className="rename">
            <summary>Edit category display name</summary>
            <p>Rename for readability. This does not change model membership or saved reports.</p>
            <div>
              <input
                aria-label="Category display name"
                value={label}
                maxLength={100}
                onChange={(e) => setLabel(e.target.value)}
              />
              <button className="button small" disabled={saving || !label.trim()} onClick={rename}>
                Save name
              </button>
            </div>
          </details>
        )}
      </div>
      <div className="evidence-controls">
        <div className="segmented">
          <button
            aria-pressed={sentiment === 'negative'}
            onClick={() => filter(setSentiment, 'negative')}
          >
            Complaints ({number(category.negative)})
          </button>
          <button aria-pressed={sentiment === ''} onClick={() => filter(setSentiment, '')}>
            All feedback ({number(category.total)})
          </button>
        </div>
        <label className="search">
          <Icon name="search" size={16} />
          <input
            aria-label="Search evidence"
            placeholder="Search these reviews"
            value={search}
            onChange={(e) => filter(setSearch, e.target.value)}
          />
        </label>
      </div>
      <div className="evidence-meta">
        <span>{loading ? 'Loading evidence…' : `${number(result?.total)} matching reviews`}</span>
        <a
          className="inline-link"
          href={
            reportId
              ? apiUrl(`/reports/${reportId}/download`, { format: 'csv' })
              : apiUrl('/dashboard/export', { days, topic_id: category.id, sentiment, search })
          }
        >
          <Icon name="download" size={14} />
          {reportId ? 'Export report evidence' : 'Export this view'}
        </a>
      </div>
      <div className="evidence-list" aria-busy={loading}>
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : result?.reviews.length ? (
          result.reviews.map((r) => <ReviewCard key={r.review_id} review={r} />)
        ) : (
          !loading && (
            <Empty title="No matching reviews">
              Try a different search or switch to All feedback.
            </Empty>
          )
        )}
      </div>
      <footer className="pagination">
        <span>
          Page {page} of {Math.max(1, Math.ceil((result?.total || 0) / 20))}
        </span>
        <div>
          <button
            className="button secondary small"
            disabled={page === 1 || loading}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <button
            className="button secondary small"
            disabled={page * 20 >= (result?.total || 0) || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </footer>
    </Modal>
  );
}
