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
  GitCompare,
  RotateCcw
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
      <div className="screen-container">
        {/* Rejection Header */}
        <div className="screen-header">
          <div className="screen-header-left">
            <div className="screen-header-icon" style={{ borderColor: 'var(--status-rose-border)', color: 'var(--status-rose)' }}>
              <AlertOctagon size={20} />
            </div>
            <div>
              <h1 className="screen-title" style={{ color: '#fca5a5' }}>Deterministic Solver Verification Rejection</h1>
              <p className="screen-description">
                Physical constraint solver completed with non-zero unsatisfied compatibility rules.
              </p>
            </div>
          </div>

          <div className="screen-header-meta">
            <span className="badge badge-rose">
              SOLVER_FAILED_CONSTRAINT_R2
            </span>
          </div>
        </div>

        <div className="studio-card">
          <div className="card-header">
            <div className="card-title-group">
              <h2 className="card-title">Hardware Topology Verification Failure</h2>
              <p className="card-subtitle">
                Constraint satisfaction solver rejected candidate combinations because physical requirements cannot be met under current parameters.
              </p>
            </div>
            <span className="badge badge-rose">
              Physical Incompatibility
            </span>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="callout callout-error">
              <AlertOctagon size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--status-rose)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  No Feasible Hardware Bundle Exists Under Stated Constraints:
                </strong>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                  {errorMessage}
                </p>
                <p style={{ fontSize: '0.8125rem', color: '#fca5a5', lineHeight: 1.5, margin: 0 }}>
                  <strong>Failure Diagnosis:</strong> In a 2-person podcast scenario, an audio interface with only 1 XLR input violates Rule R2 (Input Capacity). Unconstrained LLMs frequently recommend such bundles; BundleGraph strictly verifies physical compatibility to avoid unworkable purchases.
                </p>
              </div>
            </div>

            <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'var(--font-mono)' }}>
                Recommended Recovery Actions:
              </div>
              <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <li>Upgrade budget to allow 2-input interface (e.g. Synthetic Interface Two @ $149).</li>
                <li>Reduce participant count to 1 if solo host recording.</li>
                <li>Select a multi-channel USB mixer alternative from the verified catalog.</li>
              </ul>
            </div>
          </div>

          <div className="card-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setStep('review')}
            >
              <ArrowLeft size={16} />
              <span>Adjust Constraints</span>
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setStep('builder')}
            >
              <RotateCcw size={14} />
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
    <div className="screen-container">
      {/* Modern Screen Header */}
      <div className="screen-header">
        <div className="screen-header-left">
          <div className="screen-header-icon">
            <GitCompare size={20} />
          </div>
          <div>
            <h1 className="screen-title">Stage 3: Bundle Candidate Comparison &amp; Topology Graph</h1>
            <p className="screen-description">
              Compare deterministic bundle proposals, inspect DAG signal routing, and verify shipping schedules.
            </p>
          </div>
        </div>

        <div className="screen-header-meta">
          <span className="badge badge-emerald">
            <CheckCircle2 size={12} />
            <span>Fully Verified</span>
          </span>
          <span className="badge badge-neutral">
            <span>Solver Run: 0x8F92</span>
          </span>
        </div>
      </div>

      <div className="studio-card">
        <div className="card-header">
          <div className="card-title-group">
            <h2 className="card-title">Bundle Proposals &amp; Verification Topology</h2>
            <p className="card-subtitle">
              Inspect candidate compatibility, topological signal routing graphs, integer minor-unit pricing, and delivery timelines.
            </p>
          </div>
          <div className="badge badge-neutral">
            <ShieldCheck size={12} />
            <span>USD Minor Units</span>
          </div>
        </div>

        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* 4-Box Telemetry / Proposal Summary Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem' }}>
            <div className="surface-panel">
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Candidate Bundles Evaluated
              </div>
              <div style={{ fontSize: '1.0625rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: '0.35rem' }}>
                3 Options (Alpha, Beta, Gamma)
              </div>
            </div>

            <div className="surface-panel">
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Target Budget
              </div>
              <div style={{ fontSize: '1.0625rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: '0.35rem' }}>
                ${(budgetDollars).toFixed(2)} USD
              </div>
            </div>

            <div className="surface-panel">
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Candidate Total
              </div>
              <div style={{ fontSize: '1.1875rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: '0.35rem' }}>
                {allInCost} USD
              </div>
            </div>

            <div className="surface-panel">
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Budget Headroom
              </div>
              <div style={{ fontSize: '1.1875rem', fontWeight: 700, color: 'var(--status-emerald)', fontFamily: 'var(--font-mono)', marginTop: '0.35rem' }}>
                +${headroom} Available
              </div>
            </div>
          </div>

          {/* View Switcher Segmented Control */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', borderBottom: '1px solid var(--border-default)', paddingBottom: '0.875rem' }}>
            <div className="segmented-control" role="tablist" aria-label="Comparison views">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'grid'}
                className={`segmented-tab ${activeTab === 'grid' ? 'active' : ''}`}
                onClick={() => setActiveTab('grid')}
              >
                <Table size={14} />
                <span>Hardware Manifest (AG Grid)</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'graph'}
                className={`segmented-tab ${activeTab === 'graph' ? 'active' : ''}`}
                onClick={() => setActiveTab('graph')}
              >
                <Share2 size={14} />
                <span>DAG Routing Topology</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'timeline'}
                className={`segmented-tab ${activeTab === 'timeline' ? 'active' : ''}`}
                onClick={() => setActiveTab('timeline')}
              >
                <Calendar size={14} />
                <span>Bryntum Delivery Schedule</span>
              </button>
            </div>

            <div className="badge badge-neutral">
              <span>SKUs: {selectedProposal?.line_items?.length || 5} Verified Items</span>
            </div>
          </div>

          {/* Active Tab View with Suspense */}
          <div style={{ minHeight: '380px' }}>
            <Suspense fallback={<div className="surface-panel" role="status" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading view…</div>}>
              {activeTab === 'grid' && <BundleGrid proposal={selectedProposal} />}
              {activeTab === 'graph' && <EvidenceGraph report={selectedProposal?.compatibility_report} />}
              {activeTab === 'timeline' && <ScheduleTimeline deadlineDays={7} isDelayed={false} />}
            </Suspense>
          </div>
        </div>

        {/* Footer Navigation Bar */}
        <div className="card-footer">
          <div className="button-group">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setStep('review')}
            >
              <ArrowLeft size={16} />
              <span>Back to Constraints</span>
            </button>
          </div>

          <button
            type="button"
            className="btn-primary btn-lg"
            onClick={approvePlan}
            disabled={isLoading || !selectedProposal}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                <span>Preparing Plan Binding...</span>
              </>
            ) : (
              <>
                <Lock size={15} />
                <span>Lock Plan &amp; Proceed to Authorization</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
