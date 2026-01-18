import React, { useState } from "react";
import { api } from "../services/api";

/* ================= ICONS ================= */

const SunIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2" />
    <g stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="1" x2="12" y2="5" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="1" y1="12" x2="5" y2="12" />
      <line x1="19" y1="12" x2="23" y2="12" />
      <line x1="4.2" y1="4.2" x2="7" y2="7" />
      <line x1="17" y1="17" x2="19.8" y2="19.8" />
      <line x1="4.2" y1="19.8" x2="7" y2="17" />
      <line x1="17" y1="7" x2="19.8" y2="4.2" />
    </g>
  </svg>
);

const MoonIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <path
      d="M21 12.8A9 9 0 1111.2 3 7 7 0 0021 12.8z"
      stroke="currentColor"
      strokeWidth="2"
    />
  </svg>
);

/* ================= MAIN ================= */

export default function Session() {
  // ---------- STATE ----------
  const [theme, setTheme] = useState("dark");
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [score, setScore] = useState(100);
  const [probe, setProbe] = useState(null);
  const [answer, setAnswer] = useState("");
  const [logs, setLogs] = useState([]);
  const [syncRequired, setSyncRequired] = useState(false);

  // ---------- THEMES ----------
  const themes = {
    dark: {
      bg: "#000000",
      panel: "#0a0a0a",
      border: "#1a1a1a",
      text: "#ffffff",
      subtext: "#777777",
      accent: "#3b82f6",
      danger: "#ef4444",
      success: "#22c55e"
    },
    light: {
      bg: "#f5f5f5",
      panel: "#ffffff",
      border: "#dddddd",
      text: "#111111",
      subtext: "#555555",
      accent: "#2563eb",
      danger: "#dc2626",
      success: "#16a34a"
    }
  };

  const t = themes[theme];

  // ---------- UTILS ----------
  const addLog = (msg) => {
    setLogs((prev) => [
      `[${new Date().toLocaleTimeString()}] ${msg}`,
      ...prev
    ]);
  };

  const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

  // ---------- CORE PIPELINE ----------
  const fetchQuestionWithRetry = async (retries = 5) => {
    setSyncRequired(false);

    for (let i = 0; i < retries; i++) {
      try {
        const q = await api.getQuestion();
        const text = q?.followup_question || q?.question;

        if (text) {
          addLog("SUCCESS: Agents synchronized.");
          return text;
        }
      } catch {
        addLog(`Attempt ${i + 1}: Agent cluster timeout.`);
      }

      const wait = 2000 + i * 1000;
      addLog(`Retrying in ${wait / 1000}s...`);
      await sleep(wait);
    }

    addLog("CRITICAL: Agent synchronization failed.");
    setSyncRequired(true);
    return null;
  };

  const handleInitialization = async (file) => {
    if (!file) return;

    setLoading(true);
    setLogs([]);

    try {
      addLog("Step 1: Uploading document...");
      const media = await api.uploadFile(file);
      setContext(media.text || "Context Loaded");

      addLog("Step 2: Initializing exam session...");
      await api.startExam();

      addLog("Step 3: Generating first probe...");
      const q = await fetchQuestionWithRetry();

      if (q) {
        setProbe(q);
        addLog("SUCCESS: First probe ready.");
      }
    } catch {
      addLog("ERROR: Backend connection failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSubmit = async () => {
    if (!answer.trim() || loading) return;

    setLoading(true);

    try {
      addLog("Step 4: Submitting answer...");
      const data = await api.submitAnswer(answer);

      addLog("Step 5: Updating stability score...");
      setScore(data.stability_score ?? score);

      addLog("Step 6: Checking probe status...");
      const status = await api.getProbeStatus();

      if (status?.status === "REJECTED") {
        addLog("WARNING: Probe rejected. Re-aligning agents...");
      }

      addLog("Step 7: Fetching next probe...");
      const nextQ = await fetchQuestionWithRetry();

      if (nextQ) {
        setProbe(nextQ);
        setAnswer("");
        addLog("SUCCESS: Next probe deployed.");
      }
    } catch {
      addLog("ERROR: Pipeline execution failed.");
    } finally {
      setLoading(false);
    }
  };

  // ---------- UI ----------
  return (
    <div
      style={{
        minHeight: "100vh",
        background: t.bg,
        color: t.text,
        fontFamily: "monospace",
        padding: "40px"
      }}
    >
      {/* HEADER BAR */}
      <div
        style={{
          maxWidth: "900px",
          margin: "0 auto 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between"
        }}
      >
        <div style={{ width: "42px" }} />

        {/* CENTER TITLE */}
        <div
          style={{
            fontSize: "50px",
            letterSpacing: "4px",
            fontWeight: "bold"
          }}
        >
          FUD.AI
        </div>

        {/* THEME TOGGLE */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          style={{
            background: t.panel,
            color: t.text,
            border: `1px solid ${t.border}`,
            width: "42px",
            height: "42px",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer"
          }}
        >
          {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>

      {/* STABILITY BAR */}
      <div style={{ maxWidth: "700px", margin: "20px auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
          <span>SYSTEM STABILITY</span>
          <span>{score}%</span>
        </div>
        <div style={{ height: "3px", background: t.border }}>
          <div
            style={{
              width: `${score}%`,
              height: "100%",
              background: t.accent,
              transition: "1.5s"
            }}
          />
        </div>
      </div>

      {/* UPLOAD STATE */}
      {!context ? (
        <div
          style={{
            maxWidth: "600px",
            margin: "80px auto",
            textAlign: "center",
            border: `1px solid ${t.border}`,
            padding: "50px",
            borderRadius: "10px",
            background: t.panel
          }}
        >
          <input
            type="file"
            id="up"
            hidden
            onChange={(e) => handleInitialization(e.target.files[0])}
          />
          <label
            htmlFor="up"
            style={{
              cursor: "pointer",
              color: t.accent,
              border: `1px solid ${t.accent}`,
              padding: "12px 24px",
              borderRadius: "6px"
            }}
          >
            {loading ? "WAKING AGENTS..." : "UPLOAD DOCUMENT"}
          </label>
        </div>
      ) : (
        <div style={{ maxWidth: "700px", margin: "0 auto" }}>
          {/* PROBE */}
          <div
            style={{
              background: t.panel,
              border: `1px solid ${t.border}`,
              padding: "25px",
              borderRadius: "6px",
              marginBottom: "20px"
            }}
          >
            <p style={{ fontSize: "11px", color: t.subtext }}>
              {loading ? "AGENT BUSY..." : "AGENT PROBE"}
            </p>
            <p style={{ fontSize: "16px", lineHeight: "1.6" }}>
              {probe || "Synchronizing cluster..."}
            </p>
          </div>

          {syncRequired && (
            <button
              onClick={async () => {
                setLoading(true);
                const q = await fetchQuestionWithRetry();
                if (q) setProbe(q);
                setLoading(false);
              }}
              style={{
                width: "100%",
                marginBottom: "15px",
                padding: "12px",
                background: t.danger,
                color: "#fff",
                border: "none",
                cursor: "pointer",
                fontWeight: "bold"
              }}
            >
              FORCE AGENT RESYNC
            </button>
          )}

          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={loading}
            placeholder="Provide your reasoning..."
            style={{
              width: "100%",
              minHeight: "150px",
              padding: "20px",
              background: t.panel,
              border: `1px solid ${t.border}`,
              color: t.text,
              marginBottom: "15px"
            }}
          />

          <button
            onClick={handleAnswerSubmit}
            disabled={loading || !answer.trim()}
            style={{
              width: "100%",
              padding: "15px",
              background: loading ? t.border : t.accent,
              color: "#fff",
              border: "none",
              cursor: "pointer",
              fontWeight: "bold"
            }}
          >
            {loading ? "TRANSMITTING..." : "SUBMIT RESPONSE"}
          </button>
        </div>
      )}

      {/* LOGS */}
      <div style={{ maxWidth: "700px", margin: "40px auto" }}>
        <p style={{ fontSize: "11px", color: t.subtext }}>AGENT ACTIVITY LOG</p>
        <div style={{ maxHeight: "160px", overflowY: "auto", fontSize: "11px" }}>
          {logs.length === 0 && <span>System idle.</span>}
          {logs.map((log, i) => (
            <div
              key={i}
              style={{
                marginBottom: "6px",
                color: log.includes("ERROR") || log.includes("CRITICAL")
                  ? t.danger
                  : log.includes("SUCCESS")
                  ? t.success
                  : t.subtext
              }}
            >
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}