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
  CheckCircle2
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
          <span style={{ color: '#666666', cursor: 'pointer' }} onClick={() => setStep('builder')}>1. Request Builder</span>
          <span style={{ color: '#333333' }}>/</span>
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
              2
            </span>
            <span>Requirements Review</span>
          </span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>3. Comparison &amp; Graph</span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>4. Plan Authorization</span>
          <span style={{ color: '#333333' }}>/</span>
          <span style={{ color: '#666666' }}>5. Execution &amp; Recovery</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.625rem' }}>
          <span style={{ color: '#666666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Schema Status:</span>
          <span style={{ padding: '0.15rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #222222', color: '#00e575', fontWeight: 600 }}>
            PYDANTIC_VALIDATED
          </span>
        </div>
      </div>

      {/* Main Workspace Card */}
      <div className="studio-card">
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
                ✓
              </span>
              <span>Requirements Verification &amp; Constraint Confirmation</span>
            </h1>
            <p className="card-subtitle">
              Verify interpreted constraints before feeding them into the deterministic solver. AI interpretations remain draft until confirmed by the operator.
            </p>
          </div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.25rem 0.6rem',
              borderRadius: '2px',
              backgroundColor: '#111111',
              border: '1px solid #282828',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              color: '#ffffff',
            }}
          >
            <ShieldCheck size={14} style={{ color: '#00e575' }} />
            <span>Pydantic Draft Schema</span>
            <span style={{ color: '#888888', fontSize: '0.625rem' }}>• v2.8.2</span>
          </div>
        </div>

        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {interpretation?.missing_information && interpretation.missing_information.length > 0 && (
            <div className="callout callout-warning">
              <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ display: 'block', marginBottom: '0.2rem', color: '#fabc45', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  Missing Constraint Data in Natural Language Request:
                </strong>
                <p style={{ fontSize: '0.8125rem', marginBottom: '0.4rem', color: '#ffffff' }}>
                  The natural language prompt lacked specific evidence for several essential parameters:
                </p>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8125rem', display: 'flex', flexDirection: 'column', gap: '0.2rem', color: '#888888' }}>
                  {interpretation.clarification_questions.map((q, idx) => (
                    <li key={idx}>{q}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Two-Column Split Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
            {/* Left Column: Interpreted Request Evidence */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div
                style={{
                  backgroundColor: '#080808',
                  border: '1px solid #222222',
                  borderRadius: '2px',
                  overflow: 'hidden',
                }}
              >
                <div style={{ padding: '0.6rem 0.875rem', borderBottom: '1px solid #222222', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <FileCheck size={14} style={{ color: '#ffffff' }} />
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>
                      Interpreted Request Evidence
                    </span>
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#888888', textTransform: 'uppercase' }}>
                    AST_SRC_01
                  </span>
                </div>

                <div style={{ padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.65rem', backgroundColor: '#050505', border: '1px solid #222222', borderRadius: '2px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#888888' }}>Extraction Provider:</span>
                    <span style={{ padding: '0.15rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #282828', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#ffffff' }}>
                      {interpretation?.provider_mode || 'heuristic_fixture'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.65rem', backgroundColor: '#050505', border: '1px solid #222222', borderRadius: '2px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#888888' }}>Detected Use Case:</span>
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>
                      {interpretation?.draft.use_case || `${participants}-person podcast`}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.65rem', backgroundColor: '#050505', border: '1px solid #222222', borderRadius: '2px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#888888' }}>Microphone Count:</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>{participants} Units</span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem', padding: '0.1rem 0.35rem', borderRadius: '2px', backgroundColor: '#000000', border: '1px solid #00e575', color: '#00e575', fontFamily: 'var(--font-mono)', fontSize: '0.625rem' }}>
                        <CheckCircle2 size={10} /> Verified
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.65rem', backgroundColor: '#050505', border: '1px solid #222222', borderRadius: '2px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#888888' }}>Host Connectivity:</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>{laptopConnector.toUpperCase()}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#888888' }}>(Host Bus Ready)</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.65rem', backgroundColor: '#050505', border: '1px solid #222222', borderRadius: '2px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#888888' }}>Currency Standard:</span>
                    <span style={{ padding: '0.15rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #282828', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#ffffff' }}>
                      USD (Integer Minor Units)
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.65rem', backgroundColor: '#050505', border: '1px solid #222222', borderRadius: '2px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#888888' }}>Interpretation Confidence:</span>
                    <span style={{ padding: '0.15rem 0.4rem', borderRadius: '2px', backgroundColor: '#111111', border: '1px solid #333333', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#ffffff' }}>
                      Deterministic Rule Set (1.00)
                    </span>
                  </div>
                </div>

                {/* Collapsible AST Box */}
                <div style={{ borderTop: '1px solid #222222' }}>
                  <button
                    type="button"
                    onClick={() => setShowJsonAst(!showJsonAst)}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.875rem',
                      backgroundColor: '#0a0a0a',
                      border: 'none',
                      color: '#888888',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.6875rem',
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Code size={12} />
                      <span>Raw Pydantic AST JSON</span>
                    </span>
                    {showJsonAst ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>
                  {showJsonAst && (
                    <pre
                      style={{
                        padding: '0.875rem',
                        backgroundColor: '#050505',
                        borderTop: '1px solid #1e1e1e',
                        color: '#34d399',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.6875rem',
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
            </div>

            {/* Right Column: Interactive Requirement Override Form */}
            <div
              style={{
                backgroundColor: '#080808',
                border: '1px solid #222222',
                borderRadius: '2px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ padding: '0.6rem 0.875rem', borderBottom: '1px solid #222222', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <SlidersHorizontal size={14} style={{ color: '#00e575' }} />
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>
                      Authoritative Solver Constraints
                    </span>
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: '#888888', textTransform: 'uppercase' }}>
                    CONFIRM_SCHEMA
                  </span>
                </div>

                <div style={{ padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label" style={{ fontSize: '0.75rem', color: '#888888' }}>Budget Upper Bound (USD):</label>
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
                    <label className="form-label" style={{ fontSize: '0.75rem', color: '#888888' }}>Required Microphone Inputs (Rule R2):</label>
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
                    <label className="form-label" style={{ fontSize: '0.75rem', color: '#888888' }}>Host Laptop Port Bus:</label>
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
                    <label className="form-label" style={{ fontSize: '0.75rem', color: '#888888' }}>Monitoring Output Setup:</label>
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
                    <label className="form-label" style={{ fontSize: '0.75rem', color: '#888888' }}>Delivery Deadline:</label>
                    <input
                      type="date"
                      className="studio-input tabular-num"
                      value={deadlineDate}
                      onChange={(e) => setDeadlineDate(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Confirmation Checkbox */}
              <div style={{ padding: '0.75rem 0.875rem', borderTop: '1px solid #1e1e1e', backgroundColor: '#050505' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.75rem', color: '#cccccc' }}>
                  <input
                    type="checkbox"
                    checked={operatorConfirmed}
                    onChange={(e) => setOperatorConfirmed(e.target.checked)}
                    style={{ accentColor: '#00e575' }}
                  />
                  <span>I confirm verified hardware requirements are authoritative.</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="card-footer" style={{ borderTop: '1px solid #222222', backgroundColor: '#050505', padding: '1rem 1.25rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setStep('builder')}
          >
            <ArrowLeft size={14} />
            <span>Back to Request Prompt</span>
          </button>

          <button
            type="button"
            className="btn-primary"
            onClick={confirmRequirements}
            disabled={isLoading || !operatorConfirmed}
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
                <span>Running Compatibility Solver...</span>
              </>
            ) : (
              <>
                <span>Confirm Constraints &amp; Compile Bundles</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
