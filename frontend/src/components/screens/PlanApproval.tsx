import React, { useState } from 'react';
import { useDemo } from '../../store/demoStore';
import { 
  ShieldCheck, 
  ArrowLeft, 
  ArrowRight, 
  CreditCard, 
  AlertTriangle, 
  CheckCircle2
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
          <span style={{ color: '#666666', cursor: 'pointer' }} onClick={() => setStep('comparison')}>3. Comparison &amp; Graph</span>
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
              4
            </span>
            <span>Plan Authorization</span>
          </span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>5. Execution &amp; Recovery</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.625rem' }}>
          <span style={{ color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Binding Protocol:</span>
          <span style={{ padding: '0.15rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #222222', color: '#00e575', fontWeight: 600 }}>
            SHA256_MUTATION_LOCKED
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
                🔒
              </span>
              <span>Cryptographic Plan Binding &amp; Authorization</span>
            </h1>
            <p className="card-subtitle">
              Authorize an immutable plan manifest. The authorization token binds to this exact version hash and total; material merchant deltas invalidate this token.
            </p>
          </div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.25rem 0.6rem',
              borderRadius: '2px',
              backgroundColor: '#111111',
              border: '1px solid #282828',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              color: '#ffffff',
            }}
          >
            <ShieldCheck size={14} style={{ color: '#00e575' }} />
            <span>PayPal Payments v2 Bound</span>
          </div>
        </div>

        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Plan Version Lock Summary Grid (4 Boxes) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
            <div style={{ backgroundColor: '#000000', border: '1px solid #222222', borderRadius: '2px', padding: '0.875rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Durable Plan Reference
              </span>
              <div style={{ fontSize: '0.9375rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: '#ffffff' }}>
                {approvalRecord?.plan_id || selectedProposal?.proposal_key || 'plan-v1-8f92'}
              </div>
            </div>

            <div style={{ backgroundColor: '#000000', border: '1px solid #222222', borderRadius: '2px', padding: '0.875rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Plan Manifest Version
              </span>
              <div style={{ fontSize: '0.9375rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <CheckCircle2 size={13} style={{ color: '#00e575' }} />
                <span>Version 1.0 (Locked)</span>
              </div>
            </div>

            <div style={{ backgroundColor: '#000000', border: '1px solid #222222', borderRadius: '2px', padding: '0.875rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Approval Session Token
              </span>
              <div style={{ fontSize: '0.9375rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: '#00e575' }}>
                {approvalRecord?.approval_id || 'appr-token-bound-v1'}
              </div>
            </div>

            <div style={{ backgroundColor: '#000000', border: '1px solid #222222', borderRadius: '2px', padding: '0.875rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Authorized All-In Total
              </span>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#ffffff', display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
                <span>${amountDollars}</span>
                <span style={{ fontSize: '0.6875rem', color: '#888888', fontWeight: 500 }}>USD</span>
              </div>
            </div>
          </div>

          {/* Itemized Order Review Table */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              <span style={{ color: '#444444' }}>#</span>
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
                <tbody style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                  {selectedProposal?.line_items.map((item, idx) => (
                    <tr key={idx} style={{ backgroundColor: idx % 2 === 0 ? '#000000' : '#080808' }}>
                      <td style={{ fontWeight: 600, color: '#ffffff' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#00e575', display: 'inline-block' }} />
                          <span>{item.product_id}</span>
                          <span style={{ color: '#777777', fontFamily: 'var(--font-sans)', fontSize: '0.75rem', fontWeight: 400 }}>
                            {nameMap[item.product_id] || ''}
                          </span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'center', color: '#ffffff' }}>
                        {item.quantity}
                      </td>
                      <td style={{ textAlign: 'right', color: '#aaaaaa' }}>
                        ${(item.unit_price.amount_minor / 100).toFixed(2)}
                      </td>
                      <td style={{ textAlign: 'right', color: '#ffffff', fontWeight: 600 }}>
                        ${(item.merchandise_total.amount_minor / 100).toFixed(2)}
                      </td>
                      <td style={{ color: '#666666', fontSize: '0.6875rem' }}>
                        synthetic-offline-merchant
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Plan Binding Cryptographic Policy Alert */}
          <div
            style={{
              padding: '0.875rem 1rem',
              backgroundColor: '#0a0a0a',
              border: '1px solid #282828',
              borderRadius: '2px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.75rem',
            }}
          >
            <ShieldCheck size={18} style={{ color: '#00e575', flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', fontWeight: 700, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.2rem' }}>
                Plan Binding Policy:
              </div>
              <p style={{ fontSize: '0.8125rem', color: '#888888', lineHeight: 1.5, margin: 0 }}>
                The issued approval token is cryptographically bound to the exact offer IDs and price sum. Any upstream merchant price delta or stock variance revokes this token immediately, ensuring zero unauthorized mutations at checkout.
              </p>
            </div>
          </div>

          {/* Fault Injection Simulator Card */}
          <div
            style={{
              padding: '0.875rem 1rem',
              backgroundColor: '#0a0a0a',
              border: '1px solid rgba(250, 188, 69, 0.4)',
              borderRadius: '2px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <AlertTriangle size={18} style={{ color: '#fabc45', flexShrink: 0 }} />
              <div>
                <strong style={{ color: '#fabc45', fontSize: '0.8125rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
                  Failure Injection Simulation:
                </strong>
                <p style={{ fontSize: '0.75rem', color: '#888888', marginTop: '0.15rem', margin: 0 }}>
                  Inject merchant zero-inventory condition on checkout to test the PayPal approval invalidation hook and automatic re-planning flow.
                </p>
              </div>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                style={{ width: '15px', height: '15px', accentColor: '#fabc45', cursor: 'pointer' }}
              />
              <span>Inject Stock Outage</span>
            </label>
          </div>
        </div>

        <div className="card-footer" style={{ borderTop: '1px solid #222222', backgroundColor: '#050505', padding: '1rem 1.25rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setStep('comparison')}
          >
            <ArrowLeft size={14} />
            <span>Back to Bundle Comparison</span>
          </button>

          <button
            type="button"
            className="btn-primary"
            onClick={handleCheckout}
            disabled={isLoading}
            style={{
              padding: '0.55rem 1.25rem',
              fontSize: '0.875rem',
              backgroundColor: '#ffffff',
              color: '#000000',
              minWidth: '260px',
            }}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                <span>Authorizing PayPal Sandbox...</span>
              </>
            ) : (
              <>
                <CreditCard size={14} />
                <span>Authorize &amp; Bind Plan (${amountDollars})</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
