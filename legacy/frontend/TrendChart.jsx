import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function TrendChart({ trends }) {
  return (
    <div className="card">
      <div className="section-title" style={{ marginBottom: 4 }}>Monthly feedback trend</div>
      <div className="chart-note">All reviews compared with classified complaints</div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={trends} margin={{ top: 12, right: 12, left: 0, bottom: 4 }}>
          <XAxis dataKey="month" fontSize={11} />
          <YAxis allowDecimals={false} fontSize={11} />
          <Tooltip />
          <Line type="monotone" dataKey="review_count" name="All reviews" stroke="#1a1a2e" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="complaint_count" name="Complaints" stroke="#b91c1c" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="negative_count" name="Negative" stroke="#d97706" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}