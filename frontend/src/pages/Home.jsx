import React, { useState } from 'react';
import { api } from '../services/api';

export default function Session() {
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [score, setScore] = useState(100);
  const [probe, setProbe] = useState(null);
  const [answer, setAnswer] = useState("");
  const [logs, setLogs] = useState([]);
  const [syncRequired, setSyncRequired] = useState(false);

  const addLog = (msg) => setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);

  /**
   * Updated fetch logic to handle different backend payload keys.
   * Backend uses 'question' for Step 3 and 'followup_question' for Step 7.
   */
  const fetchQuestionWithRetry = async (retries = 5) => {
    setSyncRequired(false);
    for (let i = 0; i < retries; i++) {
      try {
        const q = await api.getQuestion();
        
        // MAPPING FIX: Check both possible keys returned by the backend
        const questionText = q?.followup_question || q?.question;
        
        if (questionText) {
          addLog("Success: Agent cluster synchronized.");
          return questionText;
        }
      } catch (e) {
        addLog(`Attempt ${i + 1}: Agent cluster timed out...`);
      }
      
      const waitTime = 2000 + (i * 1000); 
      addLog(`Retry ${i + 1}: Waiting ${waitTime/1000}s for concept alignment...`);
      await new Promise(res => setTimeout(res, waitTime));
    }
    
    addLog("CRITICAL: Agents rejected probe or timed out.");
    setSyncRequired(true); 
    return null;
  };

  const handleInitialization = async (file) => {
    if (!file) return;
    setLoading(true);
    setLogs([]); 
    try {
      addLog("Step 1: Contacting Media API...");
      const media = await api.uploadFile(file);
      setContext(media.text || "Context Extracted");

      addLog("Step 2: Initializing Exam State...");
      await api.startExam();

      addLog("Step 3: Triggering Question Generator...");
      const question = await fetchQuestionWithRetry();
      
      if (question) {
        setProbe(question);
        addLog("Success: Agent Probe generated.");
      }
    } catch (e) {
      addLog("ERROR: Connection to backend failed.");
    } finally { setLoading(false); }
  };

  const handleAnswerSubmit = async () => {
    if (!answer.trim() || loading) return;
    setLoading(true);
    try {
      addLog("Step 4: Submitting answer to Chat Agent...");
      const data = await api.submitAnswer(answer);
      
      addLog("Step 5: Stability Analyser evaluating...");
      setScore(data.stability_score || score);

      addLog("Step 6: Syncing with Probe Agent...");
      const probeStatus = await api.getProbeStatus(); 

      // Check if backend rejected the concept
      if (probeStatus?.status === "REJECTED") {
        addLog("Warning: Probe rejected (Off Concept). Attempting re-generation...");
      }

      addLog("Step 7: Finalizing next question...");
      await new Promise(res => setTimeout(res, 2500)); 

      const nextQ = await fetchQuestionWithRetry();
      
      if (nextQ) {
        setProbe(nextQ);
        addLog("Step 8: Interaction archived. New probe ready.");
        setAnswer("");
      }
    } catch (e) {
      addLog("ERROR: Sequence broken. Check backend logs.");
      console.error(e);
    } finally { setLoading(false); }
  };
  
  return (
    <div style={{ backgroundColor: '#000000', color: '#fff', minHeight: '100vh', padding: '40px', fontFamily: 'monospace' }}>
      <div style={{ maxWidth: '700px', margin: '0 auto 40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginBottom: '8px' }}>
          <span>SYSTEM STABILITY</span>
          <span>{score}%</span>
        </div>
        <div style={{ width: '100%', height: '2px', backgroundColor: '#222' }}>
          <div style={{ width: `${score}%`, height: '100%', backgroundColor: '#007bff', transition: '1.5s' }} />
        </div>
      </div>

      {!context ? (
        <div style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center', border: '1px solid #333', padding: '50px', borderRadius: '10px' }}>
          <input type="file" id="up" style={{ display: 'none' }} onChange={(e) => handleInitialization(e.target.files[0])} />
          <label htmlFor="up" style={{ color: '#007bff', cursor: 'pointer', border: '1px solid #007bff', padding: '10px 20px', borderRadius: '5px', textTransform: 'uppercase' }}>
            {loading ? "WAKING AGENTS..." : "UPLOAD DOCUMENT"}
          </label>
        </div>
      ) : (
        <div style={{ maxWidth: '700px', margin: '0 auto' }}>
          <div style={{ background: '#0a0a0a', padding: '25px', borderRadius: '5px', border: '1px solid #1a1a1a', marginBottom: '20px' }}>
            <p style={{ color: '#444', fontSize: '10px', marginBottom: '10px' }}>{loading ? "AGENT BUSY..." : "AGENT PROBE"}</p>
            <p style={{ fontSize: '16px', color: '#ccc', lineHeight: '1.5' }}>{probe || "Synchronizing cluster..."}</p>
          </div>

          {syncRequired && (
            <button 
              onClick={async () => {
                setLoading(true);
                const q = await fetchQuestionWithRetry();
                if (q) setProbe(q);
                setLoading(false);
              }}
              style={{ background: '#ff4444', color: '#fff', border: 'none', padding: '10px', width: '100%', marginBottom: '15px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              RETRIES FAILED: CLICK TO FORCE SYNC AGENTS
            </button>
          )}

          <textarea 
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={loading}
            style={{ width: '100%', background: '#000', border: '1px solid #1a1a1a', padding: '20px', color: '#fff', marginBottom: '15px', outline: 'none', minHeight: '150px', fontSize: '14px' }}
            placeholder="Provide your reasoning to the agents..."
          />
          <button onClick={handleAnswerSubmit} disabled={loading || !answer.trim()} style={{ width: '100%', padding: '15px', background: loading ? '#222' : '#007bff', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 'bold', transition: '0.3s' }}>
            {loading ? "TRANSMITTING..." : "SUBMIT RESPONSE"}
          </button>
        </div>
      )}

      <div style={{ maxWidth: '700px', margin: '40px auto 0', borderTop: '1px solid #1a1a1a', paddingTop: '20px' }}>
        <p style={{ fontSize: '10px', color: '#444', marginBottom: '10px' }}>AGENT ACTIVITY LOG</p>
        <div style={{ height: '150px', overflowY: 'auto', fontSize: '11px', color: '#666', scrollbarWidth: 'thin' }}>
          {logs.length === 0 && <span>System idle.</span>}
          {logs.map((log, i) => (
            <div key={i} style={{ marginBottom: '6px', color: log.includes('ERROR') || log.includes('CRITICAL') ? '#ff4444' : log.includes('Success') ? '#00ff00' : '#666' }}>{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
}