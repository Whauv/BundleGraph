# BundleGraph frontend

This directory contains the single BundleGraph frontend: a React 19, TypeScript,
and Vite application. The earlier dependency-free prototype has been retired so
there is one entry point, one state model, one API adapter, and one build.

## Run locally

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. With no environment configuration the application
runs in visibly labeled synthetic fixture mode. Fixture approval, execution, and
recovery records are demonstrations only; they do not call a provider.

To connect the optional, non-authoritative demo API in `bundlegraph_api`, copy
`frontend/.env.example` to `frontend/.env.local` and set:

```dotenv
VITE_BUNDLEGRAPH_DEMO_API_BASE=http://127.0.0.1:8000
```

Then start that API separately:

```powershell
python -m uvicorn bundlegraph_api.app:app --port 8000
```

If a configured API cannot be reached, the frontend reports an error. It does
not silently display fixture success as if it came from the API.

## Checks and production build

```powershell
npm --prefix frontend run check
npm --prefix frontend run build
npm --prefix frontend run preview
```

The production artifact is written to `frontend/dist/`. Deploy that directory
behind the same origin as the authoritative API when the Member 2 confirmation,
plan, evidence, and approval bridge is connected.

## Boundaries

- The browser never decides compatibility, authoritative confirmation, payment
  recipients, or payment outcomes.
- Synthetic fixtures remain labeled and are not substituted after a configured
  backend failure.
- Unknown costs, evidence, and delivery feasibility remain unknown.
- Browser variables beginning with `VITE_` are public configuration, never
  credentials.
- PayPal, provider, database, and authentication secrets remain server-side.

See [INTEGRATION.md](INTEGRATION.md) for the API and release boundary.
