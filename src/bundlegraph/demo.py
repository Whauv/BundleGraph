"""One-command, fixture-only BundleGraph demonstration."""

from __future__ import annotations

import json

from .catalog import OFFLINE_FIXTURE_CATALOG
from .compatibility_graph import SelectedProduct, evaluate_compatibility
from .models import ConfirmedRequirements, LaptopConnectorFact, ListeningRequirement, Money, QuantityRequirement


def run_demo() -> dict[str, object]:
    requirements = ConfirmedRequirements(
        request_reference="demo-request", confirmation_reference="demo-confirmation-reference",
        use_case="two-person podcast", participants=2, budget=Money(amount_minor=100_000, currency="USD"),
        required_quantities=(QuantityRequirement(category="microphone", quantity=2),),
        laptop_connectors=(LaptopConnectorFact(connector="usb-c"),),
        listening_requirement=ListeningRequirement.INDEPENDENT_HEADPHONES,
    )
    graph = evaluate_compatibility(requirements, (
        SelectedProduct(product_id="mic-alpha", quantity=2), SelectedProduct(product_id="interface-two", quantity=1),
        SelectedProduct(product_id="xlr-alpha", quantity=2), SelectedProduct(product_id="headphones-alpha", quantity=2),
    ), OFFLINE_FIXTURE_CATALOG)
    return {
        "schema_version": "member1-demo-v1", "origin": "fixture",
        "catalog": {"products": len(OFFLINE_FIXTURE_CATALOG.products), "offers": len(OFFLINE_FIXTURE_CATALOG.offers), "evidence": len(OFFLINE_FIXTURE_CATALOG.evidence)},
        "compatibility_graph": graph.model_dump(mode="json"),
        "notice": "This is synthetic offline fixture data, not live catalog or purchase output.",
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
