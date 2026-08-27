import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function CategoryChart({ categories }) {
  const data = [...categories].sort((a, b) => b.count - a.count);
  return (
    <div className="card">
      <div className="section-title" style={{ marginBottom: 12 }}>Complaints by Category</div>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
          <XAxis type="number" fontSize={12} />
          <YAxis dataKey="category" type="category" width={200} fontSize={11.5} />
          <Tooltip />
          <Bar dataKey="count" fill="#1a1a2e" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}