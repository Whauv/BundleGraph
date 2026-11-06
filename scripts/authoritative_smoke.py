"""Disposable same-origin application smoke test for CI.

Uses only the local synthetic catalog, local test identity, and documented HTTP
contracts. It never calls a provider, merchant, or payment endpoint.
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("BUNDLEGRAPH_SMOKE_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
TOKEN = os.environ.get("BUNDLEGRAPH_SMOKE_TOKEN", "local-dev-token")


def call(method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"{BASE_URL}{path}", data=body, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "X-Correlation-ID": "ci-authoritative-smoke"},
    )
    with urlopen(request, timeout=15) as response:  # noqa: S310 - loopback/CI URL is explicit operator configuration
        value = json.loads(response.read(2_000_000))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} returned a non-object response")
    return value


def main() -> None:
    reference = "ci-smoke-request"
    saved = call("POST", "/requirement-drafts/guided", {
        "request_reference": reference, "use_case": "two-person podcast", "participants": 2,
        "budget_minor": 90_000, "currency": "USD", "laptop_connectors": ["usb-c"],
        "monitoring": "independent", "deadline": None,
    })
    if saved.get("can_confirm") is not True or not isinstance(saved.get("version"), int):
        raise RuntimeError("guided draft did not become confirmable")
    confirmed = call("POST", f"/requirement-drafts/{reference}/confirm", {"expected_version": saved["version"]})
    confirmation_reference = confirmed.get("confirmation_reference")
    if not isinstance(confirmation_reference, str):
        raise RuntimeError("confirmation reference missing")
    generated = call("POST", "/bundle-plans/generate", {"schema_version": "1.0", "correlation_id": "ci-generate", "confirmation_reference": confirmation_reference})
    result = generated.get("result")
    proposals = result.get("proposals") if isinstance(result, dict) else None
    if not isinstance(proposals, list) or not proposals or not isinstance(proposals[0], dict):
        raise RuntimeError("authoritative synthetic catalog returned no candidate")
    proposal_key = proposals[0].get("proposal_key")
    if not isinstance(proposal_key, str):
        raise RuntimeError("candidate proposal key missing")
    created = call("POST", "/plans", {"schema_version": "1.0", "correlation_id": "ci-persist", "confirmation_reference": confirmation_reference, "proposal_key": proposal_key})
    plan = created.get("plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("plan_id"), str):
        raise RuntimeError("persisted plan missing")
    versions = plan.get("versions")
    if not isinstance(versions, list) or not versions or not isinstance(versions[-1], dict):
        raise RuntimeError("persisted plan version missing")
    head = versions[-1]
    evidence = call("GET", f"/bundle-plans/{plan['plan_id']}/evidence?correlation_id=ci-evidence")
    if not isinstance(evidence.get("evidence"), list):
        raise RuntimeError("stored-plan evidence did not resolve")
    approval = call("POST", "/approvals", {"plan_id": plan["plan_id"], "plan_version": head["version"], "plan_fingerprint": head["fingerprint"], "permitted_total": head["total"]})
    if not isinstance(approval.get("approval"), dict):
        raise RuntimeError("exact-version approval missing")
    runtime = call("GET", "/runtime-config")
    capabilities = runtime.get("capabilities")
    if not isinstance(capabilities, dict) or capabilities.get("payments") is not False:
        raise RuntimeError("application-mode smoke expected payment execution to remain unavailable")
    print(json.dumps({"result": "ok", "runtime": runtime.get("runtime"), "proposal_count": len(proposals), "evidence_count": len(evidence["evidence"]), "payments_enabled": False}))


if __name__ == "__main__":
    main()
