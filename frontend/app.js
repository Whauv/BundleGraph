import { fixture, fixtureProposals, replacementBundle } from "./modules/fixtures.js";
import { configureAccessToken, confirmRequirementDraft, createAuthoritativePlan, getBackendReadiness, getPlanEvidence, getRuntimeConfig, requestBundlePlans, saveGuidedRequirementDraft, submitAuthoritativeApproval } from "./modules/api-client.js";
import { canVisit, invalidateFrom, resetState, screens, store } from "./modules/state.js";
import { renderComparison } from "./modules/render-comparison.js";
import { bindCandidateFilters, renderCandidates } from "./modules/render-candidates.js";
import { $, escapeHtml, money, monitoringText, statusClass } from "./modules/utils.js";

const requestedApiBase = new URLSearchParams(location.search).get("apiBase");
function allowedApiBase(value) { if (!value) return null; try { const target = new URL(value, location.origin); const localHosts = new Set(["127.0.0.1", "localhost", "::1"]); return target.origin === location.origin || (localHosts.has(target.hostname) && localHosts.has(location.hostname)) ? target.origin : null; } catch { return null; } }
let apiBase = allowedApiBase(requestedApiBase);
const state = () => store.value;
const planningBackendReady = () => Boolean(state().backendReadiness?.checks?.persistence && state().backendReadiness?.checks?.authentication && state().backendReadiness?.checks?.catalog !== false);

function showStatus(message, kind = "success") { const element = $("#app-status"); element.textContent = message; element.className = `status-message ${kind}`; element.hidden = false; }
function clearStatus() { $("#app-status").hidden = true; }

function syncForm() {
  const form = $("#request-form"), requirements = state().requirements;
  form.elements.useCase.value = requirements.useCase; form.elements.budget.value = requirements.budget; form.elements.participants.value = requirements.participants; form.elements.deadline.value = requirements.deadline;
  form.querySelectorAll("[data-connector]").forEach((input) => { input.checked = requirements.connectors.includes(input.value); });
  form.querySelectorAll("[data-use-case]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.useCase === requirements.useCase)));
  form.querySelectorAll("[data-budget]").forEach((button) => button.setAttribute("aria-pressed", String(Number(button.dataset.budget) === Number(requirements.budget))));
  form.querySelectorAll("[data-monitoring]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.monitoring === requirements.monitoring)));
}

function renderGuides() {
  $("#use-case-suggestions").innerHTML = ["Two-person podcast", "Remote interview", "Voice-over recording"].map((value) => `<button class="choice" type="button" data-use-case="${escapeHtml(value)}">${escapeHtml(value)}</button>`).join("");
  $("#budget-presets").innerHTML = [500, 750, 900, 1200].map((value) => `<button class="choice" type="button" data-budget="${value}">${money(value)}</button>`).join("");
  $("#monitoring-options").innerHTML = [["independent", "Independent headphones"], ["shared", "Shared listening"], ["unknown", "I’m not sure yet"]].map(([value, label]) => `<button class="choice" type="button" data-monitoring="${value}">${label}</button>`).join("");
  $("#connector-options").innerHTML = [["usb-c", "USB-C", "Small rounded oval"], ["usb-a", "USB-A", "Larger rectangular port"], ["headphone-jack", "3.5 mm", "Circular headphone port"], ["unknown", "I’m not sure", "Keep the fact unknown"]].map(([value, label, hint]) => `<label class="choice connector-choice"><input type="checkbox" data-connector value="${value}"><span><strong>${label}</strong><small>${hint}</small></span></label>`).join("");
  $("#use-case-suggestions").addEventListener("click", (event) => updateChoice(event, "useCase", "useCase"));
  $("#budget-presets").addEventListener("click", (event) => updateChoice(event, "budget", "budget", Number));
  $("#monitoring-options").addEventListener("click", (event) => updateChoice(event, "monitoring", "monitoring"));
  $("#connector-options").addEventListener("change", () => { state().requirements.connectors = [...$("#connector-options").querySelectorAll("input:checked")].map((input) => input.value); markRequestChanged(); });
  syncForm();
}

function updateChoice(event, dataName, field, convert = (value) => value) { const button = event.target.closest("button"); if (!button) return; state().requirements[field] = convert(button.dataset[dataName]); markRequestChanged(); syncForm(); }
function markRequestChanged() { const reference = $("#request-form")?.elements?.confirmationReference; if (reference) reference.value = ""; if (invalidateFrom("request")) showStatus("Requirements changed. Review them again before selecting a proposal."); }

function renderJourney() {
  const labels = { request: "Request", review: "Review", compare: "Compare", approval: "Approve", recovery: "Recovery" };
  $("#journey").innerHTML = screens.map((screen, index) => `<button class="${state().current === screen ? "active" : ""}" data-screen="${screen}" ${state().current === screen ? 'aria-current="step"' : ""} ${canVisit(screen) ? "" : "disabled"}>${index + 1}. ${labels[screen]}</button>`).join("");
  $("#journey").querySelectorAll("button").forEach((button) => button.addEventListener("click", () => go(button.dataset.screen)));
}

function go(screen) {
  if (!canVisit(screen)) { showStatus("Complete the previous step before opening this screen.", "error"); return; }
  state().current = screen; screens.forEach((name) => { $(`#screen-${name}`).hidden = name !== screen; }); renderJourney();
  ({ request: syncForm, review: renderReview, compare: () => { renderCandidates(state()); renderComparison(state(), { back: () => go("request"), approve: () => { state().maxScreen = Math.max(state().maxScreen, 3); go("approval"); } }); }, approval: renderApproval, recovery: renderRecovery })[screen]?.();
  const heading = $(`#screen-${screen} h2`); heading?.setAttribute("tabindex", "-1"); heading?.focus({ preventScroll: true }); window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderReview() {
  const requirements = state().requirements, source = state().source === "backend" ? "Authoritative backend response" : "Curated fixture preview";
  const rows = [["Use case", requirements.useCase, "useCase"], ["Budget", money(requirements.budget), "budget"], ["Participants", requirements.participants === "unknown" ? "Not confirmed" : requirements.participants, "participants"], ["Laptop connectors", requirements.connectors.length ? requirements.connectors.join(", ") : "Not confirmed", "connectors"], ["Listening", monitoringText(requirements.monitoring), "monitoring"], ["Deadline", requirements.deadline || "Not provided — delivery feasibility remains unknown", "deadline"], ["Plan source", source, null]];
  const retry = state().error ? `<div class="form-error"><p>${escapeHtml(state().error)}</p><button class="button secondary" id="retry-generation">Retry backend generation</button></div>` : "";
  $("#requirements-review").innerHTML = `<p>These are draft constraints until the authoritative backend records confirmation. Fixture mode supports exactly the labeled two-person USB-C sample.</p><dl class="kv">${rows.map(([key, value, field]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)} ${field ? `<button class="text-button" data-edit="${field}">Edit</button>` : ""}</dd>`).join("")}</dl>${retry}`;
  $("#retry-generation")?.addEventListener("click", generateAndCompare); $("#requirements-review").querySelectorAll("[data-edit]").forEach((button) => button.addEventListener("click", () => { const field = button.dataset.edit; go("request"); requestAnimationFrame(() => (field === "connectors" ? $("#connector-options input") : field === "monitoring" ? $("#monitoring-options button") : $(`[name="${field}"]`))?.focus()); }));
}

function renderApproval() {
  const bundle = state().selected; if (!bundle) { go("compare"); return; }
  const plan = state().authoritativePlan, version = plan?.versions?.find((item) => item.version === plan.current_version);
  const sourceAllocations = version?.merchant_allocations?.map((item) => ({ merchant: item.merchant_reference, amount: item.amount?.amount_minor / 100, components: item.offer_ids?.join(", ") })) || bundle.allocations || [];
  const allocations = sourceAllocations.length ? `<ul>${sourceAllocations.map((allocation) => `<li>${escapeHtml(allocation.merchant)} — ${money(allocation.amount)} (${escapeHtml(allocation.components)})</li>`).join("")}</ul>` : "No merchant allocation was supplied.";
  $("#approval-summary").innerHTML = `<span class="badge fixture">${state().source === "backend" ? plan ? "Authoritative stored plan" : "Backend proposal — not yet persisted" : "Fixture preview — simulated approval only"}</span><h3>${escapeHtml(bundle.name)}</h3><dl class="kv">${plan ? `<dt>Plan ID</dt><dd>${escapeHtml(plan.plan_id)}</dd>` : ""}<dt>Plan version</dt><dd>${escapeHtml(version?.version ?? bundle.version)}</dd><dt>${plan ? "Persisted total" : "Supplied total"}</dt><dd>${money(version?.total?.amount_minor !== undefined ? version.total.amount_minor / 100 : bundle.total)}</dd><dt>Shipping / tax</dt><dd>${escapeHtml(bundle.shippingStatus)} / ${escapeHtml(bundle.taxStatus)}</dd><dt>Compatibility</dt><dd><span class="tag ${statusClass(bundle.status)}">${escapeHtml(bundle.status)}</span></dd><dt>Merchant allocations</dt><dd>${allocations}</dd><dt>Approval boundary</dt><dd>${state().source === "backend" ? plan ? "Submitting will call Member 2's authoritative approval route for this exact stored version." : "Create the stored plan before submitting approval." : "This records a local simulation only. It sends no approval or payment."}</dd>${state().authoritativeApproval ? `<dt>Approval status</dt><dd>${escapeHtml(state().authoritativeApproval.status)} · ${escapeHtml(state().authoritativeApproval.approval_id)}</dd>` : ""}</dl><h4>Confirmed checks for this supplied proposal</h4><ul class="status-checklist">${(bundle.requirementStatus || []).map((item) => `<li><span class="status-dot ${statusClass(item.status)}" aria-hidden="true"></span><span><strong>${escapeHtml(item.label)}</strong> — ${escapeHtml(item.detail)}</span></li>`).join("")}</ul>`;
  const backendReady = planningBackendReady();
  $("#authoritative-approval-fields").hidden = state().source !== "backend" || !plan; $("#approve-plan").textContent = state().source === "backend" ? backendReady ? plan ? "Submit authoritative approval" : "Create authoritative plan" : "Backend is not ready for authoritative writes" : "Simulate fixture approval"; $("#approval-checkbox").checked = false; $("#approval-checkbox").disabled = state().source === "backend" && !backendReady; $("#approve-plan").disabled = true;
}

function renderRecovery() {
  $("#execution-status").innerHTML = state().approved ? `<h3>Execution status</h3><p><span class="tag ok">${state().source === "backend" ? "Awaiting authoritative execution" : "Fixture approval simulated"}</span></p><p>${state().failed ? "A simulated availability failure requires revised-plan review." : "No external payment has occurred."}</p>` : '<h3>Execution status</h3><p class="muted">Review a plan preview first.</p>';
  const schedule = state().failed ? ["Revised plan review", "Arrival timing remains unknown", "Assembly after arrival", "Audio test"] : ["Plan review", "Arrival timing remains unknown", "Assembly after arrival", "Audio test"]; $("#schedule").innerHTML = schedule.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  $("#simulate-failure").disabled = state().source === "backend"; $("#simulate-failure").textContent = state().source === "backend" ? "Await schema-validated replan proposal" : "Simulate unavailable interface";
  if (state().source === "backend" && !state().failed) { $("#recovery-result").innerHTML = '<p class="notice">The current API can apply an already-structured replacement proposal, but it does not expose a route that generates one. The browser will not invent a replan payload.</p>'; return; }
  if (!state().failed) return;
  $("#recovery-result").innerHTML = `<h4>Structured fixture recovery</h4><div class="recovery-grid">${[["Removed", fixture.recovery.removed], ["Added", fixture.recovery.added], ["Retained", fixture.recovery.retained], ["Quantity changes", fixture.recovery.quantityChanges]].map(([label, items]) => `<div><strong>${label}</strong><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>`).join("")}</div><p><strong>Cost difference:</strong> ${fixture.recovery.costChange}. <strong>Missing information:</strong> ${escapeHtml(fixture.recovery.missing)}. <strong>New approval required:</strong> ${fixture.recovery.requiresNewApproval ? "Yes" : "No"}.</p><button class="button" id="review-replacement">Review revised fixture plan</button>`;
  $("#review-replacement").addEventListener("click", () => { Object.assign(state(), { proposals: [structuredClone(replacementBundle)], selected: null, inspected: null, approved: false, maxScreen: 2 }); go("compare"); });
}

async function generateAndCompare() {
  state().error = null; $("#confirm-requirements").disabled = true; $("#confirm-requirements").setAttribute("aria-busy", "true"); showStatus("Generating bundle proposals…");
  configureAccessToken($("#request-form").elements.accessToken.value);
  let reference = $("#request-form").elements.confirmationReference.value.trim();
  try {
    if (apiBase) {
      if (!reference) {
        const requestReference = `req_${crypto.randomUUID()}`;
        const values = state().requirements;
        const deadline = values.deadline ? new Date(`${values.deadline}T23:59:59`).toISOString() : null;
        const draft = await saveGuidedRequirementDraft(apiBase, { request_reference: requestReference, use_case: values.useCase || null, participants: values.participants === "unknown" ? null : Number(values.participants), budget_minor: Number.isFinite(values.budget) ? Math.round(values.budget * 100) : null, currency: "USD", laptop_connectors: values.connectors, monitoring: values.monitoring, deadline });
        if (!draft.can_confirm) throw new Error(`More information is required: ${(draft.clarification_questions || []).join(" ")}`);
        const confirmation = await confirmRequirementDraft(apiBase, requestReference, draft.version);
        reference = confirmation.confirmation_reference;
        $("#request-form").elements.confirmationReference.value = reference;
      }
      const result = await requestBundlePlans(apiBase, reference); state().proposals = result.proposals; state().evidence = result.evidence; state().source = "backend"; if (!result.proposals.length) throw new Error("The backend did not supply a proposal."); showStatus("Draft confirmed and proposals generated by the authoritative backend.");
    }
    else { state().source = "fixture"; state().evidence = structuredClone(fixture.evidence); state().proposals = fixtureProposals(state().requirements); if (!state().proposals.length) throw new Error("Fixture mode supports exactly the two-person, $900, USB-C, independent-monitoring sample. Reload the sample or use a backend confirmation reference."); showStatus("Showing the labeled curated fixture response."); }
    Object.assign(state(), { selected: state().proposals.find((proposal) => proposal.classification === "verified_complete") || null, inspected: null, authoritativePlan: null, authoritativeApproval: null, maxScreen: Math.max(state().maxScreen, 2) }); go("compare");
  } catch (error) { Object.assign(state(), { proposals: [], selected: null, inspected: null, error: error.message, maxScreen: Math.max(state().maxScreen, 1) }); renderReview(); showStatus(error.message, "error"); }
  finally { $("#confirm-requirements").disabled = false; $("#confirm-requirements").removeAttribute("aria-busy"); }
}

$("#request-form").addEventListener("input", () => { configureAccessToken($("#request-form").elements.accessToken.value); const values = new FormData($("#request-form")); const next = { useCase: values.get("useCase"), budget: Number(values.get("budget")), participants: values.get("participants"), connectors: [...$("#connector-options").querySelectorAll("input:checked")].map((input) => input.value), monitoring: state().requirements.monitoring, deadline: values.get("deadline") || "" }; if (JSON.stringify(next) !== JSON.stringify(state().requirements)) { state().requirements = next; markRequestChanged(); } });
$("#request-form").addEventListener("submit", (event) => { event.preventDefault(); const error = $("#request-error"); if (!state().requirements.useCase.trim() || !Number.isFinite(state().requirements.budget) || state().requirements.budget <= 0) { error.textContent = "Enter a use case and a positive maximum budget."; error.hidden = false; return; } error.hidden = true; state().maxScreen = Math.max(state().maxScreen, 1); go("review"); });
$("#sample-request").addEventListener("click", () => { state().requirements = structuredClone(fixture.requirements); state().source = "fixture"; state().error = null; markRequestChanged(); syncForm(); clearStatus(); });
$("#confirm-requirements").addEventListener("click", generateAndCompare); $("#approval-checkbox").addEventListener("change", (event) => { $("#approve-plan").disabled = !event.currentTarget.checked || (state().source === "backend" && !planningBackendReady()); });
$("#approve-plan").addEventListener("click", handleApprovalAction);
$("#simulate-failure").addEventListener("click", () => { state().failed = true; $("#notification").hidden = false; $("#notification").textContent = "Simulated notification: the plan changed and needs a new review. No external notification was sent."; renderRecovery(); });
$("#reset").addEventListener("click", () => { resetState(); $("#request-form").reset(); $("#candidate-filters").reset(); $("#notification").hidden = true; $("#recovery-result").innerHTML = ""; $("#request-error").hidden = true; clearStatus(); syncForm(); initializeBackendMode(); go("request"); });
document.querySelectorAll(".back").forEach((button) => button.addEventListener("click", () => go(button.dataset.target)));

async function handleApprovalAction() {
  if (state().source !== "backend") { state().approved = true; state().maxScreen = Math.max(state().maxScreen, 4); showStatus("Fixture approval simulated locally. No approval or payment was sent."); go("recovery"); return; }
  if (!planningBackendReady()) { showStatus("The backend is not ready for authenticated authoritative writes.", "error"); return; }
  const reference = $("#request-form").elements.confirmationReference.value.trim();
  if (!apiBase || !reference) { showStatus("A configured backend and confirmation reference are required.", "error"); return; }
  $("#approve-plan").disabled = true; $("#approve-plan").setAttribute("aria-busy", "true");
  try {
    if (!state().authoritativePlan) {
      const response = await createAuthoritativePlan(apiBase, reference, state().selected.key);
      if (!response.plan) throw new Error(response.reason_codes?.join(", ") || "The backend did not create a plan.");
      state().authoritativePlan = response.plan;
      try { const evidenceResponse = await getPlanEvidence(apiBase, response.plan.plan_id); state().persistedEvidenceCount = evidenceResponse.evidence?.length || 0; } catch { state().persistedEvidenceCount = null; }
      showStatus("Authoritative plan created. Review its stored version and submit approval separately."); renderApproval(); return;
    }
    const response = await submitAuthoritativeApproval(apiBase, state().authoritativePlan); if (!response.approval) throw new Error("The backend did not return an approval record.");
    state().authoritativeApproval = response.approval; state().approved = response.approval.status === "granted"; state().maxScreen = Math.max(state().maxScreen, 4); showStatus(`Authoritative approval returned status: ${response.approval.status}.`); go("recovery");
  } catch (error) { showStatus(error.message, "error"); }
  finally { $("#approve-plan").removeAttribute("aria-busy"); if (state().current === "approval") $("#approve-plan").disabled = !$("#approval-checkbox").checked; }
}

async function initializeBackendMode() {
  const badge = $("#mode-badge");
  if (!apiBase) {
    try { const runtime = await getRuntimeConfig(location.origin); if (runtime.runtime === "application" || runtime.runtime === "production") apiBase = location.origin; } catch { /* A standalone static server has no backend runtime endpoint. */ }
  }
  if (!apiBase) { badge.textContent = "Curated fixture demo"; return; }
  badge.textContent = "Checking backend readiness";
  try { state().backendReadiness = await getBackendReadiness(apiBase); const planningReady = planningBackendReady(); const fullyReady = state().backendReadiness.status === "ready"; badge.textContent = fullyReady ? "Backend connected · ready" : planningReady ? "Planning backend ready · payments disabled" : "Backend connected · not ready"; badge.className = `badge ${planningReady ? "backend" : "not-ready"}`; }
  catch { badge.textContent = "Backend unavailable · fixture fallback"; badge.className = "badge not-ready"; state().backendReadiness = { status: "unavailable" }; }
}

renderGuides(); bindCandidateFilters(state); renderJourney(); initializeBackendMode();
