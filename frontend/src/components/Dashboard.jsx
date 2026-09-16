import { Kpis } from './Summary';
import { number } from '../format';
import Icon from './Icon';
export default function Dashboard({ data, onEvidence, onAnalyze, busy, onNavigate }) {
  const s = data.summary;
  const leading = [...data.categories].sort((a, b) => b.negative - a.negative)[0];
  return (
    <>
      {' '}
      <Kpis summary={s} />
      <div className="analysis-note">
        <span>
          {number(s.grouped)} reviews grouped into {data.categories.length} discovered categories.{' '}
          <button
            className="inline-link"
            onClick={() =>
              onEvidence({
                id: 'ungrouped',
                label: 'Not yet grouped',
                negative: s.ungrouped_negative,
                total: s.ungrouped,
              })
            }
          >
            {number(s.ungrouped)} not yet grouped
          </button>
          .
        </span>
        <details>
          <summary>About these results</summary>
          <p>
            {number(s.sentiment_methods.text_model)} text-model predictions and{' '}
            {number(s.sentiment_methods.rating)} rating-based signals.{' '}
            {number(s.total - s.analyzed)} records have no sentiment result. English categories are
            discovered from distinct text; unsupported languages and uncertain matches stay
            ungrouped. Neutral feedback is not counted as a complaint.
          </p>
        </details>
      </div>
      {data.scope.needs_analysis && (
        <div className="notice">
          <div>
            <strong>Your current feedback needs analysis</strong>
            <p>Publish discovered categories and sentiment before creating a report.</p>
          </div>
          <button className="button" disabled={busy} onClick={onAnalyze}>
            {busy ? 'Analyzing…' : 'Analyze feedback'}
            <Icon name="arrow" size={16} />
          </button>
        </div>
      )}
      <section className="panel overview-brief">
        <header className="section-head">
          <div>
            <span className="section-number">PERIOD AT A GLANCE</span>
            <h2>What your feedback is telling you</h2>
          </div>
        </header>
        <div className="overview-copy">
          <p>
            {s.analyzed
              ? `${number(s.negative)} of ${number(s.analyzed)} analyzed reviews are negative in this period.`
              : 'Analyze your feedback to see a summary of this period.'}{' '}
            {leading?.negative > 0 && (
              <>
                The largest discovered complaint category is <strong>{leading.label}</strong>, with{' '}
                {number(leading.negative)} negative reviews.
              </>
            )}
          </p>
          <p>
            {number(s.ungrouped_negative)} negative reviews remain ungrouped. These are included in
            the overall totals and are available for inspection in Priorities.
          </p>
          <div className="overview-links">
            <button className="inline-link" onClick={() => onNavigate('trends')}>
              Explore trends <Icon name="arrow" size={15} />
            </button>
            <button className="inline-link" onClick={() => onNavigate('priorities')}>
              Review priorities <Icon name="arrow" size={15} />
            </button>
            <button className="inline-link" onClick={() => onNavigate('reports')}>
              Open reports <Icon name="arrow" size={15} />
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
