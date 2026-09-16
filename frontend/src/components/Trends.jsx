import {
  Line,
  LineChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useState } from 'react';
import { dateLabel } from '../format';
export default function Trends({ data, chartTopic, setChartTopic }) {
  const [measure, setMeasure] = useState('count');
  return (
    <section className="panel">
      <header className="section-head">
        <div>
          <span className="section-number">01 / TRENDS</span>
          <h2>How feedback is changing</h2>
          <p>Select a category to follow its trend over time.</p>
        </div>
        <label className="chart-filter">
          Category
          <select
            aria-label="Chart category"
            value={chartTopic}
            onChange={(e) => setChartTopic(e.target.value)}
          >
            <option value="">All feedback</option>
            {data.categories.map((c) => (
              <option value={c.id} key={c.id}>
                {c.label}
              </option>
            ))}
            <option value="ungrouped">Not yet grouped</option>
          </select>
        </label>
      </header>
      <div className="chart-toolbar">
        <div className="legend">
          <span>
            <i className="dot brown" />
            Negative reviews
          </span>
          <span>
            <i className="dot taupe" />
            All sentiment
          </span>
        </div>
        <div className="segmented" aria-label="Chart measurement">
          <button aria-pressed={measure === 'count'} onClick={() => setMeasure('count')}>
            Review count
          </button>
          <button aria-pressed={measure === 'share'} onClick={() => setMeasure('share')}>
            Share of feedback
          </button>
        </div>
      </div>
      <div
        className="trend-chart"
        role="img"
        aria-label="Trend in negative reviews and all sentiment for the selected category"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.trends} margin={{ top: 12, right: 15, left: -15, bottom: 10 }}>
            <CartesianGrid vertical={false} stroke="#eae4da" strokeDasharray="3 4" />
            <XAxis
              dataKey="date"
              tickFormatter={dateLabel}
              minTickGap={40}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#81786b' }}
              dy={9}
            />
            <YAxis
              allowDecimals={measure === 'share'}
              unit={measure === 'share' ? '%' : ''}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#81786b' }}
            />
            <Tooltip
              labelFormatter={(v) =>
                `${data.granularity === 'week' ? 'Week of ' : ''}${dateLabel(v)}`
              }
              formatter={(value, name) => [measure === 'share' ? `${value}%` : value, name]}
              contentStyle={{ border: '1px solid #d8cfc0', borderRadius: 4, fontSize: 12 }}
            />
            <Line
              type="linear"
              dataKey={measure === 'count' ? 'total' : 'total_share'}
              name="All sentiment"
              stroke="#c6bba8"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey={measure === 'count' ? 'negative' : 'negative_share'}
              name="Negative reviews"
              stroke="#90684e"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <footer className="chart-foot">
        {measure === 'share'
          ? 'Share uses all analyzed feedback in each time bucket as its denominator.'
          : 'Counts are feedback records, not unique customers.'}{' '}
        {data.granularity === 'week' ? 'First and last weeks may be partial.' : ''}
      </footer>
    </section>
  );
}
