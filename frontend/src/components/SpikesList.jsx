export default function SpikesList({ spikes, recommendations }) {
  const briefFor = (spike) =>
    recommendations.find(
      (r) => r.app_name === spike.app_name && r.category === spike.category && r.period === spike.period
    )?.brief;

  if (!spikes.length) return <p style={{ color: "#6b7280", fontSize: 14 }}>No active spikes detected.</p>;

  return (
    <div>
      {spikes.map((s, i) => (
        <div className="spike-item" key={i}>
          <div className="spike-header">
            <span className="spike-title">{s.app_name} — {s.category}</span>
            <span className="spike-badge">+{s.pct_change}%</span>
          </div>
          <div className="spike-meta">
            {s.period} · {s.granularity} · {s.count} complaints (baseline {s.baseline})
          </div>
          <div className="spike-brief">{briefFor(s) || "Recommendation not yet generated."}</div>
        </div>
      ))}
    </div>
  );
}