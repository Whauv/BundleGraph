import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { AlertTriangle, CheckCircle2, Clipboard, Download, PackageSearch, RefreshCw, RotateCcw } from 'lucide-react';
import { useDemo } from '../../store/demoStore';
import type { Money, ReplacementBundleProposal } from '../../types/bundlegraph';

const money = (value?: Money | null) => value ? new Intl.NumberFormat(undefined, { style: 'currency', currency: value.currency, signDisplay: value.amount_minor ? 'auto' : 'never' }).format(value.amount_minor / 100) : 'Not recorded';

export const ExecutionRecovery: React.FC = () => {
  const { executionRecord, replanResult, triggerReplan, resetAll, isLoading, authoritativePlan, runtimeMode } = useDemo();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const replacements = replanResult?.replacements || [];
  const selected = replacements.find((item) => item.proposal.proposal_key === selectedKey) || replacements[0] || null;

  const failed = executionRecord?.execution_status === 'FAILED_MERCHANT_STOCK_OUTAGE';
  const simulatedComplete = runtimeMode === 'fixture' && executionRecord?.execution_status === 'COMPLETED';
  const status = replanResult ? 'Recovery proposal available' : failed ? 'Execution failed' : simulatedComplete ? 'Simulated execution completed' : executionRecord ? 'Execution recorded' : 'No execution recorded';

  const copyReference = async () => {
    try { await navigator.clipboard.writeText(authoritativePlan?.plan_id || executionRecord?.plan_id || ''); setCopyStatus('Copied'); }
    catch { setCopyStatus('Copy failed'); }
  };

  const exportSummary = () => {
    const summary = {
      exported_at: new Date().toISOString(),
      label: 'BundleGraph client-visible run summary',
      runtime_mode: runtimeMode,
      plan_id: authoritativePlan?.plan_id || executionRecord?.plan_id || null,
      plan_version: authoritativePlan?.current_version || null,
      execution_status: executionRecord?.execution_status || null,
      execution_message: executionRecord?.message || null,
      failed_offer_id: executionRecord?.failed_offer_id || null,
      recovery_search_status: replanResult?.search_status || null,
      recovery_proposal_keys: replacements.map((item) => item.proposal.proposal_key),
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(summary, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `bundlegraph-run-${Date.now()}.json`; anchor.click();
    URL.revokeObjectURL(url); setExportStatus('Summary downloaded');
  };

  const startOver = () => { if (window.confirm('Start a new setup? This clears the current browser workflow.')) void resetAll(); };

  return <div className="screen-container recovery-screen">
    <header className="screen-heading"><p className="eyebrow">Plan activity</p><h1>Track and recover</h1><p>Review recorded execution facts and replacement proposals. BundleGraph never silently substitutes equipment or carries approval to a changed plan.</p></header>
    <section className={`execution-status execution-status--${failed ? 'error' : simulatedComplete ? 'success' : replanResult ? 'warning' : 'neutral'}`}>
      <div>{failed ? <AlertTriangle size={24} /> : simulatedComplete ? <CheckCircle2 size={24} /> : <PackageSearch size={24} />}</div>
      <div><p className="eyebrow">Current status</p><h2>{status}</h2><p>{executionRecord?.message || 'No execution record has been supplied by the backend.'}</p></div>
      <dl><div><dt>Recorded amount</dt><dd>{executionRecord?.amount_minor !== undefined && executionRecord.currency ? money({ amount_minor: executionRecord.amount_minor, currency: executionRecord.currency }) : 'Not recorded'}</dd></div><div><dt>Plan version</dt><dd>{authoritativePlan?.current_version || 'Not recorded'}</dd></div><div><dt>Payment scope</dt><dd>{simulatedComplete ? 'Fixture simulation' : executionRecord ? 'Use recorded provider status' : 'None'}</dd></div></dl>
    </section>

    {failed && !replanResult && <section className="empty-state-panel"><RefreshCw size={25} /><div><h2>Replacement options have not been requested</h2><p>The failed offer is {executionRecord?.failed_offer_id || 'not identified'}.</p><button type="button" className="btn-primary" onClick={() => void triggerReplan(executionRecord?.failed_offer_id)} disabled={isLoading}>{isLoading ? 'Requesting replacements…' : 'Find replacement options'}</button></div></section>}

    <AnimatePresence initial={false}>{replanResult && <motion.section className="recovery-section" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
      <div className="section-heading"><div><p className="eyebrow">Reviewable proposal</p><h2>Replacement options</h2></div><span className="status-label status-label--warning">New approval required</span></div>
      {replacements.length > 1 && <div className="replacement-selector" role="group" aria-label="Replacement proposals">{replacements.map((replacement, index) => <button type="button" key={replacement.proposal.proposal_key} aria-pressed={selected?.proposal.proposal_key === replacement.proposal.proposal_key} onClick={() => setSelectedKey(replacement.proposal.proposal_key)}>Option {index + 1} · {money(replacement.cost_difference)}</button>)}</div>}
      {selected ? <ReplacementDetails replacement={selected} /> : <p>No replacement proposal was returned.</p>}
      <div className="status-notice status-notice--neutral"><AlertTriangle size={18} /><div><strong>This proposal has not been applied.</strong><p>The current browser contract can review replacement proposals but does not expose an apply-and-reapprove operation. The original plan remains unchanged.</p></div></div>
    </motion.section>}</AnimatePresence>

    <section className="activity-section"><div className="section-heading"><div><p className="eyebrow">Recorded events</p><h2>Activity</h2></div></div><ol className="activity-list">
      {authoritativePlan && <li><span /> <div><strong>Plan persisted</strong><p>Version {authoritativePlan.current_version} is the current stored version.</p></div></li>}
      {executionRecord && <li><span /> <div><strong>{failed ? 'Availability failure recorded' : simulatedComplete ? 'Simulated execution recorded' : 'Execution status recorded'}</strong><p>{executionRecord.message}</p></div></li>}
      {replanResult && <li><span /> <div><strong>Replacement proposal generated</strong><p>{replacements.length} option{replacements.length === 1 ? '' : 's'} returned; none applied automatically.</p></div></li>}
    </ol></section>

    <div className="run-tools"><button type="button" className="btn-secondary" onClick={() => void copyReference()} disabled={!authoritativePlan && !executionRecord}><Clipboard size={16} /> Copy plan reference</button><span role="status">{copyStatus}</span><button type="button" className="btn-secondary" onClick={exportSummary}><Download size={16} /> Download run summary</button><span role="status">{exportStatus}</span></div>
    <div className="action-bar"><span className="action-context">A changed plan requires explicit review and a new backend approval.</span><button type="button" className="btn-secondary" onClick={startOver}><RotateCcw size={16} /> Start a new setup</button></div>
  </div>;
};

const ReplacementDetails: React.FC<{ replacement: ReplacementBundleProposal }> = ({ replacement }) => <div className="replacement-comparison">
  <div><h3>Removed</h3>{replacement.removed_items.length ? replacement.removed_items.map((item) => <p key={item.offer_id}><strong>{item.product_id}</strong><span>Qty {item.previous_quantity}</span></p>) : <p>None</p>}</div>
  <div><h3>Added</h3>{replacement.added_items.length ? replacement.added_items.map((item) => <p key={item.offer_id}><strong>{item.product_id}</strong><span>Qty {item.replacement_quantity}</span></p>) : <p>None</p>}</div>
  <div><h3>Retained</h3>{replacement.retained_items.length ? replacement.retained_items.map((item) => <p key={item.offer_id}><strong>{item.product_id}</strong><span>Qty {item.replacement_quantity}</span></p>) : <p>None</p>}</div>
  <div><h3>Cost difference</h3><p><strong>{money(replacement.cost_difference)}</strong></p><h3>Compatibility</h3>{replacement.proposal.compatibility_report.findings.filter((finding) => finding.status !== 'compatible').map((finding) => <p key={finding.rule_id}>{finding.explanation}</p>)}{replacement.proposal.compatibility_report.findings.every((finding) => finding.status === 'compatible') && <p>All returned findings are compatible.</p>}</div>
</div>;
