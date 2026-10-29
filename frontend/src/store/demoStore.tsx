import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type {
  ApprovalRecord,
  BundleProposal,
  ConfirmedRequirements,
  ExecutionRecord,
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
  
  isLoading: boolean;
  errorMessage: string | null;
  loadPreset: (preset: PresetScenario) => Promise<void>;
  interpretPrompt: () => Promise<void>;
  confirmRequirements: () => Promise<void>;
  generateBundles: () => Promise<void>;
  setSelectedProposal: (prop: BundleProposal) => void;
  approvePlan: () => Promise<void>;
  executeOrder: (injectFailureOfferId?: string) => Promise<void>;
  triggerReplan: (failedOfferId?: string) => Promise<void>;
  resetAll: () => Promise<void>;
}

const DemoContext = createContext<DemoContextType | null>(null);

export const DemoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentStep, setStep] = useState<ScreenStep>('builder');
  const [promptText, setPromptText] = useState(
    'I want to start a 2-person podcast with my USB-C laptop. Budget is $600. We need 2 microphones, headphones, and all necessary cables.',
  );
  const [budgetDollars, setBudgetDollars] = useState(600);
  const [participants, setParticipants] = useState(2);
  const [laptopConnector, setLaptopConnector] = useState('usb-c');
  const [listeningRequirement, setListeningRequirement] = useState('independent_headphones');
  const [deadlineDate, setDeadlineDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().split('T')[0];
  });

  const [presets, setPresets] = useState<PresetScenario[]>(OFFLINE_PRESETS);
  const [activePresetId, setActivePresetId] = useState<string | null>('preset-standard-podcast');
  const [interpretation, setInterpretation] = useState<RequirementInterpretation | null>(null);
  const [confirmedRequirements, setConfirmedRequirements] = useState<ConfirmedRequirements | null>(SAMPLE_CONFIRMED_REQ);
  const [proposals, setProposals] = useState<BundleProposal[]>([SAMPLE_PROPOSAL]);
  const [selectedProposal, setSelectedProposal] = useState<BundleProposal | null>(SAMPLE_PROPOSAL);
  const [approvalRecord, setApprovalRecord] = useState<ApprovalRecord | null>(null);
  const [executionRecord, setExecutionRecord] = useState<ExecutionRecord | null>(null);
  const [replanResult, setReplanResult] = useState<ReplanResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getPresets().then((data) => {
      if (data && data.length) setPresets(data);
    }).catch(console.warn);
  }, []);

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
    setErrorMessage(null);

    // If it's the trap preset, immediately prepare the review step
    if (preset.id === 'preset-trap-one-input') {
      setIsLoading(true);
      try {
        const interp = await api.interpretRequirements(preset.message);
        setInterpretation(interp);
        setStep('builder');
      } catch (err: unknown) {
        setErrorMessage(String(err));
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
      const interp = await api.interpretRequirements(promptText);
      setInterpretation(interp);
      setStep('review');
    } catch (err: unknown) {
      setErrorMessage(String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const confirmRequirements = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const confirmed = await api.confirmRequirements({
        use_case: `${participants}-person podcast`,
        participants,
        budget_minor: Math.round(budgetDollars * 100),
        currency: 'USD',
        laptop_connector: laptopConnector,
        listening_requirement: listeningRequirement,
        deadline: new Date(deadlineDate).toISOString(),
      });
      setConfirmedRequirements(confirmed);
      await generateBundlesWithReq(confirmed);
    } catch (err: unknown) {
      setErrorMessage(String(err));
      setIsLoading(false);
    }
  };

  const generateBundlesWithReq = async (req: ConfirmedRequirements) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
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
      setErrorMessage(String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const generateBundles = async () => {
    if (!confirmedRequirements) return;
    await generateBundlesWithReq(confirmedRequirements);
  };

  const approvePlan = async () => {
    if (!selectedProposal) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const appr = await api.createApproval({
        plan_id: selectedProposal.proposal_key,
        plan_version: '1.0',
        amount_minor: selectedProposal.cost_breakdown.all_in_total?.amount_minor || 44300,
        currency: selectedProposal.cost_breakdown.currency || 'USD',
      });
      setApprovalRecord(appr);
      setStep('approval');
    } catch (err: unknown) {
      setErrorMessage(String(err));
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
      setErrorMessage(String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const triggerReplan = async (failedOfferId?: string) => {
    if (!selectedProposal || !confirmedRequirements) return;
    const targetFailed = failedOfferId || 'offer-mic-alpha';
    setIsLoading(true);
    try {
      const locked = selectedProposal.line_items
        .map((l) => l.offer_id)
        .filter((id) => id !== targetFailed);

      const replan = await api.replanBundle({
        original_proposal: selectedProposal,
        requirements: confirmedRequirements,
        failed_offer_ids: [targetFailed],
        locked_offer_ids: locked,
        plan_id: selectedProposal.proposal_key,
        plan_version: '1.0',
      });
      setReplanResult(replan);
      // Invalidate the old approval
      if (approvalRecord) {
        setApprovalRecord({ ...approvalRecord, valid: false, status: 'INVALIDATED_PLAN_MODIFIED' });
      }
    } catch (err: unknown) {
      setErrorMessage(`Re-planning error: ${err}`);
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
      setConfirmedRequirements(SAMPLE_CONFIRMED_REQ);
      setProposals([SAMPLE_PROPOSAL]);
      setSelectedProposal(SAMPLE_PROPOSAL);
      setApprovalRecord(null);
      setExecutionRecord(null);
      setReplanResult(null);
      setErrorMessage(null);
    } catch (err: unknown) {
      setErrorMessage(String(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <DemoContext.Provider
      value={{
        runtimeMode: frontendRuntime.mode,
        runtimeLabel: frontendRuntime.label,
        currentStep,
        setStep,
        promptText,
        setPromptText,
        budgetDollars,
        setBudgetDollars,
        participants,
        setParticipants,
        laptopConnector,
        setLaptopConnector,
        listeningRequirement,
        setListeningRequirement,
        deadlineDate,
        setDeadlineDate,
        presets,
        activePresetId,
        interpretation,
        confirmedRequirements,
        proposals,
        selectedProposal,
        approvalRecord,
        executionRecord,
        replanResult,
        isLoading,
        errorMessage,
        loadPreset,
        interpretPrompt,
        confirmRequirements,
        generateBundles,
        setSelectedProposal,
        approvePlan,
        executeOrder,
        triggerReplan,
        resetAll,
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
