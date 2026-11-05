import React from 'react';
import { ArrowRight, CalendarDays, CircleHelp, Headphones, Laptop, Sparkles, Users } from 'lucide-react';
import { useDemo } from '../../store/demoStore';

export const RequestBuilder: React.FC = () => {
  const {
    promptText, setPromptText, budgetDollars, setBudgetDollars, participants, setParticipants,
    laptopConnector, setLaptopConnector, listeningRequirement, setListeningRequirement,
    deadlineDate, setDeadlineDate, interpretPrompt, isLoading, presets, loadPreset,
  } = useDemo();
  const example = presets.find((preset) => preset.id === 'preset-standard-podcast');
  return <div className="screen-container request-screen">
    <header className="screen-heading"><p className="eyebrow">Describe your setup</p><h1>Build your podcast setup.</h1><p>Tell us who’s recording, what you already have, and your budget. We’ll help assemble a complete, compatible setup.</p></header>
    <form className="request-form" onSubmit={(event) => { event.preventDefault(); void interpretPrompt(); }}>
      <label className="request-prompt" htmlFor="prompt-input"><span className="field-label"><Sparkles size={17} /> What are you building?</span><textarea id="prompt-input" value={promptText} onChange={(event) => setPromptText(event.target.value)} placeholder="Two people recording on a USB-C laptop. Budget: $600. We need microphones, headphones, and all required cables." required aria-describedby="prompt-help" /><span id="prompt-help" className="field-help">The server creates a draft interpretation. You will review every requirement before anything is confirmed.</span></label>
      <div className="starter-row"><span>Supported example</span><button type="button" onClick={() => example && void loadPreset(example)}>Two-person podcast</button><button type="button" className="btn-ghost" onClick={() => example && void loadPreset(example)}>Load example</button></div>
      <div className="form-section"><div className="section-heading"><div><p className="eyebrow">Explicit details</p><h2>Planning constraints</h2></div></div>
        <div className="structured-inputs">
          <label htmlFor="budget"><span className="field-label">Budget</span><div className="currency-input"><span aria-hidden="true">$</span><input id="budget" type="number" min="1" step="1" value={budgetDollars} onChange={(event) => setBudgetDollars(Number(event.target.value))} required /></div><small>Equipment budget in USD.</small></label>
          <label htmlFor="participants"><span className="field-label"><Users size={16} /> Participants</span><select id="participants" value={participants} onChange={(event) => setParticipants(Number(event.target.value))}><option value={2}>Two people</option></select><small>The verified initial domain currently supports exactly two participants.</small></label>
          <label htmlFor="connector"><span className="field-label"><Laptop size={16} /> Laptop connection</span><select id="connector" value={laptopConnector} onChange={(event) => setLaptopConnector(event.target.value)}><option value="usb-c">USB-C</option><option value="usb-a">USB-A</option><option value="unknown">I’m not sure</option></select><small>USB-C is not treated as proof of Thunderbolt compatibility.</small></label>
          <label htmlFor="monitoring"><span className="field-label"><Headphones size={16} /> Headphone monitoring</span><select id="monitoring" value={listeningRequirement} onChange={(event) => setListeningRequirement(event.target.value)}><option value="independent_headphones">Separate headphone monitoring</option><option value="shared_headphones">Shared headphone listening</option><option value="no_monitoring">No monitoring required</option><option value="unknown">I’m not sure</option></select><small>Choose separate monitoring when each person needs their own output.</small></label>
          <label htmlFor="target-date"><span className="field-label"><CalendarDays size={16} /> Recording target <em>Optional</em></span><input id="target-date" type="date" value={deadlineDate} onChange={(event) => setDeadlineDate(event.target.value)} /><small>A target date is not a delivery promise. Delivery stays unknown without evidence.</small></label>
        </div>
      </div>
      <div className="action-bar"><p className="quiet-note"><CircleHelp size={16} /> The next step reviews a draft. No bundle has been validated yet.</p><button className="btn-primary" type="submit" disabled={isLoading || !promptText.trim() || budgetDollars <= 0}>{isLoading ? 'Preparing requirements…' : <>Review requirements <ArrowRight size={17} /></>}</button></div>
    </form>
  </div>;
};
