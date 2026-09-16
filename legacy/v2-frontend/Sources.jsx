import { useEffect, useState } from 'react';
import { request, apiUrl, uploadCsv } from '../api';
import Icon from './Icon';
import { Badge, Modal } from './ui';
import { number, dateLabel, pct } from '../format';

export function ImportDialog({ onClose, onDone, running }) {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('append');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  function choose(selected) {
    setError('');
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith('.csv') || selected.size > 10 * 1024 * 1024) {
      setError('Choose a CSV file up to 10 MB.');
      return;
    }
    setFile(selected);
  }
  async function submit() {
    setBusy(true);
    setError('');
    try {
      const result = await uploadCsv(file, mode);
      onDone(result);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title="Bring your customer feedback"
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <div className="import-content">
        <p>Import a CSV to turn customer reviews into your next product priorities.</p>
        <label
          className={`dropzone ${dragging ? 'dragging' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            choose(e.dataTransfer.files[0]);
          }}
        >
          <span className="upload-symbol">
            <Icon name={file ? 'document' : 'upload'} size={28} />
          </span>
          <strong>{file ? file.name : 'Drop your CSV here, or browse files'}</strong>
          <span>
            {file
              ? `${(file.size / 1024).toFixed(1)} KB · Ready for validation`
              : 'UTF-8 CSV · up to 10 MB · 50,000 reviews'}
          </span>
          <input
            type="file"
            aria-label="Choose reviews CSV"
            accept=".csv"
            onChange={(e) => choose(e.target.files[0])}
            disabled={busy}
          />
        </label>
        <div className="template-link">
          <span>Required: app_name, content, review_date, score</span>
          <a href={apiUrl('/ingest/template')}>
            Get template <Icon name="download" size={14} />
          </a>
        </div>
        <label className="field-label">
          Import behavior
          <select
            value={mode}
            onChange={(e) => {
              setMode(e.target.value);
              setConfirmed(false);
            }}
            disabled={busy}
          >
            <option value="append">Add reviews to the current dataset</option>
            <option value="replace">Replace the current dataset</option>
          </select>
        </label>
        {mode === 'replace' ? (
          <label className="confirm-replace">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            I understand this replaces all current reviews and resets saved actions.
          </label>
        ) : (
          <p className="import-note">
            <Icon name="shield" size={16} />
            Existing reviews are preserved. Exact duplicates are skipped.
          </p>
        )}
        {running && (
          <p className="error-inline">Wait for the current analysis to finish before importing.</p>
        )}
        {error && (
          <div className="error-inline" role="alert">
            {error}
          </div>
        )}
        <div className="modal-footer">
          <button className="button secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            className="button"
            onClick={submit}
            disabled={!file || busy || running || (mode === 'replace' && !confirmed)}
          >
            {busy ? 'Validating & importing…' : 'Import feedback'}
            <Icon name="arrow" size={16} />
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default function Sources({ data, pipeline, onImport, onAnalyze, onImported, refresh }) {
  const [history, setHistory] = useState({ runs: [], imports: [] });
  const [error, setError] = useState('');
  const [engine, setEngine] = useState('local');
  const [play, setPlay] = useState({ app_name: '', package: '', count: 200 });
  const [importing, setImporting] = useState(false);
  const running = ['queued', 'running'].includes(pipeline?.status);
  const s = data.summary;
  useEffect(() => {
    let active = true;
    Promise.all([request('/pipeline/history'), request('/ingest/history')])
      .then(([runs, imports]) => {
        if (active) setHistory({ ...runs, ...imports });
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [refresh, pipeline?.status]);
  async function importPlay(e) {
    e.preventDefault();
    setImporting(true);
    setError('');
    try {
      onImported(
        await request('/ingest/google-play', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(play),
        }),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  }
  return (
    <div className="sources-layout">
      <div className="sources-main">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Your feedback sources</h2>
              <p>One place for the voice of your customers</p>
            </div>
            <Badge tone="positive">{number(data.scope.dataset_total)} stored reviews</Badge>
          </div>
          <div className="source-csv">
            <span className="source-icon">
              <Icon name="document" size={28} />
            </span>
            <div>
              <h3>CSV import</h3>
              <p>Bring reviews from support exports, app stores or your own dataset.</p>
            </div>
            <button className="button secondary small" onClick={onImport} disabled={running}>
              <Icon name="plus" size={15} />
              Import CSV
            </button>
          </div>
          <form className="play-form" onSubmit={importPlay}>
            <div>
              <h3>Google Play</h3>
              <p>Import recent public reviews using the app’s package ID.</p>
            </div>
            <div className="play-fields">
              <label>
                App name
                <input
                  placeholder="e.g. Notion"
                  required
                  value={play.app_name}
                  onChange={(e) => setPlay({ ...play, app_name: e.target.value })}
                />
              </label>
              <label>
                Package ID
                <input
                  placeholder="e.g. notion.id"
                  required
                  pattern="[A-Za-z][\w]*(\.[\w]+)+"
                  value={play.package}
                  onChange={(e) => setPlay({ ...play, package: e.target.value })}
                />
              </label>
              <label>
                Reviews
                <select
                  value={play.count}
                  onChange={(e) => setPlay({ ...play, count: Number(e.target.value) })}
                >
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value={500}>500</option>
                  <option value={1000}>1,000</option>
                </select>
              </label>
            </div>
            <button className="button secondary small" disabled={running || importing}>
              {importing ? 'Fetching reviews…' : 'Connect & import'}
              <Icon name="arrow" size={15} />
            </button>
            <span className="small-label">Optional connector · English / US storefront</span>
          </form>
          {error && (
            <div className="error-inline" role="alert">
              {error}
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Analysis pipeline</h2>
              <p>One run. A complete, consistent view of your feedback.</p>
            </div>
            <Badge
              tone={
                pipeline?.status === 'completed'
                  ? 'positive'
                  : pipeline?.status === 'failed'
                    ? 'negative'
                    : ''
              }
            >
              {pipeline?.status || 'idle'}
            </Badge>
          </div>
          <div className="pipeline-body">
            <div className="pipeline-steps">
              {['Prepare', 'Analyze', 'Publish'].map((name, index) => (
                <div key={name} className={pipeline?.progress >= [5, 90, 100][index] ? 'done' : ''}>
                  <span>
                    {pipeline?.progress >= [5, 90, 100][index] ? (
                      <Icon name="check" size={15} />
                    ) : (
                      index + 1
                    )}
                  </span>
                  {name}
                </div>
              ))}
            </div>
            <div className="pipeline-progress-label">
              <strong>{pipeline?.stage || 'Ready to analyze'}</strong>
              <span>
                {number(pipeline?.processed)} / {number(pipeline?.total)} reviews
              </span>
            </div>
            <progress aria-label="Analysis progress" max="100" value={pipeline?.progress || 0} />
            {pipeline?.error && (
              <div className="error-inline" role="alert">
                {pipeline.error}
              </div>
            )}
            <div className="run-controls">
              <label>
                Analysis method
                <select
                  value={engine}
                  onChange={(e) => setEngine(e.target.value)}
                  disabled={running}
                >
                  <option value="local">Local · ratings + theme rules</option>
                  <option value="transformer">Text model · cached multilingual model</option>
                </select>
              </label>
              <button
                className="button"
                onClick={() => onAnalyze(engine)}
                disabled={running || !data.scope.dataset_total}
              >
                <Icon name="play" size={16} />
                {running ? 'Analysis running…' : 'Run analysis'}
              </button>
            </div>
            <p className="small-label">
              Local analysis needs no API key. Text model mode requires an installed, cached model.
              Your previous published results stay available if a run fails.
            </p>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Activity log</h2>
              <p>Saved imports and analysis runs</p>
            </div>
          </div>
          <div className="activity-list">
            {[
              ...history.runs.map((run) => ({
                id: run.id,
                date: run.started_at,
                title: `${run.engine === 'local' ? 'Local' : 'Text model'} analysis`,
                text: `${number(run.total)} reviews · ${run.status}`,
                icon: 'pulse',
              })),
              ...history.imports.map((item) => ({
                id: `import-${item.id}`,
                date: item.created_at,
                title: item.filename,
                text: `${number(item.inserted)} added · ${item.duplicates} duplicates · ${item.mode}`,
                icon: 'upload',
              })),
            ]
              .sort((a, b) => b.date.localeCompare(a.date))
              .slice(0, 12)
              .map((item) => (
                <div className="activity" key={item.id}>
                  <Icon name={item.icon} size={19} />
                  <div>
                    <strong>{item.title}</strong>
                    <small>{item.text}</small>
                  </div>
                  <time>{dateLabel(item.date)}</time>
                </div>
              ))}
            {!history.runs.length && !history.imports.length && (
              <p className="small-label activity-empty">
                Activity appears after your first import or analysis.
              </p>
            )}
          </div>
        </section>
      </div>
      <aside className="sources-aside">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Trust the process</h2>
              <p>Coverage in your selected view</p>
            </div>
          </div>
          <div className="quality-body">
            <div className="coverage-number">
              {pct(s.analyzed, s.total)}
              <span>%</span>
            </div>
            <p>of reviews analyzed</p>
            <progress max="100" value={pct(s.analyzed, s.total)} aria-label="Analysis coverage" />
            <div className="quality-stat">
              <span>Analyzed reviews</span>
              <strong>{number(s.analyzed)}</strong>
            </div>
            <div className="quality-stat">
              <span>Awaiting analysis</span>
              <strong>{number(s.total - s.analyzed)}</strong>
            </div>
            <div className="quality-stat">
              <span>Themes matched</span>
              <strong>{number(s.categorized)}</strong>
            </div>
            <div className="quality-stat">
              <span>Complaints to review</span>
              <strong>{number(s.complaints - s.categorized)}</strong>
            </div>
            <div className="quality-stat">
              <span>Invalid dates excluded</span>
              <strong>{data.scope.invalid_dates}</strong>
            </div>
          </div>
        </section>
        <section className="method-note">
          <Icon name="shield" size={23} />
          <h3>Transparent by design</h3>
          <p>
            Local sentiment follows the star rating: 1–2 negative, 3 neutral, 4–5 positive. It does
            not claim to understand the review’s tone.
          </p>
          <p>
            Theme matching uses English keywords. Other languages and unmatched complaints remain
            available for manual review.
          </p>
          <p>
            Suggested actions are category playbooks, not AI-generated findings. Every opportunity
            includes its source evidence.
          </p>
        </section>
      </aside>
    </div>
  );
}
