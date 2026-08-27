import { useState } from "react";
import { uploadCsv, triggerPipeline, getPipelineStatus } from "../api";

export default function CsvUpload({ onDone }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setBusy(true);
    setStatus("Uploading CSV...");
    const result = await uploadCsv(file);
    setStatus(`Inserted ${result.inserted}, skipped ${result.skipped}. Running pipeline...`);

    await triggerPipeline();
    const poll = setInterval(async () => {
      const s = await getPipelineStatus();
      setStatus(`Pipeline: ${s.status} (${s.stage})`);
      if (s.status === "completed" || s.status === "failed") {
        clearInterval(poll);
        setBusy(false);
        onDone();
      }
    }, 3000);
  };

  return (
    <div className="upload-box">
      <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])} />
      <div style={{ marginTop: 12 }}>
        <button className="btn" disabled={!file || busy} onClick={handleUpload}>
          {busy ? "Processing..." : "Upload & Analyze"}
        </button>
      </div>
      {status && <div className="status-line">{status}</div>}
    </div>
  );
}