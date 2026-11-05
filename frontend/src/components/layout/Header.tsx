import React from 'react';
import { ChevronDown, FlaskConical, LogOut, Moon, MoreHorizontal, RotateCcw, Sun, UserRound } from 'lucide-react';
import { useDemo } from '../../store/demoStore';
import { clearSession } from '../../auth/session';

export type Theme = 'light' | 'dark';

export const Header: React.FC<{ theme: Theme; onToggleTheme: () => void }> = ({ theme, onToggleTheme }) => {
  const { presets, activePresetId, loadPreset, resetAll, isLoading, runtimeMode } = useDemo();
  const reset = () => { if (window.confirm('Start a new setup? This clears the current browser workflow.')) void resetAll(); };
  return <header className="app-header">
    <div className="app-header__inner">
      <a className="brand-lockup" href="#/builder" aria-label="BundleGraph home">
        <span className="brand-mark" aria-hidden="true">BG</span>
        <span><strong className="brand-name">BundleGraph</strong><span className="brand-message">Build a setup that works together.</span></span>
      </a>
      <div className="header-actions">
        <span className={`environment-indicator ${runtimeMode === 'fixture' ? 'environment-indicator--fixture' : ''}`}><span aria-hidden="true" />{runtimeMode === 'fixture' ? 'Synthetic demo data' : 'Connected application'}</span>
        <button type="button" className="icon-button" onClick={onToggleTheme} aria-label={`Use ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}</button>
        <details className="header-menu">
          <summary><FlaskConical size={16} /> Demo tools <ChevronDown size={14} /></summary>
          <div className="header-menu__panel header-menu__panel--wide">
            <p className="menu-label">Labeled scenarios</p><p className="menu-copy">These replace the current browser draft and never represent live inventory.</p>
            <div className="scenario-actions">{presets.map((preset) => <button key={preset.id} type="button" className={`scenario-button ${activePresetId === preset.id ? 'is-active' : ''}`} onClick={() => void loadPreset(preset)} disabled={isLoading}>{preset.name}</button>)}</div>
            <div className="menu-section"><p className="menu-label">Developer details</p><p className="menu-copy">Runtime: {runtimeMode}. Provider and schema diagnostics remain server-controlled.</p></div>
          </div>
        </details>
        <details className="header-menu">
          <summary aria-label="Account menu"><UserRound size={17} /><ChevronDown size={14} /></summary>
          <div className="header-menu__panel"><p className="menu-label">Browser session</p><p className="menu-copy">Authentication and ownership are enforced by the backend.</p>{runtimeMode === 'authoritative' && <button type="button" className="menu-action" onClick={clearSession}><LogOut size={15} /> Sign out</button>}</div>
        </details>
        <details className="header-menu">
          <summary aria-label="More options"><MoreHorizontal size={18} /></summary>
          <div className="header-menu__panel"><button type="button" className="menu-action" onClick={reset} disabled={isLoading}><RotateCcw size={15} /> Start a new setup</button></div>
        </details>
      </div>
    </div>
  </header>;
};
