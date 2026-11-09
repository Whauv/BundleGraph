import type {
  ApiFailure, ApprovalRecord, AuthoritativePlan, BundleProposal, ConfirmedRequirements,
  EvidenceRecord, ExecutionRecord, PresetScenario, ReplanResult, RequirementInterpretation,
} from '../types/bundlegraph';
import { clearSession, getAccessToken } from '../auth/session';
import { createFixtureAdapter, FixtureContractError } from './fixtureAdapter';

const configuredRuntime = import.meta.env.VITE_BUNDLEGRAPH_RUNTIME?.trim();
const configuredBase = import.meta.env.VITE_BUNDLEGRAPH_API_BASE?.trim();
const API_BASE = configuredBase ? configuredBase.replace(/\/$/, '') : '';
const OBSERVABILITY_ENDPOINT = import.meta.env.VITE_BUNDLEGRAPH_OBSERVABILITY_ENDPOINT?.trim();
const configuredTimeout = Number(import.meta.env.VITE_BUNDLEGRAPH_REQUEST_TIMEOUT_MS || 15_000);
const DEFAULT_TIMEOUT_MS = Number.isFinite(configuredTimeout) && configuredTimeout >= 250 && configuredTimeout <= 60_000 ? configuredTimeout : 15_000;
const fixture = createFixtureAdapter();

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
    super(message); this.status = status; this.reason_code = reasonCode; this.correlation_id = correlationId;
  }
}

function correlationId(): string { return `web-${crypto.randomUUID()}`; }
function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null && !Array.isArray(value); }
function isString(value: unknown): value is string { return typeof value === 'string' && value.length > 0; }
function isInteger(value: unknown): value is number { return typeof value === 'number' && Number.isInteger(value); }

function reportFailure(error: ApiError, endpoint: string): void {
  if (!OBSERVABILITY_ENDPOINT) return;
  try {
    const payload = JSON.stringify({ event: 'api_failure', endpoint, status: error.status, reason_code: error.reason_code, correlation_id: error.correlation_id, occurred_at: new Date().toISOString() });
    navigator.sendBeacon?.(OBSERVABILITY_ENDPOINT, new Blob([payload], { type: 'application/json' }));
  } catch { /* Telemetry must never replace the original failure. */ }
}

function parseBody(text: string): unknown {
  if (!text.trim()) return null;
  try { return JSON.parse(text); } catch { return text; }
}

function safeMessage(value: unknown, status: number): string {
  if (typeof value === 'string') {
    const normalized = value.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    if (normalized && !value.includes('<html') && !value.includes('<!DOCTYPE')) return normalized.slice(0, 240);
  }
  if (status === 401) return 'Your session has ended. Sign in again to continue.';
  if (status === 403) return 'You do not have access to this operation.';
  if (status >= 500) return 'The BundleGraph service could not complete the request.';
  return 'The request could not be completed.';
}

function invalidResponse(corr: string, endpoint: string): never {
  const error = new ApiError(502, 'INVALID_API_RESPONSE', 'The server returned an invalid response. Reload before continuing.', corr);
  reportFailure(error, endpoint); throw error;
}

type RequestOptions = RequestInit & { timeoutMs?: number };

export async function requestJson(endpoint: string, options: RequestOptions = {}): Promise<unknown> {
  const token = getAccessToken();
  const corr = correlationId();
  if (!token) throw new ApiError(401, 'AUTHENTICATION_REQUIRED', 'Sign in to continue.');
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort('timeout'), options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  const abortFromCaller = () => controller.abort(options.signal?.reason || 'cancelled');
  options.signal?.addEventListener('abort', abortFromCaller, { once: true });
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, { ...options, signal: controller.signal, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, 'X-Correlation-ID': corr, ...options.headers } });
  } catch {
    const timedOut = controller.signal.aborted && !options.signal?.aborted;
    const error = new ApiError(0, timedOut ? 'REQUEST_TIMEOUT' : options.signal?.aborted ? 'REQUEST_CANCELLED' : 'NETWORK_UNAVAILABLE', timedOut ? 'The request timed out. It is safe to retry this read operation.' : options.signal?.aborted ? 'The obsolete request was cancelled.' : 'The BundleGraph service could not be reached.', corr);
    reportFailure(error, endpoint); throw error;
  } finally {
    window.clearTimeout(timeout); options.signal?.removeEventListener('abort', abortFromCaller);
  }
  const responseCorrelation = response.headers.get('x-correlation-id') || corr;
  const text = await response.text();
  const payload = parseBody(text);
  if (!response.ok) {
    if (response.status === 401) clearSession();
    const nested = isRecord(payload) && 'detail' in payload ? payload.detail : payload;
    const reason = isRecord(nested) && isString(nested.reason_code) ? nested.reason_code : response.status === 409 ? 'STALE_RESOURCE_VERSION' : `HTTP_${response.status}`;
    const missing = isRecord(nested) && Array.isArray(nested.missing_information) ? nested.missing_information.filter(isString) : [];
    const message = missing.length ? `Please resolve: ${missing.join(', ')}.` : safeMessage(isRecord(nested) && 'message' in nested ? nested.message : nested, response.status);
    const error = new ApiError(response.status, reason, message, responseCorrelation);
    reportFailure(error, endpoint); throw error;
  }
  if (payload === null) invalidResponse(responseCorrelation, endpoint);
  return payload;
}

function asInterpretation(value: unknown): RequirementInterpretation {
  if (!isRecord(value) || !isRecord(value.draft) || !isString(value.draft.request_reference) || !Array.isArray(value.missing_information) || !Array.isArray(value.clarification_questions) || !isString(value.provider_mode)) invalidResponse('', '/requirement-drafts/interpret');
  return value as unknown as RequirementInterpretation;
}

function asGuided(value: unknown): { draft: RequirementInterpretation['draft']; version: number; clarification_questions: string[]; can_confirm: boolean } {
  if (!isRecord(value) || !isRecord(value.draft) || !isString(value.draft.request_reference) || !isInteger(value.version) || !Array.isArray(value.clarification_questions) || typeof value.can_confirm !== 'boolean') invalidResponse('', '/requirement-drafts/guided');
  return value as unknown as { draft: RequirementInterpretation['draft']; version: number; clarification_questions: string[]; can_confirm: boolean };
}

function asConfirmed(value: unknown): ConfirmedRequirements {
  if (!isRecord(value) || !isString(value.confirmation_reference) || !isRecord(value.requirements) || !isString(value.requirements.confirmation_reference)) invalidResponse('', '/confirm');
  return value.requirements as unknown as ConfirmedRequirements;
}

function asPlan(value: unknown): AuthoritativePlan {
  if (!isRecord(value) || !isRecord(value.plan) || !isString(value.plan.plan_id) || !isInteger(value.plan.current_version) || !Array.isArray(value.plan.versions)) invalidResponse('', '/plans');
  return value.plan as unknown as AuthoritativePlan;
}

function asGeneration(value: unknown) {
  if (!isRecord(value) || !isString(value.status) || !Array.isArray(value.reason_codes) || !isRecord(value.result) || !Array.isArray(value.result.proposals) || !isString(value.result.search_status)) invalidResponse('', '/bundle-plans/generate');
  return value as unknown as { status: string; reason_codes: string[]; result: { proposals: BundleProposal[]; search_status: string; evaluated_candidates?: number; infeasibility?: { reason_codes: string[]; explanation?: string } | null } };
}

function translateFixture<T>(action: () => Promise<T>): Promise<T> {
  return action().catch((error) => {
    if (error instanceof FixtureContractError) throw new ApiError(error.status, error.reason_code, error.message, 'synthetic-fixture');
    throw error;
  });
}

export const api = {
  async getPresets(): Promise<PresetScenario[]> { return fixture.getPresets(); },
  async interpretRequirements(message: string, requestReference = `req-${crypto.randomUUID()}`, signal?: AbortSignal): Promise<RequirementInterpretation> {
    if (frontendRuntime.mode === 'fixture') return translateFixture(() => fixture.interpret(message, requestReference));
    return asInterpretation(await requestJson('/requirement-drafts/interpret', { method: 'POST', body: JSON.stringify({ message, request_reference: requestReference }), signal }));
  },
  async saveGuidedDraft(params: { request_reference: string; use_case: string | null; participants: number | null; budget_minor: number | null; currency: string | null; laptop_connectors: string[]; monitoring: string | null; deadline?: string }, signal?: AbortSignal) {
    if (frontendRuntime.mode === 'fixture') return translateFixture(() => fixture.saveGuided(params));
    return asGuided(await requestJson('/requirement-drafts/guided', { method: 'POST', body: JSON.stringify(params), signal }));
  },
  async confirmDraft(requestReference: string, expectedVersion: number): Promise<ConfirmedRequirements> {
    if (frontendRuntime.mode === 'fixture') return translateFixture(() => fixture.confirm(requestReference, expectedVersion));
    return asConfirmed(await requestJson(`/requirement-drafts/${encodeURIComponent(requestReference)}/confirm`, { method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }) }));
  },
  async generateBundlePlans(requirements: ConfirmedRequirements, signal?: AbortSignal) {
    if (frontendRuntime.mode === 'fixture') return translateFixture(() => fixture.generate(requirements));
    return asGeneration(await requestJson('/bundle-plans/generate', { method: 'POST', body: JSON.stringify({ schema_version: '1.0', correlation_id: correlationId(), confirmation_reference: requirements.confirmation_reference }), signal }));
  },
  async persistPlan(requirements: ConfirmedRequirements, proposalKey: string): Promise<AuthoritativePlan> {
    if (frontendRuntime.mode === 'fixture') return translateFixture(() => fixture.persist(requirements, proposalKey));
    return asPlan(await requestJson('/plans', { method: 'POST', body: JSON.stringify({ schema_version: '1.0', correlation_id: correlationId(), confirmation_reference: requirements.confirmation_reference, proposal_key: proposalKey }) }));
  },
  async getPlanEvidence(planId: string, signal?: AbortSignal): Promise<EvidenceRecord[]> {
    if (frontendRuntime.mode === 'fixture') return fixture.evidence();
    const value = await requestJson(`/bundle-plans/${encodeURIComponent(planId)}/evidence?correlation_id=${encodeURIComponent(correlationId())}`, { signal });
    if (!isRecord(value) || !Array.isArray(value.evidence)) invalidResponse('', '/evidence');
    return value.evidence as EvidenceRecord[];
  },
  async createApproval(plan: AuthoritativePlan): Promise<ApprovalRecord> {
    if (frontendRuntime.mode === 'fixture') return translateFixture(() => fixture.approve(plan));
    const head = plan.versions.find((version) => version.version === plan.current_version);
    if (!head) throw new ApiError(409, 'PLAN_VERSION_MISSING', 'The selected plan version is unavailable.');
    const value = await requestJson('/approvals', { method: 'POST', body: JSON.stringify({ plan_id: plan.plan_id, plan_version: head.version, plan_fingerprint: head.fingerprint, permitted_total: head.total }) });
    if (!isRecord(value) || !isRecord(value.approval) || !isString(value.approval.approval_id) || !isInteger(value.approval.plan_version) || !isRecord(value.approval.permitted_total)) invalidResponse('', '/approvals');
    const approval = value.approval;
    const permittedTotal = approval.permitted_total as Record<string, unknown>;
    return { approval_id: approval.approval_id as string, plan_id: approval.plan_id as string, plan_version: String(approval.plan_version), plan_fingerprint: approval.plan_fingerprint as string, amount_minor: permittedTotal.amount_minor as number, currency: permittedTotal.currency as string, status: approval.status as string, created_at: typeof approval.granted_at === 'string' ? approval.granted_at : new Date().toISOString(), valid: approval.status === 'granted' };
  },
  async replanBundle(plan: AuthoritativePlan, failedOfferId: string): Promise<ReplanResult> {
    if (frontendRuntime.mode === 'fixture') return translateFixture(() => fixture.replan(plan, failedOfferId));
    return await requestJson(`/plans/${encodeURIComponent(plan.plan_id)}/replan-proposals`, { method: 'POST', body: JSON.stringify({ expected_plan_version: plan.current_version, failed_offer_ids: [failedOfferId] }) }) as ReplanResult;
  },
  async simulateExecution(params: { approval_id: string; plan_id: string; plan_version: string; amount_minor: number; currency: string; inject_failure_offer_id?: string }): Promise<ExecutionRecord> {
    if (frontendRuntime.mode !== 'fixture') throw new ApiError(409, 'PAYMENT_EXECUTION_NOT_ENABLED', 'Payment execution is not enabled in the application runtime.');
    return fixture.execute(params);
  },
  async resetDemo(): Promise<void> { await fixture.reset(); },
};
