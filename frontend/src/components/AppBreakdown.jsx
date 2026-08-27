export default function AppBreakdown({ perApp }) {
  return (
    <div className="card">
      <div className="section-title" style={{ marginBottom: 12 }}>By App</div>
      {perApp.map((app) => (
        <div key={app.app_name} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f0f0f0", fontSize: 13.5 }}>
          <span>{app.app_name}</span>
          <span style={{ color: "#6b7280" }}>{app.review_count} reviews · avg {app.avg_score}★</span>
        </div>
      ))}
    </div>
  );
}