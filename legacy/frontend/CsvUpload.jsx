import { useEffect, useRef, useState } from "react";
import { uploadCsv, triggerPipeline, getPipelineStatus } from "../api";

export default function CsvUpload({ onDone }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const handleUpload = async () => {
    if (!file) return;
    setBusy(true);
    setStatus("Uploading CSV...");
    try {
      const result = await uploadCsv(file);
      setStatus(`Inserted ${result.inserted}, skipped ${result.skipped}. Running pipeline...`);

      await triggerPipeline();
      const poll = async () => {
        const s = await getPipelineStatus();
        setStatus(`Pipeline: ${s.status} (${s.stage || "idle"})`);
        if (s.status === "completed" || s.status === "failed") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setBusy(false);
          if (s.status === "failed") {
            setStatus(`Pipeline failed: ${s.last_error || "Unknown pipeline error"}`);
          }
          onDone();
        }
      };
      pollRef.current = setInterval(poll, 3000);
      await poll();
    } catch (requestError) {
      clearInterval(pollRef.current);
      pollRef.current = null;
      setBusy(false);
      setStatus(`Error: ${requestError.message}`);
    }
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