export type ScreenStep = 'builder' | 'review' | 'comparison' | 'approval' | 'execution';

export interface Money {
  amount_minor: number;
  currency: string;
}

export interface PresetScenario {
  id: string;
  name: string;
  tag: string;
  badge_color: 'emerald' | 'crimson' | 'amber';
  message: string;
  budget_minor: number;
  currency: string;
  participants: number;
  laptop_connector: string;
  listening_requirement: string;
  deadline_days: number;
  description: string;
}

export interface ExtractedFact {
  path: string;
  value: string | number | boolean;
  kind: 'explicit' | 'suggested_default';
}

export interface DraftRequirements {
  request_reference: string;
  use_case: string;
  participants: number;
  budget: Money;
  required_quantities: Array<{ category: string; quantity: number }>;
  laptop_connectors: Array<{ connector: string }>;
  listening_requirement: string;
  missing_information: string[];
}

export interface RequirementInterpretation {
  draft: DraftRequirements;
  explicit_facts: ExtractedFact[];
  suggested_defaults: ExtractedFact[];
  missing_information: string[];
  clarification_questions: string[];
  provider_mode: string;
  version?: number;
  can_confirm?: boolean;
}

export interface ConfirmedRequirements {
  request_reference: string;
  confirmation_reference: string;
  use_case: string;
  participants: number;
  budget: Money;
  required_quantities: Array<{ category: string; quantity: number }>;
  laptop_connectors: Array<{ connector: string }>;
  listening_requirement: string;
  deadline: string | null;
}

export interface BundleLineItem {
  product_id: string;
  offer_id: string;
  quantity: number;
  unit_price: Money;
  merchandise_total: Money;
  shipping: Money | { reason: string };
  tax: Money | { reason: string };
}

export interface CostBreakdown {
  currency: string;
  merchandise_subtotal: Money;
  shipping_total: Money | null;
  tax_total: Money | null;
  all_in_total: Money | null;
  total_status: string;
  unknown_cost_components?: string[];
}

export interface Finding {
  rule_id: string;
  affected_product_ids: string[];
  status: 'compatible' | 'incompatible' | 'unknown';
  reason_code: string;
  explanation: string;
  evidence_ids: string[];
  missing_requirements_or_evidence?: string[];
}

export interface GraphNode {
  node_id: string;
  node_type: string;
  data: Record<string, unknown>;
}

export interface GraphEdge {
  source_id: string;
  target_id: string;
  edge_type?: string;
  relationship?: string;
  evidence_ids?: string[];
}

export interface CompatibilityReport {
  classification: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  findings: Finding[];
  evidence_references: string[];
}

export interface BundleProposal {
  proposal_key: string;
  line_items: BundleLineItem[];
  cost_breakdown: CostBreakdown;
  compatibility_report: CompatibilityReport;
  evidence_references: string[];
  ranking_rationale?: string[];
}

export interface EvidenceRecord {
  evidence_id: string;
  subject_id: string;
  attribute: string;
  observed_value: unknown;
  source_url?: string | null;
  source_type: string;
  observed_at: string;
  excerpt: string;
  origin: string;
  support_status: string;
  freshness_status: string;
  conflict_status: string;
}

export interface AuthoritativePlanVersion {
  plan_id: string;
  version: number;
  fingerprint: string;
  created_at: string;
  confirmation_reference: string;
  correlation_id: string;
  line_items: Array<BundleLineItem & { merchant_reference: string }>;
  total: Money;
  merchant_allocations: Array<{ allocation_id: string; merchant_reference: string; amount: Money; offer_ids: string[] }>;
  payload: Record<string, unknown>;
}

export interface AuthoritativePlan {
  plan_id: string;
  status: string;
  current_version: number;
  created_at: string;
  updated_at: string;
  versions: AuthoritativePlanVersion[];
}

export interface BundleSelectionResult {
  search_status: string;
  proposals: BundleProposal[];
  evaluated_candidates: number;
  infeasibility?: {
    reason_codes: string[];
    explanation?: string;
  } | null;
}

export interface ItemDelta {
  offer_id: string;
  product_id: string;
  previous_quantity: number;
  replacement_quantity: number;
  change_type: 'added' | 'removed' | 'retained' | 'quantity_changed';
  reason_code: string;
}

export interface ReplacementBundleProposal {
  proposal: BundleProposal;
  added_items: ItemDelta[];
  removed_items: ItemDelta[];
  retained_items: ItemDelta[];
  quantity_changed_items: ItemDelta[];
  material_change_reasons: string[];
  cost_difference: Money | null;
  affected_subgraph?: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  requires_new_approval: boolean;
}

export interface ReplanResult {
  original_plan_id: string;
  original_plan_version: string;
  confirmation_reference: string;
  replacements: ReplacementBundleProposal[];
  search_status: string;
  infeasibility?: {
    reason_codes: string[];
  } | null;
  requires_new_approval: boolean;
}

export interface ApprovalRecord {
  approval_id: string;
  plan_id: string;
  plan_version: string;
  amount_minor: number;
  currency: string;
  status: string;
  created_at: string;
  valid: boolean;
  plan_fingerprint?: string;
}

export type PipelineStage =
  | 'idle'
  | 'resolving_requirements'
  | 'discovering_candidates'
  | 'checking_evidence'
  | 'evaluating_compatibility'
  | 'selecting_bundles'
  | 'persisting_plan'
  | 'complete';

export interface ApiFailure {
  status: number;
  reason_code: string;
  message: string;
  correlation_id?: string;
}

export interface ExecutionRecord {
  execution_status: 'COMPLETED' | 'FAILED_MERCHANT_STOCK_OUTAGE';
  transaction_id?: string;
  plan_id: string;
  amount_minor?: number;
  currency?: string;
  settled_at?: string;
  approval_id: string;
  failed_offer_id?: string;
  approval_invalidated?: boolean;
  message: string;
  replan_recommended?: boolean;
}
