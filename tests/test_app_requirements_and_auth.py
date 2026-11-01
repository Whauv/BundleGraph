import hashlib

import pytest

from bundlegraph.models import ListeningRequirement, ProductCategory
from bundlegraph.models import ConfirmedRequirements
from bundlegraph.selection import BundleSelectionRequest, select_bundles
from bundlegraph_app.auth import ConfiguredBearerAuthenticationProvider, Identity, InMemoryResourceOwnershipRepository
from bundlegraph_app.config import application_settings
from bundlegraph_app.requirements import build_guided_draft
from bundlegraph_app.manage import local_demo_catalog


def test_guided_answers_create_an_unconfirmed_complete_draft() -> None:
    draft = build_guided_draft(request_reference="req-1", use_case="Two-person podcast", participants=2, budget_minor=90_000, currency="USD", laptop_connectors=("usb-c",), monitoring="independent")

    assert draft.missing_information == ()
    assert draft.listening_requirement is ListeningRequirement.INDEPENDENT_HEADPHONES
    assert {(item.category, item.quantity) for item in draft.required_quantities} == {
        (ProductCategory.MICROPHONE, 2),
        (ProductCategory.AUDIO_INTERFACE, 1),
        (ProductCategory.XLR_CABLE, 2),
        (ProductCategory.HEADPHONES, 2),
    }
    assert not hasattr(draft, "confirmation_reference")


def test_guided_answers_preserve_unknowns_for_clarification() -> None:
    draft = build_guided_draft(request_reference="req-2", use_case=None, participants=None, budget_minor=None, currency=None, laptop_connectors=("unknown",), monitoring="unknown")

    assert set(draft.missing_information) == {"budget", "laptop connector", "monitoring requirement", "participant count", "use case"}
    assert draft.required_quantities == ()


def test_configured_bearer_authentication_uses_only_the_token_hash() -> None:
    token = "a-high-entropy-test-token"
    digest = hashlib.sha256(token.encode()).hexdigest()
    identity = Identity(subject="user-1", roles=frozenset())
    provider = ConfiguredBearerAuthenticationProvider({digest: identity})

    assert provider.authenticate(f"Bearer {token}") == identity
    assert provider.authenticate("Bearer wrong") is None
    assert provider.authenticate(None) is None


def test_ownership_cannot_be_reassigned() -> None:
    owners = InMemoryResourceOwnershipRepository()
    owners.claim("plan", "plan-1", "user-1")

    with pytest.raises(ValueError, match="different owner"):
        owners.claim("plan", "plan-1", "user-2")


def test_application_configuration_is_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        application_settings({})

    digest = "a" * 64
    settings = application_settings({"DATABASE_URL": "postgresql://example", "BUNDLEGRAPH_AUTH_IDENTITIES": f'{{"{digest}":{{"subject":"user-1","roles":[]}}}}'})
    assert settings.auth_identities[digest]["subject"] == "user-1"


def test_local_demo_catalog_completes_the_real_selection_path() -> None:
    draft = build_guided_draft(request_reference="req-e2e", use_case="Two-person podcast", participants=2, budget_minor=90_000, currency="USD", laptop_connectors=("usb-c",), monitoring="independent")
    confirmed = ConfirmedRequirements(**draft.model_dump(), confirmation_reference="conf-e2e")

    result = select_bundles(BundleSelectionRequest(requirements=confirmed, catalog=local_demo_catalog()))

    assert result.proposals
