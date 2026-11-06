import React from 'react';
import { AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, CircleHelp, FileCheck2, ShieldCheck } from 'lucide-react';
import { useDemo } from '../../store/demoStore';
import type { Money } from '../../types/bundlegraph';

const money = (value?: Money | null) => value ? new Intl.NumberFormat(undefined, { style: 'currency', currency: value.currency }).format(value.amount_minor / 100) : 'Not recorded';

export const PlanApproval: React.FC = () => {
  const { authoritativePlan, selectedProposal, confirmedRequirements, approvalRecord, approvePlan, executeOrder, setStep, isLoading, runtimeMode, activePresetId, evidenceRecords, evidenceLoadStatus, loadEvidence } = useDemo();
  const version = authoritativePlan?.versions.find((item) => item.version === authoritativePlan.current_version);
  const approvalValid = Boolean(approvalRecord?.valid && approvalRecord.status !== 'INVALIDATED_PLAN_MODIFIED' && approvalRecord.status !== 'INVALIDATED_BY_RECORDED_EXECUTION');
  const amount = version?.total;
  const runFixture = () => void executeOrder(activePresetId === 'preset-stock-failure' ? 'offer-mic-alpha' : undefined);

  if (!authoritativePlan || !version) return <div className="screen-container"><header className="screen-heading"><p className="eyebrow">Stored plan required</p><h1>Review and approve</h1><p>The selected candidate must be persisted by the backend before approval.</p></header><div className="action-bar"><button type="button" className="btn-secondary" onClick={() => setStep('comparison')}><ArrowLeft size={17} /> Back to bundles</button></div></div>;

  return <div className="screen-container approval-screen">
    <header className="screen-heading"><p className="eyebrow">Exact plan version</p><h1>Review and approve</h1><p>Approval applies only to this stored plan version and amount. If either changes, the backend requires a new approval.</p></header>
    <section className="approval-summary">
      <div><span>Plan</span><strong>{authoritativePlan.plan_id}</strong></div><div><span>Version</span><strong>{version.version}</strong></div><div><span>Amount to approve</span><strong>{money(amount)}</strong></div><div><span>Approval status</span><strong className={approvalValid ? 'status-text--success' : 'status-text--neutral'}>{approvalValid ? 'Approved' : approvalRecord ? approvalRecord.status.replaceAll('_', ' ') : 'Not approved'}</strong></div>
    </section>
    <div className="approval-layout">
      <section className="form-section"><div className="section-heading"><div><p className="eyebrow">Selected equipment</p><h2>Plan contents</h2></div><span className="status-label status-label--neutral">{selectedProposal?.line_items.length || version.line_items.length} lines</span></div>
        <div className="equipment-list">{(version.line_items.length ? version.line_items : selectedProposal?.line_items || []).map((item) => <article key={item.offer_id} className="equipment-row"><div><strong>{item.product_id}</strong><span>{item.offer_id}</span></div><span>Qty {item.quantity}</span><span>{money(item.merchandise_total)}</span></article>)}</div>
        {selectedProposal?.compatibility_report.findings.some((finding) => finding.status !== 'compatible') ? <div className="status-notice status-notice--warning"><AlertTriangle size={18} /><div><strong>Unresolved compatibility findings</strong><p>Review the candidate findings before approval.</p></div></div> : <p className="approval-assurance"><ShieldCheck size={18} /> The persisted candidate was reported as verified complete when selected.</p>}
      </section>
      <aside className="approval-panel"><p className="eyebrow">What approval means</p><h2>Permission for this version</h2><p>You are approving version {version.version} with a stored total of {money(amount)}. This does not reserve inventory, guarantee fulfillment, or by itself execute a payment.</p>
        <dl><div><dt>Confirmed request</dt><dd>{confirmedRequirements?.confirmation_reference || 'Not recorded'}</dd></div><div><dt>Evidence status</dt><dd>{evidenceLoadStatus === 'loaded' ? evidenceRecords.length ? `${evidenceRecords.length} stored records` : runtimeMode === 'fixture' ? 'Fixture references only' : 'Loaded; no records returned' : evidenceLoadStatus === 'failed' ? 'Loading failed' : evidenceLoadStatus === 'loading' ? 'Loading' : 'Not loaded'}</dd></div><div><dt>Merchant allocations</dt><dd>{version.merchant_allocations.length || 'Not exposed'}</dd></div></dl>
        <details className="technical-details"><summary>Technical details</summary><dl><div><dt>Fingerprint</dt><dd>{version.fingerprint}</dd></div><div><dt>Correlation ID</dt><dd>{version.correlation_id}</dd></div>{version.merchant_allocations.map((allocation) => <div key={allocation.allocation_id}><dt>{allocation.allocation_id}</dt><dd>{money(allocation.amount)}</dd></div>)}</dl></details>
      </aside>
    </div>
    {runtimeMode === 'fixture' && <div className="status-notice status-notice--neutral"><CircleHelp size={18} /><div><strong>Demo equipment data. Simulated execution only.</strong><p>No PayPal or merchant call will be made. Stock-failure behavior is selected from Demo tools.</p></div></div>}
    {evidenceLoadStatus === 'failed' && <div className="status-notice status-notice--warning"><AlertTriangle size={18} /><div><strong>The plan was saved, but its evidence could not be loaded.</strong><p>Retrying this read will not create another plan.</p><button type="button" className="btn-secondary" onClick={() => void loadEvidence()} disabled={isLoading}>Retry evidence loading</button></div></div>}
    {runtimeMode === 'authoritative' && approvalValid && <div className="status-notice status-notice--neutral"><CircleHelp size={18} /><div><strong>Plan approved; payment continuation is not exposed here.</strong><p>The browser does not infer that payment execution is available. Use only a server-supported payment action when it is explicitly returned by the API.</p></div></div>}
    <div className="action-bar"><button type="button" className="btn-secondary" onClick={() => setStep('comparison')}><ArrowLeft size={17} /> Back to bundles</button><div className="action-bar__primary">{!approvalValid ? <button type="button" className="btn-primary" onClick={() => void approvePlan()} disabled={isLoading || evidenceLoadStatus !== 'loaded'}>{isLoading ? 'Approving plan…' : evidenceLoadStatus !== 'loaded' ? 'Evidence must load before approval' : <><FileCheck2 size={17} /> Approve plan</>}</button> : runtimeMode === 'fixture' ? <button type="button" className="btn-primary" onClick={runFixture} disabled={isLoading}>{isLoading ? 'Recording simulated execution…' : <>Run simulated execution <ArrowRight size={17} /></>}</button> : <span className="action-context"><CheckCircle2 size={17} /> Approval recorded by the backend</span>}</div></div>
  </div>;
};
