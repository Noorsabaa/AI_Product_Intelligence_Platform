import { useState } from 'react';
import Icon from './Icon';
import { number, dateLabel } from '../format';
export default function GenerateReport({ data, onGenerate, onHistory, onData, working, busy }) {
  const [title, setTitle] = useState('');
  const s = data.summary;
  return (
    <section className="panel generate-panel">
      <header className="section-head">
        <div>
          <span className="section-number">PERFORMANCE ANALYSIS</span>
          <h2>Turn this period into a saved report</h2>
          <p>A factual summary of the customer feedback, ready for review and handover.</p>
        </div>
      </header>
      <div className="generate-body">
        <div>
          <label className="field">
            Report title <span className="muted">(optional)</span>
            <input
              aria-label="Report title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={150}
              placeholder="e.g. September support review"
            />
          </label>
          <p>
            The report will include sentiment, the leading complaint categories, supported changes,
            service and segment breakdowns where provided, and the limitations of the analysis.
          </p>
          <p>
            Its figures and review evidence are preserved at generation time. You can reopen every
            report from{' '}
            <button className="inline-link" onClick={onHistory}>
              Report history
            </button>
            .
          </p>
          {data.scope.needs_analysis && (
            <div className="notice">
              <p>Analyze the current feedback before generating a report.</p>
              <button className="inline-link" onClick={onData}>
                Open Data <Icon name="arrow" size={14} />
              </button>
            </div>
          )}
          <button
            className="button"
            disabled={working || busy || data.scope.needs_analysis || !s.analyzed}
            onClick={() => onGenerate(title)}
          >
            <Icon name="document" size={17} />
            {working ? 'Saving report…' : 'Generate performance report'}
          </button>
        </div>
        <aside className="report-coverage">
          <span className="section-number">THIS REPORT COVERS</span>
          <h3>
            {dateLabel(data.scope.start)} – {dateLabel(data.scope.end)},{' '}
            {data.scope.end.slice(0, 4)}
          </h3>
          <dl>
            <div>
              <dt>Analyzed reviews</dt>
              <dd>{number(s.analyzed)}</dd>
            </div>
            <div>
              <dt>Negative reviews</dt>
              <dd>{number(s.negative)}</dd>
            </div>
            <div>
              <dt>Discovered categories</dt>
              <dd>{data.categories.length}</dd>
            </div>
            <div>
              <dt>Ungrouped complaints</dt>
              <dd>{number(s.ungrouped_negative)}</dd>
            </div>
          </dl>
          <small>Change the reporting period above to adjust the scope.</small>
        </aside>
      </div>
    </section>
  );
}
