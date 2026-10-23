# Phase 2 deterministic compatibility model

`evaluate_compatibility` accepts confirmed requirements, selected product quantities, and a validated catalog. It creates a JSON-serializable graph with product, required-capability, and evidence nodes; contribution and evidence edges; eight findings; and a final classification.

## Rules

1. Selected microphone quantity meets the confirmed microphone quantity.
2. One selected interface provides enough microphone inputs.
3. Each selected microphone connector matches the interface microphone-input connector.
4. A phantom-powered microphone requires usable evidence that the selected interface provides phantom power.
5. Each selected XLR microphone needs one selected XLR cable.
6. The selected interface connects directly to a confirmed laptop connector, or a selected directional adapter bridges the two.
7. Headphone monitoring supports the confirmed listening requirement. Independent monitoring requires enough outputs or a selected splitter; speaker monitoring remains unknown because no speaker model exists.
8. Any selected specification marked conflicting produces an unknown finding; a favorable value is never chosen silently.

All outcomes are deterministic and come only from the selected fixture/product data and confirmed requirements. `verified_complete` requires no incompatible or unknown finding. Preferences are not consulted by these rules and therefore cannot become hard constraints.

## Initial limits

- The model evaluates exactly one audio interface. Multiple-interface routing is unknown.
- Connector evaluation is exact string equality for the fixture values; it does not model impedance, gain, balanced wiring, TRRS/TRS, USB power delivery, or electrical safety.
- Cable evaluation covers only one XLR cable per XLR microphone. It does not model length, gender, signal routing, stock, price, or merchant delivery.
- Adapter direction is the fixture's declared `from_connector` to `to_connector`; no real-world plug/gender inference occurs.
- Headphone evaluation counts declared outputs/splitter capacity. It does not model amplifier power, impedance, splitter wiring, or speaker equipment.
