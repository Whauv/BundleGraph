import React, { lazy, Suspense, useState } from 'react';
import { motion } from 'motion/react';
import { AlertTriangle, ArrowLeft, ArrowRight, CalendarDays, CheckCircle2, Network, PackageSearch, Table2 } from 'lucide-react';
import { useDemo } from '../../store/demoStore';
import type { BundleProposal, Money } from '../../types/bundlegraph';

const BundleGrid = lazy(() => import('../grid/BundleGrid').then((module) => ({ default: module.BundleGrid })));
const EvidenceGraph = lazy(() => import('../graph/EvidenceGraph').then((module) => ({ default: module.EvidenceGraph })));
const ScheduleTimeline = lazy(() => import('../timeline/ScheduleTimeline').then((module) => ({ default: module.ScheduleTimeline })));

const money = (value: Money | null | undefined, currency = 'USD') => value ? new Intl.NumberFormat(undefined, { style: 'currency', currency: value.currency }).format(value.amount_minor / 100) : `Unknown ${currency}`;
const classification = (proposal: BundleProposal) => proposal.compatibility_report.classification === 'verified_complete' ? 'Compatible' : proposal.compatibility_report.classification.replaceAll('_', ' ');

export const BundleComparison: React.FC = () => {
  const { proposals, selectedProposal, selectProposal, budgetDollars, preparePlan, setStep, errorMessage, isLoading, evidenceRecords, confirmedRequirements } = useDemo();
  const [activeTab, setActiveTab] = useState<'equipment' | 'connections' | 'delivery'>('equipment');
  const total = selectedProposal?.cost_breakdown.all_in_total;
  const budgetMinor = Math.round(budgetDollars * 100);
  const differenceMinor = total ? budgetMinor - total.amount_minor : null;
  const limitations = selectedProposal?.compatibility_report.findings.filter((finding) => finding.status !== 'compatible') || [];

  if (!proposals.length) return <div className="screen-container">
    <header className="screen-heading"><p className="eyebrow">Bundle results</p><h1>Choose your setup</h1><p>No complete candidate is currently available for the confirmed requirements.</p></header>
    <section className="empty-state-panel"><PackageSearch size={28} /><div><h2>No feasible bundle returned</h2><p>{errorMessage || 'The search completed without a bundle that met every hard requirement.'}</p><p>Review the confirmed constraints, missing evidence, or budget. An API failure is shown separately and does not prove physical incompatibility.</p></div></section>
    <div className="action-bar"><button type="button" className="btn-secondary" onClick={() => setStep('review')}><ArrowLeft size={17} /> Review requirements</button></div>
  </div>;

  return <div className="screen-container comparison-screen">
    <header className="screen-heading"><p className="eyebrow">Compatible candidates</p><h1>Choose your setup</h1><p>Compare only the costs, findings, and evidence references returned by the backend. Selecting a different candidate clears downstream browser state.</p></header>
    <section className="candidate-selector" aria-label="Bundle candidates">
      {proposals.map((proposal, index) => {
        const selected = proposal.proposal_key === selectedProposal?.proposal_key;
        const proposalTotal = proposal.cost_breakdown.all_in_total;
        const proposalLimitations = proposal.compatibility_report.findings.filter((finding) => finding.status !== 'compatible').length;
        return <button key={proposal.proposal_key} type="button" className={`candidate-option ${selected ? 'is-selected' : ''}`} onClick={() => selectProposal(proposal.proposal_key)} aria-pressed={selected}>
          {selected && <motion.span className="candidate-option__indicator" layoutId="candidate-selection" aria-hidden="true" />}
          <span className="candidate-option__heading"><strong>Option {index + 1}</strong><span className={`status-text status-text--${proposal.compatibility_report.classification === 'verified_complete' ? 'success' : 'warning'}`}>{classification(proposal)}</span></span>
          <span className="candidate-option__price">{money(proposalTotal, proposal.cost_breakdown.currency)}</span>
          <span className="candidate-option__meta">{proposal.line_items.length} equipment lines · {proposalLimitations ? `${proposalLimitations} limitations` : 'No reported limitations'}</span>
        </button>;
      })}
    </section>
    {selectedProposal && <>
      <section className="bundle-summary-strip">
        <div><span>Merchandise subtotal</span><strong>{money(selectedProposal.cost_breakdown.merchandise_subtotal)}</strong></div>
        <div><span>Shipping</span><strong>{money(selectedProposal.cost_breakdown.shipping_total)}</strong></div>
        <div><span>Tax</span><strong>{money(selectedProposal.cost_breakdown.tax_total)}</strong></div>
        <div><span>{total ? 'All-in total' : 'Known subtotal only'}</span><strong>{money(total || selectedProposal.cost_breakdown.merchandise_subtotal)}</strong></div>
        <div><span>Budget difference</span><strong className={differenceMinor === null ? '' : differenceMinor >= 0 ? 'amount-positive' : 'amount-negative'}>{differenceMinor === null ? 'Unknown' : `${money({ amount_minor: Math.abs(differenceMinor), currency: selectedProposal.cost_breakdown.currency })} ${differenceMinor >= 0 ? 'remaining' : 'over budget'}`}</strong></div>
      </section>
      {selectedProposal.cost_breakdown.unknown_cost_components?.length ? <div className="status-notice status-notice--warning"><AlertTriangle size={18} /><div><strong>Total is incomplete</strong><p>Unknown: {selectedProposal.cost_breakdown.unknown_cost_components.join(', ')}. Unknown costs are not treated as zero.</p></div></div> : null}
      {limitations.length > 0 && <section className="limitations-section"><h2>Needs attention</h2>{limitations.map((finding) => <details key={finding.rule_id}><summary><span className={`finding-dot finding-dot--${finding.status}`} />{finding.explanation}</summary><p>{finding.missing_requirements_or_evidence?.join(', ') || finding.reason_code}</p></details>)}</section>}
      <div className="view-tabs" role="tablist" aria-label="Selected bundle details">
        <button type="button" role="tab" aria-selected={activeTab === 'equipment'} className={activeTab === 'equipment' ? 'is-active' : ''} onClick={() => setActiveTab('equipment')}><Table2 size={16} /> Equipment</button>
        <button type="button" role="tab" aria-selected={activeTab === 'connections'} className={activeTab === 'connections' ? 'is-active' : ''} onClick={() => setActiveTab('connections')}><Network size={16} /> Connections</button>
        <button type="button" role="tab" aria-selected={activeTab === 'delivery'} className={activeTab === 'delivery' ? 'is-active' : ''} onClick={() => setActiveTab('delivery')}><CalendarDays size={16} /> Delivery</button>
      </div>
      <div className="detail-view"><Suspense fallback={<div className="loading-screen" role="status">Loading details…</div>}>
        {activeTab === 'equipment' && <BundleGrid proposal={selectedProposal} />}
        {activeTab === 'connections' && <EvidenceGraph report={selectedProposal.compatibility_report} evidence={evidenceRecords} />}
        {activeTab === 'delivery' && <ScheduleTimeline deadline={confirmedRequirements?.deadline} />}
      </Suspense></div>
      <div className="action-bar"><button type="button" className="btn-secondary" onClick={() => setStep('review')}><ArrowLeft size={17} /> Review requirements</button><div className="action-bar__primary"><span className="action-context">{selectedProposal.compatibility_report.classification === 'verified_complete' ? <><CheckCircle2 size={16} /> Compatibility reported as verified complete</> : 'Review unresolved findings before continuing'}</span><button type="button" className="btn-primary" onClick={() => void preparePlan()} disabled={isLoading || selectedProposal.compatibility_report.classification !== 'verified_complete'}>{isLoading ? 'Saving selected plan…' : <>Review selected bundle <ArrowRight size={17} /></>}</button></div></div>
    </>}
  </div>;
};
