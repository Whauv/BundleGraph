# Frontend integration and release contract

The React application is the repository's only frontend. It has two explicit
runtime modes and never infers a stronger state from a successful request.

| Mode | Selection | Behavior |
| --- | --- | --- |
| Synthetic fixture | `VITE_BUNDLEGRAPH_DEMO_API_BASE` is unset | Uses versioned offline examples and labels every approval/execution result as simulated |
| Connected demo API | `VITE_BUNDLEGRAPH_DEMO_API_BASE` is set | Calls only the `/api/*` demonstration bridge and fails visibly on network or server errors |

The connected demo API is not Member 2's authoritative persistence/payment
boundary. It exists for the hackathon walkthrough. Production integration must
use `bundlegraph_app` and preserve these rules:

1. Submit a confirmation reference, not browser-authored confirmed requirements.
2. Persist the selected proposal before approval.
3. Retrieve evidence for the stored plan.
4. Approve the exact stored version, fingerprint, total, and merchant allocation.
5. Apply a schema-validated replan as a new version and require new approval.
6. Keep authentication, PayPal, provider, and merchant credentials server-side.

`VITE_BUNDLEGRAPH_DEMO_API_BASE` is a public browser setting, not a secret. For
production, prefer a same-origin reverse proxy and remove the demo API setting.

## Release checks

```powershell
npm --prefix frontend ci
npm --prefix frontend run check
```

An opt-in smoke test can check Member 2 liveness/readiness independently:

```powershell
$env:BUNDLEGRAPH_FRONTEND_API_BASE="http://127.0.0.1:8080"
npm --prefix frontend run check:live
```

No frontend command requires provider credentials for fixture mode or normal
tests.
