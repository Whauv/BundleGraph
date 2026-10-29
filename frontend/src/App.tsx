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
        <footer style={{ backgroundColor: '#000000', borderTop: '1px solid #222222', padding: '0.625rem 1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#666666' }}>
          <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#00e575' }} />
                <span>Engine: <strong style={{ color: '#ffffff' }}>v1.0.4-rc2</strong></span>
              </span>
              <span style={{ borderLeft: '1px solid #222222', paddingLeft: '1rem' }}>
                Deterministic Offline: <strong style={{ color: '#00e575' }}>ENABLED</strong>
              </span>
              <span style={{ borderLeft: '1px solid #222222', paddingLeft: '1rem' }}>
                Solver Latency: <strong style={{ color: '#ffffff' }}>0.42ms</strong>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <span style={{ color: '#888888' }}>Integrated: AG Grid • Bryntum • PayPal SDK v2</span>
              <span style={{ padding: '0.1rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #222222', fontSize: '0.625rem', color: '#ffffff', fontWeight: 600 }}>
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
