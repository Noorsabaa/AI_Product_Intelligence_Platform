import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Icon from './Icon';
import { AppMark, Badge, Empty } from './ui';
import { dateLabel, number, pct } from '../format';

export default function Overview({ data, onInsight, onNavigate, onCategory, onAnalyze, busy }) {
  const { summary: s, insights, categories, trends, apps, scope } = data;
  const attention = insights.filter((i) => i.status !== 'resolved');
  const spikes = attention.filter((i) => i.is_spike);
  const positive = pct(s.sentiments.positive || 0, s.analyzed);
  const cards = [
    {
      title: 'Customer reviews',
      value: number(s.total),
      note: `${apps.length} ${apps.length === 1 ? 'app' : 'apps'} in this view`,
      icon: 'feedback',
      tone: '',
    },
    {
      title: 'Positive feedback',
      value: s.analyzed ? `${positive}%` : '—',
      note: `${number(s.sentiments.positive)} of ${number(s.analyzed)} analyzed`,
      icon: 'pulse',
      tone: 'green',
    },
    {
      title: 'Average rating',
      value: s.avg_score?.toFixed(2) || '—',
      note: 'Out of 5 · all reviews in view',
      icon: 'star',
      tone: 'amber',
    },
    {
      title: 'Open opportunities',
      value: number(attention.length),
      note: `${spikes.length} rising complaint signals`,
      icon: 'actions',
      tone: 'purple',
    },
  ];
  return (
    <>
      <div className="metrics">
        {cards.map((card) => (
          <article className="metric" key={card.title}>
            <div className="metric-label">
              {card.title}
              <span className={`metric-icon ${card.tone}`}>
                <Icon name={card.icon} size={18} />
              </span>
            </div>
            <div className="metric-value">{card.value}</div>
            <div className="metric-note">{card.note}</div>
          </article>
        ))}
      </div>
      {scope.needs_analysis && (
        <div className="notice">
          <Icon name="info" />
          <div>
            <strong>
              {scope.published_run
                ? 'New feedback is ready to analyze'
                : 'Your feedback is here. Let’s find the signal.'}
            </strong>
            <span>
              Run analysis to publish themes, priorities and evidence from the current dataset.
            </span>
          </div>
          <button className="button small" onClick={onAnalyze} disabled={busy}>
            Analyze reviews <Icon name="arrow" size={15} />
          </button>
        </div>
      )}
      <div className="overview-charts">
        <section className="panel trend-panel">
          <div className="panel-heading">
            <div>
              <h2>The customer pulse</h2>
              <p>Weekly feedback across the selected period</p>
            </div>
            <span className="small-label">
              {s.sentiment_methods.rating ? 'Rating-based sentiment' : 'Sentiment'}
            </span>
          </div>
          <div className="chart-legend">
            <span>
              <i className="dot green" />
              Positive
            </span>
            <span>
              <i className="dot coral" />
              Negative
            </span>
            <span>
              <i className="dot amber" />
              Neutral
            </span>
            <span>
              <i className="dot gray" />
              Pending
            </span>
          </div>
          <div
            className="trend-chart"
            role="img"
            aria-label={`Weekly feedback chart: ${s.sentiments.positive || 0} positive, ${s.sentiments.negative || 0} negative, ${s.sentiments.neutral || 0} neutral and ${s.sentiments.pending || 0} pending reviews.`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends} margin={{ top: 12, right: 12, left: -22, bottom: 2 }}>
                <defs>
                  <linearGradient id="positiveFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#448971" stopOpacity={0.21} />
                    <stop offset="100%" stopColor="#448971" stopOpacity={0.015} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#edf0ed" strokeDasharray="4 4" />
                <XAxis
                  dataKey="date"
                  tickFormatter={dateLabel}
                  minTickGap={36}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#87918d', fontSize: 11 }}
                  dy={9}
                />
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#87918d', fontSize: 11 }}
                />
                <Tooltip
                  labelFormatter={(v) => `Week of ${dateLabel(v)}`}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e3e9e4', fontSize: 12 }}
                />
                <Area
                  isAnimationActive={false}
                  type="monotone"
                  dataKey="positive"
                  name="Positive"
                  stroke="#43876d"
                  fill="url(#positiveFill)"
                  strokeWidth={2.5}
                />
                <Area
                  isAnimationActive={false}
                  type="monotone"
                  dataKey="negative"
                  name="Negative"
                  stroke="#d78b76"
                  fill="transparent"
                  strokeWidth={2}
                />
                <Area
                  isAnimationActive={false}
                  type="monotone"
                  dataKey="neutral"
                  name="Neutral"
                  stroke="#c5a96a"
                  fill="transparent"
                  strokeWidth={1.5}
                />
                <Area
                  isAnimationActive={false}
                  type="monotone"
                  dataKey="pending"
                  name="Pending"
                  stroke="#a9afba"
                  fill="transparent"
                  strokeWidth={1.5}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="panel themes-panel">
          <div className="panel-heading">
            <div>
              <h2>What customers talk about</h2>
              <p>Themes in negative & neutral feedback</p>
            </div>
          </div>
          {categories.length ? (
            <div className="theme-list">
              {categories.slice(0, 5).map((category, index) => (
                <button
                  className="theme"
                  key={category.name}
                  onClick={() => onCategory(category.name)}
                >
                  <div>
                    <span>
                      <em>0{index + 1}</em>
                      {category.name}
                    </span>
                    <strong>{number(category.count)}</strong>
                  </div>
                  <div className="theme-track">
                    <i
                      style={{
                        width: `${(category.count / categories[0].count) * 100}%`,
                        opacity: 1 - index * 0.12,
                      }}
                    />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <Empty title="Themes will appear here">
              Analyze reviews to identify recurring feedback.
            </Empty>
          )}
          <button className="text-button panel-footer" onClick={() => onNavigate('feedback')}>
            Explore all feedback <Icon name="arrow" size={16} />
          </button>
        </section>
      </div>
      <section className="panel priorities-panel">
        <div className="panel-heading">
          <div>
            <h2>
              Where to focus next <span className="count-tag">{attention.length}</span>
            </h2>
            <p>Prioritized by feedback volume, rating severity and recent growth</p>
          </div>
          <button className="text-button" onClick={() => onNavigate('actions')}>
            View action board <Icon name="arrow" size={16} />
          </button>
        </div>
        {attention.length ? (
          <div className="priority-table">
            <div className="priority-table-head">
              <span>Opportunity</span>
              <span>Evidence</span>
              <span>Priority</span>
              <span>Suggested team</span>
              <span />
            </div>
            {attention.slice(0, 5).map((insight) => (
              <button className="priority-row" key={insight.id} onClick={() => onInsight(insight)}>
                <div className="priority-title">
                  <AppMark name={insight.app_name} />
                  <div>
                    <strong>{insight.category}</strong>
                    <small>
                      {insight.app_name}
                      {insight.is_spike && <span className="rising"> ↗ Rising signal</span>}
                    </small>
                  </div>
                </div>
                <span>{number(insight.count)} reviews</span>
                <span>
                  <Badge tone={insight.priority.toLowerCase()}>{insight.priority}</Badge>
                </span>
                <span className="team-name">{insight.owner}</span>
                <Icon name="chevron" size={17} />
              </button>
            ))}
          </div>
        ) : (
          <Empty
            title={
              s.analyzed
                ? 'No open opportunities in this view'
                : 'Good decisions start with evidence'
            }
          >
            {s.analyzed
              ? 'Try a wider period or a different app to explore more feedback.'
              : 'Analyze the imported reviews to surface themes and suggested next steps.'}
          </Empty>
        )}
      </section>
      <div className="overview-bottom">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Across your products</h2>
              <p>Review volume and average customer rating</p>
            </div>
          </div>
          <div className="products-grid">
            {apps.map((app) => (
              <div className="product" key={app.app_name}>
                <AppMark name={app.app_name} />
                <div>
                  <strong>{app.app_name}</strong>
                  <small>{number(app.count)} reviews</small>
                </div>
                <span>
                  <Icon name="star" size={14} />
                  {app.avg_score.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </section>
        <section className="coverage-card">
          <span className="eyebrow">BUILT ON EVIDENCE</span>
          <h2>
            Know what’s behind <br />
            every recommendation.
          </h2>
          <p>
            {number(s.categorized)} of {number(s.complaints)} negative or neutral reviews have a
            matched theme. Unmatched feedback stays available for review.
          </p>
          <button onClick={() => onNavigate('sources')}>
            View analysis coverage <Icon name="arrow" size={16} />
          </button>
        </section>
      </div>
    </>
  );
}
