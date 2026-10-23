"""Synthetic, offline-only catalog fixture. It is never provider or retailer data."""

from .models import Evidence, EvidenceStatus, Money, Product, ProductCategory, ProductFact


def _fixture_fact(claim: str, value: object) -> ProductFact:
    return ProductFact(
        value=value,
        evidence=Evidence(
            claim=claim,
            source_url="fixture://bundlegraph/catalog-v1",
            status=EvidenceStatus.FIXTURE,
            source_kind="synthetic_fixture",
        ),
    )


def _product(product_id: str, name: str, category: ProductCategory, cents: int, **facts: object) -> Product:
    return Product(
        product_id=product_id,
        name=name,
        category=category,
        price=Money(amount_minor=cents, currency="USD"),
        source_kind="curated_fixture",
        is_fixture=True,
        facts={key: _fixture_fact(f"{name}: {key}", value) for key, value in facts.items()},
    )


CURATED_DEMO_CATALOG: tuple[Product, ...] = (
    _product("mic-alpha", "Demo Mic Alpha", ProductCategory.MICROPHONE, 7900, connector="xlr"),
    _product("mic-bravo", "Demo Mic Bravo", ProductCategory.MICROPHONE, 9900, connector="xlr"),
    _product("mic-charlie", "Demo Mic Charlie", ProductCategory.MICROPHONE, 11900, connector="xlr"),
    _product("mic-delta", "Demo Mic Delta", ProductCategory.MICROPHONE, 14900, connector="xlr"),
    _product("mic-echo", "Demo Mic Echo", ProductCategory.MICROPHONE, 18900, connector="xlr"),
    _product("interface-one", "Demo Interface One", ProductCategory.AUDIO_INTERFACE, 8900, microphone_inputs=1, laptop_connector="usb-c"),
    _product("interface-two", "Demo Interface Two", ProductCategory.AUDIO_INTERFACE, 15900, microphone_inputs=2, laptop_connector="usb-c", headphone_outputs=2),
    _product("interface-three", "Demo Interface Three", ProductCategory.AUDIO_INTERFACE, 21900, microphone_inputs=2, laptop_connector="usb-a", headphone_outputs=1),
    _product("interface-four", "Demo Interface Four", ProductCategory.AUDIO_INTERFACE, 27900, microphone_inputs=4, laptop_connector="usb-c", headphone_outputs=2),
    _product("interface-five", "Demo Interface Five", ProductCategory.AUDIO_INTERFACE, 32900, microphone_inputs=2, laptop_connector="usb-c", headphone_outputs=2),
    _product("headphones-alpha", "Demo Headphones Alpha", ProductCategory.HEADPHONES, 4900, connector="3.5mm"),
    _product("headphones-bravo", "Demo Headphones Bravo", ProductCategory.HEADPHONES, 6900, connector="3.5mm"),
    _product("headphones-charlie", "Demo Headphones Charlie", ProductCategory.HEADPHONES, 8900, connector="6.35mm"),
    _product("headphones-delta", "Demo Headphones Delta", ProductCategory.HEADPHONES, 10900, connector="3.5mm"),
    _product("splitter-alpha", "Demo Headphone Splitter Alpha", ProductCategory.HEADPHONE_SPLITTER, 1200, outputs=2),
    _product("splitter-bravo", "Demo Headphone Splitter Bravo", ProductCategory.HEADPHONE_SPLITTER, 1800, outputs=2),
    _product("splitter-charlie", "Demo Headphone Splitter Charlie", ProductCategory.HEADPHONE_SPLITTER, 2500, outputs=3),
    _product("xlr-alpha", "Demo XLR Cable Alpha", ProductCategory.XLR_CABLE, 1400, connector="xlr"),
    _product("xlr-bravo", "Demo XLR Cable Bravo", ProductCategory.XLR_CABLE, 1900, connector="xlr"),
    _product("xlr-charlie", "Demo XLR Cable Charlie", ProductCategory.XLR_CABLE, 2400, connector="xlr"),
    _product("xlr-delta", "Demo XLR Cable Delta", ProductCategory.XLR_CABLE, 2900, connector="xlr"),
    _product("usb-adapter-alpha", "Demo USB Adapter Alpha", ProductCategory.USB_ADAPTER, 1600, from_connector="usb-a", to_connector="usb-c"),
    _product("usb-adapter-bravo", "Demo USB Adapter Bravo", ProductCategory.USB_ADAPTER, 2100, from_connector="usb-c", to_connector="usb-a"),
)
