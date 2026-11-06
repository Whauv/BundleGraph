import type {
  ApprovalRecord, AuthoritativePlan, BundleProposal, ConfirmedRequirements, DraftRequirements,
  EvidenceRecord, ExecutionRecord, PresetScenario, ReplanResult, RequirementInterpretation,
} from '../types/bundlegraph';
import { OFFLINE_PRESETS, SAMPLE_INTERPRETATION, SAMPLE_PROPOSAL, SAMPLE_REPLAN_RESULT } from '../fixtures/offlineData';

export class FixtureContractError extends Error {
  status: number;
  reason_code: string;
  constructor(status: number, reasonCode: string, message: string) {
    super(message); this.status = status; this.reason_code = reasonCode;
  }
}

type GuidedParams = {
  request_reference: string; use_case: string | null; participants: number | null;
  budget_minor: number | null; currency: string | null; laptop_connectors: string[];
  monitoring: string | null; deadline?: string;
};

const DEFAULT_MESSAGE = 'I want to start a two-person podcast with my USB-C laptop. My equipment budget is $600, and I need microphones, headphones, and all required cables.';
const KNOWN_MESSAGES = new Map([
  [DEFAULT_MESSAGE, { budget: 60000, connector: 'usb-c', monitoring: 'independent_headphones' }],
  ...OFFLINE_PRESETS.map((preset) => [preset.message, { budget: preset.budget_minor, connector: preset.laptop_connector, monitoring: preset.listening_requirement }] as const),
]);

function clone<T>(value: T): T { return structuredClone(value); }

function secondCandidate(): BundleProposal {
  const proposal = clone(SAMPLE_PROPOSAL);
  proposal.proposal_key = 'prop-verified-alt-v1';
  proposal.ranking_rationale = ['Verified complete fixture alternative.', 'Higher deterministic fixture rank than Option 1.'];
  return proposal;
}

function confirmedFromDraft(draft: DraftRequirements, version: number): ConfirmedRequirements {
  if (!draft.use_case || draft.participants === null || !draft.budget || !draft.listening_requirement || draft.missing_information.length || !draft.laptop_connectors.length) {
    throw new FixtureContractError(422, 'CLARIFICATION_REQUIRED', 'The synthetic draft is incomplete and cannot be confirmed.');
  }
  return {
    request_reference: draft.request_reference, confirmation_reference: `fixture-confirmed-v${version}`,
    use_case: draft.use_case, participants: draft.participants, budget: draft.budget,
    required_quantities: draft.required_quantities, laptop_connectors: draft.laptop_connectors,
    listening_requirement: draft.listening_requirement, deadline: draft.deadline || null,
  };
}

export function createFixtureAdapter() {
  let draft: DraftRequirements | null = null;
  let version = 0;
  let proposals: BundleProposal[] = [];

  return {
    getPresets: async (): Promise<PresetScenario[]> => clone(OFFLINE_PRESETS),
    interpret: async (message: string, requestReference: string): Promise<RequirementInterpretation> => {
      version += 1;
      const known = KNOWN_MESSAGES.get(message);
      if (!known) {
        draft = { request_reference: requestReference, use_case: null, participants: null, budget: null, required_quantities: [], laptop_connectors: [], listening_requirement: null, deadline: null, missing_information: ['supported use case', 'participant count', 'budget', 'laptop connector', 'monitoring requirement'] };
        return { draft: clone(draft), explicit_facts: [], suggested_defaults: [], missing_information: clone(draft.missing_information), clarification_questions: ['This synthetic scenario does not recognize that request. Choose the supported two-person podcast example or enter the requirements explicitly.'], provider_mode: 'synthetic_fixture', version, can_confirm: false };
      }
      draft = {
        ...clone(SAMPLE_INTERPRETATION.draft), request_reference: requestReference,
        budget: { amount_minor: known.budget, currency: 'USD' },
        laptop_connectors: [{ connector: known.connector }], listening_requirement: known.monitoring,
      };
      return { ...clone(SAMPLE_INTERPRETATION), draft: clone(draft), provider_mode: 'synthetic_fixture', version, can_confirm: true };
    },
    saveGuided: async (params: GuidedParams) => {
      version += 1;
      const listening = ({ independent: 'independent_headphones', shared: 'shared_headphones', none: 'no_monitoring' } as Record<string, string>)[params.monitoring || ''] || null;
      const missing = [params.use_case?.trim().toLowerCase() !== 'two-person podcast' ? 'supported use case' : null, params.participants !== 2 ? 'supported participant topology' : null, params.budget_minor === null || params.budget_minor <= 0 ? 'budget' : null, !params.currency ? 'currency' : null, params.laptop_connectors.includes('unknown') || !params.laptop_connectors.length ? 'laptop connector' : null, !listening ? 'monitoring requirement' : null].filter((item): item is string => Boolean(item));
      draft = {
        request_reference: params.request_reference, use_case: params.use_case, participants: params.participants,
        budget: params.budget_minor !== null && params.currency ? { amount_minor: params.budget_minor, currency: params.currency } : null,
        required_quantities: params.participants === null ? [] : [{ category: 'microphone', quantity: params.participants }, { category: 'audio_interface', quantity: 1 }, { category: 'xlr_cable', quantity: params.participants }, { category: 'headphones', quantity: params.participants }],
        laptop_connectors: params.laptop_connectors.filter((item) => item !== 'unknown').map((connector) => ({ connector })),
        listening_requirement: listening, deadline: params.deadline || null, missing_information: missing,
      };
      return { draft: clone(draft), version, clarification_questions: missing.map((item) => `Please resolve ${item}.`), can_confirm: !missing.length };
    },
    confirm: async (requestReference: string, expectedVersion: number): Promise<ConfirmedRequirements> => {
      if (!draft || draft.request_reference !== requestReference) throw new FixtureContractError(404, 'FIXTURE_DRAFT_NOT_FOUND', 'No matching synthetic draft exists.');
      if (expectedVersion !== version) throw new FixtureContractError(409, 'STALE_RESOURCE_VERSION', 'The synthetic draft version changed. Review it again.');
      return confirmedFromDraft(draft, version);
    },
    generate: async (requirements: ConfirmedRequirements) => {
      if (requirements.use_case !== 'two-person podcast' || requirements.participants !== 2) throw new FixtureContractError(422, 'UNSUPPORTED_FIXTURE_SCENARIO', 'The synthetic catalog supports only the labeled two-person podcast scenario.');
      if (requirements.laptop_connectors[0]?.connector === 'usb-a') {
        proposals = [];
        return { status: 'blocked', reason_codes: ['COMPATIBILITY_NOT_VERIFIED'], result: { proposals: [], search_status: 'completed', evaluated_candidates: 2, infeasibility: { reason_codes: ['COMPATIBILITY_NOT_VERIFIED'], explanation: 'The synthetic scenario has no evidence-backed USB-A path.' } } };
      }
      if (requirements.budget.amount_minor < 44300) {
        proposals = [];
        return { status: 'infeasible', reason_codes: ['BUDGET_EXCEEDED'], result: { proposals: [], search_status: 'completed', evaluated_candidates: 2, infeasibility: { reason_codes: ['BUDGET_EXCEEDED'], explanation: 'Every precomputed complete synthetic bundle exceeds the confirmed budget.' } } };
      }
      proposals = [clone(SAMPLE_PROPOSAL), secondCandidate()];
      return { status: 'ok', reason_codes: [], result: { proposals: clone(proposals), search_status: 'completed', evaluated_candidates: proposals.length, infeasibility: null } };
    },
    persist: async (requirements: ConfirmedRequirements, proposalKey: string): Promise<AuthoritativePlan> => {
      const proposal = proposals.find((item) => item.proposal_key === proposalKey);
      if (!proposal) throw new FixtureContractError(422, 'FIXTURE_PROPOSAL_NOT_FOUND', 'The selected synthetic proposal is not part of the latest search result.');
      const now = '2026-01-01T00:00:00Z';
      const total = proposal.cost_breakdown.all_in_total || proposal.cost_breakdown.merchandise_subtotal;
      return { plan_id: proposal.proposal_key, status: 'awaiting_approval', current_version: 1, created_at: now, updated_at: now, versions: [{ plan_id: proposal.proposal_key, version: 1, fingerprint: `fixture-fingerprint-${proposal.proposal_key}`, created_at: now, confirmation_reference: requirements.confirmation_reference, correlation_id: 'fixture-correlation', line_items: proposal.line_items.map((item) => ({ ...item, merchant_reference: 'synthetic-merchant' })), total, merchant_allocations: [], payload: { fixture: true, proposal_key: proposal.proposal_key } }] };
    },
    evidence: async (): Promise<EvidenceRecord[]> => [],
    approve: async (plan: AuthoritativePlan): Promise<ApprovalRecord> => {
      const head = plan.versions.find((item) => item.version === plan.current_version);
      if (!head) throw new FixtureContractError(409, 'PLAN_VERSION_MISSING', 'The selected plan version is unavailable.');
      return { approval_id: 'fixture-approval-v1', plan_id: plan.plan_id, plan_version: String(head.version), plan_fingerprint: head.fingerprint, amount_minor: head.total.amount_minor, currency: head.total.currency, status: 'SIMULATED_FIXTURE_APPROVAL', created_at: '2026-01-01T00:00:00Z', valid: true };
    },
    replan: async (plan: AuthoritativePlan, failedOfferId: string): Promise<ReplanResult> => {
      const head = plan.versions.find((item) => item.version === plan.current_version);
      if (!head?.line_items.some((item) => item.offer_id === failedOfferId)) throw new FixtureContractError(422, 'INVALID_RECOVERY_TARGET', 'Choose a failed offer from the current stored plan.');
      return { ...clone(SAMPLE_REPLAN_RESULT), original_plan_id: plan.plan_id, original_plan_version: String(plan.current_version), confirmation_reference: head.confirmation_reference };
    },
    execute: async (params: { approval_id: string; plan_id: string; amount_minor: number; currency: string; inject_failure_offer_id?: string }): Promise<ExecutionRecord> => params.inject_failure_offer_id
      ? { execution_status: 'FAILED_MERCHANT_STOCK_OUTAGE', plan_id: params.plan_id, approval_id: params.approval_id, approval_invalidated: true, failed_offer_id: params.inject_failure_offer_id, message: `Synthetic stock outage for ${params.inject_failure_offer_id}. No transaction was attempted.`, replan_recommended: true }
      : { execution_status: 'COMPLETED', transaction_id: 'fixture-transaction-v1', plan_id: params.plan_id, amount_minor: params.amount_minor, currency: params.currency, settled_at: '2026-01-01T00:00:00Z', approval_id: params.approval_id, message: 'Synthetic fixture execution completed. No payment provider was called.' },
    reset: async () => { draft = null; version = 0; proposals = []; },
  };
}
