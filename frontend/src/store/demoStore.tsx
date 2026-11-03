import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type {
  ApiFailure,
  ApprovalRecord,
  AuthoritativePlan,
  BundleProposal,
  ConfirmedRequirements,
  EvidenceRecord,
  ExecutionRecord,
  PipelineStage,
  PresetScenario,
  ReplanResult,
  RequirementInterpretation,
  ScreenStep,
} from '../types/bundlegraph';
import { api, frontendRuntime, type FrontendRuntimeMode } from '../api/client';
import { OFFLINE_PRESETS, SAMPLE_CONFIRMED_REQ, SAMPLE_PROPOSAL } from '../fixtures/offlineData';

interface DemoContextType {
  runtimeMode: FrontendRuntimeMode;
  runtimeLabel: string;
  currentStep: ScreenStep;
  setStep: (step: ScreenStep) => void;
  promptText: string;
  setPromptText: (text: string) => void;
  budgetDollars: number;
  setBudgetDollars: (val: number) => void;
  participants: number;
  setParticipants: (val: number) => void;
  laptopConnector: string;
  setLaptopConnector: (val: string) => void;
  listeningRequirement: string;
  setListeningRequirement: (val: string) => void;
  deadlineDate: string;
  setDeadlineDate: (val: string) => void;
  
  presets: PresetScenario[];
  activePresetId: string | null;
  interpretation: RequirementInterpretation | null;
  confirmedRequirements: ConfirmedRequirements | null;
  proposals: BundleProposal[];
  selectedProposal: BundleProposal | null;
  approvalRecord: ApprovalRecord | null;
  executionRecord: ExecutionRecord | null;
  replanResult: ReplanResult | null;
  authoritativePlan: AuthoritativePlan | null;
  evidenceRecords: EvidenceRecord[];
  pipelineStage: PipelineStage;
  apiFailure: ApiFailure | null;
  
  isLoading: boolean;
  errorMessage: string | null;
  loadPreset: (preset: PresetScenario) => Promise<void>;
  interpretPrompt: () => Promise<void>;
  confirmRequirements: () => Promise<void>;
  generateBundles: () => Promise<void>;
  setSelectedProposal: (prop: BundleProposal) => void;
  preparePlan: () => Promise<void>;
  approvePlan: () => Promise<void>;
  executeOrder: (injectFailureOfferId?: string) => Promise<void>;
  triggerReplan: (failedOfferId?: string) => Promise<void>;
  resetAll: () => Promise<void>;
  retryLastAction: () => Promise<void>;
}

const DemoContext = createContext<DemoContextType | null>(null);

interface SavedWorkflow {
  promptText?: string;
  budgetDollars?: number;
  participants?: number;
  laptopConnector?: string;
  listeningRequirement?: string;
  deadlineDate?: string;
  requestReference?: string;
}

function savedWorkflow(): SavedWorkflow {
  try { return JSON.parse(sessionStorage.getItem('bundlegraph.workflow') || '{}') as SavedWorkflow; }
  catch { sessionStorage.removeItem('bundlegraph.workflow'); return {}; }
}

export const DemoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [restoredWorkflow] = useState(savedWorkflow);
  const [currentStep, setStep] = useState<ScreenStep>(() => {
    const candidate = window.location.hash.replace('#/', '') as ScreenStep;
    return ['builder', 'review', 'comparison', 'approval', 'execution'].includes(candidate) ? candidate : 'builder';
  });
  const [promptText, setPromptText] = useState(restoredWorkflow.promptText || 'I want to start a 2-person podcast with my USB-C laptop. Budget is $600. We need 2 microphones, headphones, and all necessary cables.');
  const [budgetDollars, setBudgetDollars] = useState(restoredWorkflow.budgetDollars || 600);
  const [participants, setParticipants] = useState(restoredWorkflow.participants || 2);
  const [laptopConnector, setLaptopConnector] = useState(restoredWorkflow.laptopConnector || 'usb-c');
  const [listeningRequirement, setListeningRequirement] = useState(restoredWorkflow.listeningRequirement || 'independent_headphones');
  const [deadlineDate, setDeadlineDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return restoredWorkflow.deadlineDate || d.toISOString().split('T')[0];
  });

  const [presets, setPresets] = useState<PresetScenario[]>(OFFLINE_PRESETS);
  const [activePresetId, setActivePresetId] = useState<string | null>('preset-standard-podcast');
  const [interpretation, setInterpretation] = useState<RequirementInterpretation | null>(null);
  const fixtureMode = frontendRuntime.mode === 'fixture';
  const [confirmedRequirements, setConfirmedRequirements] = useState<ConfirmedRequirements | null>(fixtureMode ? SAMPLE_CONFIRMED_REQ : null);
  const [proposals, setProposals] = useState<BundleProposal[]>(fixtureMode ? [SAMPLE_PROPOSAL] : []);
  const [selectedProposal, setSelectedProposal] = useState<BundleProposal | null>(fixtureMode ? SAMPLE_PROPOSAL : null);
  const [approvalRecord, setApprovalRecord] = useState<ApprovalRecord | null>(null);
  const [executionRecord, setExecutionRecord] = useState<ExecutionRecord | null>(null);
  const [replanResult, setReplanResult] = useState<ReplanResult | null>(null);
  const [authoritativePlan, setAuthoritativePlan] = useState<AuthoritativePlan | null>(null);
  const [evidenceRecords, setEvidenceRecords] = useState<EvidenceRecord[]>([]);
  const [pipelineStage, setPipelineStage] = useState<PipelineStage>('idle');
  const [apiFailure, setApiFailure] = useState<ApiFailure | null>(null);
  const [draftVersion, setDraftVersion] = useState<number | null>(null);
  const [requestReference] = useState(() => restoredWorkflow.requestReference || `req-${crypto.randomUUID()}`);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getPresets().then((data) => {
      if (data && data.length) setPresets(data);
    }).catch(console.warn);
  }, []);

  useEffect(() => {
    window.history.replaceState({}, '', `#/${currentStep}`);
    sessionStorage.setItem('bundlegraph.workflow', JSON.stringify({ promptText, budgetDollars, participants, laptopConnector, listeningRequirement, deadlineDate, requestReference }));
  }, [currentStep, promptText, budgetDollars, participants, laptopConnector, listeningRequirement, deadlineDate, requestReference]);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (currentStep !== 'builder' && !approvalRecord) event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [currentStep, approvalRecord]);

  const captureError = (err: unknown) => {
    const failure = err && typeof err === 'object' && 'reason_code' in err
      ? err as ApiFailure
      : { status: 0, reason_code: 'UNEXPECTED_CLIENT_ERROR', message: String(err) };
    setApiFailure(failure);
    setErrorMessage(`${failure.reason_code}: ${failure.message}`);
  };

  const invalidatePlanState = () => {
    setConfirmedRequirements(null); setProposals([]); setSelectedProposal(null); setAuthoritativePlan(null);
    setEvidenceRecords([]); setApprovalRecord(null); setExecutionRecord(null); setReplanResult(null);
  };

  const loadPreset = async (preset: PresetScenario) => {
    setActivePresetId(preset.id);
    setPromptText(preset.message);
    setBudgetDollars(Math.round(preset.budget_minor / 100));
    setParticipants(preset.participants);
    setLaptopConnector(preset.laptop_connector);
    setListeningRequirement(preset.listening_requirement);
    setApprovalRecord(null);
    setExecutionRecord(null);
    setReplanResult(null);
    setAuthoritativePlan(null);
    setEvidenceRecords([]);
    setApiFailure(null);
    setErrorMessage(null);

    // If it's the trap preset, immediately prepare the review step
    if (preset.id === 'preset-trap-one-input') {
      setIsLoading(true);
      try {
        const interp = await api.interpretRequirements(preset.message);
        setInterpretation(interp);
        setStep('builder');
      } catch (err: unknown) {
        captureError(err);
      } finally {
        setIsLoading(false);
      }
    } else {
      setStep('builder');
    }
  };

  const interpretPrompt = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      invalidatePlanState();
      setPipelineStage('resolving_requirements');
      let interp: RequirementInterpretation;
      if (frontendRuntime.mode === 'authoritative') {
        const result = await api.saveGuidedDraft({ request_reference: requestReference, use_case: promptText, participants, budget_minor: Math.round(budgetDollars * 100), currency: 'USD', laptop_connectors: [laptopConnector], monitoring: listeningRequirement, deadline: new Date(deadlineDate).toISOString() });
        setDraftVersion(result.version);
        interp = { draft: result.draft, explicit_facts: [], suggested_defaults: [], missing_information: result.draft.missing_information, clarification_questions: result.clarification_questions, provider_mode: 'authoritative_guided', version: result.version, can_confirm: result.can_confirm };
      } else {
        interp = await api.interpretRequirements(promptText, requestReference);
        setDraftVersion(interp.version || 1);
      }
      setInterpretation(interp);
      setStep('review');
    } catch (err: unknown) {
      captureError(err);
    } finally {
      setPipelineStage('idle');
      setIsLoading(false);
    }
  };

  const confirmRequirements = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setPipelineStage('resolving_requirements');
      let version = draftVersion;
      if (frontendRuntime.mode === 'authoritative') {
        const updated = await api.saveGuidedDraft({ request_reference: requestReference, use_case: promptText, participants, budget_minor: Math.round(budgetDollars * 100), currency: 'USD', laptop_connectors: [laptopConnector], monitoring: listeningRequirement, deadline: new Date(deadlineDate).toISOString() });
        version = updated.version;
        setDraftVersion(version);
      }
      const confirmed = await api.confirmDraft(requestReference, version || 1);
      setConfirmedRequirements(confirmed);
      await generateBundlesWithReq(confirmed);
    } catch (err: unknown) {
      captureError(err);
      setIsLoading(false);
    }
  };

  const generateBundlesWithReq = async (req: ConfirmedRequirements) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setPipelineStage('discovering_candidates');
      await Promise.resolve();
      setPipelineStage('checking_evidence');
      await Promise.resolve();
      setPipelineStage('evaluating_compatibility');
      await Promise.resolve();
      setPipelineStage('selecting_bundles');
      const res = await api.generateBundlePlans(req);
      if (res.status === 'ok' && res.result.proposals.length > 0) {
        setProposals(res.result.proposals);
        setSelectedProposal(res.result.proposals[0]);
      } else {
        setProposals([]);
        setSelectedProposal(null);
        if (res.reason_codes && res.reason_codes.length > 0) {
          setErrorMessage(`No feasible bundle found: ${res.reason_codes.join(', ')}`);
        }
      }
      setStep('comparison');
    } catch (err: unknown) {
      captureError(err);
    } finally {
      setPipelineStage('complete');
      setIsLoading(false);
    }
  };

  const generateBundles = async () => {
    if (!confirmedRequirements) return;
    await generateBundlesWithReq(confirmedRequirements);
  };

  const preparePlan = async () => {
    if (!selectedProposal || !confirmedRequirements) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setPipelineStage('persisting_plan');
      const plan = await api.persistPlan(confirmedRequirements, selectedProposal.proposal_key);
      setAuthoritativePlan(plan);
      const evidence = await api.getPlanEvidence(plan.plan_id);
      setEvidenceRecords(evidence);
      setStep('approval');
    } catch (err: unknown) {
      captureError(err);
    } finally {
      setPipelineStage('complete');
      setIsLoading(false);
    }
  };

  const approvePlan = async () => {
    if (!authoritativePlan) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const appr = await api.createApproval(authoritativePlan);
      setApprovalRecord(appr);
    } catch (err: unknown) {
      captureError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const executeOrder = async (injectFailureOfferId?: string) => {
    if (!approvalRecord || !selectedProposal) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const exec = await api.simulateExecution({
        approval_id: approvalRecord.approval_id,
        plan_id: approvalRecord.plan_id,
        plan_version: approvalRecord.plan_version,
        amount_minor: approvalRecord.amount_minor,
        currency: approvalRecord.currency,
        inject_failure_offer_id: injectFailureOfferId,
      });
      setExecutionRecord(exec);
      setStep('execution');
      if (exec.execution_status === 'FAILED_MERCHANT_STOCK_OUTAGE' && injectFailureOfferId) {
        await triggerReplan(injectFailureOfferId);
      }
    } catch (err: unknown) {
      captureError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const triggerReplan = async (failedOfferId?: string) => {
    if (!selectedProposal || !confirmedRequirements || !authoritativePlan) return;
    const targetFailed = failedOfferId || 'offer-mic-alpha';
    setIsLoading(true);
    try {
      const replan = await api.replanBundle(authoritativePlan, targetFailed);
      setReplanResult(replan);
      setStep('execution');
      // Invalidate the old approval
      if (approvalRecord) {
        setApprovalRecord({ ...approvalRecord, valid: false, status: 'INVALIDATED_PLAN_MODIFIED' });
      }
    } catch (err: unknown) {
      captureError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const resetAll = async () => {
    setIsLoading(true);
    try {
      await api.resetDemo();
      setStep('builder');
      setActivePresetId('preset-standard-podcast');
      setPromptText('I want to start a 2-person podcast with my USB-C laptop. Budget is $600. We need 2 microphones, headphones, and all necessary cables.');
      setBudgetDollars(600);
      setParticipants(2);
      setLaptopConnector('usb-c');
      setListeningRequirement('independent_headphones');
      setInterpretation(null);
      setConfirmedRequirements(fixtureMode ? SAMPLE_CONFIRMED_REQ : null);
      setProposals(fixtureMode ? [SAMPLE_PROPOSAL] : []);
      setSelectedProposal(fixtureMode ? SAMPLE_PROPOSAL : null);
      setApprovalRecord(null);
      setExecutionRecord(null);
      setReplanResult(null);
      setAuthoritativePlan(null);
      setEvidenceRecords([]);
      setPipelineStage('idle');
      setApiFailure(null);
      setErrorMessage(null);
    } catch (err: unknown) {
      captureError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const retryLastAction = async () => {
    setApiFailure(null);
    setErrorMessage(null);
    if (currentStep === 'builder' || currentStep === 'review') return interpretPrompt();
    if (currentStep === 'comparison') return generateBundles();
    if (currentStep === 'approval' && selectedProposal) return authoritativePlan ? approvePlan() : preparePlan();
    if (currentStep === 'execution' && executionRecord?.failed_offer_id) return triggerReplan(executionRecord.failed_offer_id);
  };

  return (
    <DemoContext.Provider
      value={{
        runtimeMode: frontendRuntime.mode,
        runtimeLabel: frontendRuntime.label,
        currentStep,
        setStep,
        promptText,
        setPromptText: (value) => { setPromptText(value); invalidatePlanState(); },
        budgetDollars,
        setBudgetDollars: (value) => { setBudgetDollars(value); invalidatePlanState(); },
        participants,
        setParticipants: (value) => { setParticipants(value); invalidatePlanState(); },
        laptopConnector,
        setLaptopConnector: (value) => { setLaptopConnector(value); invalidatePlanState(); },
        listeningRequirement,
        setListeningRequirement: (value) => { setListeningRequirement(value); invalidatePlanState(); },
        deadlineDate,
        setDeadlineDate: (value) => { setDeadlineDate(value); invalidatePlanState(); },
        presets,
        activePresetId,
        interpretation,
        confirmedRequirements,
        proposals,
        selectedProposal,
        approvalRecord,
        executionRecord,
        replanResult,
        authoritativePlan,
        evidenceRecords,
        pipelineStage,
        apiFailure,
        isLoading,
        errorMessage,
        loadPreset,
        interpretPrompt,
        confirmRequirements,
        generateBundles,
        setSelectedProposal,
        preparePlan,
        approvePlan,
        executeOrder,
        triggerReplan,
        resetAll,
        retryLastAction,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
};

// oxlint-disable-next-line react/only-export-components -- provider and hook form one state boundary.
export const useDemo = () => {
  const context = useContext(DemoContext);
  if (!context) throw new Error('useDemo must be used within a DemoProvider');
  return context;
};
