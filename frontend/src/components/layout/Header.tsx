import React from 'react';
import { useDemo } from '../../store/demoStore';
import { Layers, RotateCcw, SlidersHorizontal, User, ShieldCheck } from 'lucide-react';

export const Header: React.FC = () => {
  const { presets, activePresetId, loadPreset, resetAll, isLoading, runtimeMode } = useDemo();

  return (
    <header className="main-header">
      {/* Top Brand & Status Tier */}
      <div className="header-top">
        <div className="brand-section">
          <div className="brand-logo-badge" title="BundleGraph Engine">
            <Layers size={16} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="brand-title">BundleGraph</span>
            <span className="badge badge-neutral">v1.0-RC</span>
          </div>
          <span className="brand-subtitle">
            Deterministic Hardware Graph &amp; Settlement Verification
          </span>
        </div>

        <div className="header-badges">
          <div className="badge badge-emerald">
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-emerald)',
                display: 'inline-block',
              }}
            />
            <span>PayPal Sandbox v2: Active</span>
          </div>

          <div className="badge badge-neutral">
            <span>Curated SKUs: <strong style={{ color: 'var(--text-primary)' }}>24 Items</strong></span>
          </div>

          <button
            type="button"
            className="reset-btn"
            onClick={resetAll}
            disabled={isLoading}
            title="Reset application state, clear cache and logs"
          >
            <RotateCcw size={13} />
            <span>Reset Session</span>
          </button>

          <div
            style={{
              width: '30px',
              height: '30px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Operator Session"
          >
            <User size={15} />
          </div>
        </div>
      </div>

      {/* Scenario Evaluation Bar */}
      <div className="preset-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div className="preset-title-group">
            <SlidersHorizontal size={13} style={{ color: 'var(--text-muted)' }} />
            <span>Test Scenarios:</span>
          </div>
          <div className="preset-buttons" role="group" aria-label="Evaluation test presets">
            {presets.map((p) => {
              const isActive = activePresetId === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  className={`preset-btn ${isActive ? 'active' : ''}`}
                  onClick={() => loadPreset(p)}
                  disabled={isLoading}
                  aria-pressed={isActive}
                  title={`Load scenario: ${p.description || p.name}`}
                >
                  <span>{p.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <span>
            Runtime:{' '}
            <strong style={{ color: runtimeMode === 'fixture' ? 'var(--status-amber)' : 'var(--status-emerald)' }}>
              {runtimeMode === 'fixture' ? 'FIXTURE_ONLY' : 'DEMO_API_CONNECTED'}
            </strong>
          </span>
          <span style={{ borderLeft: '1px solid var(--border-default)', paddingLeft: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <ShieldCheck size={14} style={{ color: 'var(--status-emerald)' }} />
            <span>Solver: <strong style={{ color: 'var(--status-emerald)' }}>DETERMINISTIC_PASS</strong></span>
          </span>
        </div>
      </div>
    </header>
  );
};
