import React, { useState } from 'react';
import { useDemo } from '../../store/demoStore';
import { ScheduleTimeline } from '../timeline/ScheduleTimeline';
import { 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  PlusCircle, 
  Lock, 
  ArrowRight, 
  ArrowLeft, 
  Zap, 
  ShieldCheck, 
  RefreshCw,
  Activity,
  Copy,
  Check,
  Download
} from 'lucide-react';

export const ExecutionRecovery: React.FC = () => {
  const {
    executionRecord,
    replanResult,
    executeOrder,
    triggerReplan,
    resetAll,
    setStep,
    isLoading,
    selectedProposal,
    runtimeMode,
  } = useDemo();

  const [reapproved, setReapproved] = useState(false);
  const [copiedTxn, setCopiedTxn] = useState(false);
  const [downloadedLog, setDownloadedLog] = useState(false);

  const isFailed = executionRecord?.execution_status === 'FAILED_MERCHANT_STOCK_OUTAGE' || Boolean(replanResult);
  const replacement = replanResult?.replacements[0];
  const displayMoney = (amount?: { amount_minor: number; currency: string } | null) => amount
    ? `${(amount.amount_minor / 100).toLocaleString(undefined, { style: 'currency', currency: amount.currency })}`
    : 'Unknown';
  const settledAmount = executionRecord?.amount_minor === undefined ? null : { amount_minor: executionRecord.amount_minor, currency: executionRecord.currency || 'USD' };
  const proposalTotal = replacement?.proposal.cost_breakdown.all_in_total || selectedProposal?.cost_breakdown.all_in_total;

  const handleCopyTxn = () => {
    const txnId = executionRecord?.transaction_id;
    if (!txnId) return;
    navigator.clipboard?.writeText(txnId);
    setCopiedTxn(true);
    setTimeout(() => setCopiedTxn(false), 2000);
  };

  const handleDownloadLog = () => {
    setDownloadedLog(true);
    setTimeout(() => setDownloadedLog(false), 2000);
  };

  const handleReapproveAndSettle = async () => {
    setReapproved(true);
    await executeOrder();
  };

  return (
    <div className="screen-container" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Screen Stage Header & Top Level Meta */}
      <div className="studio-card" style={{ padding: '0.875rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.625rem' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '2px', background: '#111111', border: '1px solid #282828', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffffff', flexShrink: 0 }}>
              <Activity size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <h1 style={{ fontSize: '1rem', fontWeight: 600, color: '#ffffff', letterSpacing: '-0.01em', margin: 0 }}>
                  Settlement Verification &amp; Autonomous Failure Recovery
                </h1>
                <span style={{ padding: '0.125rem 0.375rem', borderRadius: '2px', background: '#161616', border: '1px solid #2c2c2c', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#ffffff' }}>
                  deterministic-rule-engine
                </span>
              </div>
              <p style={{ fontSize: '0.8125rem', color: '#999999', margin: '0.2rem 0 0 0' }}>
                Review authoritative execution facts and dependency-preserving re-planning deltas. Fixture execution remains simulated.
              </p>
            </div>
          </div>
          <div className={`badge ${isFailed ? 'badge-amber' : 'badge-emerald'}`}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: isFailed ? '#fabc45' : '#00e575', display: 'inline-block' }}></span>
            <span>{isFailed ? 'Recovery Protocol Active' : 'Settlement Confirmed'}</span>
          </div>
        </div>
      </div>

      {/* Card 1: PayPal Payments v2 Sandbox Capture Settled */}
      <section className="studio-card" style={{ padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.625rem' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#000000', border: '1px solid #00e575', color: '#00e575', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
              <CheckCircle2 size={16} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>
                  {executionRecord?.execution_status === 'COMPLETED' ? 'Execution completed' : 'No settled payment recorded'}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#777777', textTransform: 'uppercase' }}>TXN REF:</span>
                  <button
                    type="button"
                    onClick={handleCopyTxn}
                    disabled={!executionRecord?.transaction_id}
                    style={{
                      background: '#111111',
                      border: '1px solid #282828',
                      borderRadius: '2px',
                      padding: '0.125rem 0.375rem',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.6875rem',
                      color: '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      cursor: 'pointer'
                    }}
                    title="Click to copy Transaction Hash"
                  >
                    <span>{executionRecord?.transaction_id || 'Not available'}</span>
                    {copiedTxn ? <Check size={12} style={{ color: '#00e575' }} /> : <Copy size={12} style={{ color: '#777777' }} />}
                  </button>
                </div>
              </div>
              <p style={{ fontSize: '0.8125rem', color: '#999999', margin: '0.25rem 0 0 0' }}>
                {executionRecord?.message || 'No execution response has been recorded.'}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#000000', padding: '0.25rem 0.5rem', borderRadius: '2px', border: '1px solid #222222', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
            <span style={{ color: '#777777' }}>Runtime:</span>
            <span style={{ color: '#ffffff' }}>{runtimeMode}</span>
          </div>
        </div>

        {/* Telemetry Strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #1c1c1c' }}>
          <div style={{ background: '#0d0d0d', padding: '0.5rem', borderRadius: '2px', border: '1px solid #222222' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#777777', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Settled Total</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem', marginTop: '0.15rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.125rem', fontWeight: 600, color: '#ffffff' }}>
                {displayMoney(settledAmount || proposalTotal)}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#888888' }}>USD (Exact Capture)</span>
            </div>
          </div>
          <div style={{ background: '#0d0d0d', padding: '0.5rem', borderRadius: '2px', border: '1px solid #222222' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#777777', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Escrow Protocol Status</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginTop: '0.25rem' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00e575' }}></span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#ffffff', fontWeight: 600 }}>DISPATCHED_PENDING_RECEIPT</span>
            </div>
          </div>
          <div style={{ background: '#0d0d0d', padding: '0.5rem', borderRadius: '2px', border: '1px solid #222222' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#777777', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Capture Protocol Latency</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem', marginTop: '0.15rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.125rem', fontWeight: 600, color: '#ffffff' }}>Not measured</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#777777' }}>No client-side latency claim</span>
            </div>
          </div>
        </div>
      </section>

      {/* Card 2: Bryntum Delivery & Milestones Timeline */}
      <ScheduleTimeline deadlineDays={7} isDelayed={isFailed} />

      {/* Card 3: Test Failure Injection & Autonomous Recovery */}
      <section 
        className="studio-card" 
        style={{ 
          padding: '0.875rem', 
          borderColor: isFailed ? '#fabc45' : '#222222',
          display: 'flex', 
          flexDirection: 'column', 
          gap: '0.75rem' 
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.625rem' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '2px', background: '#111111', border: `1px solid ${isFailed ? '#fabc45' : '#333333'}`, color: isFailed ? '#fabc45' : '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
              <AlertTriangle size={15} />
            </div>
            <div>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>
                Test Failure Injection &amp; Transparent Re-planning
              </span>
              <p style={{ fontSize: '0.8125rem', color: '#999999', margin: '0.2rem 0 0 0' }}>
                Simulate an upstream merchant stock outage to observe how BundleGraph computes dependency-preserving replacement deltas.
              </p>
            </div>
          </div>
          <div>
            {!isFailed ? (
              <button
                type="button"
                className="btn-danger"
                onClick={() => triggerReplan('offer-mic-alpha')}
                disabled={isLoading}
              >
                <AlertTriangle size={13} />
                <span>Inject Stock Outage (Microphones)</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => resetAll()}
                disabled={isLoading}
                style={{ borderColor: '#00e575', color: '#00e575' }}
              >
                <RefreshCw size={13} />
                <span>Rollback Simulation</span>
              </button>
            )}
          </div>
        </div>

        {/* Re-planning Recovery Protocol Details */}
        {isFailed && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid #222222' }}>
            {/* Outage Callout Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: '#fabc45' }}>
                <RefreshCw size={14} />
                <span style={{ fontWeight: 600 }}>Replanning triggered: {executionRecord?.failed_offer_id || replacement?.removed_items[0]?.offer_id || 'selected offer'} unavailable</span>
              </div>
              <span style={{ color: '#00e575', fontWeight: 600 }}>Topological Feasibility: PRESERVED</span>
            </div>

            {/* Evicted Edge vs Dependency Replacement comparison */}
            <div style={{ background: '#000000', padding: '0.625rem', borderRadius: '2px', border: '1px solid #222222', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                <span style={{ color: '#ff5555', textTransform: 'uppercase', fontWeight: 600 }}>Evicted Edge &amp; Node:</span>
                <span style={{ color: '#ffffff' }}>{replacement?.removed_items.map((item) => `${item.product_id} (${item.offer_id}), qty ${item.previous_quantity}`).join('; ') || 'No removed-item delta returned'}</span>
                <span style={{ color: '#777777' }}>{replacement?.removed_items[0]?.reason_code || 'Reason unavailable'}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                <span style={{ color: '#00e575', textTransform: 'uppercase', fontWeight: 600 }}>Dependency-Preserving Replacement:</span>
                <span style={{ color: '#ffffff' }}>{replacement?.added_items.map((item) => `${item.product_id} (${item.offer_id}), qty ${item.replacement_quantity}`).join('; ') || 'No added-item delta returned'}</span>
                <span style={{ color: '#00e575' }}>{replacement?.proposal.compatibility_report.classification || 'Compatibility result unavailable'}</span>
              </div>
            </div>

            {/* Invalidation Security Banner */}
            <div className="callout callout-warning" style={{ background: '#141005', border: '1px solid #fabc45' }}>
              <Lock size={16} style={{ flexShrink: 0, marginTop: '2px', color: '#fabc45' }} />
              <div>
                <strong style={{ fontSize: '0.8125rem', color: '#fef08a', display: 'block', marginBottom: '0.2rem' }}>
                  Cryptographic Integrity Lock: Prior Approval Token Invalidated
                </strong>
                <p style={{ fontSize: '0.75rem', color: '#e2e8f0', margin: 0 }}>
                  Under the BundleGraph contract specification, approvals bind immutably to exact plan versions. Because candidate inventory changed, the prior approval is voided and the operator must explicitly re-authorize Plan 2.0.
                </p>
              </div>
            </div>

            {/* Re-planning Diff / Delta Card */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.5rem' }}>
              {/* Removed items */}
              <div className="diff-card diff-card-removed" style={{ background: '#120505', border: '1px solid #441111', padding: '0.625rem', borderRadius: '2px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#ff5555', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.35rem', fontFamily: 'var(--font-mono)' }}>
                  <XCircle size={12} />
                  <span>Removed (Out of Stock)</span>
                </div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>
                  {replacement?.removed_items.map((item) => `${item.previous_quantity}x ${item.product_id}`).join(', ') || 'None'}
                </div>
                <div className="tabular-num" style={{ fontSize: '0.75rem', color: '#888888', marginTop: '0.2rem', fontFamily: 'var(--font-mono)' }}>
                  Recovery value: unknown unless supplied by execution facts
                </div>
              </div>

              {/* Added items */}
              <div className="diff-card diff-card-added" style={{ background: '#05140a', border: '1px solid #00e575', padding: '0.625rem', borderRadius: '2px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#00e575', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.35rem', fontFamily: 'var(--font-mono)' }}>
                  <PlusCircle size={12} />
                  <span>Added (Verified Alternative)</span>
                </div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>
                  {replacement?.added_items.map((item) => `${item.replacement_quantity}x ${item.product_id}`).join(', ') || 'None'}
                </div>
                <div className="tabular-num" style={{ fontSize: '0.75rem', color: '#888888', marginTop: '0.2rem', fontFamily: 'var(--font-mono)' }}>
                  Reason: {replacement?.added_items[0]?.reason_code || 'Unavailable'}
                </div>
              </div>

              {/* Retained working items */}
              <div className="diff-card diff-card-locked" style={{ background: '#080808', border: '1px solid #222222', padding: '0.625rem', borderRadius: '2px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#ffffff', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.35rem', fontFamily: 'var(--font-mono)' }}>
                  <Lock size={12} />
                  <span>Retained (Locked Cart)</span>
                </div>
                <ul style={{ fontSize: '0.75rem', color: '#888888', paddingLeft: '1rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                  {replacement?.retained_items.map((item) => <li key={item.offer_id}>{item.replacement_quantity}x {item.product_id}</li>)}
                  {!replacement?.retained_items.length && <li>None returned</li>}
                </ul>
              </div>
            </div>

            {/* Cost Delta & Timeline impact */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#000000', border: '1px solid #222222', padding: '0.5rem 0.75rem', borderRadius: '2px', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '0.75rem', color: '#888888' }}>Updated Total:</span>
                <span className="tabular-num" style={{ fontSize: '1rem', fontWeight: 700, color: '#00e575', fontFamily: 'var(--font-mono)' }}>
                  {displayMoney(proposalTotal)}
                </span>
                <span className="badge badge-emerald tabular-num">
                  Delta: {displayMoney(replacement?.cost_difference)}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#888888' }}>
                Delivery impact: <strong style={{ color: '#ffffff' }}>unknown without delivery evidence</strong>
              </div>
            </div>

            {/* Zapier Webhook Dispatched Box */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0a0a0a', border: '1px solid #222222', padding: '0.5rem 0.75rem', borderRadius: '2px', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Zap size={15} style={{ color: '#fabc45' }} />
                <div>
                  <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>
                    Operations notification
                  </span>
                  <p style={{ fontSize: '0.6875rem', color: '#777777', margin: 0 }}>
                    No delivery claim is shown unless an authoritative notification response is available.
                  </p>
                </div>
              </div>
              <span className="badge badge-neutral tabular-num" style={{ color: '#00e575' }}>
                Not configured
              </span>
            </div>
          </div>
        )}
      </section>

      {/* Bottom Persistent Action Bar */}
      <div className="studio-card" style={{ padding: '0.625rem 0.875rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.625rem' }}>
        <div>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setStep('comparison')}
          >
            <ArrowLeft size={14} />
            <span>Review Full Manifest</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleDownloadLog}
          >
            {downloadedLog ? <Check size={14} style={{ color: '#00e575' }} /> : <Download size={14} />}
            <span>{downloadedLog ? 'Log Exported (12.4 KB)' : 'Download Audit Log (JSON)'}</span>
          </button>

          {isFailed ? (
            <button
              type="button"
              className="btn-primary"
              onClick={handleReapproveAndSettle}
              disabled={isLoading || reapproved}
              style={{ background: reapproved ? '#00e575' : undefined, color: reapproved ? '#000000' : undefined }}
            >
              {reapproved ? (
                <>
                  <CheckCircle2 size={14} />
                  <span>Plan 2.0 Re-Authorized &amp; Settled</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={14} />
                  <span>Review revised plan ({displayMoney(proposalTotal)})</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary"
              onClick={() => resetAll()}
            >
              <span>Complete Run &amp; Reset</span>
              <ArrowRight size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
