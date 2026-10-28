const observedAt = "2026-10-22T15:00:00Z";

export const fixtureEvidence = {
  "fixture:harbor-duo-inputs": { source: "Curated fixture catalog", sourceType: "fixture", observedAt, freshness: "fresh", conflict: "none", excerpt: "Harbor Duo exposes two simultaneously usable microphone inputs." },
  "fixture:xlr-connector-match": { source: "Curated fixture catalog", sourceType: "fixture", observedAt, freshness: "fresh", conflict: "none", excerpt: "Aurora microphones and Harbor Duo microphone inputs use XLR." },
  "fixture:harbor-duo-monitoring": { source: "Curated fixture catalog", sourceType: "fixture", observedAt, freshness: "fresh", conflict: "none", excerpt: "Two independent headphone outputs are listed." },
  "fixture:usb-c-data-cable": { source: "Curated fixture catalog", sourceType: "fixture", observedAt, freshness: "fresh", conflict: "none", excerpt: "USB-C data cable is included in the selected bundle." },
  "fixture:xlr-cable-quantity": { source: "Curated fixture catalog", sourceType: "fixture", observedAt, freshness: "fresh", conflict: "none", excerpt: "Two XLR cables are required for two microphones." },
  "fixture:missing-xlr-cables": { source: "Curated fixture catalog", sourceType: "fixture", observedAt, freshness: "fresh", conflict: "none", excerpt: "No XLR cable offer is present in this bundle.", missing: "Two XLR cable line items" },
  "fixture:duo-lite-phantom-power": { source: "Curated fixture catalog", sourceType: "fixture", observedAt: "2026-08-01T15:00:00Z", freshness: "stale", conflict: "unknown", excerpt: "The listing does not document phantom-power support.", missing: "Interface phantom-power evidence" }
};

const completeItems = [
  { category: "Microphones", name: "Aurora dynamic microphone", quantity: 2, unitPrice: 129, shipping: 0, tax: 0, lineTotal: 258, includedBecause: "Two participants require two microphones." },
  { category: "Audio interface", name: "Harbor Duo interface", quantity: 1, unitPrice: 229, shipping: 0, tax: 0, lineTotal: 229, includedBecause: "Provides the two evidenced microphone inputs." },
  { category: "Cables", name: "XLR cable", quantity: 2, unitPrice: 19, shipping: 0, tax: 0, lineTotal: 38, includedBecause: "Each XLR microphone needs its own signal cable." },
  { category: "Monitoring", name: "Closed-back headphones", quantity: 2, unitPrice: 74, shipping: 0, tax: 0, lineTotal: 148, includedBecause: "Supports the confirmed two-listener requirement." },
  { category: "Laptop connection", name: "USB-C data cable", quantity: 1, unitPrice: 5, shipping: 0, tax: 0, lineTotal: 5, includedBecause: "Connects the interface to the confirmed USB-C laptop port." }
];

const complete = {
  key: "studio-ready", name: "Studio-ready fixture bundle", version: 1, total: 678, budgetDifference: 222,
  status: "verified complete", classification: "verified_complete", shippingStatus: "included", taxStatus: "included",
  allocations: [{ merchant: "Synthetic merchant", amount: 678, components: "All five line items" }], items: completeItems,
  requirementStatus: [
    { label: "2 microphones", status: "passed", detail: "Quantity 2 included", target: "mic-a" },
    { label: "2 simultaneous mic inputs", status: "passed", detail: "Harbor Duo provides 2", target: "interface" },
    { label: "Required XLR cables", status: "passed", detail: "Quantity 2 included", target: "cables" },
    { label: "USB-C laptop connection", status: "passed", detail: "Data cable included", target: "laptop" },
    { label: "Independent monitoring", status: "passed", detail: "2 headphone outputs evidenced", target: "headphones" }
  ],
  rationale: ["Satisfies every confirmed hard requirement in the fixture.", "Includes all required accessories and quantities.", "Has no unknown required compatibility finding."],
  tradeoffs: ["Uses the higher-cost two-input interface.", "Delivery feasibility remains unknown because the fixture has no delivery evidence."],
  ranking: "Rank 1: lowest supplied verified-complete total in this fixture response.",
  evidence: [
    { status: "Passed", text: "Interface has 2 simultaneously usable microphone inputs.", source: "fixture:harbor-duo-inputs" },
    { status: "Passed", text: "Both microphones use XLR and the interface exposes XLR microphone inputs.", source: "fixture:xlr-connector-match" },
    { status: "Passed", text: "2 independent headphone outputs are evidenced.", source: "fixture:harbor-duo-monitoring" }
  ],
  graphNodes: [
    { id: "mic-a", label: "Mic A", role: "Microphone", quantity: 1, finding: "XLR connector matches the interface microphone input.", evidence: "fixture:xlr-connector-match", status: "Passed" },
    { id: "mic-b", label: "Mic B", role: "Microphone", quantity: 1, finding: "XLR connector matches the interface microphone input.", evidence: "fixture:xlr-connector-match", status: "Passed" },
    { id: "interface", label: "Harbor Duo", role: "Audio interface", quantity: 1, finding: "Two simultaneously usable microphone inputs; independent monitoring supported.", evidence: "fixture:harbor-duo-inputs", status: "Passed" },
    { id: "laptop", label: "Laptop", role: "Host device", quantity: 1, finding: "USB-C connection is included in the fixture bundle.", evidence: "fixture:usb-c-data-cable", status: "Passed" },
    { id: "headphones", label: "Headphones", role: "Monitoring", quantity: 2, finding: "Two listeners are supported independently.", evidence: "fixture:harbor-duo-monitoring", status: "Passed" },
    { id: "cables", label: "XLR cables", role: "Required accessory", quantity: 2, finding: "Two cables cover two microphones.", evidence: "fixture:xlr-cable-quantity", status: "Passed" }
  ],
  graphEdges: [
    { id: "mic-a-interface", from: "mic-a", to: "interface", status: "Passed", finding: "Mic A connects to a compatible XLR interface input.", evidence: "fixture:xlr-connector-match" },
    { id: "mic-b-interface", from: "mic-b", to: "interface", status: "Passed", finding: "Mic B connects to a compatible XLR interface input.", evidence: "fixture:xlr-connector-match" },
    { id: "interface-laptop", from: "interface", to: "laptop", status: "Passed", finding: "A USB-C data connection is included.", evidence: "fixture:usb-c-data-cable" },
    { id: "interface-headphones", from: "interface", to: "headphones", status: "Passed", finding: "Independent monitoring is evidenced for two listeners.", evidence: "fixture:harbor-duo-monitoring" },
    { id: "cables-interface", from: "cables", to: "interface", status: "Passed", finding: "Two XLR cables satisfy the required cable quantity.", evidence: "fixture:xlr-cable-quantity" }
  ]
};

const incomplete = {
  key: "unknown", name: "Low-price incomplete fixture", version: 1, total: 529, budgetDifference: 371,
  status: "blocked: unknown", classification: "unknown", shippingStatus: "unknown", taxStatus: "unknown", allocations: [],
  items: [
    { category: "Microphones", name: "Aurora dynamic microphone", quantity: 2, unitPrice: 129, shipping: "unknown", tax: "unknown", lineTotal: 258 },
    { category: "Audio interface", name: "Harbor Duo Lite interface", quantity: 1, unitPrice: 199, shipping: "unknown", tax: "unknown", lineTotal: 199 },
    { category: "Monitoring", name: "Headphones", quantity: 2, unitPrice: 36, shipping: "unknown", tax: "unknown", lineTotal: 72 }
  ],
  requirementStatus: [
    { label: "2 microphones", status: "passed", detail: "Quantity 2 included" },
    { label: "Required XLR cables", status: "missing", detail: "No cable line item supplied" },
    { label: "Phantom-power evidence", status: "unknown", detail: "Required interface fact is absent" },
    { label: "All-in cost", status: "unknown", detail: "Shipping and tax are unknown" }
  ],
  rationale: ["Lower supplied subtotal than the complete fixture bundle."],
  tradeoffs: ["Missing both required XLR cables.", "Required interface evidence is unknown.", "Shipping and tax are unknown, so this is not an all-in price."],
  ranking: "Rejected: it is incomplete and cannot be ranked as a verified proposal.",
  evidence: [
    { status: "Missing", text: "Required XLR cable line items are absent.", source: "fixture:missing-xlr-cables" },
    { status: "Unknown", text: "Phantom-power evidence is missing for the selected interface.", source: "fixture:duo-lite-phantom-power" }
  ], graphNodes: [], graphEdges: []
};

export const fixture = {
  requirements: { useCase: "Two-person podcast", budget: 900, participants: "2", connectors: ["usb-c"], monitoring: "independent", deadline: "" },
  evidence: fixtureEvidence, bundles: [complete, incomplete],
  recovery: { removed: ["Harbor Duo interface"], added: ["Crescent Duo interface", "USB-C data cable"], retained: ["2 × Aurora dynamic microphone", "2 × XLR cable", "2 × closed-back headphones"], quantityChanges: ["USB-C data cable: 0 → 1"], costChange: "+$32", missing: "Delivery evidence for the replacement interface", requiresNewApproval: true }
};

export const replacementBundle = { ...structuredClone(complete), key: "crescent-replacement", name: "Crescent Duo replacement fixture", version: 2, total: 710, budgetDifference: 190, ranking: "Replan candidate: preserves confirmed requirements after the original interface became unavailable.", allocations: [{ merchant: "Synthetic merchant", amount: 710, components: "All five revised line items" }], items: completeItems.map((item) => item.category === "Audio interface" ? { ...item, name: "Crescent Duo interface", unitPrice: 261, lineTotal: 261 } : item) };

export function fixtureProposals(requirements) {
  const matches = requirements.useCase === fixture.requirements.useCase && requirements.budget === fixture.requirements.budget && requirements.participants === fixture.requirements.participants && requirements.monitoring === fixture.requirements.monitoring && requirements.connectors.length === 1 && requirements.connectors[0] === "usb-c";
  return matches ? structuredClone(fixture.bundles) : [];
}
