import React, { lazy, Suspense, useRef, useState } from 'react';
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
  const { proposals, selectedProposal, selectProposal, budgetDollars, preparePlan, setStep, errorMessage, isLoading, evidenceRecords, confirmedRequirements, searchResult } = useDemo();
  const [activeTab, setActiveTab] = useState<'equipment' | 'connections' | 'delivery'>('equipment');
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const tabs = ['equipment', 'connections', 'delivery'] as const;
  const onTabKeyDown = (event: React.KeyboardEvent, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    setActiveTab(tabs[next]); tabRefs.current[next]?.focus();
  };
  const total = selectedProposal?.cost_breakdown.all_in_total;
  const budgetMinor = Math.round(budgetDollars * 100);
  const differenceMinor = total ? budgetMinor - total.amount_minor : null;
  const limitations = selectedProposal?.compatibility_report.findings.filter((finding) => finding.status !== 'compatible') || [];

  if (!proposals.length) return <div className="screen-container">
    <header className="screen-heading"><p className="eyebrow">Bundle results</p><h1>Choose your setup</h1><p>No complete candidate is currently available for the confirmed requirements.</p></header>
    <section className="empty-state-panel"><PackageSearch size={28} /><div><h2>{searchResult.status === 'infeasible' ? 'No feasible bundle found' : searchResult.status === 'blocked' ? 'Search blocked by unresolved information' : 'Bundle search did not complete'}</h2><p>{searchResult.infeasibility?.explanation || errorMessage || 'No candidate result is available.'}</p><p>{searchResult.status === 'infeasible' ? 'The backend completed its search and reported the listed constraints as infeasible.' : searchResult.status === 'blocked' ? 'Review missing evidence or requirements. This is not proof of physical incompatibility.' : 'A failed or interrupted request is not proof of physical incompatibility.'}</p>{searchResult.reason_codes.length > 0 && <p>Reason codes: {searchResult.reason_codes.join(', ')}</p>}</div></section>
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
        <button ref={(node) => { tabRefs.current[0] = node; }} id="bundle-tab-equipment" type="button" role="tab" aria-controls="bundle-panel-equipment" aria-selected={activeTab === 'equipment'} tabIndex={activeTab === 'equipment' ? 0 : -1} className={activeTab === 'equipment' ? 'is-active' : ''} onKeyDown={(event) => onTabKeyDown(event, 0)} onClick={() => setActiveTab('equipment')}><Table2 size={16} /> Equipment</button>
        <button ref={(node) => { tabRefs.current[1] = node; }} id="bundle-tab-connections" type="button" role="tab" aria-controls="bundle-panel-connections" aria-selected={activeTab === 'connections'} tabIndex={activeTab === 'connections' ? 0 : -1} className={activeTab === 'connections' ? 'is-active' : ''} onKeyDown={(event) => onTabKeyDown(event, 1)} onClick={() => setActiveTab('connections')}><Network size={16} /> Connections</button>
        <button ref={(node) => { tabRefs.current[2] = node; }} id="bundle-tab-delivery" type="button" role="tab" aria-controls="bundle-panel-delivery" aria-selected={activeTab === 'delivery'} tabIndex={activeTab === 'delivery' ? 0 : -1} className={activeTab === 'delivery' ? 'is-active' : ''} onKeyDown={(event) => onTabKeyDown(event, 2)} onClick={() => setActiveTab('delivery')}><CalendarDays size={16} /> Delivery</button>
      </div>
      <div id={`bundle-panel-${activeTab}`} role="tabpanel" aria-labelledby={`bundle-tab-${activeTab}`} className="detail-view"><Suspense fallback={<div className="loading-screen" role="status">Loading details…</div>}>
        {activeTab === 'equipment' && <BundleGrid proposal={selectedProposal} />}
        {activeTab === 'connections' && <EvidenceGraph report={selectedProposal.compatibility_report} evidence={evidenceRecords} />}
        {activeTab === 'delivery' && <ScheduleTimeline deadline={confirmedRequirements?.deadline} />}
      </Suspense></div>
      <div className="action-bar"><button type="button" className="btn-secondary" onClick={() => setStep('review')}><ArrowLeft size={17} /> Review requirements</button><div className="action-bar__primary"><span className="action-context">{selectedProposal.compatibility_report.classification === 'verified_complete' ? <><CheckCircle2 size={16} /> Compatibility reported as verified complete</> : 'Review unresolved findings before continuing'}</span><button type="button" className="btn-primary" onClick={() => void preparePlan()} disabled={isLoading || selectedProposal.compatibility_report.classification !== 'verified_complete'}>{isLoading ? 'Saving selected plan…' : <>Review selected bundle <ArrowRight size={17} /></>}</button></div></div>
    </>}
  </div>;
};
