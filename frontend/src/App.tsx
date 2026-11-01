import React from 'react';
import { DemoProvider, useDemo } from './store/demoStore';
import { Header } from './components/layout/Header';
import { StepNav } from './components/layout/StepNav';
import { RequestBuilder } from './components/screens/RequestBuilder';
import { RequirementsReview } from './components/screens/RequirementsReview';
import { BundleComparison } from './components/screens/BundleComparison';
import { PlanApproval } from './components/screens/PlanApproval';
import { ExecutionRecovery } from './components/screens/ExecutionRecovery';

const MainView: React.FC = () => {
  const { currentStep } = useDemo();

  return (
    <main className="main-content">
      {currentStep === 'builder' && <RequestBuilder />}
      {currentStep === 'review' && <RequirementsReview />}
      {currentStep === 'comparison' && <BundleComparison />}
      {currentStep === 'approval' && <PlanApproval />}
      {currentStep === 'execution' && <ExecutionRecovery />}
    </main>
  );
};

export const App: React.FC = () => {
  return (
    <DemoProvider>
      <div className="app-container">
        <Header />
        <StepNav />
        <MainView />
        <footer style={{ backgroundColor: 'var(--bg-header)', borderTop: '1px solid var(--border-default)', padding: '0.875rem 1.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--status-emerald)', display: 'inline-block' }} />
                <span>Engine: <strong style={{ color: 'var(--text-primary)' }}>v1.0.4-rc2</strong></span>
              </span>
              <span style={{ borderLeft: '1px solid var(--border-default)', paddingLeft: '1.25rem' }}>
                Deterministic Offline: <strong style={{ color: '#10b981' }}>ENABLED</strong>
              </span>
              <span style={{ borderLeft: '1px solid var(--border-default)', paddingLeft: '1.25rem' }}>
                Solver Latency: <strong style={{ color: 'var(--text-primary)' }}>0.42ms</strong>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Integrated: AG Grid • Bryntum • PayPal SDK v2</span>
              <span className="badge badge-neutral">
                PROD-SIM
              </span>
            </div>
          </div>
        </footer>
      </div>
    </DemoProvider>
  );
};

export default App;
