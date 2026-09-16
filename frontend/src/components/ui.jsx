import { useEffect, useRef } from 'react';
import Icon from './Icon';
import { dateLabel } from '../format';
export function Badge({ children, tone = '' }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Empty({ title, children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    d.showModal();
    return () => d.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? 'wide' : ''}`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-label={title}
    >
      <header className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
          <Icon name="close" />
        </button>
      </header>
      {children}
    </dialog>
  );
}
export function ReviewCard({ review }) {
  return (
    <article className="review">
      <div className="review-meta">
        <Badge tone={review.sentiment || 'pending'}>
          {review.sentiment || 'No sentiment result'}
        </Badge>
        <time>{dateLabel(review.review_date)}</time>
        {review.score != null && <span>Rating {review.score}/5</span>}
        {review.service && <span>{review.service}</span>}
        {review.segment && <span>{review.segment}</span>}
      </div>
      <p>{review.content}</p>
      <small>
        {review.sentiment_method === 'text_model'
          ? 'Text-model sentiment'
          : review.sentiment_method === 'rating'
            ? 'Rating-based signal'
            : 'Sentiment unavailable'}{' '}
        · {review.language || 'unknown language'}
        {review.category ? ` · ${review.category}` : ' · Not yet grouped'}
      </small>
    </article>
  );
}
