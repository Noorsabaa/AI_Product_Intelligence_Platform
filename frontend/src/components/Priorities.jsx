import { PriorityTable } from './Summary';
import Icon from './Icon';
import { number } from '../format';
export default function Priorities({ data, onEvidence }) {
  const s = data.summary;
  return (
    <section className="panel">
      <header className="section-head">
        <div>
          <span className="section-number">02 / PRIORITIES</span>
          <h2>Categories that need attention</h2>
          <p>Ranked by complaint volume, negative concentration and supported growth.</p>
        </div>
        <span className="quiet-label">Click a category to inspect its evidence</span>
      </header>
      <PriorityTable categories={data.categories} onEvidence={onEvidence} />
      <div className="table-note">
        <span>
          Change compares complaint share of all feedback: latest 7 days vs previous 28. “pp” means
          percentage points. Priority is a ranking, not confidence.
        </span>
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
          Review {number(s.ungrouped_negative)} ungrouped complaints <Icon name="arrow" size={14} />
        </button>
      </div>
    </section>
  );
}
