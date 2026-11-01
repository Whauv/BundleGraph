import pytest

from bundlegraph_app.config import frontend_origins


def test_frontend_origins_are_explicit_normalized_and_deduplicated() -> None:
    assert frontend_origins({"BUNDLEGRAPH_FRONTEND_ORIGINS": "http://127.0.0.1:5173/, https://bundle.example, http://127.0.0.1:5173"}) == ("http://127.0.0.1:5173", "https://bundle.example")


@pytest.mark.parametrize("value", ["*", "file:///tmp/frontend", "javascript:alert(1)", "https://bundle.example/path", "https://user:secret@bundle.example"])
def test_frontend_origins_reject_unsafe_values(value: str) -> None:
    with pytest.raises(RuntimeError):
        frontend_origins({"BUNDLEGRAPH_FRONTEND_ORIGINS": value})
