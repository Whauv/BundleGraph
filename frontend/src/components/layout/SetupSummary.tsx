import React from 'react';
import { CheckCircle2, CircleHelp, Laptop, Users } from 'lucide-react';
import { useDemo } from '../../store/demoStore';

const connectorLabel = (value: string) => ({ 'usb-c': 'USB-C', 'usb-a': 'USB-A', unknown: 'Needs clarification' } as Record<string, string>)[value] || value;
const monitoringLabel = (value: string) => ({ independent_headphones: 'Separate headphones', shared_headphones: 'Shared listening', no_monitoring: 'No monitoring', unknown: 'Needs clarification' } as Record<string, string>)[value] || value;

const SummaryContent: React.FC = () => {
  const { participants, budgetDollars, laptopConnector, listeningRequirement, deadlineDate, confirmedRequirements, authoritativePlan } = useDemo();
  const confirmed = Boolean(confirmedRequirements);
  const values = confirmedRequirements ? {
    participants: confirmedRequirements.participants,
    budget: confirmedRequirements.budget.amount_minor,
    connector: confirmedRequirements.laptop_connectors[0]?.connector || laptopConnector,
    monitoring: confirmedRequirements.listening_requirement,
    deadline: confirmedRequirements.deadline,
  } : { participants, budget: Math.round(budgetDollars * 100), connector: laptopConnector, monitoring: listeningRequirement, deadline: deadlineDate || null };
  return <>
    <div className="setup-summary__heading"><div><p className="eyebrow">Current setup</p><h2>Requirements at a glance</h2></div><span className={`status-label ${confirmed ? 'status-label--success' : 'status-label--neutral'}`}>{confirmed ? <CheckCircle2 size={14} /> : <CircleHelp size={14} />}{confirmed ? 'Confirmed' : 'Draft'}</span></div>
    <dl className="summary-list">
      <div><dt><Users size={15} /> Participants</dt><dd>{values.participants} people</dd></div>
      <div><dt>Equipment budget</dt><dd>{new Intl.NumberFormat(undefined, { style: 'currency', currency: confirmedRequirements?.budget.currency || 'USD', maximumFractionDigits: 0 }).format(values.budget / 100)}</dd></div>
      <div><dt><Laptop size={15} /> Laptop</dt><dd>{connectorLabel(values.connector)}</dd></div>
      <div><dt>Monitoring</dt><dd>{monitoringLabel(values.monitoring)}</dd></div>
      {values.deadline && <div><dt>Target date</dt><dd>{new Date(values.deadline.includes('T') ? values.deadline : `${values.deadline}T12:00:00`).toLocaleDateString()}</dd></div>}
      {authoritativePlan && <div><dt>Stored plan</dt><dd>Version {authoritativePlan.current_version}</dd></div>}
    </dl>
    <p className="summary-note">{confirmed ? 'Server-confirmed values currently guide bundle selection.' : 'Edited browser values remain a draft until the server confirms them.'}</p>
  </>;
};

export const SetupSummary: React.FC = () => <>
  <aside className="setup-summary setup-summary--desktop" aria-label="Current setup summary"><SummaryContent /></aside>
  <details className="setup-summary setup-summary--mobile"><summary>View current setup</summary><div className="setup-summary__mobile-content"><SummaryContent /></div></details>
</>;
