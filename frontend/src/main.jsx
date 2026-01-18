import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

// This "root" must match the ID in your index.html
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)