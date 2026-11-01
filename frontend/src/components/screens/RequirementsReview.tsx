import React, { useState } from 'react';
import { useDemo } from '../../store/demoStore';
import { 
  AlertTriangle, 
  ArrowLeft, 
  ArrowRight, 
  FileCheck, 
  SlidersHorizontal, 
  ShieldCheck, 
  Code, 
  ChevronDown, 
  ChevronUp,
  CheckCircle2,
  CheckSquare
} from 'lucide-react';

export const RequirementsReview: React.FC = () => {
  const {
    interpretation,
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
    confirmRequirements,
    setStep,
    isLoading,
  } = useDemo();

  const [showJsonAst, setShowJsonAst] = useState(false);
  const [operatorConfirmed, setOperatorConfirmed] = useState(true);

  return (
    <div className="screen-container">
      {/* Modern Screen Header */}
      <div className="screen-header">
        <div className="screen-header-left">
          <div className="screen-header-icon">
            <CheckSquare size={20} />
          </div>
          <div>
            <h1 className="screen-title">Stage 2: Requirements Verification &amp; Constraint Review</h1>
            <p className="screen-description">
              Verify interpreted constraints before submitting to the deterministic solver. Adjust authoritative values below as needed.
            </p>
          </div>
        </div>

        <div className="screen-header-meta">
          <span className="badge badge-emerald">
            <ShieldCheck size={12} />
            <span>Pydantic v2.8 Validated</span>
          </span>
          <span className="badge badge-neutral">
            <span>Mode: {interpretation?.provider_mode || 'Heuristic Fixture'}</span>
          </span>
        </div>
      </div>

      {/* Main Workspace Card */}
      <div className="studio-card">
        <div className="card-header">
          <div className="card-title-group">
            <h2 className="card-title">Interpreted Constraints vs. Operator Overrides</h2>
            <p className="card-subtitle">
              The AI interpretation remains draft until confirmed. Validate hardware requirements, port bus type, and upper budget limits.
            </p>
          </div>
          <div className="badge badge-neutral">
            <span>Rule Set: R2_STRICT_PODCAST</span>
          </div>
        </div>

        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {interpretation?.missing_information && interpretation.missing_information.length > 0 && (
            <div className="callout callout-warning">
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--status-amber)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  Missing Constraint Data in Natural Language Request:
                </strong>
                <p style={{ fontSize: '0.8125rem', marginBottom: '0.4rem', color: 'var(--text-primary)' }}>
                  The natural language prompt lacked specific evidence for several essential parameters:
                </p>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8125rem', display: 'flex', flexDirection: 'column', gap: '0.25rem', color: 'var(--text-secondary)' }}>
                  {interpretation.clarification_questions.map((q, idx) => (
                    <li key={idx}>{q}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Two-Column Split Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
            {/* Left Column: Interpreted Request Evidence */}
            <div className="surface-panel" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'rgba(11, 16, 29, 0.7)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileCheck size={16} style={{ color: 'var(--text-primary)' }} />
                  <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Interpreted Request Evidence
                  </span>
                </div>
                <span className="badge badge-neutral">
                  AST_SRC_01
                </span>
              </div>

              <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                <div className="kv-row" style={{ padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-xs)' }}>
                  <span className="kv-key">Extraction Provider:</span>
                  <span className="badge badge-neutral">
                    {interpretation?.provider_mode || 'heuristic_fixture'}
                  </span>
                </div>

                <div className="kv-row" style={{ padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-xs)' }}>
                  <span className="kv-key">Detected Use Case:</span>
                  <span className="kv-val">
                    {interpretation?.draft.use_case || `${participants}-person podcast`}
                  </span>
                </div>

                <div className="kv-row" style={{ padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-xs)' }}>
                  <span className="kv-key">Microphone Count:</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="kv-val">{participants} Units</span>
                    <span className="badge badge-emerald">
                      <CheckCircle2 size={11} /> Verified
                    </span>
                  </div>
                </div>

                <div className="kv-row" style={{ padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-xs)' }}>
                  <span className="kv-key">Host Connectivity:</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span className="badge badge-neutral">{laptopConnector.toUpperCase()}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>(Bus Ready)</span>
                  </div>
                </div>

                <div className="kv-row" style={{ padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-xs)' }}>
                  <span className="kv-key">Currency Standard:</span>
                  <span className="badge badge-neutral">
                    USD (Integer Cents)
                  </span>
                </div>

                <div className="kv-row" style={{ padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-app)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-xs)' }}>
                  <span className="kv-key">Confidence Score:</span>
                  <span className="badge badge-emerald">
                    Deterministic Rule (1.00)
                  </span>
                </div>
              </div>

              {/* Collapsible AST Box */}
              <div style={{ borderTop: '1px solid var(--border-default)', marginTop: 'auto' }}>
                <button
                  type="button"
                  onClick={() => setShowJsonAst(!showJsonAst)}
                  style={{
                    width: '100%',
                    padding: '0.625rem 1rem',
                    backgroundColor: 'rgba(11, 16, 29, 0.4)',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                    <Code size={13} />
                    <span>Raw Pydantic AST JSON</span>
                  </span>
                  {showJsonAst ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                {showJsonAst && (
                  <pre
                    style={{
                      padding: '1rem',
                      backgroundColor: 'var(--bg-app)',
                      borderTop: '1px solid var(--border-default)',
                      color: '#34d399',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                      overflowX: 'auto',
                      maxHeight: '220px',
                      margin: 0,
                    }}
                  >
                    {JSON.stringify(interpretation?.draft || {
                      use_case: `${participants}-person podcast`,
                      budget: { amount_minor: budgetDollars * 100, currency: 'USD' },
                      participants,
                      laptop_connector: laptopConnector,
                      listening_requirement: listeningRequirement,
                      deadline: deadlineDate
                    }, null, 2)}
                  </pre>
                )}
              </div>
            </div>

            {/* Right Column: Authoritative Constraint Overrides */}
            <div className="surface-panel" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'rgba(11, 16, 29, 0.7)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <SlidersHorizontal size={16} style={{ color: 'var(--status-emerald)' }} />
                  <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Authoritative Solver Constraints
                  </span>
                </div>
                <span className="badge badge-emerald">
                  CONFIRM_SCHEMA
                </span>
              </div>

              <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Budget Upper Bound (USD):</label>
                  <input
                    type="number"
                    className="studio-input tabular-num"
                    value={budgetDollars}
                    onChange={(e) => setBudgetDollars(Number(e.target.value))}
                    min={100}
                    max={5000}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Required Microphone Inputs (Rule R2):</label>
                  <select
                    className="studio-select"
                    value={participants}
                    onChange={(e) => setParticipants(Number(e.target.value))}
                  >
                    <option value={1}>1 Participant (1 XLR Input)</option>
                    <option value={2}>2 Participants (2 XLR Inputs - Strict)</option>
                    <option value={3}>3 Participants (3 XLR Inputs)</option>
                    <option value={4}>4 Participants (4 XLR Inputs)</option>
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Host Laptop Port Bus:</label>
                  <select
                    className="studio-select"
                    value={laptopConnector}
                    onChange={(e) => setLaptopConnector(e.target.value)}
                  >
                    <option value="usb-c">Native USB-C (Thunderbolt 3/4)</option>
                    <option value="usb-a">USB-A 3.0 Standard</option>
                    <option value="lightning">Lightning (Legacy iOS)</option>
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Monitoring Output Setup:</label>
                  <select
                    className="studio-select"
                    value={listeningRequirement}
                    onChange={(e) => setListeningRequirement(e.target.value)}
                  >
                    <option value="independent_headphones">Independent Headphones (TRS)</option>
                    <option value="shared">Shared Splitter (Stereo 3.5mm)</option>
                    <option value="monitors">Active Studio Nearfield Monitors</option>
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Delivery Deadline:</label>
                  <input
                    type="date"
                    className="studio-input tabular-num"
                    value={deadlineDate}
                    onChange={(e) => setDeadlineDate(e.target.value)}
                  />
                </div>
              </div>

              {/* Confirmation Checkbox */}
              <div style={{ padding: '0.875rem 1rem', borderTop: '1px solid var(--border-default)', backgroundColor: 'rgba(11, 16, 29, 0.4)', marginTop: 'auto' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer', fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                  <input
                    type="checkbox"
                    checked={operatorConfirmed}
                    onChange={(e) => setOperatorConfirmed(e.target.checked)}
                    style={{ width: '16px', height: '16px', accentColor: '#238636', cursor: 'pointer' }}
                  />
                  <span style={{ fontWeight: 500 }}>I confirm verified hardware requirements are authoritative.</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Navigation Bar */}
        <div className="card-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setStep('builder')}
          >
            <ArrowLeft size={16} />
            <span>Back to Request Builder</span>
          </button>

          <button
            type="button"
            className="btn-primary btn-lg"
            onClick={confirmRequirements}
            disabled={isLoading || !operatorConfirmed}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                <span>Running Compatibility Solver...</span>
              </>
            ) : (
              <>
                <span>Confirm Constraints &amp; Compile Bundles</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
