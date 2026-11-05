import React, { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import type {
  ApiFailure, ApprovalRecord, AuthoritativePlan, BundleProposal, ConfirmedRequirements,
  EvidenceRecord, ExecutionRecord, PipelineStage, PresetScenario, ReplanResult,
  RequirementInterpretation, ScreenStep, WorkflowOperation,
} from '../types/bundlegraph';
import { ApiError, api, frontendRuntime, type FrontendRuntimeMode } from '../api/client';
import { OFFLINE_PRESETS } from '../fixtures/offlineData';

const STEPS: ScreenStep[] = ['builder', 'review', 'comparison', 'approval', 'execution'];
const DEFAULT_PROMPT = 'I want to start a two-person podcast with my USB-C laptop. My equipment budget is $600, and I need microphones, headphones, and all required cables.';

interface SavedWorkflow {
  promptText?: string; budgetDollars?: number; participants?: number; laptopConnector?: string;
  listeningRequirement?: string; deadlineDate?: string; requestReference?: string;
}

interface DemoContextType {
  runtimeMode: FrontendRuntimeMode; runtimeLabel: string; currentStep: ScreenStep;
  setStep: (step: ScreenStep) => void; canNavigate: (step: ScreenStep) => boolean; navigationNotice: string | null;
  promptText: string; setPromptText: (text: string) => void;
  budgetDollars: number; setBudgetDollars: (value: number) => void;
  participants: number; setParticipants: (value: number) => void;
  laptopConnector: string; setLaptopConnector: (value: string) => void;
  listeningRequirement: string; setListeningRequirement: (value: string) => void;
  deadlineDate: string; setDeadlineDate: (value: string) => void;
  presets: PresetScenario[]; activePresetId: string | null;
  interpretation: RequirementInterpretation | null; confirmedRequirements: ConfirmedRequirements | null;
  proposals: BundleProposal[]; selectedProposal: BundleProposal | null;
  approvalRecord: ApprovalRecord | null; executionRecord: ExecutionRecord | null; replanResult: ReplanResult | null;
  authoritativePlan: AuthoritativePlan | null; evidenceRecords: EvidenceRecord[];
  pipelineStage: PipelineStage; apiFailure: ApiFailure | null; failedOperation: WorkflowOperation | null;
  draftVersion: number | null; isLoading: boolean; errorMessage: string | null;
  loadPreset: (preset: PresetScenario) => Promise<void>; interpretPrompt: () => Promise<void>;
  confirmRequirements: () => Promise<void>; generateBundles: () => Promise<void>;
  selectProposal: (proposalKey: string) => void; preparePlan: () => Promise<void>; approvePlan: () => Promise<void>;
  executeOrder: (injectFailureOfferId?: string) => Promise<void>; triggerReplan: (failedOfferId?: string) => Promise<void>;
  resetAll: () => Promise<void>; retryLastAction: () => Promise<void>; dismissFailure: () => void;
}

const DemoContext = createContext<DemoContextType | null>(null);

function savedWorkflow(): SavedWorkflow {
  try { return JSON.parse(sessionStorage.getItem('bundlegraph.workflow') || '{}') as SavedWorkflow; }
  catch { sessionStorage.removeItem('bundlegraph.workflow'); return {}; }
}

function monitoringForApi(value: string): string {
  return ({ independent_headphones: 'independent', shared_headphones: 'shared', no_monitoring: 'none' } as Record<string, string>)[value] || value;
}

function asFailure(error: unknown): ApiFailure {
  if (error && typeof error === 'object' && 'reason_code' in error) return error as ApiFailure;
  return { status: 0, reason_code: 'UNEXPECTED_CLIENT_ERROR', message: error instanceof Error ? error.message : String(error) };
}

export const DemoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [restored] = useState(savedWorkflow);
  const [currentStep, setCurrentStep] = useState<ScreenStep>('builder');
  const [navigationNotice, setNavigationNotice] = useState<string | null>(() => {
    const requested = window.location.hash.replace('#/', '') as ScreenStep;
    return STEPS.includes(requested) && requested !== 'builder' ? 'Saved server records are not reconstructed from browser storage. Resume from Describe.' : null;
  });
  const [promptText, setPromptTextState] = useState(restored.promptText || DEFAULT_PROMPT);
  const [budgetDollars, setBudgetDollarsState] = useState(restored.budgetDollars ?? 600);
  const [participants, setParticipantsState] = useState(restored.participants ?? 2);
  const [laptopConnector, setLaptopConnectorState] = useState(restored.laptopConnector || 'usb-c');
  const [listeningRequirement, setListeningRequirementState] = useState(restored.listeningRequirement || 'independent_headphones');
  const [deadlineDate, setDeadlineDateState] = useState(restored.deadlineDate || '');
  const [requestReference, setRequestReference] = useState(restored.requestReference || `req-${crypto.randomUUID()}`);
  const [presets, setPresets] = useState<PresetScenario[]>(OFFLINE_PRESETS);
  const [activePresetId, setActivePresetId] = useState<string | null>(null);
  const [interpretation, setInterpretation] = useState<RequirementInterpretation | null>(null);
  const [confirmedRequirements, setConfirmedRequirements] = useState<ConfirmedRequirements | null>(null);
  const [proposals, setProposals] = useState<BundleProposal[]>([]);
  const [selectedProposal, setSelectedProposal] = useState<BundleProposal | null>(null);
  const [approvalRecord, setApprovalRecord] = useState<ApprovalRecord | null>(null);
  const [executionRecord, setExecutionRecord] = useState<ExecutionRecord | null>(null);
  const [replanResult, setReplanResult] = useState<ReplanResult | null>(null);
  const [authoritativePlan, setAuthoritativePlan] = useState<AuthoritativePlan | null>(null);
  const [evidenceRecords, setEvidenceRecords] = useState<EvidenceRecord[]>([]);
  const [pipelineStage, setPipelineStage] = useState<PipelineStage>('idle');
  const [apiFailure, setApiFailure] = useState<ApiFailure | null>(null);
  const [failedOperation, setFailedOperation] = useState<WorkflowOperation | null>(null);
  const [draftVersion, setDraftVersion] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const revisionRef = useRef(0);
  const operationRef = useRef(0);

  const canNavigate = useCallback((step: ScreenStep): boolean => {
    if (step === 'builder') return true;
    if (step === 'review') return Boolean(interpretation);
    if (step === 'comparison') return Boolean(confirmedRequirements && proposals.length);
    if (step === 'approval') return Boolean(authoritativePlan);
    return Boolean(executionRecord || replanResult);
  }, [authoritativePlan, confirmedRequirements, executionRecord, interpretation, proposals.length, replanResult]);

  const commitStep = useCallback((step: ScreenStep, replace = false) => {
    setCurrentStep(step);
    const hash = `#/${step}`;
    if (window.location.hash !== hash) window.history[replace ? 'replaceState' : 'pushState']({}, '', hash);
  }, []);

  const setStep = useCallback((requested: ScreenStep) => {
    if (canNavigate(requested)) { setNavigationNotice(null); commitStep(requested); return; }
    const fallback: ScreenStep = authoritativePlan ? 'approval' : proposals.length ? 'comparison' : interpretation ? 'review' : 'builder';
    setNavigationNotice('That step is not available in this browser session. Continue from the earliest completed step.');
    commitStep(fallback, true);
  }, [authoritativePlan, canNavigate, commitStep, interpretation, proposals.length]);

  useEffect(() => {
    commitStep('builder', true);
  }, [commitStep]);

  useEffect(() => {
    const onHashChange = () => {
      const next = window.location.hash.replace('#/', '') as ScreenStep;
      if (STEPS.includes(next)) setStep(next);
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, [setStep]);

  useEffect(() => { api.getPresets().then((data) => { if (data.length) setPresets(data); }).catch(() => undefined); }, []);
  useEffect(() => {
    sessionStorage.setItem('bundlegraph.workflow', JSON.stringify({ promptText, budgetDollars, participants, laptopConnector, listeningRequirement, deadlineDate, requestReference }));
  }, [budgetDollars, deadlineDate, laptopConnector, listeningRequirement, participants, promptText, requestReference]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (currentStep !== 'builder' && !approvalRecord) event.preventDefault(); };
    window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn);
  }, [approvalRecord, currentStep]);

  const beginOperation = (operation: WorkflowOperation, stage: PipelineStage) => {
    const token = { identity: ++operationRef.current, revision: revisionRef.current };
    setApiFailure(null); setErrorMessage(null); setFailedOperation(null); setPipelineStage(stage); setIsLoading(true);
    return { ...token, operation };
  };
  const isCurrent = (token: { identity: number; revision: number }) => token.identity === operationRef.current && token.revision === revisionRef.current;
  const finishOperation = (token: { identity: number; revision: number }, stage: PipelineStage = 'complete') => {
    if (!isCurrent(token)) return false; setPipelineStage(stage); setIsLoading(false); return true;
  };
  const captureError = (error: unknown, operation: WorkflowOperation, token: { identity: number; revision: number }, retryable = true) => {
    if (!isCurrent(token)) return;
    const failure = asFailure(error); setApiFailure(failure); setErrorMessage(failure.message);
    setFailedOperation(retryable ? operation : null); setPipelineStage('failed'); setIsLoading(false);
  };

  const clearDownstream = (includeInterpretation = false) => {
    if (includeInterpretation) { setInterpretation(null); setDraftVersion(null); }
    setConfirmedRequirements(null); setProposals([]); setSelectedProposal(null); setAuthoritativePlan(null);
    setEvidenceRecords([]); setApprovalRecord(null); setExecutionRecord(null); setReplanResult(null);
  };
  const invalidateForEdit = () => {
    revisionRef.current += 1; operationRef.current += 1; setIsLoading(false); setPipelineStage('idle');
    setApiFailure(null); setErrorMessage(null); setFailedOperation(null); clearDownstream(false);
  };
  const applyInput = <T,>(setter: React.Dispatch<React.SetStateAction<T>>, value: T) => { setter(value); invalidateForEdit(); };

  const loadPreset = async (preset: PresetScenario) => {
    revisionRef.current += 1; operationRef.current += 1; setActivePresetId(preset.id);
    setPromptTextState(preset.message); setBudgetDollarsState(Math.round(preset.budget_minor / 100)); setParticipantsState(preset.participants);
    setLaptopConnectorState(preset.laptop_connector); setListeningRequirementState(preset.listening_requirement); setDeadlineDateState('');
    clearDownstream(true); setApiFailure(null); setErrorMessage(null); setFailedOperation(null); setPipelineStage('idle'); setIsLoading(false); commitStep('builder');
  };

  const interpretPrompt = async () => {
    const token = beginOperation('interpret', 'resolving_requirements'); clearDownstream(true);
    try {
      const result = await api.interpretRequirements(promptText, requestReference);
      if (!isCurrent(token)) return; setInterpretation(result); setDraftVersion(result.version || 1); finishOperation(token); commitStep('review');
    } catch (error) { captureError(error, 'interpret', token); }
  };

  const guidedDraft = () => api.saveGuidedDraft({
    request_reference: requestReference, use_case: 'two-person podcast', participants,
    budget_minor: Math.round(budgetDollars * 100), currency: 'USD', laptop_connectors: [laptopConnector],
    monitoring: monitoringForApi(listeningRequirement), deadline: deadlineDate ? new Date(`${deadlineDate}T12:00:00Z`).toISOString() : undefined,
  });

  const confirmRequirements = async () => {
    const token = beginOperation('confirm', 'resolving_requirements');
    try {
      let version = draftVersion || 1;
      const updated = await guidedDraft(); if (!isCurrent(token)) return; version = updated.version; setDraftVersion(version);
      setInterpretation((current) => ({ draft: updated.draft, explicit_facts: current?.explicit_facts || [], suggested_defaults: current?.suggested_defaults || [], missing_information: updated.draft.missing_information, clarification_questions: updated.clarification_questions, provider_mode: current?.provider_mode || (frontendRuntime.mode === 'fixture' ? 'synthetic_fixture' : 'authoritative_guided'), version: updated.version, can_confirm: updated.can_confirm }));
      if (!updated.can_confirm) throw new ApiError(422, 'CLARIFICATION_REQUIRED', `Resolve: ${updated.draft.missing_information.join(', ')}`);
      const confirmed = await api.confirmDraft(requestReference, version); if (!isCurrent(token)) return;
      setConfirmedRequirements(confirmed); setPipelineStage('selecting_bundles');
      const response = await api.generateBundlePlans(confirmed); if (!isCurrent(token)) return;
      const next = response.status === 'ok' ? response.result.proposals : []; setProposals(next); setSelectedProposal(next[0] || null);
      if (!next.length) setErrorMessage((response.reason_codes.length ? response.reason_codes : response.result.infeasibility?.reason_codes || ['NO_FEASIBLE_BUNDLE']).join(', '));
      finishOperation(token); commitStep('comparison');
    } catch (error) { captureError(error, 'confirm', token); }
  };

  const generateBundles = async () => {
    if (!confirmedRequirements) return; const token = beginOperation('generate', 'selecting_bundles');
    try {
      const response = await api.generateBundlePlans(confirmedRequirements); if (!isCurrent(token)) return;
      const next = response.status === 'ok' ? response.result.proposals : []; setProposals(next); setSelectedProposal(next[0] || null);
      setErrorMessage(next.length ? null : (response.reason_codes.length ? response.reason_codes.join(', ') : 'No feasible bundle was returned.'));
      finishOperation(token); commitStep('comparison');
    } catch (error) { captureError(error, 'generate', token); }
  };

  const selectProposal = (proposalKey: string) => {
    const proposal = proposals.find((item) => item.proposal_key === proposalKey);
    if (!proposal || proposal.proposal_key === selectedProposal?.proposal_key) return;
    revisionRef.current += 1; operationRef.current += 1; setSelectedProposal(proposal); setAuthoritativePlan(null);
    setEvidenceRecords([]); setApprovalRecord(null); setExecutionRecord(null); setReplanResult(null);
    setApiFailure(null); setErrorMessage(null); setPipelineStage('idle'); setIsLoading(false);
  };

  const preparePlan = async () => {
    if (!selectedProposal || !confirmedRequirements) return; const token = beginOperation('persist', 'persisting_plan');
    try {
      const plan = await api.persistPlan(confirmedRequirements, selectedProposal.proposal_key); if (!isCurrent(token)) return; setAuthoritativePlan(plan);
      const evidence = await api.getPlanEvidence(plan.plan_id); if (!isCurrent(token)) return; setEvidenceRecords(evidence); finishOperation(token); commitStep('approval');
    } catch (error) { captureError(error, 'persist', token); }
  };

  const approvePlan = async () => {
    if (!authoritativePlan) return; const token = beginOperation('approve', 'persisting_plan');
    try { const approval = await api.createApproval(authoritativePlan); if (!isCurrent(token)) return; setApprovalRecord(approval); finishOperation(token); }
    catch (error) { captureError(error, 'approve', token, false); }
  };

  const executeOrder = async (injectFailureOfferId?: string) => {
    if (!approvalRecord?.valid || !selectedProposal) return; const token = beginOperation('execute', 'persisting_plan');
    try {
      const execution = await api.simulateExecution({ approval_id: approvalRecord.approval_id, plan_id: approvalRecord.plan_id, plan_version: approvalRecord.plan_version, amount_minor: approvalRecord.amount_minor, currency: approvalRecord.currency, inject_failure_offer_id: injectFailureOfferId });
      if (!isCurrent(token)) return; setExecutionRecord(execution);
      if (execution.approval_invalidated) setApprovalRecord((current) => current ? { ...current, valid: false, status: 'INVALIDATED_BY_RECORDED_EXECUTION' } : null);
      finishOperation(token); commitStep('execution');
      if (execution.execution_status === 'FAILED_MERCHANT_STOCK_OUTAGE' && execution.failed_offer_id) await triggerReplan(execution.failed_offer_id);
    } catch (error) { captureError(error, 'execute', token, false); }
  };

  const triggerReplan = async (failedOfferId?: string) => {
    if (!selectedProposal || !confirmedRequirements || !authoritativePlan) return; const token = beginOperation('replan', 'selecting_bundles');
    try {
      const result = await api.replanBundle(authoritativePlan, failedOfferId || executionRecord?.failed_offer_id || 'offer-mic-alpha');
      if (!isCurrent(token)) return; setReplanResult(result); finishOperation(token); commitStep('execution');
    } catch (error) { captureError(error, 'replan', token); }
  };

  const resetAll = async () => {
    const token = beginOperation('reset', 'resolving_requirements');
    try {
      await api.resetDemo(); if (token.identity !== operationRef.current) return; revisionRef.current += 1;
      setPromptTextState(DEFAULT_PROMPT); setBudgetDollarsState(600); setParticipantsState(2); setLaptopConnectorState('usb-c');
      setListeningRequirementState('independent_headphones'); setDeadlineDateState(''); setRequestReference(`req-${crypto.randomUUID()}`); setActivePresetId(null);
      clearDownstream(true); setNavigationNotice(null); setApiFailure(null); setErrorMessage(null); setFailedOperation(null); setPipelineStage('idle'); setIsLoading(false); commitStep('builder', true);
    } catch (error) { captureError(error, 'reset', token, false); }
  };

  const retryLastAction = async () => {
    if (failedOperation === 'interpret') return interpretPrompt(); if (failedOperation === 'confirm') return confirmRequirements();
    if (failedOperation === 'generate') return generateBundles(); if (failedOperation === 'persist') return preparePlan();
    if (failedOperation === 'replan') return triggerReplan(executionRecord?.failed_offer_id);
  };
  const dismissFailure = () => { setApiFailure(null); setErrorMessage(null); setFailedOperation(null); if (pipelineStage === 'failed') setPipelineStage('idle'); };

  return <DemoContext.Provider value={{
    runtimeMode: frontendRuntime.mode, runtimeLabel: frontendRuntime.label, currentStep, setStep, canNavigate, navigationNotice,
    promptText, setPromptText: (value) => applyInput(setPromptTextState, value), budgetDollars, setBudgetDollars: (value) => applyInput(setBudgetDollarsState, value),
    participants, setParticipants: (value) => applyInput(setParticipantsState, value), laptopConnector, setLaptopConnector: (value) => applyInput(setLaptopConnectorState, value),
    listeningRequirement, setListeningRequirement: (value) => applyInput(setListeningRequirementState, value), deadlineDate, setDeadlineDate: (value) => applyInput(setDeadlineDateState, value),
    presets, activePresetId, interpretation, confirmedRequirements, proposals, selectedProposal, approvalRecord, executionRecord, replanResult,
    authoritativePlan, evidenceRecords, pipelineStage, apiFailure, failedOperation, draftVersion, isLoading, errorMessage,
    loadPreset, interpretPrompt, confirmRequirements, generateBundles, selectProposal, preparePlan, approvePlan, executeOrder, triggerReplan, resetAll, retryLastAction, dismissFailure,
  }}>{children}</DemoContext.Provider>;
};

// oxlint-disable-next-line react/only-export-components -- provider and hook share one workflow boundary.
export const useDemo = () => { const context = useContext(DemoContext); if (!context) throw new Error('useDemo must be used within a DemoProvider'); return context; };
