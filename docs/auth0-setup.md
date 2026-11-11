# Auth0 setup for the hosted hackathon demo

BundleGraph uses Auth0 Universal Login with Authorization Code + PKCE. Judges
click **Continue with Auth0** and use a prepared demo account. The access token
is a credential: it is kept in browser `sessionStorage`, sent only as a bearer
token to the same-origin API, and never displayed, logged, or committed.

## 1. Create the browser application

In the Auth0 dashboard, create a **Single Page Application** named
`BundleGraph Demo`. Configure these exact URLs:

- Allowed Callback URLs: `https://bundlegraph.onrender.com/`
- Allowed Logout URLs: `https://bundlegraph.onrender.com/`
- Allowed Web Origins: `https://bundlegraph.onrender.com`
- Allowed Origins (CORS): `https://bundlegraph.onrender.com`

Use Authorization Code with PKCE. Do not create or embed a browser client
secret. Record the public Client ID and tenant domain.

## 2. Create the API

Create an Auth0 API named `BundleGraph API`:

- Identifier/audience: choose one stable URI, for example
  `https://bundlegraph-api`
- Signing algorithm: `RS256`
- Permission: `payments:execute`
- Enable RBAC and **Add Permissions in the Access Token** for the demo API.

Authorize the SPA for this API according to the tenant's access policy. The
audience in Render must exactly match this API identifier.

## 3. Create the demo user

Create one database-connection user for the live demonstration. Keep its
password in the team's password manager or enter it before screen sharing. Do
not put demo credentials in GitHub, Render variables, screenshots, or the
submission document.

## 4. Configure Render

Add these values in the Render service's **Environment** page:

```dotenv
BUNDLEGRAPH_MODE=production
BUNDLEGRAPH_PUBLIC_BASE_URL=https://bundlegraph.onrender.com
BUNDLEGRAPH_FRONTEND_ORIGINS=https://bundlegraph.onrender.com
BUNDLEGRAPH_OIDC_ISSUER=https://YOUR_TENANT_REGION.auth0.com/
BUNDLEGRAPH_OIDC_BROWSER_CLIENT_ID=YOUR_PUBLIC_SPA_CLIENT_ID
BUNDLEGRAPH_OIDC_AUDIENCE=https://bundlegraph-api
BUNDLEGRAPH_OIDC_SCOPE=openid profile email payments:execute
```

Retain the existing PostgreSQL, Groq, PayPal Sandbox, webhook, merchant, and
catalog configuration. OIDC JWT validation does not use
`BUNDLEGRAPH_OIDC_CLIENT_SECRET` or the RFC 7662 introspection variables.

## 5. Deploy and verify

Deploy the latest Docker image, then verify:

1. `GET /healthz` returns `status: ok`.
2. `GET /readyz` returns `status: ready`.
3. `GET /runtime-config` reports `runtime: production` and public Auth0 values,
   but no secret.
4. The sign-in page shows **Continue with Auth0**, not a token field.
5. Auth0 redirects back to `https://bundlegraph.onrender.com/`.
6. An authenticated planning request succeeds.
7. A signed-out request returns 401.
8. The payment action is authorized only when the token contains
   `payments:execute`.

If Auth0 returns an opaque access token, confirm the authorization request uses
the exact API audience. BundleGraph expects a signed JWT access token for its
custom API.
