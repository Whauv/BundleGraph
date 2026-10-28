"""Tests for the bundlegraph_api FastAPI bridge."""

from fastapi.testclient import TestClient

from bundlegraph_api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["catalog_products"] == 24
    assert data["catalog_offers"] == 15


def test_presets():
    response = client.get("/api/presets")
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) == 3
    assert presets[0]["id"] == "preset-standard-podcast"
    assert presets[1]["id"] == "preset-trap-one-input"


def test_catalog():
    response = client.get("/api/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["total_products"] == 24
    assert data["total_offers"] == 15


def test_interpret_exact_fixture():
    response = client.post("/api/requirements/interpret", json={"message": "two-person-usb-c"})
    assert response.status_code == 200
    data = response.json()
    assert data["draft"]["use_case"] == "two-person podcast"
    assert data["draft"]["participants"] == 2


def test_interpret_heuristic():
    response = client.post("/api/requirements/interpret", json={"message": "I need a podcast setup for 2 people with $550 budget on usb-c"})
    assert response.status_code == 200
    data = response.json()
    assert data["draft"]["participants"] == 2
    assert data["draft"]["budget"]["amount_minor"] == 55_000
    assert data["draft"]["laptop_connectors"][0]["connector"] == "usb-c"


def test_confirm_requirements():
    response = client.post("/api/requirements/confirm", json={
        "use_case": "two-person podcast",
        "participants": 2,
        "budget_minor": 60_000,
        "currency": "USD",
        "laptop_connector": "usb-c",
        "listening_requirement": "independent_headphones"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["participants"] == 2
    assert data["budget"]["amount_minor"] == 60_000


def test_generate_bundle_plans():
    # 1. Confirm
    conf_res = client.post("/api/requirements/confirm", json={
        "use_case": "two-person podcast",
        "participants": 2,
        "budget_minor": 60_000,
        "currency": "USD",
        "laptop_connector": "usb-c",
        "listening_requirement": "independent_headphones"
    })
    confirmed_req = conf_res.json()

    # 2. Generate
    gen_res = client.post("/api/bundle-plans/generate", json={"requirements": confirmed_req})
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["status"] == "ok"
    assert len(gen_data["result"]["proposals"]) >= 1

    proposal = gen_data["result"]["proposals"][0]
    assert proposal["cost_breakdown"]["total_status"] == "verified_all_in"
    assert len(proposal["line_items"]) >= 3


def test_generate_trap_one_input_incompatible():
    # Attempting 2 mics with a tight budget that would force 1-input or exceed budget
    conf_res = client.post("/api/requirements/confirm", json={
        "use_case": "two-person podcast",
        "participants": 2,
        "budget_minor": 10_000,
        "currency": "USD",
        "laptop_connector": "usb-c",
        "listening_requirement": "independent_headphones"
    })
    confirmed_req = conf_res.json()

    gen_res = client.post("/api/bundle-plans/generate", json={"requirements": confirmed_req})
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["status"] == "no_feasible_bundle"


def test_approvals_and_executions():
    appr_res = client.post("/api/approvals/create", json={
        "plan_id": "plan-demo-1",
        "plan_version": "1.0",
        "amount_minor": 48_950,
        "currency": "USD"
    })
    assert appr_res.status_code == 200
    appr = appr_res.json()
    assert appr["status"] == "APPROVED"

    # Test success execution
    exec_res = client.post("/api/executions/simulate", json={
        "approval_id": appr["approval_id"],
        "plan_id": "plan-demo-1",
        "plan_version": "1.0",
        "amount_minor": 48_950,
        "currency": "USD"
    })
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["execution_status"] == "COMPLETED"
    assert "PAYPAL-TXN-" in exec_data["transaction_id"]

    # Test failure injection
    fail_res = client.post("/api/executions/simulate", json={
        "approval_id": appr["approval_id"],
        "plan_id": "plan-demo-1",
        "plan_version": "1.0",
        "amount_minor": 48_950,
        "currency": "USD",
        "inject_failure_offer_id": "offer-mic-alpha"
    })
    assert fail_res.status_code == 200
    fail_data = fail_res.json()
    assert fail_data["execution_status"] == "FAILED_MERCHANT_STOCK_OUTAGE"
    assert fail_data["approval_invalidated"] is True


def test_replan_recovery():
    # 1. Generate valid plan
    conf_res = client.post("/api/requirements/confirm", json={
        "use_case": "two-person podcast",
        "participants": 2,
        "budget_minor": 60_000,
        "currency": "USD",
        "laptop_connector": "usb-c",
        "listening_requirement": "independent_headphones"
    })
    confirmed_req = conf_res.json()
    gen_res = client.post("/api/bundle-plans/generate", json={"requirements": confirmed_req})
    proposal = gen_res.json()["result"]["proposals"][0]

    # 2. Replan with failed interface
    replan_res = client.post("/api/bundle-plans/replan", json={
        "original_proposal": proposal,
        "requirements": confirmed_req,
        "failed_offer_ids": ["offer-interface-two"],
        "locked_offer_ids": ["offer-mic-alpha", "offer-headphones-alpha"],
        "plan_id": "plan-demo-1",
        "plan_version": "1.0",
    })
    assert replan_res.status_code == 200
    replan_data = replan_res.json()
    assert "replacements" in replan_data
    assert replan_data["requires_new_approval"] is True


def test_zapier_and_demo_reset():
    notif_res = client.post("/api/notifications/zapier", json={
        "event_type": "test_notification",
        "payload": {"status": "ok", "test": True}
    })
    assert notif_res.status_code == 200

    log_res = client.get("/api/notifications/zapier/log")
    assert log_res.status_code == 200
    log = log_res.json()
    assert len(log) >= 1

    reset_res = client.post("/api/demo/reset")
    assert reset_res.status_code == 200

    log_res_after = client.get("/api/notifications/zapier/log")
    assert len(log_res_after.json()) == 0
