const ACCESS_TOKEN_KEY = 'bundlegraph.access_token';
const EXPIRES_AT_KEY = 'bundlegraph.expires_at';
const PKCE_VERIFIER_KEY = 'bundlegraph.pkce_verifier';
const OIDC_STATE_KEY = 'bundlegraph.oidc_state';

const authorizationEndpoint = import.meta.env.VITE_BUNDLEGRAPH_OIDC_AUTHORIZATION_ENDPOINT?.trim();
const tokenEndpoint = import.meta.env.VITE_BUNDLEGRAPH_OIDC_TOKEN_ENDPOINT?.trim();
const clientId = import.meta.env.VITE_BUNDLEGRAPH_OIDC_CLIENT_ID?.trim();
const scope = import.meta.env.VITE_BUNDLEGRAPH_OIDC_SCOPE?.trim() || 'openid profile';
const redirectUri = import.meta.env.VITE_BUNDLEGRAPH_OIDC_REDIRECT_URI?.trim() || `${window.location.origin}/`;

export const oidcConfigured = Boolean(authorizationEndpoint && tokenEndpoint && clientId);

function base64Url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

function randomValue(size = 32): string {
  const bytes = new Uint8Array(size);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

export function setSession(accessToken: string, expiresInSeconds = 900): void {
  if (!accessToken || !Number.isFinite(expiresInSeconds) || expiresInSeconds <= 0) throw new Error('Invalid session response');
  try {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    sessionStorage.setItem(EXPIRES_AT_KEY, String(Date.now() + expiresInSeconds * 1000));
  } catch { throw new Error('Browser session storage is unavailable'); }
  window.dispatchEvent(new Event('bundlegraph:auth-changed'));
}

export function clearSession(): void {
  try { sessionStorage.removeItem(ACCESS_TOKEN_KEY); sessionStorage.removeItem(EXPIRES_AT_KEY); } catch { /* Already unauthenticated if storage is unavailable. */ }
  window.dispatchEvent(new Event('bundlegraph:auth-changed'));
}

export function getAccessToken(): string | null {
  let token: string | null; let expiresAt: number;
  try { token = sessionStorage.getItem(ACCESS_TOKEN_KEY); expiresAt = Number(sessionStorage.getItem(EXPIRES_AT_KEY) || 0); }
  catch { return null; }
  if (!token || !expiresAt || expiresAt <= Date.now()) {
    if (token) clearSession();
    return null;
  }
  return token;
}

export function sessionExpiresAt(): number | null {
  try { const value = Number(sessionStorage.getItem(EXPIRES_AT_KEY) || 0); return Number.isFinite(value) && value > 0 ? value : null; }
  catch { return null; }
}

export async function beginSignIn(): Promise<void> {
  if (!oidcConfigured || !authorizationEndpoint || !clientId) throw new Error('OIDC is not configured');
  const verifier = randomValue(48);
  const state = randomValue();
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(OIDC_STATE_KEY, state);
  const url = new URL(authorizationEndpoint);
  url.search = new URLSearchParams({
    response_type: 'code', client_id: clientId, redirect_uri: redirectUri, scope, state,
    code_challenge: base64Url(new Uint8Array(digest)), code_challenge_method: 'S256',
  }).toString();
  window.location.assign(url);
}

export async function completeSignIn(): Promise<boolean> {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  if (!code) return false;
  const state = params.get('state');
  const expectedState = sessionStorage.getItem(OIDC_STATE_KEY);
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  if (!tokenEndpoint || !clientId || !state || state !== expectedState || !verifier) {
    clearSession();
    throw new Error('OIDC callback validation failed');
  }
  const response = await fetch(tokenEndpoint, {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'authorization_code', code, client_id: clientId, redirect_uri: redirectUri, code_verifier: verifier }),
  });
  if (!response.ok) throw new Error(`OIDC token exchange failed (${response.status})`);
  const payload = await response.json() as { access_token?: string; expires_in?: number };
  if (!payload.access_token) throw new Error('OIDC response did not contain an access token');
  setSession(payload.access_token, payload.expires_in || 900);
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(OIDC_STATE_KEY);
  window.history.replaceState({}, '', window.location.pathname + window.location.hash);
  return true;
}
