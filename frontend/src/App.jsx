import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { request, apiUrl, setCsrfToken } from './api';
import Auth from './components/Auth';
import Icon from './components/Icon';
import Data, { ImportDialog } from './components/Data';
import Evidence from './components/Evidence';
import { dateLabel } from './format';
const Dashboard = lazy(() => import('./components/Dashboard'));
const Trends = lazy(() => import('./components/Trends'));
const Priorities = lazy(() => import('./components/Priorities'));
const Reports = lazy(() => import('./components/Reports'));
const GenerateReport = lazy(() => import('./components/GenerateReport'));
import './index.css';
const pages = {
  dashboard: { label: 'Dashboard', icon: 'overview' },
  trends: { label: 'Trends', icon: 'pulse' },
  priorities: { label: 'Priorities', icon: 'feedback' },
  reports: { label: 'Generate report', icon: 'document' },
  history: { label: 'Report history', icon: 'clock' },
  data: { label: 'Data', icon: 'sources' },
};
function route() {
  const hash = location.hash.slice(1);
  return pages[hash] ? hash : 'dashboard';
}
export default function App() {
  const [session, setSession] = useState(null);
  const [checking, setChecking] = useState(true);
  const [sessionError, setSessionError] = useState('');
  function authenticated(result) {
    setCsrfToken(result.csrf);
    setSession(result.user);
    setSessionError('');
  }
  useEffect(() => {
    let active = true;
    request('/auth/session')
      .then((r) => {
        if (active) authenticated(r);
      })
      .catch((e) => {
        if (active) setSessionError(e.message);
      })
      .finally(() => {
        if (active) setChecking(false);
      });
    const expired = () => {
      setCsrfToken('');
      setSession(null);
    };
    window.addEventListener('session-expired', expired);
    return () => {
      active = false;
      window.removeEventListener('session-expired', expired);
    };
  }, []);
  async function logout() {
    try {
      await request('/auth/logout', { method: 'POST' });
      setCsrfToken('');
      setSession(null);
      location.hash = 'dashboard';
    } catch (e) {
      setSessionError(e.message);
    }
  }
  if (checking) return <div className="auth-loading">Opening your workspace…</div>;
  return (
    <>
      {sessionError && (
        <div className="error" role="alert">
          {sessionError}
        </div>
      )}
      {session ? (
        <Workspace key={session.id} user={session} onLogout={logout} />
      ) : (
        <Auth onAuthenticated={authenticated} />
      )}
    </>
  );
}
function Workspace({ user, onLogout }) {
  const [page, setPage] = useState(route);
  const [days, setDays] = useState(90);
  const [chartTopic, setChartTopic] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [pipeline, setPipeline] = useState(null);
  const [starting, setStarting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [evidence, setEvidence] = useState(null);
  const [reportId, setReportId] = useState(null);
  const [reporting, setReporting] = useState(false);
  const [toast, setToast] = useState('');
  const [menu, setMenu] = useState(false);
  const previous = useRef('');
  const busy = starting || ['queued', 'running'].includes(pipeline?.status);
  const reload = useCallback(() => setRevision((x) => x + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    request(`/dashboard/overview?${new URLSearchParams({ days, topic_id: chartTopic })}`, {
      signal: controller.signal,
    })
      .then((r) => {
        setData(r);
        setError('');
        if (
          chartTopic &&
          chartTopic !== 'ungrouped' &&
          !r.categories.some((c) => c.id === chartTopic)
        )
          setChartTopic('');
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [days, chartTopic, revision]);
  useEffect(() => {
    let active = true,
      timer;
    async function poll() {
      try {
        const r = await request('/pipeline/status');
        if (!active) return;
        setPipeline(r);
        const key = `${r.id}:${r.status}`;
        if (
          previous.current &&
          key !== previous.current &&
          ['completed', 'failed', 'interrupted'].includes(r.status)
        ) {
          setChartTopic('');
          reload();
          setToast(
            r.status === 'completed'
              ? 'Analysis complete. The dashboard is up to date.'
              : 'Analysis did not finish. See Data for details.',
          );
        }
        previous.current = key;
      } catch (e) {
        if (active) setError(e.message);
      }
      if (active) timer = setTimeout(poll, 2500);
    }
    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [reload]);
  useEffect(() => {
    const change = () => setPage(route());
    addEventListener('hashchange', change);
    return () => removeEventListener('hashchange', change);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(''), 6000);
    return () => clearTimeout(timer);
  }, [toast]);
  function navigate(next) {
    if (next === 'history') setReportId(null);
    setPage(next);
    location.hash = next;
    setMenu(false);
    window.scrollTo(0, 0);
  }
  async function analyze(engine = 'semantic') {
    setStarting(true);
    setError('');
    try {
      const r = await request(`/pipeline/run?engine=${engine}`, { method: 'POST' });
      setPipeline({ ...r, stage: 'Preparing analysis', progress: 0 });
      setToast('Analysis started. You can keep using the workspace.');
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setStarting(false);
    }
  }
  async function imported(result) {
    setChartTopic('');
    reload();
    navigate('data');
    setToast(`${result.inserted} records added; ${result.duplicates} duplicates skipped.`);
    try {
      await analyze();
    } catch {
      /* Imported data is preserved and the error is visible. */
    }
  }
  async function report(title = '') {
    setReporting(true);
    setError('');
    try {
      const r = await request('/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days, title }),
      });
      reload();
      navigate('history');
      setReportId(r.id);
      setToast('Performance report saved.');
    } catch (e) {
      setError(e.message);
    } finally {
      setReporting(false);
    }
  }
  return (
    <div className="shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {menu && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <aside className={`sidebar ${menu ? 'open' : ''}`}>
        <a href="#dashboard" className="brand" onClick={() => navigate('dashboard')}>
          <span className="brand-icon">
            <Icon name="document" size={22} />
          </span>
          <span>
            Feedback review<small>Company workspace</small>
          </span>
        </a>
        <span className="nav-label">ANALYSIS</span>
        <nav aria-label="Main navigation">
          {['dashboard', 'trends', 'priorities', 'reports', 'history'].map((key) => (
            <button
              key={key}
              aria-current={page === key ? 'page' : undefined}
              onClick={() => navigate(key)}
              className={page === key ? 'active' : ''}
            >
              <Icon name={pages[key].icon} size={18} />
              {pages[key].label}
            </button>
          ))}
          <span className="nav-label data-nav-label">WORKSPACE</span>
          <button
            onClick={() => navigate('data')}
            aria-current={page === 'data' ? 'page' : undefined}
            className={page === 'data' ? 'active' : ''}
          >
            <Icon name="sources" size={18} />
            Data
          </button>
        </nav>
        <div className="sidebar-foot">
          <div className="account-info">
            <Icon name="shield" size={15} />
            <span>
              {user.username}
              <small>Your private workspace</small>
            </span>
          </div>
          <button className="inline-link" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <button
              className="icon-button menu-button"
              aria-label="Open navigation"
              onClick={() => setMenu(true)}
            >
              <Icon name="menu" />
            </button>
            <span>{pages[page].label}</span>
          </div>
          <span className="topbar-note">
            {busy
              ? `${pipeline?.stage || 'Analyzing'} · ${pipeline?.progress || 0}%`
              : loading
                ? 'Updating…'
                : 'Customer feedback analysis'}
          </span>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <h1>
                {page === 'dashboard'
                  ? 'Customer feedback'
                  : page === 'trends'
                    ? 'Feedback trends'
                    : page === 'priorities'
                      ? 'Complaint priorities'
                      : page === 'reports'
                        ? 'Generate a report'
                        : page === 'history'
                          ? 'Your report history'
                          : 'Your feedback data'}
              </h1>
              <p>
                {page === 'dashboard'
                  ? 'A concise overview of customer sentiment in this period.'
                  : page === 'trends'
                    ? 'Follow discovered categories and changes in the feedback mix.'
                    : page === 'priorities'
                      ? 'Understand which categories need attention and inspect the reviews behind them.'
                      : page === 'reports'
                        ? 'Save a performance analysis of your company’s feedback.'
                        : page === 'history'
                          ? 'The complete archive of reports generated by your account.'
                          : 'Import your company’s feedback and keep the analysis current.'}
              </p>
            </div>
            {page === 'dashboard' && (
              <div className="heading-actions">
                <a className="button secondary" href={apiUrl('/dashboard/export', { days })}>
                  <Icon name="download" size={16} />
                  Export CSV
                </a>
                <button className="button" disabled={busy} onClick={() => setImporting(true)}>
                  <Icon name="plus" size={16} />
                  Import feedback
                </button>
              </div>
            )}
          </div>
          {!['data', 'history'].includes(page) && (
            <div className="period-toolbar">
              <label>
                Reporting period
                <select
                  aria-label="Reporting period"
                  value={days}
                  onChange={(e) => {
                    setDays(Number(e.target.value));
                    setChartTopic('');
                  }}
                >
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                  <option value={180}>Last 180 days</option>
                  <option value={0}>All available data</option>
                </select>
              </label>
              <span>
                {data
                  ? `${dateLabel(data.scope.start)} – ${dateLabel(data.scope.end)}, ${data.scope.end.slice(0, 4)} · data through ${dateLabel(data.scope.end)}`
                  : 'Loading period…'}
              </span>
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              <span>{error}</span>
              <button className="inline-link" onClick={reload}>
                Retry
              </button>
            </div>
          )}
          {busy && (
            <button className="running-banner" onClick={() => navigate('data')}>
              <span className="spinner" />
              <span>
                {pipeline?.stage || 'Preparing feedback'}. Published results remain available while
                analysis runs.
              </span>
              <Icon name="arrow" size={16} />
            </button>
          )}
          {!data ? (
            <div className="loading">
              {loading
                ? 'Loading your feedback…'
                : 'Start the server and select Retry to reconnect.'}
            </div>
          ) : (
            <Suspense fallback={<div className="loading">Loading analysis…</div>}>
              {page === 'dashboard' && (
                <Dashboard
                  data={data}
                  onEvidence={setEvidence}
                  onNavigate={navigate}
                  onAnalyze={() => {
                    analyze().catch(() => {});
                  }}
                  busy={busy}
                />
              )}{' '}
              {page === 'trends' && (
                <Trends data={data} chartTopic={chartTopic} setChartTopic={setChartTopic} />
              )}
              {page === 'priorities' && <Priorities data={data} onEvidence={setEvidence} />}
              {page === 'reports' && (
                <GenerateReport
                  data={data}
                  onGenerate={report}
                  onHistory={() => navigate('history')}
                  onData={() => navigate('data')}
                  working={reporting}
                  busy={busy}
                />
              )}
              {page === 'history' && (
                <Reports selectedId={reportId} onSelect={setReportId} refresh={revision} />
              )}{' '}
              {page === 'data' && (
                <Data
                  data={data}
                  pipeline={pipeline}
                  busy={busy}
                  refresh={revision}
                  onImport={() => setImporting(true)}
                  onAnalyze={(engine) => {
                    analyze(engine).catch(() => {});
                  }}
                />
              )}
            </Suspense>
          )}
          <footer className="page-footer">
            <span>Feedback review</span>
            <span>Observed feedback, with evidence and context.</span>
          </footer>
        </main>
      </div>
      {importing && (
        <ImportDialog onClose={() => setImporting(false)} onDone={imported} busy={busy} />
      )}{' '}
      {evidence && (
        <Evidence
          key={evidence.id}
          category={evidence}
          days={days}
          runId={data?.scope.published_run?.id}
          onClose={() => setEvidence(null)}
          onRenamed={reload}
        />
      )}{' '}
      {toast && (
        <div className="toast" role="status">
          <Icon name="check" size={17} />
          <span>{toast}</span>
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setToast('')}
          >
            <Icon name="close" size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
