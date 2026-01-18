import React from 'react';
import { AlertCircle, XOctagon } from 'lucide-react';

export default function QuestionCard({ data, onOptionSelect }) {
  const { probe, responseType, options, explanation } = data;

  // TERMINAL FAILURE: Completely off the mark [cite: 195-197]
  if (responseType === 'terminal_failure') {
    return (
      <div className="p-8 border-2 border-red-600 bg-red-950/20 rounded-2xl text-center">
        <XOctagon className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-red-500 mb-2">Understanding lacks.</h2>
        <p className="text-slate-300 mb-6">{explanation || "Conceptual reasoning has collapsed."}</p>
        <button onClick={() => window.location.reload()} className="bg-red-600 px-6 py-2 rounded font-bold">Restart Session</button>
      </div>
    );
  }

  return (
    <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl">
      <h3 className="text-xl font-medium text-slate-100 mb-6 italic">"{probe}"</h3>

      {/* MCQ: Bit off the mark [cite: 177, 181-188] */}
      {responseType === 'mcq' && (
        <div className="grid grid-cols-1 gap-3">
          {options.map((opt, i) => (
            <button key={i} onClick={() => onOptionSelect(opt)} className="p-4 bg-slate-800 hover:bg-blue-900/40 border border-slate-700 hover:border-blue-500 rounded-xl text-left transition-all">
              <span className="font-bold text-blue-400 mr-3">{i + 1}.</span> {opt}
            </button>
          ))}
        </div>
      )}

      {/* LONG ANSWER: Too far off or initial probe [cite: 178, 189-191] */}
      {responseType === 'long_answer' && (
        <div className="flex items-center gap-2 text-amber-400 text-sm bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">
          <AlertCircle className="w-4 h-4" />
          <span>Detailed reasoning required to realign understanding.</span>
        </div>
      )}
    </div>
  );
}