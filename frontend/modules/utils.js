export const $ = (selector) => document.querySelector(selector);
export const money = (value) => typeof value === "number" ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value) : "Unknown";
export const escapeHtml = (text) => String(text ?? "").replace(/[&<>\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[character]));
export const statusClass = (status) => { const value = String(status || "").toLowerCase(); if (/incompatible|missing|failed/.test(value)) return "bad"; if (/unknown|blocked|not verified/.test(value)) return "unknown"; return /passed|verified complete|compatible/.test(value) ? "ok" : "unknown"; };
export const monitoringText = (value) => ({ independent: "Independent headphones for both people", shared: "Shared listening", unknown: "Not confirmed" })[value] || value;

export function evidenceInfo(reference, evidence) {
  return evidence[reference] || { source: "Backend reference", sourceType: "not supplied", observedAt: "Not supplied", freshness: "unknown", conflict: "unknown", excerpt: "The proposal returned an evidence identifier but no observation metadata in this response.", missing: "Evidence metadata" };
}

export function evidenceMarkup(reference, evidence) {
  const info = evidenceInfo(reference, evidence);
  return `<dl class="kv compact-kv"><dt>Reference</dt><dd>${escapeHtml(reference)}</dd><dt>Source</dt><dd>${escapeHtml(info.source)}</dd><dt>Source type</dt><dd>${escapeHtml(info.sourceType)}</dd><dt>Observed</dt><dd>${escapeHtml(info.observedAt)}</dd><dt>Freshness</dt><dd>${escapeHtml(info.freshness)}</dd><dt>Conflict</dt><dd>${escapeHtml(info.conflict)}</dd><dt>Excerpt</dt><dd>${escapeHtml(info.excerpt)}</dd>${info.missing ? `<dt>Missing fact</dt><dd>${escapeHtml(info.missing)}</dd>` : ""}</dl>`;
}
