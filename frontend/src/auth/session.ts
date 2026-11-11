const ACCESS_TOKEN_KEY = 'bundlegraph.access_token';
const EXPIRES_AT_KEY = 'bundlegraph.expires_at';
const PKCE_VERIFIER_KEY = 'bundlegraph.pkce_verifier';
const OIDC_STATE_KEY = 'bundlegraph.oidc_state';

export interface BrowserOidcConfig {
  provider?: string;
  authorization_endpoint: string;
  token_endpoint: string;
  client_id: string;
  audience?: string;
  scope?: string;
  redirect_uri?: string;
}

let oidcConfig: BrowserOidcConfig | null = (() => {
  const authorizationEndpoint = import.meta.env.VITE_BUNDLEGRAPH_OIDC_AUTHORIZATION_ENDPOINT?.trim();
  const tokenEndpoint = import.meta.env.VITE_BUNDLEGRAPH_OIDC_TOKEN_ENDPOINT?.trim();
  const clientId = import.meta.env.VITE_BUNDLEGRAPH_OIDC_CLIENT_ID?.trim();
  return authorizationEndpoint && tokenEndpoint && clientId ? {
    authorization_endpoint: authorizationEndpoint,
    token_endpoint: tokenEndpoint,
    client_id: clientId,
    audience: import.meta.env.VITE_BUNDLEGRAPH_OIDC_AUDIENCE?.trim(),
    scope: import.meta.env.VITE_BUNDLEGRAPH_OIDC_SCOPE?.trim() || 'openid profile email',
    redirect_uri: import.meta.env.VITE_BUNDLEGRAPH_OIDC_REDIRECT_URI?.trim(),
  } : null;
})();

export function configureOidc(config: BrowserOidcConfig | null): void { oidcConfig = config; }
export function isOidcConfigured(): boolean { return Boolean(oidcConfig); }

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
  const config = oidcConfig;
  if (!config) throw new Error('OIDC is not configured');
  const verifier = randomValue(48);
  const state = randomValue();
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(OIDC_STATE_KEY, state);
  const redirectUri = config.redirect_uri || `${window.location.origin}/`;
  const parameters: Record<string, string> = {
    response_type: 'code', client_id: config.client_id, redirect_uri: redirectUri, scope: config.scope || 'openid profile email', state,
    code_challenge: base64Url(new Uint8Array(digest)), code_challenge_method: 'S256',
  };
  if (config.audience) parameters.audience = config.audience;
  const url = new URL(config.authorization_endpoint);
  url.search = new URLSearchParams(parameters).toString();
  window.location.assign(url);
}

export async function completeSignIn(): Promise<boolean> {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  if (!code) return false;
  const state = params.get('state');
  const expectedState = sessionStorage.getItem(OIDC_STATE_KEY);
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  const config = oidcConfig;
  if (!config || !state || state !== expectedState || !verifier) {
    clearSession();
    throw new Error('OIDC callback validation failed');
  }
  const redirectUri = config.redirect_uri || `${window.location.origin}/`;
  const tokenParameters: Record<string, string> = { grant_type: 'authorization_code', code, client_id: config.client_id, redirect_uri: redirectUri, code_verifier: verifier };
  if (config.audience) tokenParameters.audience = config.audience;
  const response = await fetch(config.token_endpoint, {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(tokenParameters),
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
