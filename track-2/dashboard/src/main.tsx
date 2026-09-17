import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
if (import.meta.env.PROD && import.meta.env.VITE_USE_FIXTURES === 'true') throw new Error('Fixture mode is disabled in production builds.');
async function start() {
  if (import.meta.env.DEV && import.meta.env.VITE_USE_FIXTURES === 'true') {
    const { worker } = await import('./mocks/browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }
  createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
}
void start();
