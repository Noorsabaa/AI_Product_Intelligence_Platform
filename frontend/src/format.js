export const number = (value) => new Intl.NumberFormat('en').format(value || 0);
export const dateLabel = (value) =>
  value
    ? new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString('en', {
        month: 'short',
        day: 'numeric',
      })
    : '—';
export const pct = (part, total) => (total ? Math.round((part / total) * 100) : 0);
