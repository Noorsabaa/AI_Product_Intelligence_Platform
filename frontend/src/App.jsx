import { useEffect, useState, useCallback } from "react";
import { getSummary, getCategories, getSpikes, getRecommendations } from "./api";
import SummaryCards from "./components/SummaryCards";
import CategoryChart from "./components/CategoryChart";
import AppBreakdown from "./components/AppBreakdown";
import SpikesList from "./components/SpikesList";
import CsvUpload from "./components/CsvUpload";
import "./index.css";

export default function App() {
  const [summary, setSummary] = useState(null);
  const [categories, setCategories] = useState([]);
  const [spikes, setSpikes] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  const loadAll = useCallback(async () => {
    const [s, c, sp, r] = await Promise.all([
      getSummary(), getCategories(), getSpikes(), getRecommendations(),
    ]);
    setSummary(s);
    setCategories(c.categories);
    setSpikes(sp.spikes);
    setRecommendations(r.recommendations);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  return (
    <div className="app">
      <div className="header">
        <h1>Complaint Intelligence Dashboard</h1>
        <p>B2B SaaS review monitoring — last 180 days</p>
      </div>

      <SummaryCards summary={summary} />

      <div className="section grid grid-2">
        {categories.length > 0 && <CategoryChart categories={categories} />}
        {summary && <AppBreakdown perApp={summary.per_app} />}
      </div>

      <div className="section">
        <div className="section-title">Active Spikes & Recommendations</div>
        <SpikesList spikes={spikes} recommendations={recommendations} />
      </div>

      <div className="section">
        <div className="section-title">Add New Reviews (CSV)</div>
        <CsvUpload onDone={loadAll} />
      </div>
    </div>
  );
}