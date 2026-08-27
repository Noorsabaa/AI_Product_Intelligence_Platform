const BASE_URL = "http://127.0.0.1:8000";

export async function getSummary() {
    const res = await fetch(`${BASE_URL}/dashboard/summary`);
    return res.json();
}

export async function getCategories() {
    const res = await fetch(`${BASE_URL}/dashboard/categories`);
    return res.json();
}

export async function getSpikes() {
    const res = await fetch(`${BASE_URL}/dashboard/spikes`);
    return res.json();
}

export async function getRecommendations() {
    const res = await fetch(`${BASE_URL}/dashboard/recommendations`);
    return res.json();
}

export async function uploadCsv(file) {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${BASE_URL}/ingest/csv`, {
        method: "POST",
        body: formData
    });

    return res.json();
}

export async function triggerPipeline() {
    const res = await fetch(`${BASE_URL}/pipeline/run`, {
        method: "POST"
    });

    return res.json();
}

export async function getPipelineStatus() {
    const res = await fetch(`${BASE_URL}/pipeline/status`);
    return res.json();
}