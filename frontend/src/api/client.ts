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

const BASE_URL = 'http://localhost:8000';

async function safeFetch<T>(endpoint: string, options?: RequestInit, fallback?: T): Promise<T> {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) {
      if (fallback !== undefined) return fallback;
      throw new Error(`API error ${res.status}: ${await res.text()}`);
    }
    return await res.json();
  } catch (err) {
    if (fallback !== undefined) {
      console.warn(`[BundleGraph API] Offline mode active for ${endpoint}:`, err);
      return fallback;
    }
    throw err;
  }
}

export const api = {
  async getPresets(): Promise<PresetScenario[]> {
    return safeFetch<PresetScenario[]>('/api/presets', { method: 'GET' }, OFFLINE_PRESETS);
  },

  async interpretRequirements(message: string, requestReference?: string): Promise<RequirementInterpretation> {
    const fallback: RequirementInterpretation = {
      ...SAMPLE_INTERPRETATION,
      draft: {
        ...SAMPLE_INTERPRETATION.draft,
        use_case: message.slice(0, 50),
      },
    };
    return safeFetch<RequirementInterpretation>(
      '/api/requirements/interpret',
      {
        method: 'POST',
        body: JSON.stringify({ message, request_reference: requestReference }),
      },
      fallback,
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
    const fallback: ConfirmedRequirements = {
      ...SAMPLE_CONFIRMED_REQ,
      use_case: params.use_case,
      participants: params.participants,
      budget: { amount_minor: params.budget_minor, currency: params.currency },
      laptop_connectors: [{ connector: params.laptop_connector }],
      listening_requirement: params.listening_requirement,
      deadline: params.deadline || SAMPLE_CONFIRMED_REQ.deadline,
    };
    return safeFetch<ConfirmedRequirements>(
      '/api/requirements/confirm',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      fallback,
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
    const fallback = {
      status: 'ok',
      reason_codes: [],
      result: {
        proposals: [SAMPLE_PROPOSAL],
        search_status: 'completed',
      },
    };
    return safeFetch('/api/bundle-plans/generate', {
      method: 'POST',
      body: JSON.stringify({ requirements }),
    }, fallback);
  },

  async replanBundle(params: {
    original_proposal: BundleProposal;
    requirements: ConfirmedRequirements;
    failed_offer_ids: string[];
    locked_offer_ids: string[];
    plan_id: string;
    plan_version: string;
  }): Promise<ReplanResult> {
    return safeFetch<ReplanResult>(
      '/api/bundle-plans/replan',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      SAMPLE_REPLAN_RESULT,
    );
  },

  async createApproval(params: {
    plan_id: string;
    plan_version: string;
    amount_minor: number;
    currency: string;
  }): Promise<ApprovalRecord> {
    const fallback: ApprovalRecord = {
      approval_id: `appr-${Math.random().toString(36).substring(2, 9)}`,
      plan_id: params.plan_id,
      plan_version: params.plan_version,
      amount_minor: params.amount_minor,
      currency: params.currency,
      status: 'APPROVED',
      created_at: new Date().toISOString(),
      valid: true,
    };
    return safeFetch<ApprovalRecord>(
      '/api/approvals/create',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      fallback,
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
    if (params.inject_failure_offer_id) {
      const failFallback: ExecutionRecord = {
        execution_status: 'FAILED_MERCHANT_STOCK_OUTAGE',
        plan_id: params.plan_id,
        approval_id: params.approval_id,
        approval_invalidated: true,
        failed_offer_id: params.inject_failure_offer_id,
        message: `Merchant reported stock outage for offer '${params.inject_failure_offer_id}'. Transaction halted.`,
        replan_recommended: true,
      };
      return safeFetch<ExecutionRecord>(
        '/api/executions/simulate',
        {
          method: 'POST',
          body: JSON.stringify(params),
        },
        failFallback,
      );
    }

    const successFallback: ExecutionRecord = {
      execution_status: 'COMPLETED',
      transaction_id: `PAYPAL-TXN-${Math.random().toString(36).substring(2, 12).toUpperCase()}`,
      plan_id: params.plan_id,
      amount_minor: params.amount_minor,
      currency: params.currency,
      settled_at: new Date().toISOString(),
      approval_id: params.approval_id,
      message: 'PayPal Sandbox payment captured and reconciled successfully.',
    };
    return safeFetch<ExecutionRecord>(
      '/api/executions/simulate',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      successFallback,
    );
  },

  async sendZapierNotification(event_type: string, payload: Record<string, unknown>): Promise<{ status: string }> {
    return safeFetch(
      '/api/notifications/zapier',
      {
        method: 'POST',
        body: JSON.stringify({ event_type, payload }),
      },
      { status: 'simulated_local' },
    );
  },

  async resetDemo(): Promise<void> {
    await safeFetch('/api/demo/reset', { method: 'POST' }, { status: 'reset_completed' });
  },
};
