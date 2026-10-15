import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Global handler for Vite dynamic chunk updates across deployments
window.addEventListener('vite:preloadError', (event) => {
  console.warn('Vite chunk preload error detected; reloading to latest deployment bundle...', event);
  const reloaded = sessionStorage.getItem('vite_preload_reloaded');
  if (!reloaded) {
    sessionStorage.setItem('vite_preload_reloaded', 'true');
    window.location.reload();
  }
});

// Clear reload guard once successfully mounted
window.addEventListener('load', () => {
  setTimeout(() => {
    sessionStorage.removeItem('vite_preload_reloaded');
  }, 3000);
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
