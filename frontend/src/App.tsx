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
      <Suspense fallback={<div className="screen-container" role="status">Loading interface…</div>}>
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
    <footer style={{ backgroundColor: '#000000', borderTop: '1px solid #222222', padding: '0.625rem 1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#666666' }}>
      <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <span>BundleGraph · deterministic compatibility presentation</span>
        <span style={{ color: runtimeMode === 'fixture' ? '#fabc45' : '#00e575' }}>
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
