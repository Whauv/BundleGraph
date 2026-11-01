import type {
  ApprovalRecord,
  BundleProposal,
  ConfirmedRequirements,
  ExecutionRecord,
  PresetScenario,
  ReplanResult,
  RequirementInterpretation,
} from '../types/bundlegraph';
import {
  OFFLINE_PRESETS,
  SAMPLE_CONFIRMED_REQ,
  SAMPLE_INTERPRETATION,
  SAMPLE_PROPOSAL,
  SAMPLE_REPLAN_RESULT,
} from '../fixtures/offlineData';

const configuredDemoBase = import.meta.env.VITE_BUNDLEGRAPH_DEMO_API_BASE?.trim();
const DEMO_API_BASE = configuredDemoBase
  ? configuredDemoBase.replace(/\/$/, '')
  : null;

export type FrontendRuntimeMode = 'fixture' | 'demo_api';

export const frontendRuntime: {
  mode: FrontendRuntimeMode;
  label: string;
  apiBase: string | null;
} = DEMO_API_BASE
  ? {
      mode: 'demo_api',
      label: 'Connected demo API',
      apiBase: DEMO_API_BASE,
    }
  : {
      mode: 'fixture',
      label: 'Synthetic offline fixtures',
      apiBase: null,
    };

function cloneFixture<T>(value: T): T {
  return structuredClone(value);
}

async function requestDemoApi<T>(endpoint: string, options: RequestInit, fixture: T): Promise<T> {
  if (!DEMO_API_BASE) return cloneFixture(fixture);

  let response: Response;
  try {
    response = await fetch(`${DEMO_API_BASE}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch (error) {
    throw new Error(
      `Configured demo API is unavailable for ${endpoint}. Fixture data was not substituted. ${String(error)}`,
    );
  }

  if (!response.ok) {
    throw new Error(`Demo API ${endpoint} returned ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async getPresets(): Promise<PresetScenario[]> {
    return requestDemoApi('/api/presets', { method: 'GET' }, OFFLINE_PRESETS);
  },

  async interpretRequirements(message: string, requestReference?: string): Promise<RequirementInterpretation> {
    const fixture: RequirementInterpretation = {
      ...cloneFixture(SAMPLE_INTERPRETATION),
      draft: {
        ...cloneFixture(SAMPLE_INTERPRETATION.draft),
        use_case: message.slice(0, 80),
      },
      provider_mode: 'synthetic_fixture',
    };
    return requestDemoApi(
      '/api/requirements/interpret',
      {
        method: 'POST',
        body: JSON.stringify({ message, request_reference: requestReference }),
      },
      fixture,
    );
  },

  async confirmRequirements(params: {
    use_case: string;
    participants: number;
    budget_minor: number;
    currency: string;
    laptop_connector: string;
    listening_requirement: string;
    deadline?: string;
  }): Promise<ConfirmedRequirements> {
    const fixture: ConfirmedRequirements = {
      ...cloneFixture(SAMPLE_CONFIRMED_REQ),
      use_case: params.use_case,
      participants: params.participants,
      budget: { amount_minor: params.budget_minor, currency: params.currency },
      laptop_connectors: [{ connector: params.laptop_connector }],
      listening_requirement: params.listening_requirement,
      deadline: params.deadline || null,
    };
    return requestDemoApi(
      '/api/requirements/confirm',
      { method: 'POST', body: JSON.stringify(params) },
      fixture,
    );
  },

  async generateBundlePlans(requirements: ConfirmedRequirements): Promise<{
    status: string;
    reason_codes: string[];
    result: {
      proposals: BundleProposal[];
      search_status: string;
      infeasibility?: { reason_codes: string[] };
    };
  }> {
    const fixture = {
      status: 'ok',
      reason_codes: [] as string[],
      result: {
        proposals: [cloneFixture(SAMPLE_PROPOSAL)],
        search_status: 'fixture_completed',
      },
    };
    return requestDemoApi(
      '/api/bundle-plans/generate',
      { method: 'POST', body: JSON.stringify({ requirements }) },
      fixture,
    );
  },

  async replanBundle(params: {
    original_proposal: BundleProposal;
    requirements: ConfirmedRequirements;
    failed_offer_ids: string[];
    locked_offer_ids: string[];
    plan_id: string;
    plan_version: string;
  }): Promise<ReplanResult> {
    return requestDemoApi(
      '/api/bundle-plans/replan',
      { method: 'POST', body: JSON.stringify(params) },
      SAMPLE_REPLAN_RESULT,
    );
  },

  async createApproval(params: {
    plan_id: string;
    plan_version: string;
    amount_minor: number;
    currency: string;
  }): Promise<ApprovalRecord> {
    const fixture: ApprovalRecord = {
      approval_id: 'fixture-approval-v1',
      plan_id: params.plan_id,
      plan_version: params.plan_version,
      amount_minor: params.amount_minor,
      currency: params.currency,
      status: 'SIMULATED_FIXTURE_APPROVAL',
      created_at: '2026-01-01T00:00:00Z',
      valid: true,
    };
    return requestDemoApi(
      '/api/approvals/create',
      { method: 'POST', body: JSON.stringify(params) },
      fixture,
    );
  },

  async simulateExecution(params: {
    approval_id: string;
    plan_id: string;
    plan_version: string;
    amount_minor: number;
    currency: string;
    inject_failure_offer_id?: string;
  }): Promise<ExecutionRecord> {
    const fixture: ExecutionRecord = params.inject_failure_offer_id
      ? {
          execution_status: 'FAILED_MERCHANT_STOCK_OUTAGE',
          plan_id: params.plan_id,
          approval_id: params.approval_id,
          approval_invalidated: true,
          failed_offer_id: params.inject_failure_offer_id,
          message: `Synthetic stock outage for ${params.inject_failure_offer_id}. No transaction was attempted.`,
          replan_recommended: true,
        }
      : {
          execution_status: 'COMPLETED',
          transaction_id: 'fixture-transaction-v1',
          plan_id: params.plan_id,
          amount_minor: params.amount_minor,
          currency: params.currency,
          settled_at: '2026-01-01T00:00:00Z',
          approval_id: params.approval_id,
          message: 'Synthetic fixture execution completed. No payment provider was called.',
        };
    return requestDemoApi(
      '/api/executions/simulate',
      { method: 'POST', body: JSON.stringify(params) },
      fixture,
    );
  },

  async resetDemo(): Promise<void> {
    if (!DEMO_API_BASE) return;
    await requestDemoApi('/api/demo/reset', { method: 'POST' }, { status: 'fixture_reset' });
  },
};
