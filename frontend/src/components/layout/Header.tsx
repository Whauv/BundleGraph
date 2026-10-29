import React from 'react';
import { useDemo } from '../../store/demoStore';
import { Layers, RotateCcw, SlidersHorizontal, User } from 'lucide-react';

export const Header: React.FC = () => {
  const { presets, activePresetId, loadPreset, resetAll, isLoading, runtimeMode, runtimeLabel } = useDemo();

  return (
    <header className="main-header" style={{ padding: 0, gap: 0, borderBottom: 'none' }}>
      {/* Top Brand Tier */}
      <div
        className="header-top"
        style={{
          height: '56px',
          padding: '0 1.25rem',
          borderBottom: '1px solid #222222',
          backgroundColor: '#000000',
        }}
      >
        <div className="brand-section">
          <div className="brand-logo-badge" style={{ background: '#111111', borderColor: '#2a2a2a', color: '#ffffff' }} title="BundleGraph Engine">
            <Layers size={15} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.0625rem', fontWeight: 700, letterSpacing: '-0.02em', color: '#ffffff' }}>
              BundleGraph
            </span>
            <span
              style={{
                padding: '0.1rem 0.4rem',
                borderRadius: '2px',
                backgroundColor: '#111111',
                border: '1px solid #2a2a2a',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.6875rem',
                color: '#ffffff',
                fontWeight: 600,
              }}
            >
              v1.0-RC
            </span>
          </div>
          <span className="brand-subtitle" style={{ color: '#888888', borderColor: '#222222', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
            Evidence-Backed Hardware Graph &amp; PayPal Settlement Engine
          </span>
        </div>

        <div className="header-badges" style={{ gap: '0.75rem' }}>
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
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: '#00e575',
                display: 'inline-block',
                boxShadow: '0 0 8px #00e575',
              }}
            />
            <span>{runtimeLabel}</span>
          </div>

          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.25rem 0.6rem',
              borderRadius: '2px',
              backgroundColor: '#0a0a0a',
              border: '1px solid #222222',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              color: '#888888',
            }}
          >
            <span>Curated Fixtures: <strong style={{ color: '#ffffff' }}>24 SKUs</strong></span>
          </div>

          <button
            type="button"
            className="reset-btn"
            onClick={resetAll}
            disabled={isLoading}
            title="Reset application state, clear cache and logs"
          >
            <RotateCcw size={12} />
            <span>Reset Session</span>
          </button>

          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '2px',
              backgroundColor: '#ffffff',
              color: '#000000',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <User size={15} />
          </div>
        </div>
      </div>

      {/* Evaluation Scenarios Bar */}
      <div className="preset-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div className="preset-title-group" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <SlidersHorizontal size={12} style={{ color: '#666666' }} />
            <span>Scenarios:</span>
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
                >
                  <span>{p.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#666666' }}>
          <span>
            Runtime:{' '}
            <strong style={{ color: runtimeMode === 'fixture' ? '#fabc45' : '#00e575' }}>
              {runtimeMode === 'fixture' ? 'FIXTURE_ONLY' : 'DEMO_API_CONNECTED'}
            </strong>
          </span>
        </div>
      </div>
    </header>
  );
};
