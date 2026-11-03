import React, { useEffect, useState, type ReactNode } from 'react';
import { beginSignIn, completeSignIn, getAccessToken, oidcConfigured, setSession } from '../../auth/session';
import { frontendRuntime } from '../../api/client';

export const AuthGate: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [authenticated, setAuthenticated] = useState(() => frontendRuntime.mode === 'fixture' || Boolean(getAccessToken()));
  const [localToken, setLocalToken] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const update = () => setAuthenticated(frontendRuntime.mode === 'fixture' || Boolean(getAccessToken()));
    window.addEventListener('bundlegraph:auth-changed', update);
    completeSignIn().then(update).catch((reason: unknown) => setError(String(reason)));
    return () => window.removeEventListener('bundlegraph:auth-changed', update);
  }, []);

  if (authenticated) return children;
  return (
    <main className="auth-gate" aria-labelledby="sign-in-title">
      <section className="studio-card auth-card">
        <h1 id="sign-in-title">Sign in to BundleGraph</h1>
        <p>Your session protects confirmed requirements, stored plans, evidence, approvals, and recovery proposals.</p>
        {error && <div className="callout callout-error" role="alert">{error}</div>}
        {oidcConfigured ? (
          <button type="button" className="btn-primary" onClick={() => beginSignIn().catch((reason: unknown) => setError(String(reason)))}>
            Continue with identity provider
          </button>
        ) : (
          <form onSubmit={(event) => { event.preventDefault(); if (localToken.trim()) setSession(localToken.trim(), 3600); }}>
            <label className="form-label" htmlFor="local-access-token">Local application access token</label>
            <input id="local-access-token" className="studio-input" type="password" autoComplete="off" value={localToken} onChange={(event) => setLocalToken(event.target.value)} />
            <p className="form-help">For local application mode only. Configure OIDC for deployed environments.</p>
            <button type="submit" className="btn-primary" disabled={!localToken.trim()}>Start protected session</button>
          </form>
        )}
      </section>
    </main>
  );
};
