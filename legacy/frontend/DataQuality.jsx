export default function DataQuality({ summary }) {
  if (!summary?.analysis_coverage) return null;

  const coverage = summary.analysis_coverage;
  const languageRows = Object.entries(summary.language_breakdown || {});
  const percent = (value) => `${Math.round(value * 100)}%`;

  return (
    <div className="quality-panel">
      <div>
        <div className="section-title">Data & model coverage</div>
        <div className="quality-grid">
          <div>
            <span className="quality-label">Language processed</span>
            <strong>{percent(coverage.language_coverage)}</strong>
            <span className="quality-detail">{coverage.language_processed} of {coverage.window_reviews} reviews</span>
          </div>
          <div>
            <span className="quality-label">Sentiment processed</span>
            <strong>{percent(coverage.sentiment_coverage)}</strong>
            <span className="quality-detail">avg confidence {coverage.avg_sentiment_confidence == null ? "n/a" : coverage.avg_sentiment_confidence}</span>
          </div>
          <div>
            <span className="quality-label">Trusted categories</span>
            <strong>{percent(coverage.category_coverage)}</strong>
            <span className="quality-detail">{coverage.trusted_categories} of {coverage.complaint_reviews} complaint reviews</span>
          </div>
          <div>
            <span className="quality-label">Category confidence</span>
            <strong>{coverage.avg_category_confidence == null ? "n/a" : coverage.avg_category_confidence}</strong>
            <span className="quality-detail">trusted threshold 0.7</span>
          </div>
        </div>
      </div>
      <div className="language-breakdown">
        <span className="quality-label">Review languages</span>
        {languageRows.map(([language, count]) => (
          <div className="language-row" key={language}>
            <span>{language}</span>
            <strong>{count}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
