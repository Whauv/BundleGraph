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
  Cpu
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
    <div className="screen-container" style={{ gap: '1rem' }}>
      {/* Pipeline Breadcrumb Ribbon */}
      <div
        style={{
          width: '100%',
          backgroundColor: '#0a0a0a',
          border: '1px solid #222222',
          padding: '0.5rem 0.875rem',
          borderRadius: '2px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.25rem 0.6rem',
              backgroundColor: '#141414',
              border: '1px solid #333333',
              borderRadius: '2px',
              color: '#ffffff',
              fontWeight: 600,
            }}
          >
            <span
              style={{
                width: '16px',
                height: '16px',
                borderRadius: '2px',
                backgroundColor: '#ffffff',
                color: '#000000',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.625rem',
              }}
            >
              1
            </span>
            <span>Request Builder</span>
          </span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>2. Requirements Review</span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>3. Comparison &amp; Graph</span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>4. Plan Authorization</span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>5. Execution &amp; Recovery</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.625rem' }}>
          <span style={{ color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Active Model:</span>
          <span style={{ padding: '0.15rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #222222', color: '#ffffff' }}>
            gemini-1.5-pro-deterministic
          </span>
        </div>
      </div>

      {/* Main Workspace Card */}
      <div className="studio-card">
        {/* Specification Header */}
        <div className="card-header">
          <div className="card-title-group">
            <h1 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '2px',
                  backgroundColor: '#161616',
                  border: '1px solid #333333',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: '#ffffff',
                }}
              >
                &gt;_
              </span>
              <span>Podcast Studio Setup Specification</span>
            </h1>
            <p className="card-subtitle">
              Input natural language audio requirements. BundleGraph extracts hardware constraints and evaluates deterministic topology against verified merchant stock.
            </p>
          </div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.25rem 0.6rem',
              borderRadius: '2px',
              backgroundColor: '#051108',
              border: '1px solid rgba(0, 229, 117, 0.4)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              color: '#00e575',
              fontWeight: 600,
            }}
          >
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#00e575' }} />
            <span>Deterministic Solver v2.4</span>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Natural Language Prompt Area */}
            <div className="form-group" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <label htmlFor="prompt-input" className="form-label" style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.8125rem' }}>
                  Natural Language Studio Request
                </label>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#666666' }}>
                  Input audio spec or requirements prompt
                </span>
              </div>
              <div style={{ position: 'relative' }}>
                <textarea
                  id="prompt-input"
                  className="studio-textarea"
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  placeholder="I want to start a 2-person podcast with my USB-C laptop. Budget is $600. We need 2 microphones, headphones, and all necessary cables."
                  rows={3}
                  required
                  spellCheck={false}
                  style={{ paddingBottom: '1.75rem' }}
                />
                <div style={{ position: 'absolute', bottom: '8px', right: '10px', pointerEvents: 'none' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#555555' }}>
                    {promptText.length} chars
                  </span>
                </div>
              </div>
              <span className="form-hint" style={{ marginTop: '0.25rem' }}>
                Specify participant count, host laptop connectivity, target budget, and monitoring preferences.
              </span>
            </div>

            {/* Authoritative Parameter Grid (5 Columns) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', paddingTop: '0.25rem' }}>
              {/* Field 1: Target Budget */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="budget-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <DollarSign size={13} style={{ color: '#888888' }} />
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
                <span className="form-hint tabular-num" style={{ fontFamily: 'var(--font-mono)', color: '#666666' }}>
                  {(budgetDollars * 100).toLocaleString()} integer cents
                </span>
              </div>

              {/* Field 2: Participants */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="participants-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Users size={13} style={{ color: '#888888' }} />
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
                <span className="form-hint" style={{ fontFamily: 'var(--font-mono)', color: '#666666' }}>
                  Enforces interface XLR input capacity
                </span>
              </div>

              {/* Field 3: Host Laptop Port */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="laptop-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Laptop size={13} style={{ color: '#888888' }} />
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
                <span className="form-hint" style={{ fontFamily: 'var(--font-mono)', color: '#666666' }}>
                  Physical bus topology check
                </span>
              </div>

              {/* Field 4: Audio Monitoring */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="listening-select" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Headphones size={13} style={{ color: '#888888' }} />
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
                <span className="form-hint" style={{ fontFamily: 'var(--font-mono)', color: '#666666' }}>
                  Dual headphone amp DAC required
                </span>
              </div>

              {/* Field 5: Recording Deadline */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="deadline-input" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Calendar size={13} style={{ color: '#888888' }} />
                  <span>Recording Deadline</span>
                </label>
                <input
                  id="deadline-input"
                  type="date"
                  className="studio-input tabular-num"
                  value={deadlineDate}
                  onChange={(e) => setDeadlineDate(e.target.value)}
                />
                <span className="form-hint" style={{ fontFamily: 'var(--font-mono)', color: '#666666' }}>
                  Used by Bryntum timeline scheduler
                </span>
              </div>
            </div>
          </div>

          {/* Action Execution Bar */}
          <div className="card-footer" style={{ borderTop: '1px solid #222222', backgroundColor: '#050505', padding: '1rem 1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#888888' }}>
              <Cpu size={15} style={{ color: '#00e575' }} />
              <span>
                Deterministic validation evaluates <strong style={{ color: '#ffffff' }}>24 products</strong> and <strong style={{ color: '#ffffff' }}>15 synthetic offers</strong>.
              </span>
            </div>
            <button
              type="submit"
              className="btn-primary"
              disabled={isLoading || !promptText.trim()}
              style={{
                padding: '0.55rem 1.25rem',
                fontSize: '0.875rem',
                backgroundColor: '#ffffff',
                color: '#000000',
              }}
            >
              {isLoading ? (
                <>
                  <span className="spinner" />
                  <span>Compiling Topology...</span>
                </>
              ) : (
                <>
                  <span>Extract Requirements &amp; Review</span>
                  <ArrowRight size={15} />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Protocol Enforcement Alert Banner */}
        <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid #222222', backgroundColor: '#070707' }}>
          <div
            style={{
              padding: '0.875rem 1rem',
              backgroundColor: '#0a0a0a',
              border: '1px solid #282828',
              borderRadius: '2px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.75rem',
            }}
          >
            <ShieldCheck size={18} style={{ color: '#00e575', flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', fontWeight: 700, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.2rem' }}>
                Hardware Constraint Protocol (Rule R2):
              </div>
              <p style={{ fontSize: '0.8125rem', color: '#888888', lineHeight: 1.5, margin: 0 }}>
                A 2-person podcast setup strictly requires <strong style={{ color: '#00e575', fontFamily: 'var(--font-mono)' }}>&ge; 2 physical XLR microphone inputs</strong>, 2 balanced XLR cables, 2 dedicated headphone outputs, and a host bus match. If an interface provides only 1 XLR input, BundleGraph safely rejects the combination at the solver layer instead of presenting an unusable bundle.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Telemetry Diagnostic Stream Grid (3 Cards) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
        {/* Telemetry Card 1 */}
        <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.625rem', textTransform: 'uppercase', color: '#666666' }}>
            <span>Graph Solver Stage</span>
            <span style={{ color: '#00e575' }}>01_INGEST</span>
          </div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>
            Graph Node Formulation
          </div>
          <p style={{ fontSize: '0.75rem', color: '#888888', margin: '0.2rem 0' }}>
            Extracting typed constraints into solver adjacency matrix with continuous validation.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', marginTop: '0.25rem', borderTop: '1px solid #1e1e1e', paddingTop: '0.35rem' }}>
            <span style={{ color: '#666666' }}>Parser: <strong style={{ color: '#ffffff' }}>RegexLexer+LLM</strong></span>
            <span style={{ color: '#00e575' }}>CONF: 0.994</span>
          </div>
        </div>

        {/* Telemetry Card 2 */}
        <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.625rem', textTransform: 'uppercase', color: '#666666' }}>
            <span>Constraint Rule</span>
            <span style={{ color: '#ffffff' }}>TOPOLOGY_P2</span>
          </div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>
            Port Topology Matrix
          </div>
          <p style={{ fontSize: '0.75rem', color: '#888888', margin: '0.2rem 0' }}>
            Matching host bus compatibility (Type-C to Type-C bus power minimum 5V 3A).
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', marginTop: '0.25rem', borderTop: '1px solid #1e1e1e', paddingTop: '0.35rem' }}>
            <span style={{ color: '#666666' }}>Bus Power: <strong style={{ color: '#ffffff' }}>Compliant</strong></span>
            <span style={{ color: '#ffffff' }}>15W OK</span>
          </div>
        </div>

        {/* Telemetry Card 3 */}
        <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.625rem', textTransform: 'uppercase', color: '#666666' }}>
            <span>Settlement Assurance</span>
            <span style={{ color: '#ffffff' }}>PAYPAL_V2</span>
          </div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>
            Atomic Escrow Pre-check
          </div>
          <p style={{ fontSize: '0.75rem', color: '#888888', margin: '0.2rem 0' }}>
            Validating merchant capture routes against ${(budgetDollars).toFixed(2)} minor unit authorization.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', marginTop: '0.25rem', borderTop: '1px solid #1e1e1e', paddingTop: '0.35rem' }}>
            <span style={{ color: '#666666' }}>Vault Status: <strong style={{ color: '#ffffff' }}>Ready</strong></span>
            <span style={{ color: '#00e575' }}>SANDBOX_LIVE</span>
          </div>
        </div>
      </div>
    </div>
  );
};
