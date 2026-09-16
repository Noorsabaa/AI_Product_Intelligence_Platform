import { useState } from 'react';
import Icon from './Icon';
import { AppMark, Badge, Empty, Modal, ReviewCard } from './ui';
import { number } from '../format';

const statuses = { open: 'Open', investigating: 'Investigating', resolved: 'Resolved' };
export function ActionBoard({ insights, onInsight }) {
  if (!insights.length)
    return (
      <section className="panel">
        <Empty title="Your next steps will live here" icon="actions">
          Analyze feedback or expand your filters to find opportunities. Each action links back to
          the reviews behind it.
        </Empty>
      </section>
    );
  return (
    <div className="action-board">
      {Object.entries(statuses).map(([status, label]) => (
        <section className={`board-column ${status}`} key={status}>
          <h2>
            <i
              className={`dot ${status === 'resolved' ? 'green' : status === 'investigating' ? 'amber' : 'gray'}`}
            />
            {label}
            <span className="count-tag">{insights.filter((i) => i.status === status).length}</span>
          </h2>
          <div className="board-cards">
            {insights
              .filter((i) => i.status === status)
              .map((insight) => (
                <button className="action-card" key={insight.id} onClick={() => onInsight(insight)}>
                  <div className="action-card-top">
                    <Badge tone={insight.priority.toLowerCase()}>{insight.priority} priority</Badge>
                    {insight.is_spike && <Icon name="up" size={17} />}
                  </div>
                  <h3>{insight.category}</h3>
                  <p>{insight.brief}</p>
                  <div className="action-card-app">
                    <AppMark name={insight.app_name} />
                    {insight.app_name}
                  </div>
                  <footer>
                    <span>
                      <Icon name="feedback" size={14} />
                      {number(insight.count)} reviews
                    </span>
                    <span>{insight.owner}</span>
                  </footer>
                </button>
              ))}
          </div>
          {!insights.some((i) => i.status === status) && (
            <div className="board-empty">
              {status === 'resolved'
                ? 'Completed investigations appear here.'
                : 'Move an opportunity here from its detail view.'}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}

export function InsightDetail({ insight, onClose, onSave, onExplore }) {
  const [status, setStatus] = useState(insight.status);
  const [owner, setOwner] = useState(insight.owner);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  async function save() {
    setSaving(true);
    setError('');
    try {
      await onSave(insight.id, { status, owner });
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <Modal title="Opportunity brief" onClose={onClose} wide>
      <div className="detail-content">
        <div className="detail-kicker">
          <AppMark name={insight.app_name} />
          {insight.app_name}
          <Badge tone={insight.priority.toLowerCase()}>
            {insight.priority} priority · {insight.priority_score}/100
          </Badge>
        </div>
        <h1>{insight.category}</h1>
        <p className="detail-summary">{insight.brief}</p>
        <div className="detail-stats">
          <div>
            <strong>{insight.count}</strong>
            <span>Reviews in period</span>
          </div>
          <div>
            <strong>{insight.current}</strong>
            <span>Latest 7 days</span>
          </div>
          <div>
            <strong>{insight.has_baseline ? insight.baseline : '—'}</strong>
            <span>Prior 4-week average</span>
          </div>
          <div>
            <strong>{insight.avg_score}</strong>
            <span>Average rating / 5</span>
          </div>
        </div>
        <div className="insight-explanation">
          <Icon name="info" size={17} />
          <span>
            {insight.is_spike
              ? 'Rising signal: the latest 7 days have at least 5 complaints, twice the previous weekly baseline and an absolute increase of at least 5.'
              : insight.has_baseline
                ? 'A recurring theme. Recent volume does not meet the rising-signal threshold.'
                : 'Not enough history to assess a spike. This opportunity is based on observed feedback volume and ratings.'}{' '}
            Priority is a heuristic, not a confidence score.
          </span>
        </div>
        <div className="recommended-action">
          <span className="eyebrow">SUGGESTED NEXT STEP · RULE-BASED PLAYBOOK</span>
          <p>{insight.recommendation}</p>
        </div>
        <div className="action-controls">
          <label>
            Status
            <select
              aria-label="Action status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {Object.entries(statuses).map(([key, value]) => (
                <option key={key} value={key}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            Responsible team
            <input
              aria-label="Responsible team"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              maxLength={80}
            />
          </label>
          <button className="button" onClick={save} disabled={saving}>
            {saving ? 'Saving…' : 'Save action'}
            <Icon name="check" size={16} />
          </button>
        </div>
        {error && (
          <div className="error-inline" role="alert">
            {error}
          </div>
        )}
        <div className="evidence-heading">
          <h2>
            Source evidence{' '}
            <span className="count-tag">
              {insight.evidence.length} of {insight.count}
            </span>
          </h2>
          <button className="text-button" onClick={() => onExplore(insight)}>
            View all reviews <Icon name="arrow" size={15} />
          </button>
        </div>
        <p className="small-label">
          Sample ordered by lowest rating, then most recent. Theme matches require human review.
        </p>
        <div className="evidence-list">
          {insight.evidence.map((review) => (
            <ReviewCard key={review.review_id} review={review} />
          ))}
        </div>
      </div>
    </Modal>
  );
}
