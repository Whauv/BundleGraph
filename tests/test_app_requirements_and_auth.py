import hashlib
from datetime import UTC, datetime

import pytest

from bundlegraph.models import ListeningRequirement, ProductCategory
from bundlegraph.models import ConfirmedRequirements
from bundlegraph.selection import BundleSelectionRequest, select_bundles
from bundlegraph_app.auth import ConfiguredBearerAuthenticationProvider, Identity, InMemoryResourceOwnershipRepository, OidcIntrospectionAuthenticationProvider, OidcJwtAuthenticationProvider
from bundlegraph_app.config import application_settings
from bundlegraph_app.requirements import InMemoryRequirementDraftRepository, StaleDraftError, build_guided_draft, new_draft_record
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


def test_draft_compare_and_swap_rejects_stale_edit_and_preserves_created_at() -> None:
    repository = InMemoryRequirementDraftRepository()
    first_draft = build_guided_draft(request_reference="req-cas", use_case="Two-person podcast", participants=2, budget_minor=90_000, currency="USD", laptop_connectors=("usb-c",), monitoring="independent")
    first = new_draft_record("user-1", 1, first_draft, (), now=datetime(2026, 1, 1, tzinfo=UTC))
    repository.save(first, expected_version=None)
    second = new_draft_record("user-1", 2, first_draft, (), now=datetime(2026, 1, 2, tzinfo=UTC), created_at=first.created_at)
    repository.save(second, expected_version=1)
    with pytest.raises(StaleDraftError):
        repository.save(second, expected_version=1)
    stored = repository.get("req-cas")
    assert stored is not None
    assert stored.version == 2
    assert stored.created_at == first.created_at


def test_confirmation_snapshot_blocks_stale_review_version() -> None:
    repository = InMemoryRequirementDraftRepository()
    draft = build_guided_draft(request_reference="req-confirm-cas", use_case="Two-person podcast", participants=2, budget_minor=90_000, currency="USD", laptop_connectors=("usb-c",), monitoring="independent")
    repository.save(new_draft_record("user-1", 1, draft, ()), expected_version=None)
    repository.save(new_draft_record("user-1", 2, draft, ()), expected_version=1)
    with pytest.raises(StaleDraftError):
        repository.confirm_current("req-confirm-cas", "user-1", 1, lambda _record: None)


def test_configured_bearer_authentication_uses_only_the_token_hash() -> None:
    token = "a-high-entropy-test-token"
    digest = hashlib.sha256(token.encode()).hexdigest()
    identity = Identity(subject="user-1", roles=frozenset())
    provider = ConfiguredBearerAuthenticationProvider({digest: identity})

    assert provider.authenticate(f"Bearer {token}") == identity
    assert provider.authenticate("Bearer wrong") is None
    assert provider.authenticate(None) is None


def test_oidc_introspection_requires_active_unexpired_expected_audience() -> None:
    calls = []
    def transport(request, timeout):
        calls.append((request, timeout))
        return {"active": True, "sub": "user-oidc", "exp": 4_102_444_800, "aud": ["bundlegraph"], "scope": "plans:read plans:approve"}

    provider = OidcIntrospectionAuthenticationProvider(
        "https://identity.example/oauth/introspect", "bundlegraph-client", "server-secret",
        expected_audience="bundlegraph", transport=transport,
    )
    identity = provider.authenticate("Bearer short-lived-token")

    assert identity == Identity(subject="user-oidc", roles=frozenset({"plans:read", "plans:approve"}))
    assert len(calls) == 1
    assert b"short-lived-token" in calls[0][0].data


def test_oidc_introspection_fails_closed_for_inactive_or_wrong_audience() -> None:
    inactive = OidcIntrospectionAuthenticationProvider("https://identity.example/introspect", "id", "secret", transport=lambda _request, _timeout: {"active": False})
    wrong_audience = OidcIntrospectionAuthenticationProvider("https://identity.example/introspect", "id", "secret", expected_audience="bundlegraph", transport=lambda _request, _timeout: {"active": True, "sub": "user", "exp": 4_102_444_800, "aud": "other"})

    assert inactive.authenticate("Bearer token") is None
    assert wrong_audience.authenticate("Bearer token") is None


def test_oidc_jwt_requires_issuer_audience_expiry_and_collects_permissions() -> None:
    provider = OidcJwtAuthenticationProvider(
        "https://bundlegraph-demo.us.auth0.com",
        "https://bundlegraph-api",
        decoder=lambda _token: {
            "iss": "https://bundlegraph-demo.us.auth0.com/",
            "aud": ["https://bundlegraph-api"],
            "sub": "auth0|demo-user",
            "exp": 4_102_444_800,
            "scope": "openid profile",
            "permissions": ["payments:execute"],
        },
    )

    assert provider.authenticate("Bearer signed.jwt.token") == Identity(
        subject="auth0|demo-user",
        roles=frozenset({"openid", "profile", "payments:execute"}),
    )


def test_oidc_jwt_fails_closed_for_wrong_claims_or_decoder_failure() -> None:
    wrong_audience = OidcJwtAuthenticationProvider(
        "https://bundlegraph-demo.us.auth0.com/", "https://bundlegraph-api",
        decoder=lambda _token: {"iss": "https://bundlegraph-demo.us.auth0.com/", "aud": "other", "sub": "user", "exp": 4_102_444_800},
    )
    invalid_signature = OidcJwtAuthenticationProvider(
        "https://bundlegraph-demo.us.auth0.com/", "https://bundlegraph-api",
        decoder=lambda _token: (_ for _ in ()).throw(ValueError("invalid signature")),
    )

    assert wrong_audience.authenticate("Bearer signed.jwt.token") is None
    assert invalid_signature.authenticate("Bearer signed.jwt.token") is None


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

    oidc = application_settings({"DATABASE_URL": "postgresql://example", "BUNDLEGRAPH_OIDC_INTROSPECTION_URL": "https://identity.example/introspect", "BUNDLEGRAPH_OIDC_CLIENT_ID": "client", "BUNDLEGRAPH_OIDC_CLIENT_SECRET": "secret"})
    assert oidc.oidc_client_id == "client"

    jwt = application_settings({"DATABASE_URL": "postgresql://example", "BUNDLEGRAPH_OIDC_ISSUER": "https://tenant.auth0.com/", "BUNDLEGRAPH_OIDC_AUDIENCE": "https://bundlegraph-api", "BUNDLEGRAPH_OIDC_BROWSER_CLIENT_ID": "public-client"})
    assert jwt.oidc_issuer == "https://tenant.auth0.com/"

    with pytest.raises(RuntimeError, match="all required"):
        application_settings({"DATABASE_URL": "postgresql://example", "BUNDLEGRAPH_OIDC_CLIENT_ID": "client"})

    with pytest.raises(RuntimeError, match="issuer, audience, and browser client ID"):
        application_settings({"DATABASE_URL": "postgresql://example", "BUNDLEGRAPH_OIDC_ISSUER": "https://tenant.auth0.com/"})


def test_local_demo_catalog_completes_the_real_selection_path() -> None:
    draft = build_guided_draft(request_reference="req-e2e", use_case="Two-person podcast", participants=2, budget_minor=90_000, currency="USD", laptop_connectors=("usb-c",), monitoring="independent")
    confirmed = ConfirmedRequirements(**draft.model_dump(), confirmation_reference="conf-e2e")

    result = select_bundles(BundleSelectionRequest(requirements=confirmed, catalog=local_demo_catalog()))

    assert result.proposals
