import React from 'react';
import { useDemo } from '../../store/demoStore';
import { 
  ArrowRight, 
  ShieldCheck, 
  DollarSign, 
  Users, 
  Laptop, 
  Headphones, 
  Calendar, 
  Cpu,
  Terminal
} from 'lucide-react';

export const RequestBuilder: React.FC = () => {
  const {
    promptText,
    setPromptText,
    budgetDollars,
    setBudgetDollars,
    participants,
    setParticipants,
    laptopConnector,
    setLaptopConnector,
    listeningRequirement,
    setListeningRequirement,
    deadlineDate,
    setDeadlineDate,
    interpretPrompt,
    isLoading,
  } = useDemo();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    interpretPrompt();
  };

  return (
    <div className="screen-container">
      {/* Screen Header */}
      <div className="screen-header">
        <div className="screen-header-left">
          <div className="screen-header-icon">
            <Terminal size={18} />
          </div>
          <div>
            <h1 className="screen-title">Stage 1: Studio Specification &amp; Constraint Request</h1>
            <p className="screen-description">
              Describe your studio setup in natural language or customize parameters. BundleGraph solves physical hardware compatibility deterministically.
            </p>
          </div>
        </div>

        <div className="screen-header-meta">
          <span className="badge badge-neutral">
            <span>Extraction: Schema Adapter</span>
          </span>
          <span className="badge badge-neutral">
            <Cpu size={12} />
            <span>gemini-1.5-pro</span>
          </span>
          <span className="badge badge-emerald">
            <ShieldCheck size={12} />
            <span>Solver Ready</span>
          </span>
        </div>
      </div>

      {/* Main Workspace Card */}
      <div className="studio-card">
        <div className="card-header">
          <div className="card-title-group">
            <h2 className="card-title">Natural Language Requirements &amp; Parameters</h2>
            <p className="card-subtitle">
              Input studio specifications. The solver checks bus power, XLR capacity, DAC latency, and inventory availability in real time.
            </p>
          </div>
          <div className="badge badge-emerald">
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--status-emerald)' }} />
            <span>Deterministic Matrix Active</span>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Natural Language Prompt Area */}
            <div className="form-group" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <label htmlFor="prompt-input" className="form-label" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  Natural Language Studio Request
                </label>
                <span className="tabular-num" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {promptText.length} characters
                </span>
              </div>
              <textarea
                id="prompt-input"
                className="studio-textarea"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                placeholder="I want to start a 2-person podcast with my USB-C laptop. Budget is $600. We need 2 microphones, headphones, and all necessary cables."
                rows={3}
                required
                spellCheck={false}
              />
              <span className="form-hint" style={{ marginTop: '0.25rem' }}>
                State participant count, host laptop connectivity, target budget, and monitoring preferences.
              </span>
            </div>

            {/* Authoritative Parameter Grid (5 Columns) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem', paddingTop: '0.25rem' }}>
              {/* Field 1: Target Budget */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="budget-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <DollarSign size={14} style={{ color: 'var(--text-secondary)' }} />
                  <span>Target Budget (USD)</span>
                </label>
                <input
                  id="budget-input"
                  type="number"
                  className="studio-input tabular-num"
                  value={budgetDollars}
                  onChange={(e) => setBudgetDollars(Number(e.target.value))}
                  min={50}
                  max={5000}
                  step={10}
                />
                <span className="form-hint tabular-num" style={{ fontFamily: 'var(--font-mono)' }}>
                  {(budgetDollars * 100).toLocaleString()} integer cents
                </span>
              </div>

              {/* Field 2: Participants */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="participants-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Users size={14} style={{ color: 'var(--text-secondary)' }} />
                  <span>Participants (Mics)</span>
                </label>
                <select
                  id="participants-select"
                  className="studio-select"
                  value={participants}
                  onChange={(e) => setParticipants(Number(e.target.value))}
                >
                  <option value={1}>1 Solo Creator (1 XLR)</option>
                  <option value={2}>2 Participants (Host + Co-Host)</option>
                  <option value={3}>3 Participants (Panel Setup)</option>
                  <option value={4}>4 Multi-Guest Ensemble</option>
                </select>
                <span className="form-hint">
                  Enforces interface XLR input capacity
                </span>
              </div>

              {/* Field 3: Host Laptop Port */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="laptop-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Laptop size={14} style={{ color: 'var(--text-secondary)' }} />
                  <span>Host Laptop Port</span>
                </label>
                <select
                  id="laptop-select"
                  className="studio-select"
                  value={laptopConnector}
                  onChange={(e) => setLaptopConnector(e.target.value)}
                >
                  <option value="usb-c">Native USB-C (Thunderbolt 3/4)</option>
                  <option value="usb-a">USB-A 3.0 Standard</option>
                  <option value="lightning">Lightning (Legacy iOS)</option>
                </select>
                <span className="form-hint">
                  Physical bus topology match
                </span>
              </div>

              {/* Field 4: Audio Monitoring */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="listening-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Headphones size={14} style={{ color: 'var(--text-secondary)' }} />
                  <span>Audio Monitoring</span>
                </label>
                <select
                  id="listening-select"
                  className="studio-select"
                  value={listeningRequirement}
                  onChange={(e) => setListeningRequirement(e.target.value)}
                >
                  <option value="independent_headphones">Independent Headphones (TRS)</option>
                  <option value="shared">Shared Splitter (Stereo 3.5mm)</option>
                  <option value="monitors">Active Studio Nearfield Monitors</option>
                </select>
                <span className="form-hint">
                  Dual headphone amp DAC required
                </span>
              </div>

              {/* Field 5: Recording Deadline */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="deadline-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Calendar size={14} style={{ color: 'var(--text-secondary)' }} />
                  <span>Recording Deadline</span>
                </label>
                <input
                  id="deadline-input"
                  type="date"
                  className="studio-input tabular-num"
                  value={deadlineDate}
                  onChange={(e) => setDeadlineDate(e.target.value)}
                />
                <span className="form-hint">
                  Used by Bryntum timeline scheduler
                </span>
              </div>
            </div>
          </div>

          {/* Action Execution Footer Bar */}
          <div className="card-footer">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <Cpu size={15} style={{ color: 'var(--status-emerald)' }} />
              <span>
                Deterministic solver tests <strong style={{ color: 'var(--text-primary)' }}>24 hardware SKUs</strong> against verified merchant inventory.
              </span>
            </div>

            <button
              type="submit"
              className="btn-primary btn-lg"
              disabled={isLoading || !promptText.trim()}
            >
              {isLoading ? (
                <>
                  <span className="spinner" />
                  <span>Extracting Requirements...</span>
                </>
              ) : (
                <>
                  <span>Extract Requirements &amp; Review</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Protocol Enforcement Alert Banner */}
        <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid var(--border-default)', backgroundColor: 'rgba(13, 17, 23, 0.4)' }}>
          <div className="callout callout-info">
            <ShieldCheck size={18} style={{ color: 'var(--status-emerald)', flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.2rem' }}>
                Hardware Constraint Enforcement Protocol (Rule R2):
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                A 2-person podcast setup strictly requires <strong style={{ color: 'var(--status-emerald)', fontFamily: 'var(--font-mono)' }}>&ge; 2 physical XLR microphone inputs</strong>, 2 balanced XLR cables, 2 dedicated headphone outputs, and a host bus match. If an interface provides only 1 XLR input, BundleGraph safely rejects the combination at the solver layer instead of presenting an unusable bundle.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Telemetry Diagnostic Stream Grid (3 Cards) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.875rem' }}>
        {/* Telemetry Card 1 */}
        <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            <span>Solver Stage</span>
            <span style={{ color: 'var(--status-emerald)', fontWeight: 600 }}>01_INGEST</span>
          </div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Graph Node Formulation
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
            Extracting typed constraints into solver adjacency matrix with continuous validation.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', marginTop: 'auto', paddingTop: '0.45rem', borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-muted)' }}>Parser: <strong style={{ color: 'var(--text-primary)' }}>RegexLexer+LLM</strong></span>
            <span style={{ color: 'var(--status-emerald)' }}>CONF: 0.994</span>
          </div>
        </div>

        {/* Telemetry Card 2 */}
        <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            <span>Constraint Rule</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>TOPOLOGY_P2</span>
          </div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Port Topology Matrix
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
            Matching host bus compatibility (Type-C to Type-C bus power minimum 5V 3A).
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', marginTop: 'auto', paddingTop: '0.45rem', borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-muted)' }}>Bus Power: <strong style={{ color: 'var(--text-primary)' }}>Compliant</strong></span>
            <span style={{ color: 'var(--text-primary)' }}>15W OK</span>
          </div>
        </div>

        {/* Telemetry Card 3 */}
        <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            <span>Settlement Assurance</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>PAYPAL_V2</span>
          </div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Atomic Escrow Pre-check
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
            Validating merchant capture routes against ${(budgetDollars).toFixed(2)} minor unit authorization.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', marginTop: 'auto', paddingTop: '0.45rem', borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-muted)' }}>Vault Status: <strong style={{ color: 'var(--text-primary)' }}>Ready</strong></span>
            <span style={{ color: 'var(--status-emerald)' }}>SANDBOX_LIVE</span>
          </div>
        </div>
      </div>
    </div>
  );
};
