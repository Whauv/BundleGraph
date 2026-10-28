const amount = (money) => typeof money?.amount_minor === "number" ? money.amount_minor / 100 : null;

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = "";
    try { const payload = await response.json(); detail = payload.detail || payload.reason_codes?.join(", ") || ""; } catch { /* response had no JSON body */ }
    throw new Error(`Backend request failed with ${response.status}${detail ? `: ${detail}` : ""}.`);
  }
  return response.json();
}

export function normalizeBackendResponse(response) {
  const proposals = response?.result?.proposals;
  if (!Array.isArray(proposals)) return { proposals: [], evidence: {} };
  const normalized = proposals.map((proposal, index) => {
    const graph = proposal.compatibility_report || {};
    const findings = graph.findings || [];
    const nodeDetail = (node) => findings.find((finding) => (finding.affected_product_ids || []).some((id) => node.node_id.includes(id))) || {};
    return {
      key: proposal.proposal_key || `backend-${index}`, name: proposal.display_name || `Backend proposal ${index + 1}`, version: proposal.version || "Not supplied",
      total: amount(proposal.cost_breakdown?.all_in_total), budgetDifference: amount(proposal.cost_breakdown?.budget_difference),
      status: graph.classification === "verified_complete" ? "verified complete" : graph.classification || "not verified", classification: graph.classification || "unknown",
      shippingStatus: proposal.cost_breakdown?.shipping?.status || "unknown", taxStatus: proposal.cost_breakdown?.tax?.status || "unknown", allocations: (proposal.merchant_allocations || []).map((allocation) => ({ merchant: allocation.merchant_reference || allocation.merchant || "Not supplied", amount: amount(allocation.amount) ?? allocation.amount, components: allocation.components || allocation.offer_ids?.join(", ") || "Not supplied" })),
      items: (proposal.line_items || []).map((item) => ({ category: item.category || "Component", name: item.product_id, quantity: item.quantity, unitPrice: amount(item.unit_price), shipping: item.shipping?.status || "unknown", tax: item.tax?.status || "unknown", lineTotal: amount(item.line_total), includedBecause: item.included_because })),
      requirementStatus: proposal.requirement_status || findings.map((finding) => ({ label: finding.reason_code || finding.rule_id, status: finding.status, detail: finding.explanation, target: finding.affected_product_ids?.[0] })),
      rationale: proposal.ranking_rationale?.reasons || [], tradeoffs: proposal.assumptions || [], ranking: proposal.ranking_rationale?.summary || "No ranking rationale supplied.",
      evidence: findings.map((finding) => ({ status: finding.status, text: finding.explanation, source: (finding.evidence_ids || []).join(", ") || "No evidence reference" })),
      graphNodes: (graph.nodes || []).map((node) => { const detail = nodeDetail(node); return { id: node.node_id, label: node.label, role: node.node_type, quantity: node.data?.quantity ?? "Not stated", finding: detail.explanation || "No finding directly references this node.", evidence: (detail.evidence_ids || node.evidence_ids || []).join(", ") || "No evidence reference", status: detail.status || "Unknown" }; }),
      graphEdges: (graph.edges || []).map((edge) => { const detail = findings.find((finding) => (finding.evidence_ids || []).some((id) => (edge.evidence_ids || []).includes(id))) || {}; return { id: `${edge.source_id}-${edge.target_id}-${edge.relationship}`, from: edge.source_id, to: edge.target_id, status: detail.status || "Unknown", finding: detail.explanation || edge.relationship, evidence: (detail.evidence_ids || edge.evidence_ids || []).join(", ") || "No evidence reference" }; })
    };
  });
  const evidence = Object.fromEntries((response?.result?.evidence || []).map((item) => [item.evidence_id, { source: item.source_url || item.fixture_reference || "Not supplied", sourceType: item.source_type || "unknown", observedAt: item.observed_at || "Not supplied", freshness: item.freshness_status || "unknown", conflict: item.conflict_status || "unknown", excerpt: item.excerpt || "Not supplied", missing: item.missing_fact }]));
  return { proposals: normalized, evidence };
}

export async function requestBundlePlans(apiBase, confirmationReference) {
  const payload = await requestJson(`${apiBase.replace(/\/$/, "")}/bundle-plans/generate`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ schema_version: "1.0", correlation_id: crypto.randomUUID(), confirmation_reference: confirmationReference }) });
  return normalizeBackendResponse(payload);
}

export const getBackendReadiness = (apiBase) => requestJson(`${apiBase.replace(/\/$/, "")}/readyz`);

export async function createAuthoritativePlan(apiBase, confirmationReference, proposalKey) {
  return requestJson(`${apiBase.replace(/\/$/, "")}/plans`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ schema_version: "1.0", correlation_id: crypto.randomUUID(), confirmation_reference: confirmationReference, proposal_key: proposalKey }) });
}

export async function submitAuthoritativeApproval(apiBase, plan, actorReference) {
  const version = plan.versions.find((item) => item.version === plan.current_version);
  if (!version) throw new Error("The authoritative plan response has no current version.");
  return requestJson(`${apiBase.replace(/\/$/, "")}/approvals`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ plan_id: plan.plan_id, plan_version: version.version, plan_fingerprint: version.fingerprint, actor_reference: actorReference, permitted_total: version.total }) });
}

export const getPlanEvidence = (apiBase, planId) => requestJson(`${apiBase.replace(/\/$/, "")}/bundle-plans/${encodeURIComponent(planId)}/evidence?correlation_id=${encodeURIComponent(crypto.randomUUID())}`);

export async function applyAuthoritativeReplan(apiBase, planId, confirmationReference, replacementProposal) {
  if (!replacementProposal) throw new Error("A schema-validated replacement proposal is required.");
  return requestJson(`${apiBase.replace(/\/$/, "")}/plans/${encodeURIComponent(planId)}/replans`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ schema_version: "1.0", correlation_id: crypto.randomUUID(), confirmation_reference: confirmationReference, replacement: replacementProposal }) });
}
