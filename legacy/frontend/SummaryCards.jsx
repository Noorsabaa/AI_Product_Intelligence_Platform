export default function SummaryCards({ summary }) {
  if (!summary) return null;
  const { total_reviews_last_180_days, sentiment_breakdown } = summary;
  const coverage = summary.analysis_coverage;
  const analyzedTotal = coverage?.sentiment_processed ||
    Object.values(sentiment_breakdown).reduce((sum, count) => sum + (count || 0), 0);
  const pct = (n) => Math.round(((n || 0) / (analyzedTotal || 1)) * 100);

  return (
    <div className="grid grid-5">
      <div className="card">
        <h3>Total Reviews</h3>
        <div className="value">{summary.total_reviews}</div>
      </div>
      <div className="card">
        <h3>Reviews (180d)</h3>
        <div className="value">{total_reviews_last_180_days}</div>
      </div>
      <div className="card">
        <h3>Negative (analyzed)</h3>
        <div className="value" style={{ color: "#b91c1c" }}>{pct(sentiment_breakdown.negative)}%</div>
      </div>
      <div className="card">
        <h3>Neutral (analyzed)</h3>
        <div className="value" style={{ color: "#92600a" }}>{pct(sentiment_breakdown.neutral)}%</div>
      </div>
      <div className="card">
        <h3>Positive (analyzed)</h3>
        <div className="value" style={{ color: "#15803d" }}>{pct(sentiment_breakdown.positive)}%</div>
      </div>
    </div>
  );
}