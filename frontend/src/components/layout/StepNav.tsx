import React from 'react';
import { useDemo } from '../../store/demoStore';
import type { ScreenStep } from '../../types/bundlegraph';
import { Terminal, CheckSquare, GitCompare, Lock, Activity } from 'lucide-react';

interface StepItem {
  id: ScreenStep;
  label: string;
  number: number;
  icon: React.ComponentType<{ size?: number; style?: React.CSSProperties; className?: string }>;
}

const STEPS: StepItem[] = [
  { id: 'builder', label: 'Request Builder', number: 1, icon: Terminal },
  { id: 'review', label: 'Requirements Review', number: 2, icon: CheckSquare },
  { id: 'comparison', label: 'Comparison & Graph', number: 3, icon: GitCompare },
  { id: 'approval', label: 'Plan Authorization', number: 4, icon: Lock },
  { id: 'execution', label: 'Execution & Recovery', number: 5, icon: Activity },
];

export const StepNav: React.FC = () => {
  const { currentStep, setStep } = useDemo();

  return (
    <div style={{ height: '44px', width: '100%', backgroundColor: '#000000', borderBottom: '1px solid #222222', padding: '0 1.25rem' }}>
      <nav className="step-nav" style={{ height: '100%', padding: 0, borderBottom: 'none', gap: '0.25rem' }} aria-label="Demo workflow navigation">
        {STEPS.map((step) => {
          const isActive = currentStep === step.id;
          const IconComponent = step.icon;

          return (
            <button
              key={step.id}
              type="button"
              className={`step-tab ${isActive ? 'active' : ''}`}
              onClick={() => setStep(step.id)}
              aria-current={isActive ? 'step' : undefined}
              style={{
                height: '100%',
                padding: '0 1rem',
                borderBottom: isActive ? '2px solid #ffffff' : '2px solid transparent',
              }}
            >
              <span
                style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '2px',
                  backgroundColor: isActive ? '#000000' : '#141414',
                  color: isActive ? '#ffffff' : '#888888',
                  border: `1px solid ${isActive ? '#000000' : '#222222'}`,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.625rem',
                  fontWeight: 700,
                }}
              >
                {step.number}
              </span>
              <IconComponent size={13} style={{ opacity: isActive ? 1 : 0.6 }} />
              <span style={{ fontWeight: isActive ? 600 : 500 }}>{step.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
