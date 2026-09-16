import { useState } from 'react';
import Icon from './Icon';
import { Badge, Empty } from './ui';
import { number, pct } from '../format';
export function Kpis({ summary: s }) {
  return (
    <section className="kpis" aria-label="Sentiment summary">
      {[
        ['analyzed', 'Reviews analyzed', 'In this reporting period'],
        ['positive', 'Positive', `${pct(s.positive, s.analyzed)}% of analyzed reviews`],
        ['negative', 'Negative', `${pct(s.negative, s.analyzed)}% of analyzed reviews`],
        ['neutral', 'Neutral', `${pct(s.neutral, s.analyzed)}% of analyzed reviews`],
      ].map(([key, label, note]) => (
        <div className={`kpi ${key}`} key={key}>
          <span>
            <i />
            {label}
          </span>
          <strong>{number(s[key])}</strong>
          <small>{note}</small>
        </div>
      ))}
    </section>
  );
}
export function PriorityTable({ categories, onEvidence, expanded = false }) {
  const [showAll, setShowAll] = useState(expanded);
  const priorities = categories
    .filter((c) => c.negative > 0)
    .sort(
      (a, b) =>
        b.priority_score - a.priority_score ||
        b.negative - a.negative ||
        a.label.localeCompare(b.label),
    );
  return priorities.length ? (
    <>
      <div className="table-scroll">
        <table className="priority-table">
          <thead>
            <tr>
              <th>Discovered category</th>
              <th>Negative reviews</th>
              <th>Share of complaints</th>
              <th>Change vs baseline</th>
              <th>Priority / 100</th>
              <th>
                <span className="sr-only">Open evidence</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {(showAll ? priorities : priorities.slice(0, 8)).map((c) => (
              <tr key={c.id}>
                <td>
                  <button className="category-link" onClick={() => onEvidence(c)}>
                    {c.label}
                    <small>
                      {c.total} total reviews · {c.unique_texts} distinct texts
                    </small>
                  </button>
                </td>
                <td>{number(c.negative)}</td>
                <td>{c.complaint_share}%</td>
                <td>
                  {c.change_pp == null ? (
                    <span className="muted">Insufficient history</span>
                  ) : (
                    <span className={c.change_pp > 0 ? 'rise' : ''}>
                      {c.change_pp > 0 ? '+' : ''}
                      {c.change_pp.toFixed(1)} pp
                    </span>
                  )}
                </td>
                <td>
                  <div className="priority-score">
                    <strong>{c.priority_score}</strong>
                    <span className="score-track">
                      <i style={{ width: `${c.priority_score}%` }} />
                    </span>
                    <Badge tone={c.priority.toLowerCase()}>{c.priority}</Badge>
                  </div>
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`View evidence for ${c.label}`}
                    onClick={() => onEvidence(c)}
                  >
                    <Icon name="chevron" size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {priorities.length > 8 && !expanded && (
        <div className="table-expand">
          <button className="inline-link" onClick={() => setShowAll(!showAll)}>
            {showAll
              ? 'Show leading categories'
              : `Show all ${priorities.length} complaint categories`}
          </button>
        </div>
      )}
    </>
  ) : (
    <Empty title="No ranked complaint categories yet">
      Run analysis or choose a wider period. Feedback without a coherent category remains available
      below.
    </Empty>
  );
}
