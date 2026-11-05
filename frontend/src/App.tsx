import React, { lazy, Suspense, useEffect, useState } from 'react';
import { AnimatePresence, MotionConfig, motion } from 'motion/react';
import { DemoProvider, useDemo } from './store/demoStore';
import { Header, type Theme } from './components/layout/Header';
import { StepNav } from './components/layout/StepNav';
import { SetupSummary } from './components/layout/SetupSummary';
import { AuthGate } from './components/auth/AuthGate';

const RequestBuilder = lazy(() => import('./components/screens/RequestBuilder').then((module) => ({ default: module.RequestBuilder })));
const RequirementsReview = lazy(() => import('./components/screens/RequirementsReview').then((module) => ({ default: module.RequirementsReview })));
const BundleComparison = lazy(() => import('./components/screens/BundleComparison').then((module) => ({ default: module.BundleComparison })));
const PlanApproval = lazy(() => import('./components/screens/PlanApproval').then((module) => ({ default: module.PlanApproval })));
const ExecutionRecovery = lazy(() => import('./components/screens/ExecutionRecovery').then((module) => ({ default: module.ExecutionRecovery })));

function preferredTheme(): Theme {
  const saved = localStorage.getItem('bundlegraph.theme');
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

const PIPELINE_COPY: Record<string, string> = {
  resolving_requirements: 'Updating your requirements…',
  discovering_candidates: 'Finding candidate equipment…',
  checking_evidence: 'Checking available evidence…',
  evaluating_compatibility: 'Evaluating compatibility…',
  selecting_bundles: 'Selecting complete bundles…',
  persisting_plan: 'Saving the selected plan…',
  complete: 'Latest operation completed.',
  failed: 'The latest operation did not complete.',
  idle: '',
};

const errorTitle = (reason: string) => {
  if (reason === 'CLARIFICATION_REQUIRED') return 'A requirement still needs attention';
  if (reason === 'AUTHENTICATION_REQUIRED') return 'Your session has ended';
  if (reason === 'NETWORK_UNAVAILABLE') return 'BundleGraph could not reach the server';
  if (reason.includes('STALE')) return 'This information is out of date';
  return 'BundleGraph could not complete that action';
};

const Workspace: React.FC<{ theme: Theme; onToggleTheme: () => void }> = ({ theme, onToggleTheme }) => {
  const { currentStep, pipelineStage, apiFailure, failedOperation, retryLastAction, dismissFailure, navigationNotice, runtimeMode } = useDemo();
  return <div className="app-container">
    <Header theme={theme} onToggleTheme={onToggleTheme} />
    <div className="workspace-shell">
      <StepNav />
      <main className="workspace-main" aria-label="Bundle planning workspace">
        {navigationNotice && <div className="status-notice status-notice--neutral" role="status">{navigationNotice}</div>}
        <AnimatePresence initial={false}>
          {pipelineStage !== 'idle' && pipelineStage !== 'complete' && !apiFailure && <motion.div className="operation-status" role="status" aria-live="polite" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}><span className="operation-spinner" aria-hidden="true" />{PIPELINE_COPY[pipelineStage]}</motion.div>}
          {apiFailure && <motion.section className="status-notice status-notice--error" role="alert" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div><strong>{errorTitle(apiFailure.reason_code)}</strong><p>{apiFailure.message}</p></div>
            <div className="notice-actions">{failedOperation && <button type="button" className="btn-secondary" onClick={() => retryLastAction()}>Try again</button>}<button type="button" className="btn-ghost" onClick={dismissFailure}>Dismiss</button></div>
            <details className="technical-details"><summary>Technical details</summary><dl><div><dt>Reason code</dt><dd>{apiFailure.reason_code}</dd></div><div><dt>HTTP status</dt><dd>{apiFailure.status || 'No response'}</dd></div>{apiFailure.correlation_id && <div><dt>Correlation ID</dt><dd>{apiFailure.correlation_id}</dd></div>}</dl></details>
          </motion.section>}
        </AnimatePresence>
        <section className="workspace-content">
          <Suspense fallback={<div className="loading-screen" role="status">Loading workspace…</div>}>
            {currentStep === 'builder' && <RequestBuilder />}
            {currentStep === 'review' && <RequirementsReview />}
            {currentStep === 'comparison' && <BundleComparison />}
            {currentStep === 'approval' && <PlanApproval />}
            {currentStep === 'execution' && <ExecutionRecovery />}
          </Suspense>
        </section>
      </main>
      <SetupSummary />
    </div>
    <footer className="app-footer">{runtimeMode === 'fixture' ? 'Synthetic equipment data and simulated actions are clearly labeled. No provider or payment calls are made.' : 'Connected application state is supplied by the authenticated server.'}</footer>
  </div>;
};

export const App: React.FC = () => {
  const [theme, setTheme] = useState<Theme>(preferredTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    localStorage.setItem('bundlegraph.theme', theme);
  }, [theme]);
  return <MotionConfig reducedMotion="user" transition={{ duration: 0.16, ease: 'easeOut' }}>
    <AuthGate><DemoProvider><Workspace theme={theme} onToggleTheme={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')} /></DemoProvider></AuthGate>
  </MotionConfig>;
};

export default App;
