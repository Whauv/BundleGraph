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
  } = useDemo();

  const [reapproved, setReapproved] = useState(false);
  const [copiedTxn, setCopiedTxn] = useState(false);
  const [downloadedLog, setDownloadedLog] = useState(false);

  const isFailed = executionRecord?.execution_status === 'FAILED_MERCHANT_STOCK_OUTAGE' || Boolean(replanResult);

  const handleCopyTxn = () => {
    const txnId = executionRecord?.transaction_id || 'PAYPAL-TXN-8A92BC34E10F';
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
    <div className="screen-container">
      {/* Modern Screen Header */}
      <div className="screen-header">
        <div className="screen-header-left">
          <div className="screen-header-icon">
            <Activity size={20} />
          </div>
          <div>
            <h1 className="screen-title">Stage 5: Settlement Verification &amp; Autonomous Failure Recovery</h1>
            <p className="screen-description">
              Inspect PayPal sandbox execution status, simulate merchant inventory outages, and review dependency-preserving re-planning deltas.
            </p>
          </div>
        </div>

        <div className="screen-header-meta">
          <div className={`badge ${isFailed ? 'badge-amber' : 'badge-emerald'}`}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: isFailed ? 'var(--status-amber)' : 'var(--status-emerald)', display: 'inline-block' }}></span>
            <span>{isFailed ? 'Recovery Protocol Active' : 'Settlement Confirmed'}</span>
          </div>
          <span className="badge badge-neutral">
            <span>PayPal Sandbox v2</span>
          </span>
        </div>
      </div>

      {/* Card 1: PayPal Payments v2 Sandbox Capture Settled */}
      <section className="studio-card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: 'var(--radius-xs)', background: 'var(--status-emerald-bg)', border: '1px solid var(--status-emerald-border)', color: 'var(--status-emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <CheckCircle2 size={16} />
            </div>
            <div>
              <h2 className="card-title" style={{ fontSize: '1rem' }}>
                PayPal Payments v2 Sandbox Capture Settled
              </h2>
              <p className="card-subtitle">
                Idempotency token bound and verified. Synthetic merchant orders dispatched to inventory fulfillment.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flexWrap: 'wrap' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>TXN ID:</span>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={handleCopyTxn}
              title="Click to copy Transaction Hash"
            >
              <span className="tabular-num">{executionRecord?.transaction_id || 'PAYPAL-TXN-8A92BC34E10F'}</span>
              {copiedTxn ? <Check size={13} style={{ color: 'var(--status-emerald)' }} /> : <Copy size={13} style={{ color: 'var(--text-muted)' }} />}
            </button>
          </div>
        </div>

        {/* Telemetry Strip */}
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem' }}>
            <div className="surface-panel">
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Settled Total</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', marginTop: '0.35rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {isFailed && replanResult ? '$415.00' : '$443.00'}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>USD (Exact Capture)</span>
              </div>
            </div>
            <div className="surface-panel">
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Escrow Protocol Status</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.45rem' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-emerald)' }}></span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 600 }}>DISPATCHED_PENDING_RECEIPT</span>
              </div>
            </div>
            <div className="surface-panel">
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Capture Protocol Latency</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', marginTop: '0.35rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>184ms</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>HTTP 201 Created</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Card 2: Bryntum Delivery & Milestones Timeline */}
      <ScheduleTimeline deadlineDays={7} isDelayed={isFailed} />

      {/* Card 3: Test Failure Injection & Autonomous Recovery */}
      <section className="studio-card" style={{ borderColor: isFailed ? 'var(--status-amber-border)' : undefined }}>
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '30px', height: '30px', borderRadius: 'var(--radius-xs)', background: isFailed ? 'var(--status-amber-bg)' : 'var(--bg-card-hover)', border: `1px solid ${isFailed ? 'var(--status-amber-border)' : 'var(--border-default)'}`, color: isFailed ? 'var(--status-amber)' : 'var(--text-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <AlertTriangle size={16} />
            </div>
            <div>
              <h2 className="card-title" style={{ fontSize: '1rem' }}>
                Failure Simulation &amp; Autonomous Re-planning
              </h2>
              <p className="card-subtitle">
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
                <AlertTriangle size={15} />
                <span>Inject Stock Outage (Microphones)</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => resetAll()}
                disabled={isLoading}
                style={{ borderColor: 'var(--status-emerald-border)', color: 'var(--status-emerald)' }}
              >
                <RefreshCw size={14} />
                <span>Rollback Simulation</span>
              </button>
            )}
          </div>
        </div>

        {/* Re-planning Recovery Protocol Details */}
        {isFailed && (
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Outage Callout Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.8125rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--status-amber)' }}>
                <RefreshCw size={15} />
                <span style={{ fontWeight: 600 }}>Replanning Triggered: RODE PodMic SKU Outage Detected at B&amp;H</span>
              </div>
              <span className="badge badge-emerald">Topological Feasibility: PRESERVED</span>
            </div>

            {/* Evicted Edge vs Dependency Replacement comparison */}
            <div style={{ background: 'var(--bg-app)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <span style={{ color: 'var(--status-rose)', textTransform: 'uppercase', fontWeight: 600 }}>Evicted Edge &amp; Node:</span>
                <span style={{ color: 'var(--text-primary)' }}>RODE PodMic Dynamic XLR (Qty 2) • Unit Cost: $99.00</span>
                <span style={{ color: 'var(--text-muted)' }}>Interface Constraint: XLR_M_BALANCED • Power: Dynamic (0V)</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <span style={{ color: 'var(--status-emerald)', textTransform: 'uppercase', fontWeight: 600 }}>Dependency-Preserving Replacement:</span>
                <span style={{ color: 'var(--text-primary)' }}>Shure MV7X Dynamic XLR (Qty 2) • Unit Cost: $119.00</span>
                <span style={{ color: 'var(--status-emerald)' }}>Interface Match: PASS (Dual XLR Direct Compatible)</span>
              </div>
            </div>

            {/* Invalidation Security Banner */}
            <div className="callout callout-warning">
              <Lock size={18} style={{ flexShrink: 0, marginTop: '2px', color: 'var(--status-amber)' }} />
              <div>
                <strong style={{ fontSize: '0.8125rem', color: 'var(--status-amber)', display: 'block', marginBottom: '0.25rem' }}>
                  Cryptographic Integrity Lock: Prior Approval Token Invalidated
                </strong>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Under the BundleGraph contract specification, approvals bind immutably to exact plan versions. Because candidate inventory changed, the prior approval is voided and the operator must explicitly re-authorize Plan 2.0.
                </p>
              </div>
            </div>

            {/* Re-planning Diff / Delta Card */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
              {/* Removed items */}
              <div className="diff-card diff-card-removed">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--status-rose)', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.35rem', fontFamily: 'var(--font-mono)' }}>
                  <XCircle size={13} />
                  <span>Removed (Out of Stock)</span>
                </div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  2x Synthetic Mic Alpha
                </div>
                <div className="tabular-num" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  Prior Subtotal: $198.00 USD
                </div>
              </div>

              {/* Added items */}
              <div className="diff-card diff-card-added">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--status-emerald)', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.35rem', fontFamily: 'var(--font-mono)' }}>
                  <PlusCircle size={13} />
                  <span>Added (Verified Alternative)</span>
                </div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  2x Synthetic Mic Gamma
                </div>
                <div className="tabular-num" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  Replacement Subtotal: $170.00 USD
                </div>
              </div>

              {/* Retained working items */}
              <div className="diff-card diff-card-locked">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-primary)', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.35rem', fontFamily: 'var(--font-mono)' }}>
                  <Lock size={13} />
                  <span>Retained (Locked Cart)</span>
                </div>
                <ul style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', paddingLeft: '1.25rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <li>1x Interface Two (2 XLR inputs)</li>
                  <li>2x XLR Cables (3m balanced)</li>
                  <li>2x Headphones Alpha (TRS)</li>
                </ul>
              </div>
            </div>

            {/* Cost Delta & Timeline impact */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-app)', border: '1px solid var(--border-default)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Updated Total:</span>
                <span className="tabular-num" style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--status-emerald)' }}>
                  $415.00 USD
                </span>
                <span className="badge badge-emerald tabular-num">
                  -$28.00 Net Savings
                </span>
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                Schedule Impact: <strong style={{ color: 'var(--text-primary)' }}>+1 Transit Day</strong> (Within 2-day buffer before launch)
              </div>
            </div>

            {/* Zapier Webhook Dispatched Box */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card-subtle)', border: '1px solid var(--border-default)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                <Zap size={16} style={{ color: 'var(--status-amber)' }} />
                <div>
                  <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Zapier Webhook Notification Broadcasted
                  </span>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
                    Payload: <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>bundle_replan_recovery</code> dispatched to operations webhook.
                  </p>
                </div>
              </div>
              <span className="badge badge-emerald tabular-num">
                HTTP 200 Delivered
              </span>
            </div>
          </div>
        )}
      </section>

      {/* Bottom Persistent Action Bar */}
      <div className="card-footer" style={{ borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setStep('comparison')}
        >
          <ArrowLeft size={16} />
          <span>Review Full Manifest</span>
        </button>

        <div className="button-group">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleDownloadLog}
          >
            {downloadedLog ? <Check size={15} style={{ color: 'var(--status-emerald)' }} /> : <Download size={15} />}
            <span>{downloadedLog ? 'Log Exported (12.4 KB)' : 'Download Audit Log (JSON)'}</span>
          </button>

          {isFailed ? (
            <button
              type="button"
              className="btn-primary"
              onClick={handleReapproveAndSettle}
              disabled={isLoading || reapproved}
            >
              {reapproved ? (
                <>
                  <CheckCircle2 size={16} />
                  <span>Plan 2.0 Re-Authorized &amp; Settled</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={16} />
                  <span>Approve Plan 2.0 ($415.00) &amp; Settle PayPal</span>
                  <ArrowRight size={16} />
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
              <ArrowRight size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
