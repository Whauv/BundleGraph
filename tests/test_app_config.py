import pytest

from bundlegraph_app.config import frontend_origins, production_settings


def test_frontend_origins_are_explicit_normalized_and_deduplicated() -> None:
    assert frontend_origins({"BUNDLEGRAPH_FRONTEND_ORIGINS": "http://127.0.0.1:5173/, https://bundle.example, http://127.0.0.1:5173"}) == ("http://127.0.0.1:5173", "https://bundle.example")


@pytest.mark.parametrize("value", ["*", "file:///tmp/frontend", "javascript:alert(1)", "https://bundle.example/path", "https://user:secret@bundle.example"])
def test_frontend_origins_reject_unsafe_values(value: str) -> None:
    with pytest.raises(RuntimeError):
        frontend_origins({"BUNDLEGRAPH_FRONTEND_ORIGINS": value})


def test_production_settings_require_webhook_id_and_recipients() -> None:
    with pytest.raises(RuntimeError, match="missing"):
        production_settings({"DATABASE_URL": "postgres://x", "PAYPAL_CLIENT_ID": "c", "PAYPAL_CLIENT_SECRET": "s", "PAYPAL_WEBHOOK_ID": "", "BUNDLEGRAPH_SANDBOX_RECIPIENTS": ""})


def test_production_settings_round_trip() -> None:
    settings = production_settings({
        "DATABASE_URL": "postgres://x",
        "PAYPAL_CLIENT_ID": "c",
        "PAYPAL_CLIENT_SECRET": "s",
        "PAYPAL_WEBHOOK_ID": "WH-abc",
        "BUNDLEGRAPH_SANDBOX_RECIPIENTS": "sandbox-a,sandbox-b",
    })
    assert settings.paypal_webhook_id == "WH-abc"
    assert settings.sandbox_recipients == frozenset({"sandbox-a", "sandbox-b"})
