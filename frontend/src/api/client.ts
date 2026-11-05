import type {
  ApiFailure, ApprovalRecord, AuthoritativePlan, BundleProposal, ConfirmedRequirements, DraftRequirements,
  EvidenceRecord, ExecutionRecord, PresetScenario, ReplanResult, RequirementInterpretation,
} from '../types/bundlegraph';
import { OFFLINE_PRESETS, SAMPLE_CONFIRMED_REQ, SAMPLE_INTERPRETATION, SAMPLE_PROPOSAL, SAMPLE_REPLAN_RESULT } from '../fixtures/offlineData';
import { clearSession, getAccessToken } from '../auth/session';

const configuredRuntime = import.meta.env.VITE_BUNDLEGRAPH_RUNTIME?.trim();
const configuredBase = import.meta.env.VITE_BUNDLEGRAPH_API_BASE?.trim();
const API_BASE = configuredBase ? configuredBase.replace(/\/$/, '') : '';
const OBSERVABILITY_ENDPOINT = import.meta.env.VITE_BUNDLEGRAPH_OBSERVABILITY_ENDPOINT?.trim();
let fixtureGuidedDraft: DraftRequirements | null = null;

export type FrontendRuntimeMode = 'fixture' | 'authoritative';
export const frontendRuntime = {
  mode: (configuredRuntime === 'authoritative' ? 'authoritative' : 'fixture') as FrontendRuntimeMode,
  label: configuredRuntime === 'authoritative' ? 'Authoritative application API' : 'Synthetic offline fixtures',
  apiBase: configuredRuntime === 'authoritative' ? API_BASE : null,
};

export class ApiError extends Error implements ApiFailure {
  status: number;
  reason_code: string;
  correlation_id?: string;
  constructor(status: number, reasonCode: string, message: string, correlationId?: string) {
    super(message);
    this.status = status;
    this.reason_code = reasonCode;
    this.correlation_id = correlationId;
  }
}

function cloneFixture<T>(value: T): T { return structuredClone(value); }
function correlationId(): string { return `web-${crypto.randomUUID()}`; }

function reportFailure(error: ApiError, endpoint: string): void {
  if (!OBSERVABILITY_ENDPOINT) return;
  const payload = JSON.stringify({ event: 'api_failure', endpoint, status: error.status, reason_code: error.reason_code, correlation_id: error.correlation_id, occurred_at: new Date().toISOString() });
  navigator.sendBeacon?.(OBSERVABILITY_ENDPOINT, new Blob([payload], { type: 'application/json' }));
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const corr = correlationId();
  if (!token) throw new ApiError(401, 'AUTHENTICATION_REQUIRED', 'Sign in to continue.');
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, 'X-Correlation-ID': corr, ...options.headers } });
  } catch {
    const error = new ApiError(0, 'NETWORK_UNAVAILABLE', 'The BundleGraph service could not be reached.', corr);
    reportFailure(error, endpoint);
    throw error;
  }
  const responseCorrelation = response.headers.get('x-correlation-id') || corr;
  if (!response.ok) {
    if (response.status === 401) clearSession();
    let detail: unknown;
    try { detail = await response.json(); } catch { detail = await response.text(); }
    const nested = typeof detail === 'object' && detail !== null && 'detail' in detail ? (detail as { detail: unknown }).detail : detail;
    const reason = typeof nested === 'object' && nested !== null && 'reason_code' in nested
      ? String((nested as { reason_code: unknown }).reason_code)
      : response.status === 409 ? 'STALE_RESOURCE_VERSION' : `HTTP_${response.status}`;
    const missing = typeof nested === 'object' && nested !== null && 'missing_information' in nested && Array.isArray((nested as { missing_information: unknown }).missing_information)
      ? (nested as { missing_information: unknown[] }).missing_information.map(String)
      : [];
    const message = typeof nested === 'string' ? nested : missing.length ? `Please resolve: ${missing.join(', ')}.` : response.statusText || 'The request could not be completed.';
    const error = new ApiError(response.status, reason, message || response.statusText, responseCorrelation);
    reportFailure(error, endpoint);
    throw error;
  }
  return response.json() as Promise<T>;
}

function fixtureApproval(planId: string, amountMinor: number, currency: string): ApprovalRecord {
  return { approval_id: 'fixture-approval-v1', plan_id: planId, plan_version: '1', amount_minor: amountMinor, currency, status: 'SIMULATED_FIXTURE_APPROVAL', created_at: '2026-01-01T00:00:00Z', valid: true };
}

export const api = {
  async getPresets(): Promise<PresetScenario[]> { return cloneFixture(OFFLINE_PRESETS); },

  async interpretRequirements(message: string, requestReference = `req-${crypto.randomUUID()}`): Promise<RequirementInterpretation> {
    if (frontendRuntime.mode === 'fixture') return { ...cloneFixture(SAMPLE_INTERPRETATION), draft: { ...cloneFixture(SAMPLE_INTERPRETATION.draft), request_reference: requestReference, use_case: message.slice(0, 80) }, provider_mode: 'synthetic_fixture', version: 1, can_confirm: true };
    return request('/requirement-drafts/interpret', { method: 'POST', body: JSON.stringify({ message, request_reference: requestReference }) });
  },

  async saveGuidedDraft(params: { request_reference: string; use_case: string; participants: number; budget_minor: number; currency: string; laptop_connectors: string[]; monitoring: string; deadline?: string }): Promise<{ draft: RequirementInterpretation['draft']; version: number; clarification_questions: string[]; can_confirm: boolean }> {
    if (frontendRuntime.mode === 'fixture') {
      const listening = ({ independent: 'independent_headphones', shared: 'shared_headphones', none: 'no_monitoring' } as Record<string, string>)[params.monitoring] || null;
      const missing = [params.use_case !== 'two-person podcast' ? 'supported use case' : null, params.participants !== 2 ? 'supported participant topology' : null, params.budget_minor <= 0 ? 'budget' : null, params.laptop_connectors.includes('unknown') ? 'laptop connector' : null, !listening ? 'monitoring requirement' : null].filter((item): item is string => Boolean(item));
      fixtureGuidedDraft = {
        request_reference: params.request_reference, use_case: params.use_case, participants: params.participants,
        budget: { amount_minor: params.budget_minor, currency: params.currency },
        required_quantities: [{ category: 'microphone', quantity: params.participants }, { category: 'audio_interface', quantity: 1 }, { category: 'xlr_cable', quantity: params.participants }, { category: 'headphones', quantity: params.participants }],
        laptop_connectors: params.laptop_connectors.filter((item) => item !== 'unknown').map((connector) => ({ connector })),
        listening_requirement: listening, deadline: params.deadline || null, missing_information: missing,
      };
      return { draft: cloneFixture(fixtureGuidedDraft), version: 2, clarification_questions: missing.map((item) => `Please resolve ${item}.`), can_confirm: !missing.length };
    }
    return request('/requirement-drafts/guided', { method: 'POST', body: JSON.stringify(params) });
  },

  async confirmDraft(requestReference: string, expectedVersion: number): Promise<ConfirmedRequirements> {
    if (frontendRuntime.mode === 'fixture') {
      const draft = fixtureGuidedDraft;
      if (!draft || draft.request_reference !== requestReference || draft.missing_information.length || !draft.use_case || draft.participants === null || !draft.budget || !draft.listening_requirement) return cloneFixture(SAMPLE_CONFIRMED_REQ);
      return { request_reference: draft.request_reference, confirmation_reference: `fixture-confirmed-v${expectedVersion}`, use_case: draft.use_case, participants: draft.participants, budget: draft.budget, required_quantities: draft.required_quantities, laptop_connectors: draft.laptop_connectors, listening_requirement: draft.listening_requirement, deadline: draft.deadline || null };
    }
    const response = await request<{ confirmation_reference: string; requirements: ConfirmedRequirements }>(`/requirement-drafts/${encodeURIComponent(requestReference)}/confirm`, { method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }) });
    return response.requirements;
  },

  async generateBundlePlans(requirements: ConfirmedRequirements): Promise<{ status: string; reason_codes: string[]; result: { proposals: BundleProposal[]; search_status: string; evaluated_candidates?: number; infeasibility?: { reason_codes: string[] } | null } }> {
    if (frontendRuntime.mode === 'fixture') return { status: 'ok', reason_codes: [], result: { proposals: [cloneFixture(SAMPLE_PROPOSAL)], search_status: 'fixture_completed', evaluated_candidates: 1 } };
    return request('/bundle-plans/generate', { method: 'POST', body: JSON.stringify({ schema_version: '1.0', correlation_id: correlationId(), confirmation_reference: requirements.confirmation_reference }) });
  },

  async persistPlan(requirements: ConfirmedRequirements, proposalKey: string): Promise<AuthoritativePlan> {
    if (frontendRuntime.mode === 'fixture') {
      const total = SAMPLE_PROPOSAL.cost_breakdown.all_in_total || SAMPLE_PROPOSAL.cost_breakdown.merchandise_subtotal;
      return { plan_id: SAMPLE_PROPOSAL.proposal_key, status: 'awaiting_approval', current_version: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), versions: [{ plan_id: SAMPLE_PROPOSAL.proposal_key, version: 1, fingerprint: 'fixture-fingerprint-v1', created_at: new Date().toISOString(), confirmation_reference: requirements.confirmation_reference, correlation_id: 'fixture-correlation', line_items: [], total, merchant_allocations: [], payload: {} }] };
    }
    const response = await request<{ plan: AuthoritativePlan }>('/plans', { method: 'POST', body: JSON.stringify({ schema_version: '1.0', correlation_id: correlationId(), confirmation_reference: requirements.confirmation_reference, proposal_key: proposalKey }) });
    return response.plan;
  },

  async getPlanEvidence(planId: string): Promise<EvidenceRecord[]> {
    if (frontendRuntime.mode === 'fixture') return [];
    const response = await request<{ evidence: EvidenceRecord[] }>(`/bundle-plans/${encodeURIComponent(planId)}/evidence?correlation_id=${encodeURIComponent(correlationId())}`);
    return response.evidence;
  },

  async createApproval(plan: AuthoritativePlan): Promise<ApprovalRecord> {
    const head = plan.versions.find((version) => version.version === plan.current_version);
    if (!head) throw new ApiError(409, 'PLAN_VERSION_MISSING', 'The selected plan version is unavailable.');
    if (frontendRuntime.mode === 'fixture') return fixtureApproval(plan.plan_id, head.total.amount_minor, head.total.currency);
    const response = await request<{ approval: { approval_id: string; plan_id: string; plan_version: number; plan_fingerprint: string; status: string; granted_at?: string; permitted_total: { amount_minor: number; currency: string } } }>('/approvals', { method: 'POST', body: JSON.stringify({ plan_id: plan.plan_id, plan_version: head.version, plan_fingerprint: head.fingerprint, permitted_total: head.total }) });
    return { approval_id: response.approval.approval_id, plan_id: response.approval.plan_id, plan_version: String(response.approval.plan_version), plan_fingerprint: response.approval.plan_fingerprint, amount_minor: response.approval.permitted_total.amount_minor, currency: response.approval.permitted_total.currency, status: response.approval.status, created_at: response.approval.granted_at || new Date().toISOString(), valid: response.approval.status === 'granted' };
  },

  async replanBundle(plan: AuthoritativePlan, failedOfferId: string): Promise<ReplanResult> {
    if (frontendRuntime.mode === 'fixture') return cloneFixture(SAMPLE_REPLAN_RESULT);
    return request(`/plans/${encodeURIComponent(plan.plan_id)}/replan-proposals`, { method: 'POST', body: JSON.stringify({ expected_plan_version: plan.current_version, failed_offer_ids: [failedOfferId] }) });
  },

  async simulateExecution(params: { approval_id: string; plan_id: string; plan_version: string; amount_minor: number; currency: string; inject_failure_offer_id?: string }): Promise<ExecutionRecord> {
    if (frontendRuntime.mode !== 'fixture') throw new ApiError(409, 'PAYMENT_EXECUTION_NOT_ENABLED', 'Payment execution is not enabled in the application runtime.');
    return params.inject_failure_offer_id
      ? { execution_status: 'FAILED_MERCHANT_STOCK_OUTAGE', plan_id: params.plan_id, approval_id: params.approval_id, approval_invalidated: true, failed_offer_id: params.inject_failure_offer_id, message: `Synthetic stock outage for ${params.inject_failure_offer_id}. No transaction was attempted.`, replan_recommended: true }
      : { execution_status: 'COMPLETED', transaction_id: 'fixture-transaction-v1', plan_id: params.plan_id, amount_minor: params.amount_minor, currency: params.currency, settled_at: '2026-01-01T00:00:00Z', approval_id: params.approval_id, message: 'Synthetic fixture execution completed. No payment provider was called.' };
  },

  async resetDemo(): Promise<void> { fixtureGuidedDraft = null; },
};
