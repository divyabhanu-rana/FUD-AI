const BASE = "https://unlignified-diddly-kristle.ngrok-free.dev";
const OPTS = { headers: { "ngrok-skip-browser-warning": "true", "Content-Type": "application/json" } };

export const api = {
  async uploadFile(file) {
    const fd = new FormData(); fd.append('file', file);
    const res = await fetch(`${BASE}/media/extract`, { method: "POST", body: fd, headers: {"ngrok-skip-browser-warning": "true"} });
    return res.json();
  },
  async startExam() {
    return fetch(`${BASE}/start_exam`, { method: "GET", ...OPTS }).then(r => r.json());
  },
  async getQuestion() {
    return fetch(`${BASE}/question`, { method: "GET", ...OPTS }).then(r => r.json());
  },
  // NEW PROBE ENDPOINT
  async getProbeStatus() {
    return fetch(`${BASE}/probe`, { method: "GET", ...OPTS }).then(r => r.json());
  },
  async submitAnswer(ans) {
    const res = await fetch(`${BASE}/answer`, { method: "POST", ...OPTS, body: JSON.stringify({ answer: ans }) });
    return res.json();
  }
};