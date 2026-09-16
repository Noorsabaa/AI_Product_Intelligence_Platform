import { useEffect, useState } from 'react';
import { request, apiUrl } from '../api';
import Icon from './Icon';
import { Empty, ReviewCard } from './ui';
import { number } from '../format';

export default function Feedback({ app, days, categories, initialCategory, refresh }) {
  const [category, setCategory] = useState(initialCategory || '');
  const [sentiment, setSentiment] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      setError('');
      request(
        `/dashboard/reviews?${new URLSearchParams({ app, days, category, sentiment, search, page })}`,
        { signal: controller.signal },
      )
        .then(setResult)
        .catch((e) => {
          if (e.name !== 'AbortError') setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [app, days, category, sentiment, search, page, refresh]);
  function filter(setter, value) {
    setter(value);
    setPage(1);
  }
  return (
    <section className="panel feedback-panel">
      <div className="feedback-toolbar">
        <label className="search-field">
          <Icon name="search" size={18} />
          <input
            aria-label="Search review text"
            placeholder="Search what your customers are saying…"
            value={search}
            onChange={(e) => filter(setSearch, e.target.value)}
            maxLength={200}
          />
        </label>
        <select
          aria-label="Filter sentiment"
          value={sentiment}
          onChange={(e) => filter(setSentiment, e.target.value)}
        >
          <option value="">All sentiment</option>
          <option value="positive">Positive</option>
          <option value="neutral">Neutral</option>
          <option value="negative">Negative</option>
          <option value="pending">Pending</option>
        </select>
        <select
          aria-label="Filter theme"
          value={category}
          onChange={(e) => filter(setCategory, e.target.value)}
        >
          <option value="">All themes</option>
          {categories.map((c) => (
            <option key={c.name}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="feedback-count">
        <span>{loading ? 'Finding feedback…' : `${number(result?.total)} reviews`}</span>
        <a
          className="text-button"
          href={apiUrl('/dashboard/export', { app, days, category, sentiment, search })}
        >
          <Icon name="download" size={15} />
          Export this view
        </a>
      </div>
      {error ? (
        <div className="error-inline" role="alert">
          {error}
        </div>
      ) : result?.reviews.length ? (
        <div className={`feedback-list ${loading ? 'loading-fade' : ''}`} aria-busy={loading}>
          {result.reviews.map((review) => (
            <ReviewCard key={review.review_id} review={review} />
          ))}
        </div>
      ) : (
        !loading && (
          <Empty title="No matching feedback">
            Try a different search, theme or sentiment filter.
          </Empty>
        )
      )}
      <div className="pagination">
        <span>
          Page {page} of {Math.max(1, Math.ceil((result?.total || 0) / 20))}
        </span>
        <div>
          <button
            className="button small secondary"
            disabled={page === 1 || loading}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <button
            className="button small secondary"
            disabled={page * 20 >= (result?.total || 0) || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next <Icon name="chevron" size={14} />
          </button>
        </div>
      </div>
    </section>
  );
}
