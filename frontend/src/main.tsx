import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { configureOidc } from './auth/session.ts'
import { loadRuntimeConfiguration } from './api/client.ts'

const root = createRoot(document.getElementById('root')!);

async function start(): Promise<void> {
  const oidc = await loadRuntimeConfiguration();
  configureOidc(oidc);
  root.render(<StrictMode><App /></StrictMode>);
}

start().catch((reason: unknown) => {
  const message = reason instanceof Error ? reason.message : 'Unknown startup error';
  root.render(<main className="auth-gate"><section className="studio-card auth-card"><h1>BundleGraph could not start</h1><p>{message}</p><button type="button" className="btn-primary" onClick={() => window.location.reload()}>Retry</button></section></main>);
});
