import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Session from './pages/Session.jsx';

function App() {
  return (
    <Router>
      <Routes>
        {/* This ensures the session loads immediately at http://localhost:5173/ */}
        <Route path="/" element={<Session />} />
        <Route path="/session" element={<Session />} />
      </Routes>
    </Router>
  );
}

export default App;