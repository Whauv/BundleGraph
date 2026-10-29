
import React, { lazy, Suspense, useState } from 'react';
import { useDemo } from '../../store/demoStore';
import { ScheduleTimeline } from '../timeline/ScheduleTimeline';
import { 
  Table, 
  Share2, 
  Calendar, 
  ArrowLeft, 
  ArrowRight, 
  AlertOctagon, 
  CheckCircle2, 
  ShieldCheck, 
  Lock,
  Layers
} from 'lucide-react';

const BundleGrid = lazy(() => import('../grid/BundleGrid').then((module) => ({ default: module.BundleGrid })));
const EvidenceGraph = lazy(() => import('../graph/EvidenceGraph').then((module) => ({ default: module.EvidenceGraph })));

export const BundleComparison: React.FC = () => {
  const {
    proposals,
    selectedProposal,
    budgetDollars,
    approvePlan,
    setStep,
    errorMessage,
    isLoading,
  } = useDemo();

  const [activeTab, setActiveTab] = useState<'grid' | 'graph' | 'timeline'>('grid');

  if (errorMessage && proposals.length === 0) {
    return (
      <div className="screen-container" style={{ gap: '1rem' }}>
        {/* Pipeline Breadcrumb Ribbon */}
        <div
          style={{
            width: '100%',
            backgroundColor: '#0a0a0a',
            border: '1px solid #222222',
            padding: '0.5rem 0.875rem',
            borderRadius: '2px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
            <span style={{ color: '#666666', cursor: 'pointer' }} onClick={() => setStep('builder')}>1. Request Builder</span>
            <span style={{ color: '#333333' }}>/</span>
            <span style={{ color: '#666666', cursor: 'pointer' }} onClick={() => setStep('review')}>2. Requirements Review</span>
            <span style={{ color: '#333333' }}>/</span>
            <span style={{ padding: '0.25rem 0.6rem', backgroundColor: '#260507', border: '1px solid rgba(255, 85, 85, 0.4)', borderRadius: '2px', color: '#ff5555', fontWeight: 600 }}>
              3. Verification Rejection
            </span>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#ff5555', fontWeight: 600 }}>
            SOLVER_FAILED_CONSTRAINT_R2
          </span>
        </div>

        <div className="studio-card">
          <div className="card-header">
            <div className="card-title-group">
              <h1 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '2px',
                    backgroundColor: '#260507',
                    border: '1px solid rgba(255, 85, 85, 0.4)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    color: '#ff5555',
                  }}
                >
                  ✕
                </span>
                <span>Deterministic Verification Rejection</span>
              </h1>
              <p className="card-subtitle">
                Constraint satisfaction solver completed with non-zero unsatisfied physical rules.
              </p>
            </div>
            <span className="badge badge-rose">
              Physical Incompatibility
            </span>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="callout callout-error">
              <AlertOctagon size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ display: 'block', marginBottom: '0.25rem', color: '#ff5555', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  No Feasible Hardware Bundle Exists Under Stated Constraints:
                </strong>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', marginBottom: '0.5rem', color: '#ffffff' }}>
                  {errorMessage}
                </p>
                <p style={{ fontSize: '0.75rem', color: '#ffb4ab', lineHeight: 1.5 }}>
                  <strong>Failure Diagnosis:</strong> In a 2-person podcast scenario, an audio interface with only 1 XLR input violates Rule R2 (Input Capacity). Unconstrained LLMs frequently recommend such bundles; BundleGraph strictly verifies physical compatibility to avoid unworkable purchases.
                </p>
              </div>
            </div>

            <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)' }}>
                Recommended Recovery Actions:
              </div>
              <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8125rem', color: '#cccccc', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <li>Upgrade budget to allow 2-input interface (e.g. Synthetic Interface Two @ $149).</li>
                <li>Reduce participant count to 1 if solo host recording.</li>
                <li>Select a multi-channel USB mixer alternative from the verified catalog.</li>
              </ul>
            </div>
          </div>

          <div className="card-footer" style={{ borderTop: '1px solid #222222', backgroundColor: '#050505', padding: '1rem 1.25rem' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setStep('review')}
            >
              <ArrowLeft size={14} />
              <span>Adjust Constraints</span>
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setStep('builder')}
              style={{ backgroundColor: '#ffffff', color: '#000000' }}
            >
              <span>Reset Setup Parameters</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const allInNum = selectedProposal?.cost_breakdown.all_in_total
    ? selectedProposal.cost_breakdown.all_in_total.amount_minor / 100
    : 443.00;
  const allInCost = `$${allInNum.toFixed(2)}`;
  const headroom = (budgetDollars - allInNum).toFixed(2);

  return (
    <div className="screen-container" style={{ gap: '1rem' }}>
      {/* Pipeline Breadcrumb Ribbon */}
      <div
        style={{
          width: '100%',
          backgroundColor: '#0a0a0a',
          border: '1px solid #222222',
          padding: '0.5rem 0.875rem',
          borderRadius: '2px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
          <span style={{ color: '#666666', cursor: 'pointer' }} onClick={() => setStep('builder')}>1. Request Builder</span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666', cursor: 'pointer' }} onClick={() => setStep('review')}>2. Requirements Review</span>
          <span style={{ color: '#333333' }}>/</span>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.25rem 0.6rem',
              backgroundColor: '#141414',
              border: '1px solid #333333',
              borderRadius: '2px',
              color: '#ffffff',
              fontWeight: 600,
            }}
          >
            <span
              style={{
                width: '16px',
                height: '16px',
                borderRadius: '2px',
                backgroundColor: '#ffffff',
                color: '#000000',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.625rem',
              }}
            >
              3
            </span>
            <span>Comparison &amp; Graph</span>
          </span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>4. Plan Authorization</span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>5. Execution &amp; Recovery</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.625rem' }}>
          <span style={{ color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Solver Run:</span>
          <span style={{ padding: '0.15rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #222222', color: '#00e575', fontWeight: 600 }}>
            SOLVER_RUN_0x8F92
          </span>
        </div>
      </div>

      <div className="studio-card">
        <div className="card-header">
          <div className="card-title-group">
            <h1 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '2px',
                  backgroundColor: '#161616',
                  border: '1px solid #333333',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: '#ffffff',
                }}
              >
                ⚯
              </span>
              <span>Bundle Candidate Verification &amp; Topology Analysis</span>
            </h1>
            <p className="card-subtitle">
              Inspect candidate compatibility, topological signal routing graphs, integer minor-unit pricing, and delivery timelines.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span className="badge badge-emerald">
              <CheckCircle2 size={12} />
              Fully Verified
            </span>
            <span className="badge badge-sandbox">
              <ShieldCheck size={12} />
              USD Minor Units
            </span>
          </div>
        </div>

        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* 4-Box Telemetry / Proposal Summary Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
            <div className="surface-panel" style={{ padding: '0.75rem 1rem' }}>
              <div style={{ fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Candidate Bundles Evaluated
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: '#ffffff', fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                3 Options (Alpha, Beta, Gamma)
              </div>
            </div>

            <div className="surface-panel" style={{ padding: '0.75rem 1rem' }}>
              <div style={{ fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Target Budget
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: '#ffffff', fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                ${(budgetDollars).toFixed(2)} USD
              </div>
            </div>

            <div className="surface-panel" style={{ padding: '0.75rem 1rem' }}>
              <div style={{ fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Candidate Total
              </div>
              <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff', fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                {allInCost} USD
              </div>
            </div>

            <div className="surface-panel" style={{ padding: '0.75rem 1rem' }}>
              <div style={{ fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Delta to Budget
              </div>
              <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#00e575', fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                +${headroom} Headroom
              </div>
            </div>
          </div>

          {/* View Switcher Segmented Tabs */}
          <div style={{ display: 'flex', gap: '0.35rem', borderBottom: '1px solid #222222', paddingBottom: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className={`preset-btn ${activeTab === 'grid' ? 'active' : ''}`}
              onClick={() => setActiveTab('grid')}
            >
              <Table size={13} />
              <span>Hardware Manifest (AG Grid)</span>
            </button>
            <button
              type="button"
              className={`preset-btn ${activeTab === 'graph' ? 'active' : ''}`}
              onClick={() => setActiveTab('graph')}
            >
              <Share2 size={13} />
              <span>DAG Routing Topology</span>
            </button>
            <button
              type="button"
              className={`preset-btn ${activeTab === 'timeline' ? 'active' : ''}`}
              onClick={() => setActiveTab('timeline')}
            >
              <Calendar size={13} />
              <span>Bryntum Delivery Schedule</span>
            </button>
          </div>

          {/* Active Tab View */}
          <div>
            <Suspense fallback={<div className="empty-state" role="status">Loading comparison view…</div>}>
              {activeTab === 'grid' && <BundleGrid proposal={selectedProposal} />}
              {activeTab === 'graph' && <EvidenceGraph report={selectedProposal?.compatibility_report} />}
              {activeTab === 'timeline' && <ScheduleTimeline deadlineDays={7} isDelayed={false} />}
            </Suspense>
          </div>
        </div>

        <div className="card-footer" style={{ borderTop: '1px solid #222222', backgroundColor: '#050505', padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#888888' }}>
            <Layers size={14} style={{ color: '#00e575' }} />
            <span>Selected Candidate: <strong style={{ color: '#ffffff' }}>{selectedProposal?.proposal_key || 'bundle-opt-alpha-complete'}</strong></span>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={approvePlan}
            disabled={isLoading || !selectedProposal}
            style={{
              padding: '0.55rem 1.25rem',
              fontSize: '0.875rem',
              backgroundColor: '#ffffff',
              color: '#000000',
            }}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                <span>Preparing Plan Binding...</span>
              </>
            ) : (
              <>
                <Lock size={13} />
                <span>Lock Plan &amp; Proceed to Authorization</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
