import { candidateCatalog } from "./fixtures.js";
import { $, escapeHtml, money, statusClass } from "./utils.js";

function matches(candidate, filters) {
  return (filters.category === "all" || candidate.category === filters.category) && (filters.availability === "all" || candidate.availability === filters.availability) && (filters.evidence === "all" || candidate.evidence === filters.evidence) && (!filters.maximumPrice || candidate.price <= Number(filters.maximumPrice));
}

export const filterCandidates = (candidates, filters) => candidates.filter((candidate) => matches(candidate, filters));

export function renderCandidates(state) {
  const source = state.candidates || candidateCatalog, visible = filterCandidates(source, state.candidateFilters);
  $("#candidate-results").innerHTML = visible.length ? visible.map((candidate) => `<article class="candidate-card"><div><span class="tag ${statusClass(candidate.availability === "available" ? "passed" : "unknown")}">${escapeHtml(candidate.availability)}</span><span class="tag ${statusClass(candidate.evidence === "complete" ? "passed" : "unknown")}">${escapeHtml(candidate.evidence)} evidence</span><span class="tag">${escapeHtml(candidate.origin || state.candidateMode)}</span></div><h4>${escapeHtml(candidate.name)}</h4><p>${escapeHtml(candidate.variant)} · ${candidate.price === null ? "Price unknown" : money(candidate.price)}</p><dl class="compact-kv"><dt>Merchant</dt><dd>${escapeHtml(candidate.merchant)}</dd><dt>Observed</dt><dd>${escapeHtml(candidate.observedAt)}</dd><dt>Known facts</dt><dd>${candidate.facts.length ? candidate.facts.map(escapeHtml).join("; ") : "No normalized compatibility facts"}</dd></dl><button class="button secondary" data-shortlist="${candidate.id}" aria-pressed="${state.candidateShortlist.includes(candidate.id)}">${state.candidateShortlist.includes(candidate.id) ? "Remove from draft shortlist" : "Add to draft shortlist"}</button></article>`).join("") : '<div class="empty-state"><h4>No candidates match</h4><p>Broaden the filters or try another discovery query.</p></div>';
  $("#candidate-count").textContent = `${visible.length} ${escapeHtml(state.candidateMode)} candidates shown · ${state.candidateShortlist.length} shortlisted`;
  $("#candidate-results").querySelectorAll("[data-shortlist]").forEach((button) => button.addEventListener("click", () => { const id = button.dataset.shortlist; state.candidateShortlist = state.candidateShortlist.includes(id) ? state.candidateShortlist.filter((item) => item !== id) : [...state.candidateShortlist, id]; renderCandidates(state); }));
}

export function bindCandidateFilters(getState) {
  const form = $("#candidate-filters");
  form.addEventListener("input", () => { const values = new FormData(form), state = getState(); state.candidateFilters = { category: values.get("category"), availability: values.get("availability"), evidence: values.get("evidence"), maximumPrice: values.get("maximumPrice") }; renderCandidates(state); });
  $("#clear-candidate-filters").addEventListener("click", () => { const state = getState(); form.reset(); state.candidateFilters = { category: "all", availability: "all", evidence: "all", maximumPrice: "" }; renderCandidates(state); });
}
