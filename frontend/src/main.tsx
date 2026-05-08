import './app/styles/tokens.css'   // FIRST: design tokens (CSS vars + density)
import './app/styles/globals.css'  // Tailwind directives
import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from '@/app/App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
