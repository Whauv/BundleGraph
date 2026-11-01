import React, { useState } from 'react';
import { useDemo } from '../../store/demoStore';
import { 
  ShieldCheck, 
  ArrowLeft, 
  ArrowRight, 
  CreditCard, 
  AlertTriangle, 
  CheckCircle2,
  Lock
} from 'lucide-react';

export const PlanApproval: React.FC = () => {
  const {
    selectedProposal,
    approvalRecord,
    executeOrder,
    setStep,
    isLoading,
  } = useDemo();

  const [simulateFailure, setSimulateFailure] = useState(false);

  const amountDollars = selectedProposal?.cost_breakdown.all_in_total
    ? (selectedProposal.cost_breakdown.all_in_total.amount_minor / 100).toFixed(2)
    : '443.00';

  const handleCheckout = () => {
    if (simulateFailure) {
      executeOrder('offer-mic-alpha');
    } else {
      executeOrder();
    }
  };

  const nameMap: Record<string, string> = {
    'mic-alpha': '(Broadcast Cardioid Dynamic)',
    'mic-phantom': '(Condenser Mic +48V Required)',
    'mic-gamma': '(Dynamic Podcasting Mic)',
    'interface-one': '(1-In / 2-Out USB-C Preamp)',
    'interface-two': '(2-In / 2-Out USB-C Preamp)',
    'headphones-alpha': '(3.5mm TRS Studio Monitor)',
    'headphones-bravo': '(Closed-back Studio Headphones)',
    'xlr-alpha': '(10ft Balanced Studio Cable)',
    'xlr-bravo': '(6ft Balanced XLR Cable)',
  };

  return (
    <div className="screen-container">
      {/* Modern Screen Header */}
      <div className="screen-header">
        <div className="screen-header-left">
          <div className="screen-header-icon">
            <Lock size={20} />
          </div>
          <div>
            <h1 className="screen-title">Stage 4: Cryptographic Plan Binding &amp; Authorization</h1>
            <p className="screen-description">
              Authorize an immutable plan manifest. The authorization token cryptographically binds to this exact version hash and total.
            </p>
          </div>
        </div>

        <div className="screen-header-meta">
          <span className="badge badge-emerald">
            <ShieldCheck size={12} />
            <span>SHA256 Mutation Locked</span>
          </span>
          <span className="badge badge-neutral">
            <span>PayPal Sandbox v2 Bound</span>
          </span>
        </div>
      </div>

      <div className="studio-card">
        <div className="card-header">
          <div className="card-title-group">
            <h2 className="card-title">Manifest Verification &amp; Escrow Pre-Authorization</h2>
            <p className="card-subtitle">
              Any upstream merchant price delta or stock variance revokes this token immediately, ensuring zero unauthorized mutations at checkout.
            </p>
          </div>
          <span className="badge badge-emerald">
            <span>Ready for Capture</span>
          </span>
        </div>

        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Plan Version Lock Summary Grid (4 Boxes) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem' }}>
            <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Durable Plan Reference
              </span>
              <div style={{ fontSize: '1rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {approvalRecord?.plan_id || selectedProposal?.proposal_key || 'plan-v1-8f92'}
              </div>
            </div>

            <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Plan Manifest Version
              </span>
              <div style={{ fontSize: '1rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle2 size={15} style={{ color: 'var(--status-emerald)' }} />
                <span>Version 1.0 (Locked)</span>
              </div>
            </div>

            <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Approval Session Token
              </span>
              <div style={{ fontSize: '1rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {approvalRecord?.approval_id || 'appr-token-bound-v1'}
              </div>
            </div>

            <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Authorized All-In Total
              </span>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span>${amountDollars}</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>USD</span>
              </div>
            </div>
          </div>

          {/* Itemized Order Review Table */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              <span>Itemized Manifest Specifications</span>
            </div>

            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Component &amp; Model ID</th>
                    <th style={{ textAlign: 'center', width: '80px' }}>Qty</th>
                    <th style={{ textAlign: 'right', width: '120px' }}>Unit Price</th>
                    <th style={{ textAlign: 'right', width: '120px' }}>Line Total</th>
                    <th>Fulfillment Source</th>
                  </tr>
                </thead>
                <tbody style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem' }}>
                  {selectedProposal?.line_items.map((item, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--status-emerald)', display: 'inline-block' }} />
                          <span>{item.product_id}</span>
                          <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-sans)', fontSize: '0.75rem', fontWeight: 400 }}>
                            {nameMap[item.product_id] || ''}
                          </span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'center', color: 'var(--text-primary)' }}>
                        {item.quantity}
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>
                        ${(item.unit_price.amount_minor / 100).toFixed(2)}
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--text-primary)', fontWeight: 600 }}>
                        ${(item.merchandise_total.amount_minor / 100).toFixed(2)}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        synthetic-offline-merchant
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Fault Injection Simulator Card */}
          <div className="callout callout-warning" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
              <AlertTriangle size={20} style={{ color: 'var(--status-amber)', flexShrink: 0 }} />
              <div>
                <strong style={{ color: 'var(--status-amber)', fontSize: '0.8125rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
                  Test Recovery Scenario: Simulate Stock Outage:
                </strong>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.2rem', margin: 0 }}>
                  Inject merchant zero-inventory condition on checkout to verify the automatic re-planning flow and dependency preservation.
                </p>
              </div>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)', padding: '0.35rem 0.65rem', backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 'var(--radius-sm)' }}>
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#f59e0b', cursor: 'pointer' }}
              />
              <span>Inject Stock Outage</span>
            </label>
          </div>
        </div>

        {/* Footer Navigation Bar */}
        <div className="card-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setStep('comparison')}
          >
            <ArrowLeft size={16} />
            <span>Back to Bundle Comparison</span>
          </button>

          <button
            type="button"
            className="btn-primary btn-lg"
            onClick={handleCheckout}
            disabled={isLoading}
            style={{ minWidth: '280px' }}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                <span>Authorizing PayPal Sandbox...</span>
              </>
            ) : (
              <>
                <CreditCard size={16} />
                <span>Authorize &amp; Bind Plan (${amountDollars})</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
