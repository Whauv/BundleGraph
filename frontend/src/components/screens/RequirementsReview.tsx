import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, CircleHelp } from 'lucide-react';
import { useDemo } from '../../store/demoStore';
import { dollarsToMinorUnits } from '../../utils/money';

const readable = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

export const RequirementsReview: React.FC = () => {
  const {
    interpretation, promptText, useCase, setUseCase, reviewDisagreements, budgetDollars, setBudgetDollars, participants, setParticipants,
    laptopConnector, setLaptopConnector, listeningRequirement, setListeningRequirement,
    deadlineDate, setDeadlineDate, confirmRequirements, setStep, isLoading, draftVersion,
  } = useDemo();
  const reviewSignature = `${useCase}:${participants}:${budgetDollars}:${laptopConnector}:${listeningRequirement}:${deadlineDate}`;
  const [acknowledgement, setAcknowledgement] = useState({ signature: '', value: false });
  const acknowledged = acknowledgement.signature === reviewSignature && acknowledgement.value;
  const missing = interpretation?.missing_information || [];
  const fieldsResolved = useCase === 'two-person podcast' && participants === 2 && dollarsToMinorUnits(budgetDollars) !== null && laptopConnector !== 'unknown' && listeningRequirement !== 'unknown';

  return <div className="screen-container review-screen">
    <header className="screen-heading"><p className="eyebrow">Review the draft</p><h1>Confirm your setup</h1><p>AI interpretation is a proposal, not confirmation. Review the explicit controls below; the backend will validate the latest draft before confirming it.</p></header>
    <AnimatePresence initial={false}>{missing.length > 0 && <motion.section className="status-notice status-notice--warning" role="alert" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}><AlertTriangle size={19} /><div><strong>Clarification requested by the server</strong><p>Resolve the fields below, then submit them for server-side revalidation.</p><ul>{(interpretation?.clarification_questions.length ? interpretation.clarification_questions : missing).map((question) => <li key={question}>{question}</li>)}</ul></div></motion.section>}</AnimatePresence>
    {reviewDisagreements.length > 0 && <section className="status-notice status-notice--warning"><AlertTriangle size={19} /><div><strong>Request and structured answers differed</strong><p>The extracted values are shown below. Review or change them before confirming.</p><ul>{reviewDisagreements.map((item) => <li key={item}>{item}</li>)}</ul></div></section>}
    <section className="form-section requirements-editor">
      <div className="section-heading"><div><p className="eyebrow">Editable requirements</p><h2>People and equipment constraints</h2></div><span className="status-label status-label--neutral">Draft v{draftVersion || '—'}</span></div>
      <div className="review-controls">
        <label htmlFor="review-use-case"><span className="field-label">Supported setup</span><select id="review-use-case" value={useCase} onChange={(event) => setUseCase(event.target.value)} aria-invalid={useCase !== 'two-person podcast'}><option value="">Choose a supported setup</option><option value="two-person podcast">Two-person podcast</option></select><small>{useCase === 'two-person podcast' ? 'This explicitly accepts the supported initial-domain topology.' : 'Unsupported requests are not silently converted. Choose the supported topology only if it matches your intent.'}</small></label>
        <label htmlFor="review-participants"><span className="field-label">Participants</span><select id="review-participants" value={participants} onChange={(event) => setParticipants(Number(event.target.value))} aria-invalid={participants !== 2}><option value={1}>One person</option><option value={2}>Two people</option><option value={3}>Three people</option></select><small>The current verified topology supports exactly two people; other values require clarification.</small></label>
        <label htmlFor="review-budget"><span className="field-label">Equipment budget</span><div className="currency-input"><span aria-hidden="true">$</span><input id="review-budget" type="number" min="0.01" max="1000000" step="0.01" value={budgetDollars} onChange={(event) => setBudgetDollars(event.target.valueAsNumber)} aria-invalid={dollarsToMinorUnits(budgetDollars) === null} /></div>{dollarsToMinorUnits(budgetDollars) === null && <small className="field-error">Enter a finite budget with no more than two decimal places.</small>}</label>
        <label htmlFor="review-connector"><span className="field-label">Laptop connection</span><select id="review-connector" value={laptopConnector} onChange={(event) => setLaptopConnector(event.target.value)} aria-invalid={laptopConnector === 'unknown'}><option value="usb-c">USB-C</option><option value="usb-a">USB-A</option><option value="unknown">I’m not sure</option></select>{laptopConnector === 'unknown' ? <small className="field-error">Choose the laptop port before confirmation.</small> : <small>USB-C and USB-A are evaluated as distinct connector facts.</small>}</label>
        <label htmlFor="review-monitoring"><span className="field-label">Headphone monitoring</span><select id="review-monitoring" value={listeningRequirement} onChange={(event) => setListeningRequirement(event.target.value)} aria-invalid={listeningRequirement === 'unknown'}><option value="independent_headphones">Separate headphone monitoring</option><option value="shared_headphones">Shared headphone listening</option><option value="no_monitoring">No monitoring required</option><option value="unknown">I’m not sure</option></select>{listeningRequirement === 'unknown' && <small className="field-error">Choose a monitoring requirement before confirmation.</small>}</label>
        <label htmlFor="review-date"><span className="field-label">Recording target <em>Optional</em></span><input id="review-date" type="date" value={deadlineDate} onChange={(event) => setDeadlineDate(event.target.value)} /><small>This target does not establish delivery feasibility.</small></label>
      </div>
    </section>
    <section className="review-context">
      <details><summary>Original request</summary><p>{promptText}</p></details>
      <details><summary>Interpretation details</summary><div className="interpretation-details"><div><h3>Explicit facts</h3>{interpretation?.explicit_facts.length ? <ul>{interpretation.explicit_facts.map((fact, index) => <li key={`${fact.path}-${index}`}><strong>{readable(fact.path)}:</strong> {String(fact.value)}</li>)}</ul> : <p>No explicit facts were returned.</p>}</div><div><h3>Suggested defaults</h3>{interpretation?.suggested_defaults.length ? <ul>{interpretation.suggested_defaults.map((fact, index) => <li key={`${fact.path}-${index}`}><strong>{readable(fact.path)}:</strong> {String(fact.value)}</li>)}</ul> : <p>No defaults were returned.</p>}</div></div></details>
      <details className="technical-details"><summary>Technical details</summary><dl><div><dt>Provider mode</dt><dd>{interpretation?.provider_mode || 'Unknown'}</dd></div><div><dt>Draft version</dt><dd>{draftVersion || 'Not recorded'}</dd></div><div><dt>Latest server eligibility</dt><dd>{interpretation?.can_confirm === false ? 'Needs revalidation' : 'No blocker reported'}</dd></div></dl></details>
    </section>
    <label className="confirmation-check"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledgement({ signature: reviewSignature, value: event.target.checked })} /><span><CheckCircle2 size={17} /> I reviewed these values and want the server to confirm this exact draft.</span></label>
    <p className="review-boundary"><CircleHelp size={16} /> Confirmation authorizes bundle generation only. It does not approve a plan or payment.</p>
    <div className="action-bar"><button type="button" className="btn-secondary" onClick={() => setStep('builder')}><ArrowLeft size={17} /> Back to request</button><button type="button" className="btn-primary" onClick={() => void confirmRequirements()} disabled={isLoading || !acknowledged || !fieldsResolved}>{isLoading ? 'Confirming requirements…' : <>Confirm &amp; find bundles <ArrowRight size={17} /></>}</button></div>
  </div>;
};
