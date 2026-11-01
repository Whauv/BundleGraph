import React, { lazy, Suspense } from 'react';
import { DemoProvider, useDemo } from './store/demoStore';
import { Header } from './components/layout/Header';
import { StepNav } from './components/layout/StepNav';

const RequestBuilder = lazy(() => import('./components/screens/RequestBuilder').then((module) => ({ default: module.RequestBuilder })));
const RequirementsReview = lazy(() => import('./components/screens/RequirementsReview').then((module) => ({ default: module.RequirementsReview })));
const BundleComparison = lazy(() => import('./components/screens/BundleComparison').then((module) => ({ default: module.BundleComparison })));
const PlanApproval = lazy(() => import('./components/screens/PlanApproval').then((module) => ({ default: module.PlanApproval })));
const ExecutionRecovery = lazy(() => import('./components/screens/ExecutionRecovery').then((module) => ({ default: module.ExecutionRecovery })));

const MainView: React.FC = () => {
  const { currentStep } = useDemo();

  return (
    <main className="main-content">
      <Suspense fallback={<div className="screen-container" role="status" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading interface…</div>}>
        {currentStep === 'builder' && <RequestBuilder />}
        {currentStep === 'review' && <RequirementsReview />}
        {currentStep === 'comparison' && <BundleComparison />}
        {currentStep === 'approval' && <PlanApproval />}
        {currentStep === 'execution' && <ExecutionRecovery />}
      </Suspense>
    </main>
  );
};

const RuntimeFooter: React.FC = () => {
  const { runtimeMode, runtimeLabel } = useDemo();

  return (
    <footer style={{ backgroundColor: 'var(--bg-header)', borderTop: '1px solid var(--border-default)', padding: '0.75rem 1.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: runtimeMode === 'fixture' ? 'var(--status-amber)' : 'var(--status-emerald)', display: 'inline-block' }} />
          <span>BundleGraph · deterministic compatibility presentation</span>
        </div>
        <span style={{ color: runtimeMode === 'fixture' ? 'var(--status-amber)' : 'var(--status-emerald)', fontWeight: 600 }}>
          {runtimeLabel} · {runtimeMode === 'fixture' ? 'no provider, approval, or payment calls' : 'demo endpoints only'}
        </span>
      </div>
    </footer>
  );
};

export const App: React.FC = () => {
  return (
    <DemoProvider>
      <div className="app-container">
        <Header />
        <StepNav />
        <MainView />
        <RuntimeFooter />
      </div>
    </DemoProvider>
  );
};

export default App;
