import { useState } from "react";
import { getSpikeReviews } from "../api";

export default function SpikesList({ spikes, recommendations }) {
  const [filters, setFilters] = useState({ app: "all", category: "all", priority: "all" });
  const [evidence, setEvidence] = useState({});
  const [loadingKey, setLoadingKey] = useState("");

  const briefFor = (spike) =>
    recommendations.find(
      (r) => r.app_name === spike.app_name && r.category === spike.category && r.period === spike.period
    );
  const evidenceCountFor = (spike) => {
    const recommendation = briefFor(spike);
    if (!recommendation?.evidence_review_ids) return 0;
    try {
      return JSON.parse(recommendation.evidence_review_ids).length;
    } catch {
      return 0;
    }
  };

  const apps = [...new Set(spikes.map((spike) => spike.app_name))].sort();
  const categories = [...new Set(spikes.map((spike) => spike.category))].sort();
  const priorities = ["High", "Medium", "Low"].filter((priority) =>
    spikes.some((spike) => spike.priority === priority)
  );
  const visibleSpikes = spikes.filter((spike) =>
    (filters.app === "all" || spike.app_name === filters.app) &&
    (filters.category === "all" || spike.category === filters.category) &&
    (filters.priority === "all" || spike.priority === filters.priority)
  );

  const keyFor = (spike) => `${spike.app_name}|${spike.category}|${spike.period}`;
  const toggleEvidence = async (spike) => {
    const key = keyFor(spike);
    if (evidence[key]) {
      setEvidence((current) => ({ ...current, [key]: null }));
      return;
    }
    setLoadingKey(key);
    try {
      const result = await getSpikeReviews(spike);
      setEvidence((current) => ({ ...current, [key]: result.reviews }));
    } catch (error) {
      setEvidence((current) => ({ ...current, [key]: { error: error.message } }));
    } finally {
      setLoadingKey("");
    }
  };

  if (!spikes.length) return <p style={{ color: "#6b7280", fontSize: 14 }}>No active spikes detected.</p>;

  return (
    <div>
      <div className="spike-filters">
        <select value={filters.app} onChange={(event) => setFilters({ ...filters, app: event.target.value })}>
          <option value="all">All apps</option>
          {apps.map((app) => <option key={app} value={app}>{app}</option>)}
        </select>
        <select value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })}>
          <option value="all">All categories</option>
          {categories.map((category) => <option key={category} value={category}>{category}</option>)}
        </select>
        <select value={filters.priority} onChange={(event) => setFilters({ ...filters, priority: event.target.value })}>
          <option value="all">All priorities</option>
          {priorities.map((priority) => <option key={priority} value={priority}>{priority}</option>)}
        </select>
      </div>
      {!visibleSpikes.length && <p style={{ color: "#6b7280", fontSize: 14 }}>No spikes match these filters.</p>}
      {visibleSpikes.map((s) => {
        const key = keyFor(s);
        const reviews = evidence[key];
        return <div className="spike-item" key={key}>
          <div className="spike-header">
            <span className="spike-title">{s.app_name} — {s.category}</span>
            <div className="spike-badges">
              <span className={`priority-badge priority-${s.priority?.toLowerCase() || "low"}`}>
                {s.priority || "Unranked"}
              </span>
              <span className="spike-badge">+{s.pct_change}%</span>
            </div>
          </div>
          <div className="spike-meta">
            {s.period} · {s.granularity} · {s.count} complaints (baseline {s.baseline}) · avg {s.avg_score}★
          </div>
          <div className="spike-brief">{briefFor(s)?.brief || "Recommendation not yet generated."}</div>
          {evidenceCountFor(s) > 0 && <div className="evidence-count">
            Recommendation grounded in {evidenceCountFor(s)} selected source reviews.
          </div>}
          <button className="evidence-btn" onClick={() => toggleEvidence(s)} disabled={loadingKey === key}>
            {loadingKey === key ? "Loading evidence..." : reviews ? "Hide source reviews" : "Inspect source reviews"}
          </button>
          {reviews && (Array.isArray(reviews) ? (
            <div className="evidence-list">
              {reviews.length ? reviews.map((review) => (
                <div className="evidence-review" key={review.review_id}>
                  <div className="evidence-meta">
                    {review.app_name} · {review.score}★ · {review.review_date} · {review.language || "unknown"}
                    {review.secondary_category && ` · also ${review.secondary_category}`}
                  </div>
                  <div>{review.content}</div>
                </div>
              )) : <div className="status-line">No source reviews found for this spike.</div>}
            </div>
          ) : <div className="error-line">{reviews.error}</div>)}
        </div>
      })}
    </div>
  );
}