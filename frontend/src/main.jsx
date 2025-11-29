import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import CelerGraphApp from './GraphRAGChat';

/**
 * GLOBAL STYLES
 * Injected via JS to avoid 'Could not resolve ./index.css' errors
 */
const GlobalStyles = () => (
  <style>{`
    @tailwind base;
    @tailwind components;
    @tailwind utilities;
    
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
        sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      background-color: #f0f0f0;
    }
  `}</style>
);

// RENDER
const container = document.getElementById('root');

// Prevent HMR double-render warning
if (!container._reactRoot) {
  container._reactRoot = createRoot(container);
}

container._reactRoot.render(
  <React.StrictMode>
    <GlobalStyles />
    <CelerGraphApp />
  </React.StrictMode>
);
