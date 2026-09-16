import { useEffect, useState } from 'react';
import { request, apiUrl, uploadCsv } from '../api';
import { Modal, Empty } from './ui';
import Icon from './Icon';
import { number, dateLabel } from '../format';
export function ImportDialog({ onClose, onDone, busy }) {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('append');
  const [confirmed, setConfirmed] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [dateOrder, setDateOrder] = useState('auto');
  const [dateChoiceNeeded, setDateChoiceNeeded] = useState(false);
  function choose(file) {
    if (working) return;
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv') || file.size > 10 * 1024 * 1024) {
      setError('Choose a CSV file up to 10 MB.');
      return;
    }
    setFile(file);
    setDateOrder('auto');
    setDateChoiceNeeded(false);
    setError('');
  }
  async function upload() {
    setWorking(true);
    setError('');
    try {
      const result = await uploadCsv(file, mode, dateOrder);
      await onDone(result);
      onClose();
    } catch (e) {
      setError(e.message);
      if (e.detail?.code === 'ambiguous_date_order') setDateChoiceNeeded(true);
    } finally {
      setWorking(false);
    }
  }
  return (
    <Modal
      title="Import company feedback"
      onClose={() => {
        if (!working) onClose();
      }}
    >
      <div className="import-body">
        <p>
          Bring feedback from your support system, survey or review export. App names are not
          required.
        </p>
        <label
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            choose(e.dataTransfer.files[0]);
          }}
        >
          <Icon name="upload" size={28} />
          <strong>{file ? file.name : 'Choose a CSV or drop it here'}</strong>
          <span>Up to 10 MB · Common spreadsheet CSV formats</span>
          <input
            aria-label="Choose feedback CSV"
            type="file"
            accept=".csv"
            disabled={working}
            onChange={(e) => choose(e.target.files[0])}
          />
        </label>
        <div className="template-note">
          <p>
            Include feedback text and a date. Common column names and date formats are detected
            automatically.
            <br />
            Ratings, service, customer segment, customer ID and source are optional.
          </p>
          <a className="inline-link" href={apiUrl('/ingest/template')}>
            Download a template <Icon name="download" size={14} />
          </a>
        </div>
        <label className="field">
          Import behavior
          <select
            aria-label="Import behavior"
            value={mode}
            onChange={(e) => {
              setMode(e.target.value);
              setConfirmed(false);
            }}
          >
            <option value="append">Add feedback to this workspace</option>
            <option value="replace">Replace current feedback</option>
          </select>
        </label>
        {mode === 'replace' ? (
          <label className="confirmation">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            Replace current feedback and categories. Saved reports will remain available.
          </label>
        ) : (
          <p className="muted">
            Existing feedback stays intact. Exact duplicate records are skipped.
          </p>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {dateChoiceNeeded && (
          <label className="field">
            How should ambiguous dates be read?
            <select
              aria-label="Date interpretation"
              value={dateOrder}
              disabled={working}
              onChange={(e) => {
                setDateOrder(e.target.value);
                setError('');
              }}
            >
              <option value="auto">Choose a date order</option>
              <option value="mdy">Month / day / year — 8/3/2026 means August 3</option>
              <option value="dmy">Day / month / year — 8/3/2026 means March 8</option>
            </select>
          </label>
        )}
        <footer className="modal-actions">
          <button className="button secondary" disabled={working} onClick={onClose}>
            Cancel
          </button>
          <button
            className="button"
            onClick={upload}
            disabled={
              !file ||
              working ||
              busy ||
              (dateChoiceNeeded && dateOrder === 'auto') ||
              (mode === 'replace' && !confirmed)
            }
          >
            {working ? 'Importing…' : 'Import & analyze'}
            <Icon name="arrow" size={16} />
          </button>
        </footer>
      </div>
    </Modal>
  );
}
export default function Data({ data, pipeline, busy, onImport, onAnalyze, refresh }) {
  const [history, setHistory] = useState({ imports: [], runs: [] });
  const [error, setError] = useState('');
  const [engine, setEngine] = useState('semantic');
  useEffect(() => {
    let active = true;
    Promise.all([request('/ingest/history'), request('/pipeline/history')])
      .then(([a, b]) => {
        if (active) setHistory({ ...a, ...b });
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [refresh, pipeline?.status]);
  return (
    <div className="data-layout">
      <section className="panel">
        <header className="section-head">
          <div>
            <h2>Company feedback</h2>
            <p>One dataset for your support team.</p>
          </div>
          <span className="quiet-label">{number(data.scope.dataset_total)} records stored</span>
        </header>
        <div className="data-body">
          <p>
            Import support feedback, survey comments or customer reviews. Optional service and
            segment fields let reports break down the information your company already collects.
          </p>
          <button className="button" disabled={busy} onClick={onImport}>
            <Icon name="upload" size={16} />
            Import feedback
          </button>
          <a className="inline-link" href={apiUrl('/ingest/template')}>
            Download CSV template
          </a>
        </div>
      </section>
      <section className="panel">
        <header className="section-head">
          <div>
            <h2>Analysis</h2>
            <p>{pipeline?.stage || 'Ready to analyze'}</p>
          </div>
          <span className="quiet-label">{pipeline?.status || 'idle'}</span>
        </header>
        <div className="data-body">
          <progress max="100" value={pipeline?.progress || 0} aria-label="Analysis progress" />
          <div className="progress-caption">
            <span>{number(pipeline?.total)} feedback records</span>
            <span>{pipeline?.progress || 0}%</span>
          </div>
          {pipeline?.error && (
            <div className="error" role="alert">
              {pipeline.error}
            </div>
          )}
          <button
            className="button"
            onClick={() => onAnalyze(engine)}
            disabled={busy || !data.scope.dataset_total}
          >
            <Icon name="play" size={16} />
            {busy ? 'Analysis running…' : 'Analyze feedback'}
          </button>
          <details className="method-choice">
            <summary>Analysis method and limitations</summary>
            <label className="field">
              Method
              <select
                aria-label="Analysis method"
                value={engine}
                onChange={(e) => setEngine(e.target.value)}
                disabled={busy}
              >
                <option value="semantic">Semantic discovery · cached text models</option>
                <option value="lexical">Lexical discovery · no model downloads</option>
              </select>
            </label>
            <p>
              Semantic discovery groups similar meanings using an embedding model and density
              clustering. English text sentiment uses a separate model; other languages use ratings
              when available.
            </p>
            <p>
              Lexical discovery groups recurring words and phrases. It cannot reliably join
              paraphrases, and sentiment uses ratings. Without a rating, sentiment stays
              unavailable.
            </p>
            <p>
              Neither method uses a predefined category list. Uncertain reviews stay ungrouped. The
              same text is encoded once and cached for subsequent runs.
            </p>
          </details>
        </div>
      </section>
      <section className="panel data-history">
        <header className="section-head">
          <div>
            <h2>Import and analysis history</h2>
            <p>Operational history is separate from saved performance reports.</p>
          </div>
        </header>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {history.runs.length || history.imports.length ? (
          <div>
            {[
              ...history.imports.map((r) => ({
                id: `i${r.id}`,
                title: r.filename,
                date: r.created_at,
                note: `${r.inserted} added · ${r.duplicates} duplicates skipped`,
              })),
              ...history.runs.map((r) => ({
                id: r.id,
                title: `${r.engine} analysis`,
                date: r.started_at,
                note: `${r.total} records · ${r.status}`,
              })),
            ]
              .sort((a, b) => b.date.localeCompare(a.date))
              .slice(0, 12)
              .map((r) => (
                <div className="history-row" key={r.id}>
                  <Icon name="clock" size={17} />
                  <div>
                    <strong>{r.title}</strong>
                    <small>{r.note}</small>
                  </div>
                  <time>{dateLabel(r.date)}</time>
                </div>
              ))}
          </div>
        ) : (
          <Empty title="No activity yet">Your first import and analysis will appear here.</Empty>
        )}
      </section>
    </div>
  );
}
